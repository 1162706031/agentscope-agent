
from agentscope.mcp import HttpStatelessClient


_web_search_client: HttpStatelessClient | None = None

def _get_web_search_client() -> HttpStatelessClient:
    """Lazy-init shared web-search MCP client (stateless, no persistent session)."""
    global _web_search_client
    if _web_search_client is None:
        _web_search_client = HttpStatelessClient(
            name="web_search",
            transport="streamable_http",
            url="http://47.94.179.114:3000/mcp",
        )
    return _web_search_client