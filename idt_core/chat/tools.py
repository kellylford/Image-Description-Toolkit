"""Web search tools for tool-capable chat models.

Ollama's hosted search API (https://docs.ollama.com/capabilities/web-search)
gives any local model access to current information through tool calling: the
model is offered ``web_search``/``web_fetch`` as tools, decides when to call
them, and the results are fed back as tool messages. Only the search request
itself leaves the machine — the conversation still runs on the local model.

Auth is an ollama.com API key (free account), resolved through
``idt_core.keys`` under the pseudo-provider name ``"ollama.com"`` — it is a
different credential from anything the chat provider itself needs, which is
why it does not hang off the ``ollama`` provider entry.

Transport is stdlib ``urllib`` on purpose: the ``ollama`` package gained its
own ``web_search`` helper only in recent versions, and a frozen build must not
depend on which version got bundled.

A failed tool call returns its error **as the tool result string** rather than
raising: the model can still answer from its own knowledge, and the user sees
why the search did not happen. A missing key is a message telling the person
how to get one.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import List, Optional

__all__ = [
    "WEB_TOOL_NAMES",
    "execute_web_tool",
    "web_search_available",
    "missing_web_key_message",
    "web_tool_definitions",
]

OLLAMA_WEB_API = "https://ollama.com/api"
REQUEST_TIMEOUT_SECONDS = 30

DEFAULT_SEARCH_RESULTS = 5
MAX_SEARCH_RESULTS = 10
#: Per-result snippet cap. Results ride inside the model's context window,
#: which the provider floors at 32k when tools are on — five 2k-char snippets
#: fit comfortably; whole pages would not.
SEARCH_RESULT_CHAR_LIMIT = 2_000
FETCH_CHAR_LIMIT = 8_000
FETCH_LINK_LIMIT = 20

WEB_TOOL_NAMES = ("web_search", "web_fetch")


def web_tool_definitions() -> List[dict]:
    """Tool schemas in Ollama's /api/chat wire format."""
    return [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": (
                    "Search the web for current information. Returns result "
                    "titles, URLs, and content snippets."
                ),
                "parameters": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query.",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "How many results to return (1-10).",
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "web_fetch",
                "description": "Fetch the readable content of one web page.",
                "parameters": {
                    "type": "object",
                    "required": ["url"],
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Absolute URL of the page to fetch.",
                        },
                    },
                },
            },
        },
    ]


def _api_key() -> Optional[str]:
    from ..keys import resolve_api_key

    return resolve_api_key("ollama.com")


def web_search_available() -> bool:
    """True when a web-search API key can be resolved."""
    return bool(_api_key())


def missing_web_key_message() -> str:
    return (
        "Web search needs an ollama.com API key (free account). Create one at "
        "https://ollama.com/settings/keys and set the OLLAMA_API_KEY "
        "environment variable, or add it as 'ollama.com' under api_keys in "
        "the configuration."
    )


def _call_api(endpoint: str, payload: dict, key: str) -> dict:
    request = urllib.request.Request(
        f"{OLLAMA_WEB_API}/{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _clip(text: str, limit: int) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + " …[truncated]"


def _web_search(arguments: dict, key: str) -> str:
    query = str(arguments.get("query", "")).strip()
    if not query:
        return "web_search error: no query was given."

    try:
        wanted = int(arguments.get("max_results", DEFAULT_SEARCH_RESULTS))
    except (TypeError, ValueError):
        wanted = DEFAULT_SEARCH_RESULTS
    wanted = max(1, min(wanted, MAX_SEARCH_RESULTS))

    data = _call_api("web_search", {"query": query, "max_results": wanted}, key)
    results = data.get("results") or []
    if not results:
        return f"No web results for: {query}"

    trimmed = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": _clip(r.get("content", ""), SEARCH_RESULT_CHAR_LIMIT),
        }
        for r in results
    ]
    return json.dumps({"query": query, "results": trimmed}, ensure_ascii=False)


def _web_fetch(arguments: dict, key: str) -> str:
    url = str(arguments.get("url", "")).strip()
    if not url:
        return "web_fetch error: no URL was given."

    data = _call_api("web_fetch", {"url": url}, key)
    return json.dumps(
        {
            "url": url,
            "title": data.get("title", ""),
            "content": _clip(data.get("content", ""), FETCH_CHAR_LIMIT),
            "links": (data.get("links") or [])[:FETCH_LINK_LIMIT],
        },
        ensure_ascii=False,
    )


def execute_web_tool(name: str, arguments: dict) -> str:
    """Run one web tool call and return its result as a string.

    Never raises: errors come back as text so the model can still answer and
    the transcript shows what went wrong.
    """
    key = _api_key()
    if not key:
        return missing_web_key_message()

    try:
        if name == "web_search":
            return _web_search(arguments or {}, key)
        if name == "web_fetch":
            return _web_fetch(arguments or {}, key)
        return f"Unknown tool: {name}"
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return (
                f"{name} failed: the ollama.com API key was rejected "
                f"(HTTP {exc.code}). Check OLLAMA_API_KEY."
            )
        return f"{name} failed: HTTP {exc.code} from ollama.com."
    except Exception as exc:  # noqa: BLE001 - a tool failure must not fail the turn
        return f"{name} failed: {exc}"


def tool_result_summary(name: str, result: str) -> str:
    """One user-facing line about a finished tool call."""
    if name == "web_search":
        try:
            count = len(json.loads(result).get("results", []))
            return f"Found {count} result(s)"
        except (ValueError, AttributeError):
            return _clip(result, 120)
    if name == "web_fetch":
        return "Page retrieved"
    return "Done"
