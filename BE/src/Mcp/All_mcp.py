
from agentscope.mcp import HttpStatelessClient


_web_search_client: HttpStatelessClient | None = None
_texttosql_client: HttpStatelessClient | None = None


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

def _get_texttosql () -> HttpStatelessClient:
    """Lazy-init shared text-to-SQL MCP client (stateless, no persistent session)."""
    global _texttosql_client
    if _texttosql_client is None:
        _texttosql_client = HttpStatelessClient(
            name="texttosql",
            transport="streamable_http",
            url="https://api.dify.ai/mcp/server/RMUM8pAIlOZYZQVS/mcp",
        )
    return _texttosql_client