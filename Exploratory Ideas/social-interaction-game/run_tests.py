from __future__ import annotations

import unittest

from engine import SocialInteractionGame


class SocialInteractionGameTests(unittest.TestCase):
    def test_good_job_loss_response_beats_bad_one(self) -> None:
        good = "I'm really sorry. That sounds brutal. You do not have to figure everything out tonight, and I'm here with you."
        bad = "You should update your resume tonight and start networking immediately. What happened exactly? Did you see this coming?"

        game = SocialInteractionGame()
        game.reset("job-loss-support")
        good_result = game.step(good)

        game.reset("job-loss-support")
        bad_result = game.step(bad)

        self.assertGreater(good_result.total_score, bad_result.total_score)
        self.assertGreater(good_result.reward, 0.0)
        self.assertLess(bad_result.reward, 0.0)

    def test_boundary_violation_is_punished(self) -> None:
        response = "You should call her tonight and just apologize so this does not drag out."

        game = SocialInteractionGame()
        game.reset("post-argument-boundary")
        result = game.step(response)

        boundary_detail = next(detail for detail in result.details if detail.name == "boundary_respect")
        self.assertFalse(boundary_detail.passed)
        self.assertLess(result.total_score, 0.55)

    def test_celebration_response_rewards_energy_match(self) -> None:
        response = "That is actually so good. I know it was just one bug fix, but shipping the annoying one always feels amazing."

        game = SocialInteractionGame()
        game.reset("celebrate-small-win")
        result = game.step(response)

        self.assertGreater(result.total_score, 0.70)


if __name__ == "__main__":
    unittest.main()
