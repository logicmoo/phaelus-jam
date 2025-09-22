
    import os
    import asyncio
    import json
    import threading
    import time
    import glob
    from typing import Dict, Any
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
    from fastapi.responses import HTMLResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    import mido

    from phaelusjam.player import PlayerState
    from phaelusjam.composer import LLMComposer
    from phaelusjam.engine import PlaybackEngine
    from phaelusjam import metrics as _metrics

    app = FastAPI()
    app.mount(
        "/static",
        StaticFiles(directory=str((__file__).rsplit("/", 1)[0] + "/static")),
        name="static",
    )

    state = PlayerState()
    composer = LLMComposer(channel=0)
    engine: PlaybackEngine | None = None
    selected_in: str | None = None
    selected_out: str | None = None

    FILE_STATUSES: Dict[str, Dict[str, str]] = {}
    FILE_HASHES: Dict[str, str] = {}
    WS_CLIENTS: set[WebSocket] = set()
    CURRENT_SELECTION: list[str] = []
    LAST_COMBINED: Dict[str, Any] = {"version": 1, "presets": [], "boosters": []}

    def list_ports() -> tuple[list[str], list[str]]:
        return mido.get_input_names(), mido.get_output_names()

    def _presets_dir() -> str:
        return str(__file__).rsplit("/", 1)[0] + "/presets"

    def _read_json(path: str) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _file_sha1(path: str) -> str:
        try:
            import hashlib
            h = hashlib.sha1()
            with open(path, 'rb') as f:
                for b in iter(lambda: f.read(8192), b""):
                    h.update(b)
            return h.hexdigest()
        except Exception:
            return ""

    def _status_for(name: str, default: str = 'unloaded', message: str = '') -> Dict[str, str]:
        return FILE_STATUSES.get(name, {'status': default, 'message': message})

    async def send_state(ws: WebSocket) -> None:
        data = {
            "type": "state",
            "bpm": round(state.bpm_guess, 1),
            "held": sorted(list(state.held_notes)),
            "recent_notes": state.recent_notes[-16:],
            "recent_velocities": state.recent_velocities[-16:],
            "midi_in_connected": bool(selected_in),
            "midi_out_connected": bool(selected_out),
            "engine_running": bool(engine is not None),
            "ws_clients": len(WS_CLIENTS),
            "llm_enabled": bool(getattr(composer.adapter, "client", None))
            and (os.getenv("USE_LLM", "1") not in ("0", "false", "False")),
            "compact_metrics": {
                "llm_req": _metrics.snapshot().get("llm_requests", 0),
                "tok_in": _metrics.snapshot().get("prompt_tokens", 0),
                "tok_out": _metrics.snapshot().get("completion_tokens", 0),
                "midi_in": _metrics.snapshot().get("midi_in_events", 0),
                "midi_out": _metrics.snapshot().get("midi_out_events", 0),
                "late_pct": round(_metrics.snapshot().get("composer_late_ratio", 0.0) * 100, 1),
            },
        }
        await ws.send_text(json.dumps(data))

    @app.get("/", response_class=HTMLResponse)
    async def root_page() -> FileResponse:
        return FileResponse(str(__file__).rsplit("/", 1)[0] + "/templates/index.html")

    @app.get("/api/ports")
    async def api_ports() -> Dict[str, Any]:
        ins, outs = list_ports()
        return {"inputs": ins, "outputs": outs, "selected_in": selected_in, "selected_out": selected_out}

    @app.post("/api/select")
    async def api_select(in_name: str, out_name: str) -> Dict[str, Any]:
        nonlocal selected_in, selected_out, engine
        selected_in, selected_out = in_name, out_name
        if engine:
            engine.stop()
            engine = None
        engine = PlaybackEngine(mido.open_output(out_name))
        engine.start()
        return {"ok": True}

    @app.post("/api/params")
    async def api_params(
        role_swap: bool | None = None,
        density: int | None = None,
        model: str | None = None,
        preset_text: str | None = None,
        append_text: str | None = None,
        preset_name: str | None = None,
        boosters: str | None = None,
        use_llm: bool | None = None,
    ) -> Dict[str, Any]:
        if role_swap is not None:
            os.environ["ROLE_SWAP"] = "1" if role_swap else "0"
        if density is not None:
            os.environ["JAM_DENSITY"] = str(max(1, min(5, density)))
        if model is not None:
            os.environ["LLM_MODEL"] = model
        if use_llm is not None:
            os.environ["USE_LLM"] = "1" if use_llm else "0"
        # Build final preset from files selection + overrides
        final_preset = preset_text or ""
        try:
            if preset_name:
                with open(_presets_dir() + "/defaults.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                match = next((p for p in data.get("presets", []) if p.get("name") == preset_name), None)
                if match:
                    final_preset = (match.get("text", "") + ("
" + final_preset if final_preset else "")).strip()
            if boosters:
                keys = json.loads(boosters)
                with open(_presets_dir() + "/defaults.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                booster_texts = [b.get("text") for b in data.get("boosters", []) if b.get("key") in keys]
                if booster_texts:
                    final_preset = (final_preset + "
" + "
".join(booster_texts)).strip()
        except Exception:
            pass
        os.environ["PROMPT_PRESET_TEXT"] = final_preset
        if append_text is not None:
            os.environ["PROMPT_APPEND_TEXT"] = append_text
        return {"ok": True}

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        WS_CLIENTS.add(ws)
        try:
            await send_state(ws)
            while True:
                msg = await ws.receive_text()
                try:
                    data = json.loads(msg)
                except Exception:
                    await ws.send_text(json.dumps({"type": "error", "message": "invalid JSON"}))
                    continue
                if data.get("type") == "tick":
                    await send_state(ws)
                elif data.get("type") == "suggest_now":
                    from mido import Message
                    events = composer.suggest(state)
                    count = 0
                    for ev in events:
                        on = Message('note_on', note=ev.note, velocity=ev.velocity, channel=ev.channel)
                        off = Message('note_off', note=ev.note, velocity=0, channel=ev.channel)
                        if engine:
                            engine.schedule(ev.delay_ms, on)
                            engine.schedule(ev.delay_ms + ev.duration_ms, off)
                            count += 1
                    await ws.send_text(json.dumps({"type": "events_played", "count": count}))
                else:
                    await ws.send_text(json.dumps({"type": "error", "message": "unknown command"}))
        except WebSocketDisconnect:
            try:
                WS_CLIENTS.discard(ws)
            except Exception:
                pass
            return

    def midi_in_loop(in_name: str) -> None:
        nonlocal state
        with mido.open_input(in_name) as inport:
            for msg in inport:
                now = time.monotonic()
                if msg.type in ('note_on', 'note_off'):
                    state.update_from_msg(msg, now)
                    try:
                        _metrics.inc('midi_in_events', 1)
                    except Exception:
                        pass

    @app.post("/api/start")
    async def api_start(in_name: str, out_name: str) -> Dict[str, Any]:
        nonlocal selected_in, selected_out, engine
        selected_in, selected_out = in_name, out_name
        if engine:
            engine.stop()
            engine = None
        engine = PlaybackEngine(mido.open_output(out_name))
        engine.start()
        threading.Thread(target=midi_in_loop, args=(in_name,), daemon=True).start()
        return {"ok": True, "message": "started"}

    # Preset files listing/merge/upload/download
    @app.get("/api/preset_files")
    async def api_preset_files() -> Dict[str, Any]:
        files = sorted(glob.glob(_presets_dir() + "/*.json"))
        return {
            "files": [
                {"name": f.split("/")[-1], **_status_for(f.split("/")[-1])} for f in files
            ]
        }

    @app.post("/api/merge_presets")
    async def api_merge_presets(files: str) -> Dict[str, Any]:
        try:
            names = json.loads(files)
        except Exception:
            names = []
        combined = {"version": 1, "presets": [], "boosters": []}
        seen_p, seen_b = set(), set()
        # reset statuses to unloaded
        for fn in sorted(glob.glob(_presets_dir() + "/*.json")):
            bn = fn.split("/")[-1]
            FILE_STATUSES[bn] = {'status': 'unloaded', 'message': ''}
        CURRENT_SELECTION.clear()
        CURRENT_SELECTION.extend(names)
        for name in names:
            path = _presets_dir() + "/" + name
            data = _read_json(path)
            if not data:
                FILE_STATUSES[name] = {'status': 'error', 'message': 'Failed to read'}
                continue
            FILE_STATUSES[name] = {'status': 'loaded', 'message': ''}
            FILE_HASHES[name] = _file_sha1(path)
            for p in data.get("presets", []):
                k = p.get("name")
                if k and k not in seen_p:
                    combined["presets"].append(p)
                    seen_p.add(k)
            for b in data.get("boosters", []):
                k = b.get("key")
                if k and k not in seen_b:
                    combined["boosters"].append(b)
                    seen_b.add(k)
        LAST_COMBINED.clear()
        LAST_COMBINED.update(combined)
        return combined

    @app.post("/api/reload_changed")
    async def api_reload_changed() -> Dict[str, Any]:
        names = CURRENT_SELECTION or []
        combined = {"version": 1, "presets": [], "boosters": []}
        seen_p, seen_b = set(), set()
        for name in names:
            path = _presets_dir() + "/" + name
            data = _read_json(path)
            if not data:
                FILE_STATUSES[name] = {'status': 'error', 'message': 'Failed to read'}
                continue
            FILE_STATUSES[name] = {'status': 'loaded', 'message': ''}
            FILE_HASHES[name] = _file_sha1(path)
            for p in data.get("presets", []):
                k = p.get("name")
                if k and k not in seen_p:
                    combined["presets"].append(p)
                    seen_p.add(k)
            for b in data.get("boosters", []):
                k = b.get("key")
                if k and k not in seen_b:
                    combined["boosters"].append(b)
                    seen_b.add(k)
        LAST_COMBINED.clear()
        LAST_COMBINED.update(combined)
        return {"ok": True}

    @app.post("/api/presets/upload")
    async def api_presets_upload(file: UploadFile = File(...)) -> Dict[str, Any]:
        name = file.filename or ""
        if not name.lower().endswith(".json"):
            raise HTTPException(status_code=400, detail="Only .json files allowed")
        dest = _presets_dir() + "/" + name
        try:
            data = await file.read()
            json.loads(data.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")
        with open(dest, "wb") as f:
            f.write(data)
        FILE_STATUSES[name] = {'status': 'unloaded', 'message': ''}
        return {"ok": True, "name": name}

    @app.get("/api/presets/download")
    async def api_presets_download(name: str) -> FileResponse:
        if not name.lower().endswith(".json"):
            raise HTTPException(status_code=400, detail="Invalid filename")
        path = _presets_dir() + "/" + name
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(path, media_type="application/json", filename=name)

    @app.get("/api/metrics")
    async def api_metrics() -> Dict[str, Any]:
        return _metrics.snapshot()

    @app.post("/api/metrics/reset")
    async def api_metrics_reset() -> Dict[str, Any]:
        _metrics.reset()
        return {"ok": True}

    @app.get("/healthz")
    async def health() -> Dict[str, Any]:
        return {"ok": True}

    # Watcher thread: mark modified files
    def _snapshot_presets() -> tuple:
        try:
            files = sorted(glob.glob(_presets_dir() + "/*.json"))
            out = []
            import os as _os
            for f in files:
                st = _os.stat(f)
                out.append((f, st.st_mtime, st.st_size))
            return tuple(out)
        except Exception:
            return tuple()

    def watch_presets_dir() -> None:
        last = _snapshot_presets()
        while True:
            time.sleep(2.0)
            cur = _snapshot_presets()
            if cur != last:
                last = cur
                import os as _os
                for fn in sorted(glob.glob(_presets_dir() + "/*.json")):
                    bn = fn.split("/")[-1]
                    st = FILE_STATUSES.get(bn, {'status': 'unloaded', 'message': ''})
                    if st.get('status') == 'loaded':
                        cur_h = _file_sha1(fn)
                        if FILE_HASHES.get(bn) and FILE_HASHES.get(bn) != cur_h:
                            st = {'status': 'modified', 'message': 'changed on disk'}
                    FILE_STATUSES[bn] = st
    threading.Thread(target=watch_presets_dir, daemon=True).start()
