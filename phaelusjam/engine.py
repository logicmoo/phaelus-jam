
import time
import queue
import threading
import mido
from . import metrics as _metrics

class PlaybackEngine:
    '''A simple scheduler for MIDI events.'''

    def __init__(self, out_port: mido.ports.BaseOutput, latency_ms: int = 10) -> None:
        self.out = out_port
        self.latency_ms = latency_ms
        self.scheduler: queue.PriorityQueue[tuple[float, mido.Message]] = queue.PriorityQueue()
        self.running = False
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self.running = True
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        self.thread.join(timeout=1.0)

    def schedule(self, delay_ms: int, msg: mido.Message) -> None:
        '''Schedule a MIDI message to send after a delay.'''
        when = time.monotonic() + max(0, delay_ms) / 1000.0
        self.scheduler.put((when, msg))

    def _run(self) -> None:
        while self.running:
            try:
                when, msg = self.scheduler.get(timeout=0.05)
            except queue.Empty:
                continue
            now = time.monotonic()
            if when > now:
                time.sleep(max(0, when - now))
            try:
                self.out.send(msg)
                try:
                    _metrics.inc('midi_out_events', 1)
                except Exception:
                    pass
            except Exception as e:
                print(f"Send error: {e}")
