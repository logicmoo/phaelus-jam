
from dataclasses import dataclass, field
from typing import List, Optional
import mido

@dataclass
class PlayerState:
    held_notes: set = field(default_factory=set)
    recent_notes: List[int] = field(default_factory=list)
    recent_velocities: List[int] = field(default_factory=list)
    bpm_guess: float = 100.0
    last_note_on_ts: Optional[float] = None
    inter_on_intervals: List[float] = field(default_factory=list)

    def update_from_msg(self, msg: mido.Message, now: float) -> None:
        '''Update state from a MIDI message at a given timestamp.'''
        if msg.type == 'note_on' and msg.velocity > 0:
            self.held_notes.add(msg.note)
            self.recent_notes.append(msg.note)
            self.recent_notes = self.recent_notes[-64:]
            self.recent_velocities.append(int(msg.velocity))
            self.recent_velocities = self.recent_velocities[-64:]
            if self.last_note_on_ts is not None:
                self.inter_on_intervals.append(now - self.last_note_on_ts)
                self.inter_on_intervals = self.inter_on_intervals[-32:]
                self.bpm_guess = self._estimate_bpm()
            self.last_note_on_ts = now
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in self.held_notes:
                self.held_notes.remove(msg.note)

    def _estimate_bpm(self) -> float:
        '''Estimate BPM from recent inter-onset intervals.'''
        if not self.inter_on_intervals:
            return self.bpm_guess
        med = sorted(self.inter_on_intervals)[len(self.inter_on_intervals) // 2]
        if med <= 0:
            return self.bpm_guess
        return max(50.0, min(180.0, 60.0 / med))
