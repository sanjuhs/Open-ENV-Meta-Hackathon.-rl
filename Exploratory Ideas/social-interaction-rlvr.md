# Social Interaction RLVR Notes

## Core Thesis

Social interaction looks fuzzy, but a surprising amount of it can be modeled as **hidden state + observable constraints + verifiable invariants**.

The reward function should not try to identify a single perfect sentence. It should instead check whether a response is compatible with:

- the current conversational situation
- the hidden emotional state
- the partner's preferences and boundaries
- the long-horizon relationship dynamics

That makes this closer to a simulator with checkable properties than a pure text-generation benchmark.

## Why This Can Be RLVR

Hashing and physics-style environments are attractive because verification is cheap once the environment is specified. Social interaction can move in the same direction if we score:

- factual consistency
- acknowledgement of what was said
- relevance to the active topic
- boundary respect
- emotional trajectory
- initiative balance
- long-horizon trust change

These are not exact-text rewards. They are **constraint-satisfaction rewards over a hidden world model**.

## Approach 1: Conversation as a Formal Constraint Game

Conversation should not be reduced to a tiny decision tree. That collapses the action space too early.

A better framing is Sudoku-like:

- the agent can say many different things
- the environment does not prescribe one path
- the environment verifies whether the response satisfies a set of constraints

Candidate social constraints:

- acknowledge the user's message before pivoting
- remain relevant to the active topic
- do not exceed the persona's preferred response length
- do not escalate intensity faster than the user
- do not revisit banned topics after a boundary is set
- do not contradict facts established earlier in the episode

## Approach 2: Grice-Inspired Computable Properties

Grice's Maxims are a useful bridge between philosophy and RLVR.

### Quantity

The response should contain enough information, but not overload the user.

Possible checks:

- word-count range relative to scenario
- compression / verbosity heuristics
- information density compared with the input

### Relation

The response should stay on topic and advance the conversation.

Possible checks:

- token overlap with the active topic anchors
- embedding-based relevance later, if we decide to add a neural verifier
- penalty for subject shifts before acknowledgement

### Manner

The response should be clear and easy to parse.

Possible checks:

- readability heuristics
- sentence-count bounds
- ambiguity or run-on penalties

### Quality

In social environments this often means emotional sincerity and situational fit, not only factual truth.

For V1, quality can be approximated through:

- contradiction checks
- supportiveness heuristics
- agreement with scenario facts

## Approach 3: Emotional Dynamics as a Small Deterministic System

The "calorie counting" analogy is useful here. We do not need a perfect model of emotion to get a useful signal.

One practical reduction is a VAD-style space:

- valence
- arousal
- dominance

The environment can define acceptable response regions:

- upset user: respond with supportive, calming, not dismissive
- excited user: match energy without derailing
- boundary-setting user: respond with lower arousal and higher respect

This becomes a geometric verification problem:

- estimate the response's emotional coordinates
- check whether they land inside the target zone
- combine that with other invariants so the agent cannot game the signal with empty phrases

## Approach 4: Protocol Verification via Invariants

Distributed systems are often verified by checking invariants rather than evaluating vague holistic quality. Social interaction can use the same move.

Useful invariants:

- acknowledgement invariant: respond to what the user actually said
- consistency invariant: do not contradict established facts
- escalation invariant: do not intensify faster than the user
- initiative invariant: do not interrogate or monologue beyond the persona's tolerance
- boundary invariant: once a topic is disallowed, do not revisit it

Each invariant is individually simple. Together they create a much harder-to-game environment.

## Approach 5: Procedurally Generated Social Scenarios

This is the most RLVR-native route.

Instead of evaluating generic open-ended conversation, generate a structured social situation:

- user event
- emotional state
- partner persona
- relationship phase
- preferences
- boundary conditions
- desired emotional trajectory

Then derive the verifier from the scenario itself.

Example:

- Event: "I got fired today."
- User state: sad, anxious, low energy
- Preference: dislikes unsolicited advice
- Constraint: brief response, empathy first, at most one question

The verifier can then check:

- no advice phrases
- empathy markers present
- response length in range
- topic acknowledged
- emotional tone is calming and supportive

This is close to the hash-function analogy: the scenario determines the valid output region, and verification is cheap once the rules are known.

## Recommended Prototype Shape

The prototype should be a scoring function plus a small hidden-state simulator:

- input: scenario + current conversation turn + candidate response
- output: reward breakdown across verifiable axes

Initial scoring axes:

- acknowledgement
- relevance
- empathy markers
- advice-policy compliance
- question-count balance
- length appropriateness
- boundary respect
- emotional alignment

Long-horizon state:

- trust
- closeness
- irritation

The world state should update after each turn, so the agent is learning more than one-shot sympathy lines.

## Why Start Rule-Based

V1 should stay inspectable.

Rule-based verification is a feature here because:

- the reward is easier to debug
- the agent cannot hide behind a judge model
- human testing is straightforward
- failure modes are legible

Once the hand-built verifier works, we can selectively add stronger signals later.

## Prototype Workflow

1. Hand-author a small number of scenarios.
2. Implement deterministic verifiers.
3. Play the game as a human and check whether good responses score well.
4. Write adversarial responses and make sure they score poorly.
5. Only then attach a model or RL loop.

## Initial Warning

The phrase "girlfriend simulator" is broad enough to become mushy quickly.

The environment becomes much stronger if we narrow it to subgames like:

- responding to bad news without over-advising
- conflict repair after a misunderstanding
- remembering preferences across turns
- respecting explicitly stated boundaries
- matching positive energy during celebration without becoming generic

That is the path from a fuzzy social idea to a real RLVR environment.
