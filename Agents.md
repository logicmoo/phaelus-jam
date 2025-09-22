
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)]()
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](LICENSE)
[![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/status-experimental-orange.svg)]()

# Agents.md — Codegen Workflow for *PhaelusJam*

## Getting Started
```bash
git clone https://github.com/YOURNAME/phaelus-jam.git
cd phaelus-jam
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scriptsctivate
pip install -e .
uvicorn server.main:app --reload
```

## Contributing
- Use small PRs; docstrings & typing.
- `agents/agent_cli.py` composes prompts; tests under `tests/`.
- Share preset packs via `server/presets/*.json`.

## Visual Mockups
![Functional](A_2D_digital_graphic_user_interface_(GUI)_showcase.png)
![Polished](A_digital_2D_rendering_displays_a_virtual_audio_pr.png)
![Front](server/static/previews/front.png)
![Config](server/static/previews/config.png)
![Monitor](server/static/previews/monitor.png)
![Logging](server/static/previews/logging.png)
![Testing](server/static/previews/testing.png)
