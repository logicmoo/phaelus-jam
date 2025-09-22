
import os
import json
from typing import Dict, Any, List
try:
    from openai import OpenAI
except Exception:
    OpenAI = None
from .. import metrics as _metrics

class OpenAIAdapter:
    '''Wrapper around the OpenAI chat completion API used by the composer.'''

    def __init__(self, model: str | None = None, temperature: float = 0.8) -> None:
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if (api_key and OpenAI is not None) else None

    def generate_events(self, system: str, user: str) -> List[Dict[str, Any]]:
        '''Generate a sequence of note events given system and user prompts.'''
        if not self.client or (os.getenv('USE_LLM', '1') in ('0', 'false', 'False')):
            return []
        try:
            _metrics.inc('llm_requests', 1)
        except Exception:
            pass
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.8")),
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        content = resp.choices[0].message.content.strip()
        try:
            data = json.loads(content)
            try:
                u = getattr(resp, 'usage', None)
                if u:
                    _metrics.inc('prompt_tokens', int(getattr(u, 'prompt_tokens', 0) or 0))
                    _metrics.inc('completion_tokens', int(getattr(u, 'completion_tokens', 0) or 0))
            except Exception:
                pass
            return data.get("events", [])
        except Exception:
            try:
                _metrics.inc('llm_errors', 1)
            except Exception:
                pass
            return []
