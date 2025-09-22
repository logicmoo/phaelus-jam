
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)]()
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](LICENSE)
[![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/status-experimental-orange.svg)]()

# PhaelusJam
**An AI-powered real-time composer & accompanist**  
by **LogicMUSE**

## Interface (DAW-style)
- **Top bar**: Title *Phaelus Jam by LogicMUSE*, AI On/Off, LED strip (WS, IN, OUT, ENG, LLM)
- **Tabs**: Front, Configuration, Monitoring, Advanced Logging, Testing

## Run (Web UI)
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scriptsctivate
pip install -r requirements.txt
uvicorn server.main:app --reload
# open http://127.0.0.1:8000
```

## 🖼 Mockups
### Current functional look
![Mockup functional](A_2D_digital_graphic_user_interface_(GUI)_showcase.png)

### Target polished design (Cubase-style plugin)
![Mockup polished](A_digital_2D_rendering_displays_a_virtual_audio_pr.png)

### Tab Previews
- **Front Panel**  
  ![Front Panel](server/static/previews/front.png)

- **Configuration Panel**  
  ![Configuration Panel](server/static/previews/config.png)

- **Monitoring Panel**  
  ![Monitoring Panel](server/static/previews/monitor.png)

- **Advanced Logging Panel**  
  ![Advanced Logging Panel](server/static/previews/logging.png)

- **Testing Panel**  
  ![Testing Panel](server/static/previews/testing.png)

## CI
This repo includes GitHub Actions CI (ruff, black, pytest). Update the build badge after pushing.

## Developer workflow
### Pre-commit
```bash
pip install pre-commit
pre-commit install
```

### Releasing (optional)
Add PYPI_API_TOKEN secret. Tag and push `v0.1.0` to release.
