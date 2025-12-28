try:
    from langchain.tools import Tool
except Exception:
    class Tool:
        def __init__(self, *args, name=None, description=None, func=None, **kwargs):
            if len(args) >= 1 and name is None:
                name = args[0]
            if len(args) >= 2 and description is None:
                description = args[1]
            self.name = name or "tool"
            self.description = description or ""
            self.func = func

        def __call__(self, *args, **kwargs):
            if callable(self.func):
                return self.func(*args, **kwargs)
            raise RuntimeError('Tool function is not callable')
import os
import importlib

# Determine which search wrapper to use based on environment variables
# Preference: CUSTOM_SEARCH_API_KEY (user-provided) -> GOOGLE_SEARCH_API_KEY
search_tool_query = None

# NOTE: GOOGLE_API_KEY is used by the Gemini LLM; do not reuse it for search unless
# an explicit search API key is provided as GOOGLE_SEARCH_API_KEY. Prefer the
# CUSTOM_SEARCH_API_KEY (user-provided) for Custom Search.
google_llm_key = os.getenv('GOOGLE_API_KEY')  # reserved for LLM
google_search_key = os.getenv('GOOGLE_SEARCH_API_KEY')
google_cse_id = os.getenv('GOOGLE_CSE_ID')
custom_search_key = os.getenv('CUSTOM_SEARCH_API_KEY')
search_engine_url = os.getenv('SEARCH_ENGINE')

# Determine the search API key to use (preference order: CUSTOM_SEARCH_API_KEY, GOOGLE_SEARCH_API_KEY)
search_api_key = custom_search_key or google_search_key

# if we don't have a CSE id but the user provided SEARCH_ENGINE url, try to parse the 'cx' query param
if not google_cse_id and search_engine_url:
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(search_engine_url)
        qs = parse_qs(parsed.query)
        cx_list = qs.get('cx') or qs.get('cx=')
        if cx_list:
            google_cse_id = cx_list[0]
    except Exception:
        # ignore parse errors; google_cse_id may remain None
        pass

if search_api_key:
    try:
        google_module = importlib.import_module('langchain_community.utilities')
        GoogleSearchAPIWrapper = getattr(google_module, 'GoogleSearchAPIWrapper')
        # pass the determined search_api_key into the wrapper
        search_tool_query = GoogleSearchAPIWrapper(google_api_key=search_api_key, google_cse_id=google_cse_id)
        print(f"✅ Google Search initialized with API key and CSE ID: {google_cse_id}")
    except Exception as e:
        print(f"⚠️ Failed to initialize Google Search: {e}")
        search_tool_query = None

if search_tool_query is None:
    # Fallback: a callable that raises with clear instructions when invoked
    def _missing_search(query: str) -> str:
        raise RuntimeError(
            "No search API credentials found. Set SERPAPI_API_KEY or GOOGLE_API_KEY and GOOGLE_CSE_ID in your .env to enable search."
        )
    # wrap into an object with .run for compatibility with Tool expected callable
    class _MissingWrapper:
        def run(self, q):
            return _missing_search(q)
    search_tool_query = _MissingWrapper()

# tool object definition
search_tool = Tool(
    "declare tool name, a system prompt detailing when to use the tool, and the function to call the tool",
    name='google_realtime_search',
    description="""
Tool Name: google_realtime_search
Action: Executes a live web search query and returns up-to-date, external information from the public internet.
Input Constraint: The input MUST be a concise, precise, and highly focused search query string (e.g., 'latest version of Python').
Use Case: Use this tool **ONLY** for answering questions that require:
1.  Real-time data (e.g., current dates, news, stock prices, weather).
2.  General knowledge that is not related to the user's uploaded course documents.
3.  External facts or common knowledge not retrieved by the 'course_knowledge_search' (RAG) tool.
Forbidden Use: DO NOT use this tool for questions about the user's private study documents or for solving math problems.
""",
    func=search_tool_query.run,
)