import unittest

from copilot.config import account, pricing
from copilot.cost import estimate
from copilot.metadata import build as build_metadata
from copilot.storyboard import brief_template, build_shots, validate_brief


class TestCost(unittest.TestCase):
    def test_standard_profile(self):
        result = estimate(180, "standard", pricing(), overhead_pct=0.0)
        # 180 * 1.8 * 0.8 * 0.99 + 180 * 1.8 * 0.2 * 2.48
        self.assertAlmostEqual(result["subtotal_cny"], 417.31, places=1)
        self.assertAlmostEqual(result["total_cny"], 417.31, places=1)
        self.assertAlmostEqual(result["monthly_4_videos_cny"], 1669.25, places=1)

    def test_unknown_profile(self):
        with self.assertRaises(ValueError):
            estimate(180, "nope", pricing())


class TestMetadata(unittest.TestCase):
    def setUp(self):
        self.episode = {
            "title": "敦煌壁画里的供养人",
            "series": "人间旧档",
            "hook": "她被画进壁画，却没有留下名字",
        }
        self.brief = {
            "hook": self.episode["hook"],
            "summary": "一个普通女子在敦煌留下的一笔供养，牵出一整个时代。",
            "sources": ["《敦煌石窟全集》", "敦煌研究院公开资料"],
            "tags": ["敦煌", "壁画"],
        }

    def test_platform_constraints(self):
        meta = build_metadata(account(), self.episode, self.brief)
        self.assertLessEqual(len(meta["douyin"]["title"]), 30)
        self.assertLessEqual(len(meta["douyin"]["tags"]), 5)
        self.assertTrue(all(tag.startswith("#") for tag in meta["douyin"]["tags"]))
        self.assertLessEqual(len(meta["bilibili"]["title"]), 80)
        self.assertEqual(meta["bilibili"]["partition"], "人文历史")
        self.assertIn("AI", meta["douyin"]["description"])
        self.assertIn("敦煌石窟全集", meta["douyin"]["description"])


class TestStoryboard(unittest.TestCase):
    def test_build_shots_covers_duration(self):
        episode = {"title": "测试", "series": "人间旧档", "hook": "钩子"}
        brief = brief_template(episode, account())
        shots = build_shots(180, brief)
        self.assertGreaterEqual(len(shots), 15)
        total = sum(shot["duration_sec"] for shot in shots)
        self.assertAlmostEqual(total, 180, delta=1.0)

    def test_validation_catches_missing_hook(self):
        episode = {"title": "测试", "series": "人间旧档"}
        brief = brief_template(episode, account())
        brief["hook"] = ""
        issues = validate_brief(brief)
        self.assertTrue(any("hook" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
