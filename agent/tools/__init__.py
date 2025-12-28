from agent.tools.code_tool import code_tool 
from agent.tools.rag_tool import rag_tool 
from agent.tools.search_tool import search_tool
from agent.tools.formatter_tool import formatter_tool
from agent.tools.learning_tracker_tool import learning_tracker_tool
from agent.tools.solution_validator_tool import solution_validator_tool

# Compatibility shim: some langchain versions expose a `Tool` class at
# `langchain.tools.Tool`, while newer versions use a different API. To avoid
# import-time failures in environments with different langchain versions, we
# provide a minimal local `Tool` symbol that matches the expected lightweight
# shape used across this project: Tool(name=str, description=str, func=callable).
try:
    # prefer the real Tool if available
    from langchain.tools import Tool as _RealTool  # type: ignore
    Tool = _RealTool
except Exception:
    # Provide a minimal shim
    class Tool:
        def __init__(self, *args, name=None, description=None, func=None, **kwargs):
            # Accept both positional legacy signature and keyword args
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

__all__ = ["code_tool", "rag_tool", "search_tool", "formatter_tool", "learning_tracker_tool", "solution_validator_tool", "Tool"]

# export tool instances as a list
TOOLS_LIST = [
    code_tool,
    rag_tool,
    search_tool,
    formatter_tool,
    learning_tracker_tool,
    solution_validator_tool
]


def to_langchain_tools(tools):
    """
    Convert the repository's lightweight tool objects into a list of
    langchain-compatible tools suitable for LLM.bind_tools and ToolNode.
    
    Input: iterable of tool-like objects (instances from this repo)
    Output: list of LangChain Tool instances
    """
    out = []
    # Import LangChain's tool decorator
    try:
        from langchain_core.tools import tool as tool_decorator
    except ImportError:
        try:
            from langchain.tools import tool as tool_decorator
        except ImportError:
            tool_decorator = None
    
    if tool_decorator is None:
        raise RuntimeError("Cannot import LangChain tool decorator")
    
    for t in tools:
        # Extract attributes from the lightweight Tool shim used in this repo
        name = getattr(t, 'name', None) or (getattr(t, 'func', None) and getattr(t.func, '__name__', None)) or str(t)
        description = getattr(t, 'description', '') or ''
        func = getattr(t, 'func', None)
        
        if func is None and hasattr(t, 'run'):
            func = getattr(t, 'run')
        if func is None and callable(t):
            func = t
            
        if func is None:
            continue
            
        # Create a wrapper function with proper docstring for LangChain
        def make_tool_wrapper(original_func, tool_name, tool_desc):
            def wrapper(query: str) -> str:
                """Wrapper function that calls the original tool."""
                try:
                    return original_func(query)
                except Exception as e:
                    return f"Tool execution error: {str(e)}"
            
            # Set proper attributes
            wrapper.__name__ = tool_name
            wrapper.__doc__ = tool_desc
            return wrapper
        
        # Create the wrapper
        tool_func = make_tool_wrapper(func, name, description)
        
        # Use LangChain's tool decorator to create a proper Tool
        lc_tool = tool_decorator(tool_func)
        out.append(lc_tool)
    
    return out


# Export the tools


def get_bindable_tools():
    """Return the converted, langchain-bindable tool objects (used by agent creation).

    Frontends can use `get_tools_manifest()` to show available tools and
    `call_tool(name, input)` to invoke them without depending on langchain.
    """
    return to_langchain_tools(TOOLS_LIST)


def get_tools_manifest():
    """Return a simple manifest (list of dicts) describing available tools.

    Each entry contains 'name' and 'description' keys suitable for a UI.
    """
    tools = to_langchain_tools(TOOLS_LIST)
    manifest = []
    for t in tools:
        name = getattr(t, '__name__', None) or getattr(t, 'name', None) or str(t)
        desc = getattr(t, 'description', None) or ''
        manifest.append({'name': name, 'description': desc})
    return manifest


def call_tool(name: str, inp=None):
    """Invoke a tool by name using the adapter-produced tool objects.

    This is a simple, synchronous helper a frontend backend can call.
    It prefers `.run()` if available, otherwise calls the object directly.
    """
    tools = to_langchain_tools(TOOLS_LIST)
    for t in tools:
        tname = getattr(t, '__name__', None) or getattr(t, 'name', None)
        if not tname:
            continue
        if tname == name or (isinstance(tname, str) and name in tname):
            # prefer run()
            if hasattr(t, 'run') and callable(getattr(t, 'run')):
                return t.run(inp)
            # prefer .func attribute
            if hasattr(t, 'func') and callable(getattr(t, 'func')):
                return t.func(inp)
            # finally try calling directly
            if callable(t):
                return t(inp)
            raise RuntimeError(f"Tool '{name}' is not callable in this environment")
    raise RuntimeError(f"Tool '{name}' not found")