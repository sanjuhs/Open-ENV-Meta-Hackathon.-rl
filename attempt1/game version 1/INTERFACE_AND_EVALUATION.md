# Game Version 1: Human And Model Interface Plan

## Goal

Design one environment with two playable surfaces:
- a human-facing interface that is intuitive and reasonably fast,
- and a model-facing interface that is structured, auditable, and fair.

The point is not to make both interfaces identical in appearance.
The point is to make them comparable in capability and measurable in outcome.

## Principle: Same World, Same Powers, Different Surface

The cleanest design is:
- same underlying world state,
- same allowed operations,
- same grader,
- same task objective,
- different presentation layer.

That avoids the mistake of saying "the model failed" when really the interface starved it of useful navigation, or saying "the human won" because the human got a much better view of the world.

## Human Interface

The human UI should feel like a hybrid of a document editor, issue tracker, and inspector panel.

### Main Layout

- left sidebar: outline and issue list
- center pane: editable viewport
- right sidebar: entity inspector, references, comments, and validation status
- top bar: objective, timer, score preview, submit button
- bottom utility bar: search, undo/redo, action log

### Human Interaction Features

- click to navigate
- keyboard shortcuts for search and replace
- inline editing for text blocks
- constrained editing widgets for structured fields
- one-click jump from reference to target
- highlight unresolved inconsistencies
- optional validation button to preview remaining rule violations

### Why This Matters

A human should not have to fight the interface.
If the interface is frustrating, we learn more about UI cost than about true problem-solving ability.

## Model Interface

The model should interact through structured observations and tool calls.

### Observation Packet

Suggested shape:

```json
{
  "objective": "Repair the world so all references, values, and formatting match the target state.",
  "outline": [
    {"id": "sec_1", "label": "1. Indications", "line": 42},
    {"id": "sec_2", "label": "2. Dosage", "line": 180}
  ],
  "viewport": {
    "mode": "document",
    "start": 180,
    "end": 260,
    "content": "..."
  },
  "search_results": [],
  "focused_entity": {
    "id": "drug_ozempic",
    "aliases": ["Ozempic", "semaglutide"],
    "references": [203, 847]
  },
  "metrics": {
    "similarity": 0.84,
    "constraint_violations": 5,
    "steps_used": 14,
    "time_remaining_sec": 420
  }
}
```

### Tool Calls

Suggested operations:
- `jump(target)`
- `search(query)`
- `open_reference(ref_id)`
- `replace(node_id, old, new)`
- `insert_after(node_id, content)`
- `delete(node_id)`
- `move(node_id, after_node_id)`
- `set_format(node_id, format_spec)`
- `update_entity(entity_id, field, value)`
- `validate()`
- `submit()`

Every tool call should be logged with:
- timestamp,
- arguments,
- pre-state hash,
- post-state hash,
- and reward delta.

## Fairness Rules

Human-vs-model comparisons are easy to distort.
We should decide fairness rules explicitly.

### Fairness Recommendation

Equalize capabilities, not appearance.

That means:
- if a human can search globally, the model can too,
- if the model can validate the whole world, the human can too,
- if the human gets an issue list, the model should receive the same issue channel or we should remove it for both,
- if the model gets precise node identifiers, the human should get stable visible anchors.

### Things We Should Not Equalize

- raw typing speed
- visual rendering style
- mouse versus tool-call interaction

Those are presentation differences, not capability differences.

## Telemetry Plan

This is the heart of the comparison.

We should record:
- final score
- exact completion status
- wall-clock time
- number of actions
- invalid actions
- undo count
- search count
- search-to-fix conversion rate
- number of distinct regions visited
- collateral damage introduced
- collateral damage left unresolved
- validation checks used
- hint usage
- action sequence replay

This supports both leaderboard-style evaluation and deep behavior analysis.

## Comparison Metrics

We should not compress everything into one number.

Recommended top-level metrics:
- `Final correctness`: did the player restore the world?
- `Efficiency`: how much time and how many actions did it take?
- `Precision`: how often did edits damage already-correct content?
- `Coverage`: how completely did the player find all affected locations?
- `Strategy quality`: did the player navigate intelligently?

Useful derived comparisons:
- time to 50% of final score
- time to first structural fix
- average reward per action
- fixes per search
- percentage of errors caught without hints

## Recommended Experiment Modes

### Mode 1: Benchmark

- fixed task set
- no hints
- strict timer
- direct score comparison

### Mode 2: Assisted

- validation allowed
- optional hints
- useful for product-like evaluation

### Mode 3: Diagnostic

- replay review
- richer logging
- used to study strategy differences and failure modes

## UI Concepts Worth Preserving

From the existing design direction, these are especially strong:
- always-visible outline
- search as a first-class action
- chunked or windowed editing
- deterministic validation
- explicit submit step

For the human UI, I would add:
- an "affected references" panel,
- a "pending inconsistencies" panel,
- and a diff-style review before submit.

These features make the task feel like serious editing work instead of generic text manipulation.

## Failure Modes To Watch

- The human UI is too good, so the model comparison becomes meaningless.
- The model API is too narrow, so the benchmark measures interface starvation.
- The grader rewards exact formatting over meaningful correctness.
- Tasks become tedious rather than cognitively rich.
- We accidentally optimize for speed while ignoring safe editing behavior.
- Hints leak too much of the solution.

## Recommendation

If we build this, I would start with:
- one canonical underlying state model,
- one shared action vocabulary,
- one clean human UI,
- one structured model API,
- and one replay viewer that can visualize both trajectories the same way.

That replay viewer is important. It will probably teach us more than aggregate scores.

## Build-Later Notes

When we eventually implement, the stack could look like:
- backend environment service for state, grading, and replay,
- web app for human play,
- API client for model play,
- unified telemetry schema for both.

But that is intentionally deferred. The planning priority is to define fairness, observability, and score validity before we build any interface.
