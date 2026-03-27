# GLaDOS Check-in CLI

Standalone Python CLI for daily GLaDOS check-in, earned-points tracking, CSV history, Windows Task Scheduler registration, and GitHub Actions automation.

## Quick start

1. Copy `config.example.toml` to `config.toml`.
2. Fill in your `cookie` and `user_agent`.
3. Run:

```powershell
python -m glados_checkin status
python -m glados_checkin run
python -m glados_checkin install-task
```

The CSV history is written to `data/checkin_history.csv`.

## Commands

- `python -m glados_checkin run`
- `python -m glados_checkin status`
- `python -m glados_checkin install-task`

## GitHub Actions

Use [.github/workflows/glados-checkin.yml](.github/workflows/glados-checkin.yml) when you want the check-in to run even while your own computer is off.

1. Push this project to a GitHub repository.
2. Add repository secret `GLADOS_COOKIE`.
3. Optional repository variables:
   - `GLADOS_BASE_URL`
   - `GLADOS_FALLBACK_BASE_URLS`
   - `GLADOS_USER_AGENT`
4. The workflow runs daily at `05:15 UTC`, which is `13:15` in `Asia/Shanghai`.
5. Each run appends to `data/checkin_history.csv`, commits the updated CSV back to the repo, and uploads it as a workflow artifact.

## Notes

- The tool uses manual cookie configuration and never stores your password.
- The current default domain is `glados.one`, with `glados.rocks` and `glados.cloud` as fallbacks.
- The tool records daily check-in status and earned points. It no longer resolves total points.
- GitHub Actions scheduled workflows are much more reliable than a local PC, but GitHub may still delay a scheduled run by a few minutes under load.
