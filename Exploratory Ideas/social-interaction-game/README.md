# Social Interaction Game

An exploratory, dependency-free prototype for **reinforcement learning with verifiable rewards** in open-ended social roleplay.

This is not trying to grade one perfect line of dialogue. It builds a small hidden-state world and scores whether a response satisfies verifiable conversational constraints.

## V1 Goal

Given:

- a social scenario
- a current user message
- a hidden relationship state
- a set of scenario-specific rules

score the candidate response on:

- acknowledgement
- relevance
- empathy markers
- advice-policy compliance
- question balance
- response length
- quantity relative to the user's message
- manner / clarity
- cross-turn consistency
- boundary respect
- emotional alignment in valence, arousal, and dominance

Then update the hidden state:

- trust
- closeness
- irritation

## Why This Matters

The environment treats social interaction like a constraint game, not an answer-key task. Many replies can be valid, but they must satisfy checkable properties.

## File Map

- `models.py` — dataclasses for scenarios, rules, scores, and hidden state
- `lexicon.py` — rule-based lexicons and text utilities
- `vad_lexicon.py` — bundled seed VAD lexicon plus optional local NRC-style TSV loading
- `verifiers.py` — deterministic scoring functions
- `scenarios.py` — hand-authored and procedural scenario generation
- `bot.py` — baseline AI player for autoplay
- `engine.py` — game loop and hidden-state transitions
- `play.py` — CLI for human play-testing
- `server.py` — no-dependency local web server for the HTML/CSS/JS UI
- `run_tests.py` — lightweight tests for reward sanity
- `web/` — browser UI

## Run It

List scenarios:

```bash
python3 "Exploratory Ideas/social-interaction-game/play.py" --list
```

Play a hand-authored scenario:

```bash
python3 "Exploratory Ideas/social-interaction-game/play.py" --scenario job-loss-support
```

Play with secret rule details visible:

```bash
python3 "Exploratory Ideas/social-interaction-game/play.py" --scenario job-loss-support --debug
```

Score one response quickly:

```bash
python3 "Exploratory Ideas/social-interaction-game/play.py" \
  --scenario job-loss-support \
  --response "I'm really sorry. That sounds brutal. You do not need to figure everything out tonight."
```

Run the tests:

```bash
python3 "Exploratory Ideas/social-interaction-game/run_tests.py"
```

Run the browser UI:

```bash
python3 "Exploratory Ideas/social-interaction-game/server.py" --port 8765
```

Then open [http://127.0.0.1:8765](http://127.0.0.1:8765).

## Current Limits

V1 deliberately avoids external NLP dependencies. The verifier uses simple lexicons, token overlap, boundary rules, and small emotional heuristics so the reward remains debuggable.

That makes it imperfect, but it is a strong starting point for RLVR exploration.

## How The Approaches Map In

- Approach 2: partial Grice-style constraints through quantity, relevance, and manner checks
- Approach 3: explicit VAD scoring with valence, arousal, dominance, plus trajectory alignment
- Approach 4: protocol-style invariants like acknowledgement, consistency, question balance, and boundary respect
- Approach 5: hand-authored plus procedurally generated social scenarios

## Important VAD Note

This prototype ships with a **bundled seed VAD lexicon**, not the full NRC-VAD dataset. The loader is already wired so you can drop an `nrc_vad_lexicon.tsv` file into `data/` and the scorer will use it automatically.
