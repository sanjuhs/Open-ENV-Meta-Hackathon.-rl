# Open-ENV-Meta-Hackathon — DocEdit Game V2

**OpenEnv Round 1 Competition** | Sanjayprasad H S | Solo Warrior

**HF Space**: [sanjuhs/doc_edit_v5](https://huggingface.co/spaces/sanjuhs/doc_edit_v5)

## What This Is

A production-grade **document editing RL environment** for training applicator models that perform precise edits on legal and pharmaceutical documents. Built for the [OpenEnv Round 1 Hackathon](https://openenv.org) (Meta + Hugging Face).

### The Real-World Problem

Legal and pharma professionals spend hours editing massive documents — contracts, affidavits, drug labels, clinical study reports. A frontier LLM can *decide* what edits to make, but executing 200 precise edits on a 2000-page XML document is too slow and expensive for GPT-4o. This environment trains **applicator models** (1-7B params) that execute edits with near-perfect accuracy at 500x lower cost.

## Environment Design

### Game Loop

1. **Reset** → Environment generates a document with procedural corruptions
2. **Observe** → Agent sees a document chunk + edit instruction + similarity score
3. **Act** → Agent calls one tool per step (replace, format_text, delete, merge_runs, etc.)
4. **Reward** → Incremental similarity improvement to hidden target, with bonuses and penalties
5. **Win** → Achieve similarity >= 0.999

### Domains

| Domain | Document Types | Real-World Scenario |
|--------|---------------|-------------------|
| **Legal** | Contract, Affidavit, Case Brief | Redlining, name changes, section renumbering |
| **Pharma** | Drug Label, Clinical Study Report | Dosage updates, adverse reaction additions, regulatory formatting |
| **Business** | Business Report | Financial table fixes, executive summary edits |

### 12 Corruption Types (3 Tiers)

- **Tier 1 — Content**: spelling, case, names, punctuation, content deletion, content insertion
- **Tier 2 — Formatting**: formatting strip, formatting wrong, alignment, spacing
- **Tier 3 — Artifacts**: PDF-to-DOCX fragmented runs, junk characters (zero-width spaces, BOMs)

### 16+ Agent Tools (Action Space)

```json
{"tool": "replace", "params": {"target": "recieve", "content": "receive"}}
{"tool": "format_text", "params": {"target": "Important Notice", "format": "bold"}}
{"tool": "merge_runs", "params": {"line_index": 23}}
{"tool": "clean_junk_chars", "params": {}}
{"tool": "set_alignment", "params": {"line_index": 5, "alignment": "center"}}
{"tool": "scroll_to", "params": {"chunk": 47}}
```

### Observation Space

| Field | Type | Description |
|-------|------|-------------|
| `document_chunk` | str | Currently visible document chunk (XML) |
| `chunk_index` / `total_chunks` | int | Navigation position |
| `document_overview` | str | Heading index for navigation |
| `edit_instruction` | str | Natural language edit description |
| `similarity` | float | Overall similarity to target (0.0–1.0) |
| `collateral_damage` | float | Fraction of correct text accidentally damaged |
| `task_difficulty` | int | 1–6 severity level |
| `doc_type` / `domain` | str | Document template and domain |

### 5 Fixed Evaluation Tasks

| Task | Domain | Difficulty | Description |
|------|--------|-----------|-------------|
| `legal_easy` | Legal | 2 (easy) | Spelling, punctuation, content insertion |
| `legal_medium` | Legal | 3 (medium) | Mixed Tier 1+2 corruptions |
| `legal_hard` | Legal | 5 (expert) | All tiers including PDF artifacts |
| `pharma_easy` | Pharma | 2 (easy) | Spelling, content deletion |
| `pharma_hard` | Pharma | 4 (hard) | Mixed Tier 1+2 corruptions |

### Reward Design

```
reward = similarity_after - similarity_before       # incremental progress
if exact_match: reward += 1.0 + 0.2 * efficiency   # completion bonus scaled by speed
if noop: reward -= 0.01                             # wasted step penalty
if collateral_damage: reward -= 0.02 * damage       # broke something correct
```

### Dual-Seed System

```python
reset(doc_seed=42, corruption_seed=9042, difficulty=3, domain="legal")
```

- `doc_seed` controls document generation (template, content, length)
- `corruption_seed` controls corruption application (types, positions)
- 2^32 x 2^32 = ~18 quintillion unique tasks for infinite curriculum

## Setup & Usage

```bash
# Clone and install
git clone https://github.com/sanjuhs/Open-ENV-Meta-Hackathon.-rl.git
cd Open-ENV-Meta-Hackathon.-rl/attempt1/doc_edit_game_v2

# Install dependencies
uv sync

# Run server locally
uvicorn server.app:app --host 0.0.0.0 --port 8000

# Or via Docker
docker build -t doc_edit_v5:latest -f server/Dockerfile .
docker run -p 8000:8000 doc_edit_v5:latest
```

### Running Inference

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="your-token"

cd attempt1/doc_edit_game_v2
python inference.py
```

### Validate

```bash
cd attempt1/doc_edit_game_v2
openenv validate
```

## Architecture

```
attempt1/doc_edit_game_v2/
├── game/
│   ├── templates/          # 6 document generators (legal, pharma, business)
│   ├── corruptions/        # 12 corruption types in 3 tiers
│   ├── tools/              # 16+ editing tools (replace, format, merge_runs, etc.)
│   ├── windowing.py        # Chunked navigation for large docs
│   ├── grader.py           # Multi-level grading (similarity + edit accuracy + collateral)
│   ├── generator.py        # Task orchestrator with dual-seed system
│   └── content_pools.py    # Domain-specific vocabulary (legal, pharma, business)
├── models.py               # DocEditAction + DocEditObservation (Pydantic typed models)
├── client.py               # WebSocket client for remote interaction
├── inference.py            # Baseline LLM inference script (OpenAI API)
├── openenv.yaml            # OpenEnv spec metadata
├── pyproject.toml          # Package config
└── server/
    ├── doc_edit_game_v2_environment.py   # Core Environment (reset/step/state)
    ├── app.py                            # FastAPI server
    └── Dockerfile                        # Container deployment
```

## OpenEnv Spec Compliance

- `openenv.yaml` with spec_version 1, FastAPI runtime
- Typed Pydantic models: `DocEditAction` (Action) and `DocEditObservation` (Observation)
- `step(action)` → observation, reward, done, metadata
- `reset()` → initial observation with task details
- `state` property → episode_id, step_count
- 5 tasks with programmatic graders (scores 0.0–1.0)
- Baseline `inference.py` with `[START]`, `[STEP]`, `[END]` structured logs
- Working Dockerfile for containerized deployment
- Deployed to HF Spaces tagged `openenv`

## Competition Details

- **Competition**: OpenEnv Round 1 Hackathon (Meta + Hugging Face)
- **Deadline**: 8 April 2026, 11:59 PM IST
- **Participant**: Sanjayprasad H S (Solo)
- **HF Space**: https://huggingface.co/spaces/sanjuhs/doc_edit_v5
