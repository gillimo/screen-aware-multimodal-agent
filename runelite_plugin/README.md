# AgentOSRS RuneLite Plugin (Local)

This is a local-only RuneLite overlay plugin.

Build (requires RuneLite dependencies installed):
- `gradlew build`

Install:
- Use RuneLite plugin dev workflow to load the jar.

Data source:
- Reads local JSON snapshot: `data/state.json` from the AgentOSRS project.

Commands:
- `coachreload` refreshes overlay status.
- `coachui` launches the Tk companion UI.
