# Prospective Visuals and Design Elements

This document lists the proposed visual elements and common components to be included on each tab of the web UI. The goal is to unify the style and ensure we don't forget to implement them as the project evolves.

## Global Components

- **Header bar**: Title ("Phaelus Jam by LogicMUSE") and AI power toggle.
- **Status LED strip**: WebSocket (WS), MIDI IN, MIDI OUT, Engine, LLM indicators.
- **Unified dark theme**: charcoal background with subtle gradients and cyan highlights.
- **Consistent control styling**: knobs, switches, sliders, meters across all panels.
- **Navigation tabs**: Front, Configuration, Monitoring, Advanced Logging, Testing.
- **Footer stats**: quick display of BPM, intensity, token counts, etc.

## Panel-Specific Elements

### Front Panel
- Summary controls: Role swap switch, density knob or slider, model selector.
- Prompt editor: Preset dropdown, editable preset text area, user add-on input, and preview.
- Suggest button: to force a suggestion outside the bar cycle.

### Configuration Panel
- Preset file management: list of available `.json` files with status tags.
- Buttons: Load, Reload, Reload Changed, Export, Upload.
- File status indicator: loaded / unloaded / modified.

### Monitoring Panel
- Compact metrics: LLM requests, token counts, MIDI in/out counters, composer late percentage.
- Activity meters: horizontal bar graphs or LED meters for BPM and intensity.
- Held and recent notes: text display of currently held and recent MIDI notes.

### Advanced Logging Panel
- Log console: scrollable area showing JSON messages exchanged over WebSocket and HTTP.
- Filters: checkboxes to toggle WebSocket vs HTTP logging.
- Log controls: clear log, download log.

### Testing Panel
- Quick actions: buttons to ping state, force suggestion, fetch ports, apply quick params.
- Testing results area: preformatted box showing JSON responses.
- Metrics controls: buttons to fetch and reset metrics.

---

Please update this document whenever new visual ideas or components are proposed, to keep track of them.
