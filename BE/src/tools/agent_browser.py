# -*- coding: utf-8 -*-
"""Keyword-based website navigation for Xufeng New Material."""
from dataclasses import dataclass
from difflib import SequenceMatcher
import unicodedata

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse

BASE_URL = "https://www.xufengmaterial.com.cn"
MIN_MATCH_SCORE = 0.72


@dataclass(frozen=True)
class PageTarget:
    """A page that can be selected by one or more controlled aliases."""

    name: str
    path: str
    aliases: tuple[str, ...]
    specificity: int = 0


PAGE_TARGETS: tuple[PageTarget, ...] = (
    # Common pages
    PageTarget("首页", "/", ("首页", "主页", "官网首页", "home")),
    PageTarget(
        "关于我们",
        "/about/",
        ("关于我们", "公司简介", "公司介绍", "企业简介", "企业介绍", "about"),
    ),
    PageTarget(
        "产品中心",
        "/products/",
        ("产品中心", "全部产品", "产品列表", "products"),
    ),
    PageTarget(
        "牌号对照表",
        "/products/comparison/",
        ("牌号对照表", "牌号对照", "钢号对照表", "材料对照表", "comparison"),
    ),
    PageTarget(
        "产品规格表",
        "/products/specs/",
        ("产品规格表", "规格表", "尺寸规格", "specifications", "specs"),
    ),
    PageTarget(
        "联系我们",
        "/contact/",
        ("联系我们", "联系方式", "联系电话", "电话地址", "公司地址", "contact"),
    ),
    # Product categories
    PageTarget(
        "冷作模具钢",
        "/products/cold-work/",
        (
            "冷作模具钢",
            "冷作钢",
            "冷作",
            "cold work die steel",
            "cold work steel",
            "coldwork",
        ),
        1,
    ),
    PageTarget(
        "热作模具钢",
        "/products/hot-work/",
        (
            "热作模具钢",
            "热作钢",
            "热作",
            "hot work die steel",
            "hot work steel",
            "hotwork",
        ),
        1,
    ),
    PageTarget(
        "塑料模具钢",
        "/products/plastic-mold/",
        ("塑料模具钢", "塑胶模具钢", "塑料模钢", "plastic mold steel", "plasticmold"),
        1,
    ),
    PageTarget(
        "高速工具钢",
        "/products/high-speed/",
        (
            "高速工具钢",
            "高速钢",
            "high speed steel",
            "high speed tool steel",
            "hss",
        ),
        1,
    ),
    # Cold-work die steel
    PageTarget("Cr12MoV", "/products/cold-work/cr12mov/", ("Cr12MoV",), 2),
    PageTarget("Cr12", "/products/cold-work/cr12/", ("Cr12",), 2),
    PageTarget("SKD11", "/products/cold-work/skd11/", ("SKD11",), 2),
    PageTarget("D2", "/products/cold-work/d2/", ("D2",), 2),
    PageTarget("DC53", "/products/cold-work/dc53/", ("DC53",), 2),
    PageTarget("1.2379", "/products/cold-work/12379/", ("1.2379", "12379"), 2),
    PageTarget("1.2436", "/products/cold-work/12436/", ("1.2436", "12436"), 2),
    PageTarget("1.2510", "/products/cold-work/12510/", ("1.2510", "12510"), 2),
    PageTarget("1.2601", "/products/cold-work/12601/", ("1.2601", "12601"), 2),
    PageTarget("9CrWMn", "/products/cold-work/9crwmn/", ("9CrWMn",), 2),
    PageTarget("Cr8Mo2SiV", "/products/cold-work/cr8mo2siv/", ("Cr8Mo2SiV",), 2),
    PageTarget("Cr12Mo1V1", "/products/cold-work/cr12mo1v1/", ("Cr12Mo1V1",), 2),
    # Hot-work die steel
    PageTarget("H13", "/products/hot-work/h13/", ("H13",), 2),
    PageTarget("1.2344", "/products/hot-work/12344/", ("1.2344", "12344"), 2),
    PageTarget("SKD61", "/products/hot-work/skd61/", ("SKD61",), 2),
    PageTarget("4Cr5MoSiV", "/products/hot-work/4cr5mosiv/", ("4Cr5MoSiV",), 2),
    PageTarget("H11", "/products/hot-work/h11/", ("H11",), 2),
    PageTarget("1.2343", "/products/hot-work/12343/", ("1.2343", "12343"), 2),
    PageTarget("8407", "/products/hot-work/8407/", ("8407",), 2),
    PageTarget("8418", "/products/hot-work/8418/", ("8418",), 2),
    PageTarget("1.2367", "/products/hot-work/12367/", ("1.2367", "12367"), 2),
    PageTarget("5CrNiMo", "/products/hot-work/5crnimo/", ("5CrNiMo",), 2),
    PageTarget("1.2714", "/products/hot-work/12714/", ("1.2714", "12714"), 2),
    PageTarget("3Cr2W8V", "/products/hot-work/3cr2w8v/", ("3Cr2W8V",), 2),
    # Plastic mold steel
    PageTarget("718H", "/products/plastic-mold/718h/", ("718H",), 2),
    PageTarget("P20", "/products/plastic-mold/p20/", ("P20",), 2),
    PageTarget("S136", "/products/plastic-mold/s136/", ("S136",), 2),
    PageTarget("NAK80", "/products/plastic-mold/nak80/", ("NAK80",), 2),
    # High-speed tool steel
    PageTarget("M2", "/products/high-speed/m2/", ("M2",), 2),
    PageTarget("M35", "/products/high-speed/m35/", ("M35",), 2),
    PageTarget("M42", "/products/high-speed/m42/", ("M42",), 2),
    PageTarget("M51", "/products/high-speed/m51/", ("M51",), 2),
)


def _normalize_keyword(value: str) -> str:
    """Normalize case, width and separators while preserving Unicode text."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _alias_score(keyword: str, alias: str) -> float:
    """Score a normalized keyword against a normalized page alias."""
    if keyword == alias:
        return 1.0
    if _contains_alias(keyword, alias):
        return 0.95
    if len(keyword) >= 3 and keyword in alias:
        return 0.9
    if min(len(keyword), len(alias)) < 3:
        return 0.0
    return SequenceMatcher(None, keyword, alias).ratio()


def _contains_alias(keyword: str, alias: str) -> bool:
    """Check containment without treating a product code as a prefix."""
    if not (alias.isascii() and alias.isalnum()):
        return alias in keyword

    start = keyword.find(alias)
    while start >= 0:
        end = start + len(alias)
        left_is_ascii_alnum = (
            start > 0
            and keyword[start - 1].isascii()
            and keyword[start - 1].isalnum()
        )
        right_is_ascii_alnum = (
            end < len(keyword)
            and keyword[end].isascii()
            and keyword[end].isalnum()
        )
        if not left_is_ascii_alnum and not right_is_ascii_alnum:
            return True
        start = keyword.find(alias, start + 1)

    return False


def _match_page(keyword: str) -> PageTarget:
    """Return the best controlled page target or raise for a weak match."""
    normalized_keyword = _normalize_keyword(keyword)
    if not normalized_keyword:
        raise ValueError("页面关键词不能为空")

    best_target: PageTarget | None = None
    best_rank = (-1.0, -1, -1)

    for target in PAGE_TARGETS:
        for alias in (target.name, *target.aliases):
            normalized_alias = _normalize_keyword(alias)
            score = _alias_score(normalized_keyword, normalized_alias)
            rank = (score, target.specificity, len(normalized_alias))
            if rank > best_rank:
                best_target = target
                best_rank = rank

    if best_target is None or best_rank[0] < MIN_MATCH_SCORE:
        raise ValueError(f"未找到与关键词“{keyword.strip()}”匹配的官网页面")

    return best_target


async def agent_browser(
    keyword: str,
    content: str,
) -> ToolResponse:
    """Navigate to the controlled website page best matching ``keyword``.

    Use this tool for a product grade, product category, company page, contact
    page, comparison table, or specification table. The tool owns the URL
    mapping; callers should provide a short page keyword instead of a URL.

    Args:
        keyword:
            A concise page keyword, such as "H13", "冷作模具钢", "公司简介",
            or "联系方式". Minor spelling errors are tolerated.
        content:
            A brief description displayed alongside the navigation, such as
            product hardness, typical applications, or a page summary.

    Returns:
        A page-navigation action containing a URL from the controlled registry.

    Raises:
        ValueError: If the keyword is empty or no page reaches the match
            confidence threshold.
    """
    target = _match_page(keyword)
    content = content.strip()
    full_url = BASE_URL + target.path

    return ToolResponse(
        content=[
            TextBlock(
                type="text",
                text=f"已打开页面: {full_url}\n{content}",
            ),
        ],
        metadata={
            "action": "page_navigation",
            "payload": {
                "url": target.path,
                "content": content,
            },
        },
        is_last=True,
    )
