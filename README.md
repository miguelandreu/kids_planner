# Kids Planner

An AI agent that emails a weekend plan for families with young children. Every Thursday around noon (Madrid time) it:

1. Fetches the Friday–Sunday weather forecast from [Open-Meteo](https://open-meteo.com/) (free, no API key).
2. Searches the web for kids' activities in Alcobendas, San Sebastián de los Reyes, Tres Cantos and northern Madrid.
3. Emails a summary (forecast + plans by day and morning/afternoon) to a fixed list of recipients.

Built with the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/). The agent's instructions live in [`prompts.py`](src/kids_planner/prompts.py) and are written in Spanish.

## Project layout

```
src/kids_planner/
  kids_planner.py       # entrypoint: builds the agent, runs it, sets the exit code
  prompts.py            # agent instructions
  weather_tool.py       # get_weekend_weather tool (Open-Meteo)
  email_sender_tool.py  # send_email tool (SMTP, one email per run)
  preparation.ipynb     # exploration notebook
tests/                  # unit tests + live Open-Meteo tests
.github/workflows/
  weekly-plans.yml      # Thursday cron
  ci.yml                # tests on push / pull request
```

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
```

Then create a `.env` file in the project root (it is git-ignored) with the variables below.

### Configuration

Set these as environment variables (a local `.env` file is loaded automatically):

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | yes | OpenAI API key |
| `OPENAI_MODEL` | no | Model name (defaults to `gpt-6-luna`) |
| `SMTP_HOST` | yes* | SMTP server, e.g. `smtp.gmail.com` |
| `SMTP_PORT` | no | `587` (STARTTLS, default) or `465` (implicit TLS) |
| `SMTP_USERNAME` | yes* | SMTP login |
| `SMTP_PASSWORD` | yes* | SMTP password. For Gmail use an [App Password](https://support.google.com/accounts/answer/185833) |
| `EMAIL_FROM` | no | Sender, defaults to `SMTP_USERNAME` |
| `EMAIL_RECIPIENTS` | yes* | Comma- or semicolon-separated list |
| `DRY_RUN` | no | `1` prints the email instead of sending it |

\* Not needed in dry-run mode (except that `OPENAI_API_KEY` is always required).

Recipients are deliberately **not** a tool argument, so the model cannot send mail anywhere else. All recipients receive a single message and can see each other.

## Usage

```bash
# Print the email instead of sending it
uv run kids-planner --dry-run

# Run for real
uv run kids-planner
```

`python -m kids_planner.kids_planner` is equivalent. Running the file directly (`python src/kids_planner/kids_planner.py`) is not supported because the package uses relative imports.

### Exit codes

| Situation | Exit code |
|---|---|
| Email sent (or dry-run printed it) | `0` |
| Email not sent because the agent reported "no hay planes disponibles" | `0` |
| Email not sent for any other reason, or any exception (weather API, SMTP, max turns…) | `1` |

The agent is limited to 25 turns (`MAX_TURNS` in `kids_planner.py`). Only one email can be sent per run: a second `send_email` call is refused, so agent retries cannot produce duplicates.

## Tests

```bash
uv run pytest                        # everything, including live Open-Meteo calls
uv run pytest -m "not integration"   # offline unit tests only
```

Unit tests mock SMTP and Open-Meteo. Tests marked `integration` call the real Open-Meteo API to verify the response format the weather tool depends on; they fail without network access.

## Deployment (GitHub Actions)

### Weekly run

[`weekly-plans.yml`](.github/workflows/weekly-plans.yml) runs every Thursday at 10:00 UTC, which is 12:00 in Madrid during summer time and 11:00 during winter time. Scheduled runs can be delayed by a few minutes by GitHub.

It can also be launched manually from the **Actions** tab. Manual runs default to **dry run**; untick `dry_run` to actually send the email.

Configure in *Settings → Secrets and variables → Actions*:

- Secrets: `OPENAI_API_KEY`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM`, `EMAIL_RECIPIENTS`
- Variable (optional): `OPENAI_MODEL`

The job has a 20-minute timeout. Scheduled workflows on repositories with no activity for 60 days are disabled by GitHub; re-enable them from the Actions tab if that happens.

### CI

[`ci.yml`](.github/workflows/ci.yml) runs the test suite on every push to `main` and on every pull request. To make it a gate, enable branch protection on `main` and require the `CI / test` check.

## Disclaimer

The generated emails state that they were written by a virtual assistant and that information may be inaccurate. Plans come from web search; always verify details before going.
