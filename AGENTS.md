# Repository Guide

## Setup

- Use Python 3.14.
- Work from the `src/` directory for local runs.
- Create and enter the virtualenv with Pipenv:
  - `cd src`
  - `pipenv install`
  - `pipenv shell`
- Copy `src/.env.sample` to `src/.env` and set the Slack/OpenAI/Together values you need.
- `load_dotenv(...)` reads `src/.env`, so that file is the source of truth for local development.
- The bot can run in Docker as well:
  - `docker compose up`

## Validation Commands

There is no dedicated automated test suite in this repo. Use these commands to validate changes:

- Syntax check the Python modules:
  - `cd src && python3 -m py_compile index.py chat.py context.py log_config.py`
- Run the bot locally:
  - `cd src && python3 index.py`
- Build and run the containerized app:
  - `docker compose up --build`

## Coding Conventions

- Keep code ASCII unless a file already uses Unicode for a clear reason.
- Prefer small, direct changes over broad refactors.
- Use `apply_patch` for manual file edits.
- Follow the existing Python style:
  - snake_case for functions, variables, and module helpers
  - concise docstrings only where they add value
  - no unnecessary comments
- Preserve Slack formatting conventions:
  - use Slack mrkdwn, not raw Markdown, in user-facing output
  - sanitize model output before sending it to Slack
- Keep environment handling explicit:
  - add new env vars to `src/.env.sample`
  - document new env vars in `resources/docs/OPTIONS.md`
- Keep logging restrained:
  - avoid noisy startup/debug logs unless they are required for troubleshooting
- Prefer least-privilege changes in workflow files and CI config.
- When updating GitHub Actions:
  - verify the upstream release page for the action before bumping the tag
  - prefer the latest published major tag only if that major actually exists upstream
  - do not assume `v4` or `v5` exists just because it feels current
  - keep major-tag bumps scoped to the specific action that changed
  - validate workflow YAML after every change
  - document any non-obvious pin or exception in the PR or commit message

## Repository Notes

- `src/index.py` is the Slack entrypoint.
- `src/chat.py` contains provider selection and response formatting.
- `src/context.py` owns per-channel conversation state.
- `src/log_config.py` owns the local logger setup.
- The repo is chat-only; image generation support has been removed.
- When changing message formatting or model behavior, verify the Slack render, not just the raw model output.
