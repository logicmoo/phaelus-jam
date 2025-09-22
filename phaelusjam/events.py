
from dataclasses import dataclass
from typing import List
import mido

@dataclass
class JamEvent:
    note: int
    velocity: int = 90
    duration_ms: int = 300
    delay_ms: int = 0
    channel: int = 0

    def to_mido(self) -> List[mido.Message]:
        '''Return note_on and note_off mido messages for the event.'''
        on = mido.Message('note_on', note=self.note, velocity=self.velocity, channel=self.channel)
        off = mido.Message('note_off', note=self.note, velocity=0, channel=self.channel)
        return [on, off]
