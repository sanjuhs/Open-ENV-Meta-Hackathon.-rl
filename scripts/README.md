# Scripts

The main launcher for the exploratory social interaction game is:

```bash
./scripts/social-interaction-game.sh
```

It automatically activates the repository virtual environment from `.venv/`, `venv/`, or `env/`.

## Commands

List scenarios:

```bash
./scripts/social-interaction-game.sh list
```

Play in the terminal:

```bash
./scripts/social-interaction-game.sh cli --scenario job-loss-support
```

Play a procedural scenario in the terminal:

```bash
./scripts/social-interaction-game.sh cli --procedural-seed 7
```

Let the baseline AI play:

```bash
./scripts/social-interaction-game.sh ai --scenario celebrate-small-win
```

Launch the browser UI:

```bash
./scripts/social-interaction-game.sh web
```

Launch the browser UI on a custom port without auto-opening the browser:

```bash
./scripts/social-interaction-game.sh web --port 8899 --no-browser
```

Run the tests:

```bash
./scripts/social-interaction-game.sh test
```

## What The Web Script Does

`web` starts the local Python server for:

- the HTML page
- the CSS and JavaScript assets
- the local JSON API used by the page

By default it tries to open the browser automatically on macOS with `open`, or on Linux with `xdg-open`.

## Notes

- The VAD scorer uses a bundled seed lexicon by default.
- If you want a fuller NRC-style lexicon, place `nrc_vad_lexicon.tsv` in:

```text
Exploratory Ideas/social-interaction-game/data/
```

- The browser UI supports both human play and a baseline AI autoplay button.

## DocEdit Game V2

The launcher for the document corruption and correction game in `attempt1` is:

```bash
./scripts/doc-edit-game.sh start --open
```

This starts the FastAPI server in the background and serves:

- the human-playable browser UI at `http://127.0.0.1:8877/`
- the human game JSON API under `/api/game/*`
- the OpenEnv agent API under `/api/openenv`

Useful commands:

```bash
./scripts/doc-edit-game.sh run
./scripts/doc-edit-game.sh status
./scripts/doc-edit-game.sh smoke
./scripts/doc-edit-game.sh logs -f
./scripts/doc-edit-game.sh restart --open
./scripts/doc-edit-game.sh stop
```

Notes:

- `smoke` verifies the browser route, creates a seeded human-play session, and checks that the OpenEnv schema is mounted.
- The browser UI and the OpenEnv API run on the same server, but external OpenEnv agent episodes are not mirrored live into the browser session.
