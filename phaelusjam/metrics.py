
import threading

_lock = threading.Lock()
_counters = {
    'llm_requests': 0, 'llm_errors': 0,
    'prompt_tokens': 0, 'completion_tokens': 0,
    'midi_in_events': 0, 'midi_out_events': 0,
    'bars_generated': 0,
    'composer_calls': 0, 'composer_latency_ms_sum': 0,
    'composer_calls_late': 0,
}

def inc(name: str, n: int = 1) -> None:
    '''Increment a counter.'''
    with _lock:
        _counters[name] = _counters.get(name, 0) + n

def add_timing(latency_ms: int, on_time: bool) -> None:
    '''Record a composer call latency and lateness.'''
    with _lock:
        _counters['composer_calls'] += 1
        _counters['composer_latency_ms_sum'] += int(latency_ms)
        if not on_time:
            _counters['composer_calls_late'] += 1

def snapshot() -> dict:
    '''Return a snapshot of counters with derived metrics.'''
    with _lock:
        snap = dict(_counters)
        calls = snap.get('composer_calls', 0)
        snap['composer_latency_ms_avg'] = (
            snap['composer_latency_ms_sum'] / calls if calls else 0
        )
        snap['composer_late_ratio'] = (
            snap.get('composer_calls_late', 0) / calls if calls else 0.0
        )
        return snap

def reset() -> None:
    '''Reset all counters to zero.'''
    with _lock:
        for k in list(_counters.keys()):
            _counters[k] = 0
