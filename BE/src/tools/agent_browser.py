# -*- coding: utf-8 -*-
"""Agent browser navigation tool for Xufeng New Material website."""
from agentscope.tool import ToolResponse
from agentscope.message import TextBlock

BASE_URL = "https://www.xufengmaterial.com.cn"


async def agent_browser(
    url: str,
    content: str,
) -> ToolResponse:
    """Navigate to a page on the Xufeng New Material (旭丰新材料) official website.

    Use this tool when the user asks about a specific product grade, product
    category, or wants to view a particular page on the company website. It
    returns a page_navigation action that the frontend will use to navigate the
    user's browser.

    Args:
        url:
            The URL path to navigate to. Can be a relative path (e.g.
            "/products/cold-work/d2/") or a full URL starting with
            "https://www.xufengmaterial.com.cn". Relative paths will be
            automatically prefixed with the base URL.
        content:
            A brief description to display alongside the navigation, e.g.
            product hardness, typical applications, or page summary.

    Returns:
        ToolResponse:
            A structured JSON action for page navigation.
    """
    # Normalize URL: ensure it starts with /
    url = url.strip()
    if not url.startswith("/") and not url.startswith("http"):
        url = "/" + url
    if url.startswith("/"):
        full_url = BASE_URL + url
    else:
        full_url = url

    # Normalize content
    content = content.strip()

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
                "url": url if url.startswith("/") else full_url,
                "content": content,
            },
        },
        is_last=True,
    )
