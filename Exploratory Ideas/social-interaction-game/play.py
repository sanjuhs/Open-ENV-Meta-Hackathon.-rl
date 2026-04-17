from __future__ import annotations

import argparse

from engine import SocialInteractionGame


def print_observation(obs: dict) -> None:
    print(f"\nScenario: {obs['title']} [{obs['scenario_id']}]")
    print(f"Relationship stage: {obs['relationship_stage']}")
    print(f"Persona: {obs['persona_name']} — {obs['persona_style']}")
    print(f"Context: {obs['visible_context']}")
    print(f"Turn {obs['turn_index']}/{obs['max_turns']}")
    print(f"Relationship: {obs['relationship_summary']}")
    print(f"\nUser: {obs['current_user_message']}\n")


def print_result(result) -> None:
    print(f"\nBand: {result.band}")
    print(f"Total score: {result.total_score:.3f}")
    print(f"Reward: {result.reward:+.3f}")
    print("Breakdown:")
    for detail in result.details:
        marker = "PASS" if detail.passed else "FAIL"
        print(f"  - {detail.name:20s} {detail.score:.2f} [{marker}] {detail.reason}")

    print(
        "State: "
        f"trust={result.relationship_state.trust:.2f}, "
        f"closeness={result.relationship_state.closeness:.2f}, "
        f"irritation={result.relationship_state.irritation:.2f}"
    )
    print(f"Summary: {result.relationship_summary}")
    if not result.done and result.next_user_message:
        print(f"\nUser follow-up: {result.next_user_message}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Play-test the social interaction RLVR prototype.")
    parser.add_argument("--list", action="store_true", help="List the hand-authored scenarios.")
    parser.add_argument("--scenario", type=str, help="Scenario id to load.")
    parser.add_argument("--procedural-seed", type=int, help="Generate a procedural scenario with the given seed.")
    parser.add_argument("--debug", action="store_true", help="Show the secret verifier rules.")
    parser.add_argument("--response", type=str, help="Score a single response and exit.")
    parser.add_argument("--auto", action="store_true", help="Let the baseline bot play the whole scenario.")
    args = parser.parse_args()

    game = SocialInteractionGame()

    if args.list:
        print("Available scenarios:")
        for scenario_id, scenario in game.available_scenarios().items():
            print(f"  - {scenario_id:22s} {scenario.title}")
        return

    scenario_id = args.scenario
    seed = args.procedural_seed or 0
    obs = game.reset(scenario_id=scenario_id, seed=seed)

    print_observation(obs)
    if args.debug:
        print("Secret rules:")
        for key, value in game.secret_rules().items():
            print(f"  - {key}: {value}")

    if args.response is not None:
        result = game.step(args.response)
        print_result(result)
        return

    if args.auto:
        while True:
            result = game.autoplay_step()
            print(f"\nBaseline AI response: {result.assistant_response}")
            print_result(result)
            if result.done:
                print("\nEpisode complete.")
                return

    while True:
        raw = input("\nYour response> ").strip()
        if raw.lower() in {"quit", "exit"}:
            print("Ending session.")
            return
        if not raw:
            print("Enter a response or type 'quit'.")
            continue

        result = game.step(raw)
        print_result(result)
        if result.done:
            print("\nEpisode complete.")
            return


if __name__ == "__main__":
    main()
