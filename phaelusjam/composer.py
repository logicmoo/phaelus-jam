
    import os
    import json
    import random
    import time
    from typing import Dict, Any, List, Tuple
    from .events import JamEvent
    from .player import PlayerState
    from .adapters.openai_adapter import OpenAIAdapter
    from . import metrics as _metrics

    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    SCALES: Dict[str, List[int]] = {
        "major": [0, 2, 4, 5, 7, 9, 11],
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "dorian": [0, 2, 3, 5, 7, 9, 10],
        "mixolydian": [0, 2, 4, 5, 7, 9, 10],
        "pentatonic_minor": [0, 3, 5, 7, 10],
        "blues": [0, 3, 5, 6, 7, 10],
    }

    def detect_keyscale(recent_notes: List[int]) -> Tuple[int, str, float]:
        '''Detect the best matching key and scale given recent notes.'''
        if not recent_notes:
            return 0, "minor", 0.0
        pcs = [n % 12 for n in recent_notes]
        hist = [0] * 12
        for pc in pcs:
            hist[pc] += 1
        best = (0, "minor", -1)
        for scale_name, degs in SCALES.items():
            for root in range(12):
                degset = {(root + d) % 12 for d in degs}
                score = sum(hist[pc] for pc in degset)
                if score > best[2]:
                    best = (root, scale_name, score)
        return best

    class LLMComposer:
        '''Main entry point for generating accompaniment events.'''

        def __init__(self, channel: int = 0, temperature: float = 0.8) -> None:
            self.channel = channel
            self.temperature = temperature
            # Role swap: chords trigger arpeggios and single notes trigger chords
            self.role_swap = os.getenv("ROLE_SWAP", "1") not in ("0", "false", "False")
            self.adapter = OpenAIAdapter(temperature=temperature)

        def suggest(self, state: PlayerState) -> List[JamEvent]:
            '''Compute up to 4 note events given the current player state.'''
            root_pc, scale_name, _ = detect_keyscale(state.recent_notes)
            key_name = NOTE_NAMES[root_pc]
            held = sorted(list(state.held_notes))
            role_mode = (
                "arpeggio"
                if (self.role_swap and len(held) >= 2)
                else ("chord" if self.role_swap else "auto")
            )
            start_ms = int(time.time() * 1000)
            context: Dict[str, Any] = {
                "bpm": round(state.bpm_guess, 1),
                "key": f"{key_name} {scale_name}",
                "held_notes": held,
                "held_count": len(held),
                "role_mode": role_mode,
                "recent_notes": state.recent_notes[-16:],
                "recent_velocities": state.recent_velocities[-16:],
                "inter_on_intervals_ms": [int(x * 1000) for x in state.inter_on_intervals[-16:]],
                "intensity": int(
                    sum(state.recent_velocities[-16:]) / max(1, len(state.recent_velocities[-16:]))
                )
                if state.recent_velocities
                else 85,
            }
            extra_system = os.getenv("PROMPT_PRESET_TEXT", "").strip()
            extra_user = os.getenv("PROMPT_APPEND_TEXT", "").strip()
            system = (
                "You are a live MIDI accompanist. Respond with strictly valid JSON.
"
                "If role_mode='arpeggio', play a short arpeggio/melody over the held chord.
"
                "If role_mode='chord', play a supportive chord (stacked or rolled).
"
                "Use recent_velocities and inter_on_intervals_ms for dynamics and feel.
"
                + (f"Extra guidance: {extra_system}
" if extra_system else "")
                + "Schema: {"events":[{"note":0-127,"velocity":1-127,"duration_ms":int,"delay_ms":int,"channel":0-15}]}"
            )
            user = (
                "Context:
"
                + json.dumps(context)
                + "
- Return 1..4 events, span <= 1 bar at "
                + str(context['bpm'])
                + " BPM (4/4).
"
                "- Quantize delay_ms & duration_ms to 60/120/240/480.
"
                + f"- Favor key: {context['key']} | Channel: {self.channel}.
"
                "- If role_mode='chord' play notes simultaneously (same delay_ms)."
                + ("
User guidance: " + extra_user if extra_user else "")
            )
            events_data = self.adapter.generate_events(system, user)
            end_ms = int(time.time() * 1000)
            latency = end_ms - start_ms
            beat_ms = int(60000 / max(1.0, context['bpm'] or 100.0))
            bar_ms = beat_ms * 4
            on_time = latency <= max(120, int(0.8 * bar_ms))
            try:
                _metrics.add_timing(latency, on_time)
            except Exception:
                pass
            if events_data:
                return [
                    JamEvent(**{**e, "channel": e.get("channel", self.channel)})
                    for e in events_data
                ]
            return self._rule_based_events(context, root_pc, scale_name)

        def _rule_based_events(
            self, context: Dict[str, Any], root_pc: int, scale_name: str
        ) -> List[JamEvent]:
            '''Fallback generator when LLM is disabled or errors occur.'''
            bpm = context["bpm"]
            q_ms = int(60000 / max(50.0, min(180.0, bpm)))
            grid = max(60, q_ms // 2)
            intensity = int(context.get("intensity", 85))
            held = context.get("held_notes", [])
            role = context.get("role_mode", "auto")
            scale = SCALES.get(scale_name, SCALES["minor"])
            events: List[JamEvent] = []
            if role == "chord":
                base_root = 48 + root_pc
                tri = [0, 2, 4]
                for deg in tri:
                    degree_pc = (root_pc + scale[deg % len(scale)]) % 12
                    note = base_root + (degree_pc - root_pc) % 12
                    vel = max(60, min(110, intensity + 3))
                    events.append(
                        JamEvent(note=note, velocity=vel, duration_ms=grid * 2, delay_ms=0, channel=self.channel)
                    )
                return events
            if role == "arpeggio" and len(held) >= 2:
                seq = sorted(held) + [sorted(held)[0] + 12]
                t = 0
                for n in seq[:4]:
                    vel = max(60, min(110, intensity))
                    events.append(
                        JamEvent(note=n, velocity=vel, duration_ms=grid, delay_ms=t, channel=self.channel)
                    )
                    t += grid
                return events
            base_note = 48 + root_pc
            t = 0
            for i in range(3):
                degree = scale[(i * 2) % len(scale)]
                note = base_note + degree
                vel = max(60, min(110, intensity - 2 + (i % 2) * 4))
                events.append(
                    JamEvent(note=note, velocity=vel, duration_ms=grid, delay_ms=t, channel=self.channel)
                )
                t += grid
            return events
