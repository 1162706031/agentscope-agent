# -*- coding: utf-8 -*-
"""Tests for controlled keyword-to-URL navigation."""
import inspect
import unittest

from agentscope.tool import Toolkit
from tools.agent_browser import PAGE_TARGETS, _match_page, agent_browser


class PageMatchingTests(unittest.TestCase):
    def test_exact_product_and_common_page_matches(self) -> None:
        cases = {
            "H13": "/products/hot-work/h13/",
            "1.2379": "/products/cold-work/12379/",
            "冷作模具钢": "/products/cold-work/",
            "公司简介": "/about/",
            "联系方式": "/contact/",
            "牌号对照表": "/products/comparison/",
        }

        for keyword, expected_path in cases.items():
            with self.subTest(keyword=keyword):
                self.assertEqual(_match_page(keyword).path, expected_path)

    def test_case_and_separators_are_normalized(self) -> None:
        cases = {
            "skd-11": "/products/cold-work/skd11/",
            "Cr12 MoV": "/products/cold-work/cr12mov/",
            "1 ． 2 3 4 4": "/products/hot-work/12344/",
            "HIGH_SPEED-STEEL": "/products/high-speed/",
        }

        for keyword, expected_path in cases.items():
            with self.subTest(keyword=keyword):
                self.assertEqual(_match_page(keyword).path, expected_path)

    def test_minor_typographical_errors_are_tolerated(self) -> None:
        self.assertEqual(
            _match_page("SKD-1l").path,
            "/products/cold-work/skd11/",
        )
        self.assertEqual(
            _match_page("冷做模具钢").path,
            "/products/cold-work/",
        )

    def test_specific_product_wins_over_contained_category(self) -> None:
        self.assertEqual(
            _match_page("H13 热作模具钢").path,
            "/products/hot-work/h13/",
        )
        self.assertEqual(
            _match_page("M2 高速工具钢").path,
            "/products/high-speed/m2/",
        )

    def test_empty_or_unrelated_keyword_fails(self) -> None:
        for keyword in (
            "",
            " - _ ",
            "天气预报",
            "H1",
            "M4",
        ):
            with self.subTest(keyword=keyword):
                with self.assertRaises(ValueError):
                    _match_page(keyword)

    def test_registry_paths_are_unique_and_controlled(self) -> None:
        paths = [target.path for target in PAGE_TARGETS]
        self.assertEqual(len(paths), 42)
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(all(path.startswith("/") for path in paths))
        self.assertTrue(all("://" not in path for path in paths))

    def test_every_registered_name_and_alias_maps_to_its_page(self) -> None:
        for target in PAGE_TARGETS:
            for keyword in (target.name, *target.aliases):
                with self.subTest(page=target.name, keyword=keyword):
                    self.assertEqual(_match_page(keyword), target)


class AgentBrowserToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_uses_registry_url_in_metadata(self) -> None:
        response = await agent_browser("m42", "  M42 高速钢  ")

        self.assertEqual(response.metadata["action"], "page_navigation")
        self.assertEqual(
            response.metadata["payload"],
            {
                "url": "/products/high-speed/m42/",
                "content": "M42 高速钢",
            },
        )
        self.assertIn(
            response.metadata["payload"]["url"],
            {target.path for target in PAGE_TARGETS},
        )

    async def test_failed_match_raises_before_metadata_is_created(self) -> None:
        with self.assertRaises(ValueError):
            await agent_browser("不存在的页面", "不会触发导航")

    async def test_toolkit_converts_failed_match_without_navigation(self) -> None:
        toolkit = Toolkit()
        toolkit.register_tool_function(agent_browser)
        tool_call = {
            "type": "tool_use",
            "id": "failed-navigation",
            "name": "agent_browser",
            "input": {
                "keyword": "不存在的页面",
                "content": "不会触发导航",
            },
        }

        tool_result = await toolkit.call_tool_function(tool_call)
        responses = [response async for response in tool_result]

        self.assertEqual(len(responses), 1)
        self.assertIsNone(responses[0].metadata)
        self.assertTrue(responses[0].content[0]["text"].startswith("Error:"))

    def test_tool_accepts_keyword_instead_of_url(self) -> None:
        parameters = inspect.signature(agent_browser).parameters
        self.assertIn("keyword", parameters)
        self.assertNotIn("url", parameters)


if __name__ == "__main__":
    unittest.main()
