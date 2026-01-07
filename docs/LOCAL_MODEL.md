# Local Model Integration

This project uses a local model runtime via Ollama.

## Configuration
Edit `data/local_model.json`:
- provider: `ollama`
- host: `http://localhost:11434`
- model: `phi3:mini` or `phi3:mini-128k`
- timeout_s, temperature
- plan_default: `heuristic` or `model`
- strict_json: `true` to abort when decision JSON is invalid
- strict_json_retries: number of attempts when strict_json is enabled
- active_profile: humanization profile name (e.g., `normal`)
- safety_gates_enabled: enables policy gating (rate limits/deny lists) for action execution
- approval_policy: controls which actions require explicit approval before execution
- Decision logs are stored in `logs/model_decisions.jsonl`.
- Decision summaries can be exported from logs via CLI.
- Decision logs can be exported and pruned via CLI.

## Quick Check
- `ollama list` should show your installed model.
- Test via CLI: `python run_app.py model --message "hello"`
- Decision JSON: `python run_app.py model-decision --message "plan next step"`
- Plan via model: `python run_app.py plan --model-message "plan next step"`

## Notes
- Implementation lives in `src/local_model.py`.


