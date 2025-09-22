
    import mido
    import time
    import os
    from phaelusjam.player import PlayerState
    from phaelusjam.composer import LLMComposer
    from phaelusjam.engine import PlaybackEngine

    def list_ports():
        return mido.get_input_names(), mido.get_output_names()

    def choose_port(options, prompt):
        print(f"
{prompt}:")
        for i, name in enumerate(options):
            print(f"  [{i}] {name}")
        while True:
            try:
                idx = int(input(f"Select index 0..{len(options)-1}: ").strip())
                if 0 <= idx < len(options):
                    return idx
            except Exception:
                pass
            print("Invalid selection. Try again.")

    def main() -> None:
        print("=== PhaelusJam ===")
        ins, outs = list_ports()
        if not ins or not outs:
            print(
                "No MIDI ports found. Ensure your devices and virtual ports are available."
            )
            return
        in_idx = choose_port(ins, "MIDI Inputs (pick your instrument)")
        out_idx = choose_port(outs, "MIDI Outputs (pick your synth/DAW/virtual port)")
        print(f"Using IN: {ins[in_idx]}
Using OUT: {outs[out_idx]}")
        state = PlayerState()
        composer = LLMComposer(channel=0, temperature=float(os.getenv("LLM_TEMPERATURE", "0.8")))
        engine = PlaybackEngine(mido.open_output(outs[out_idx]))
        engine.start()

        def on_suggest() -> None:
            events = composer.suggest(state)
            for ev in events:
                on = mido.Message('note_on', note=ev.note, velocity=ev.velocity, channel=ev.channel)
                off = mido.Message('note_off', note=ev.note, velocity=0, channel=ev.channel)
                engine.schedule(ev.delay_ms, on)
                engine.schedule(ev.delay_ms + ev.duration_ms, off)

        import threading

        def suggestion_loop() -> None:
            while True:
                bpm = state.bpm_guess or 100.0
                beat_ms = int(60000 / bpm)
                bar_ms = beat_ms * 4
                on_suggest()
                time.sleep(bar_ms / 1000.0)

        threading.Thread(target=suggestion_loop, daemon=True).start()

        with mido.open_input(ins[in_idx]) as inport:
            last_ts = time.monotonic()
            for msg in inport:
                now = time.monotonic()
                if msg.type in ('note_on', 'note_off'):
                    state.update_from_msg(msg, now)
                if now - last_ts > 2.0 and state.recent_notes:
                    last_ts = now
                    print(
                        f"BPM≈{state.bpm_guess:.1f} | Held: {sorted(state.held_notes)} | Recent: {state.recent_notes[-6:]} "
                    )

    if __name__ == "__main__":
        main()
