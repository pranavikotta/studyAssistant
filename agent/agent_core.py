from agent.rag_logic.main import load_environment_variables
from agent.tools.__init__ import TOOLS_LIST, to_langchain_tools
from typing import TypedDict, List
from typing_extensions import Annotated
import os
from langchain_core.messages import BaseMessage
# Try to import common message classes to construct proper messages when callers
# supply lightweight tuples like ('user', 'text'). If unavailable, we fall back
# to passing through the original objects and rely on the LLM to handle them.
try:
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
except Exception:
    HumanMessage = AIMessage = SystemMessage = None
from langchain_core.tools import Tool

# If langgraph is not import-resolvable at static analysis time, provide safe fallbacks
try:
    from langgraph.graph.message import add_messages
except Exception:
    def add_messages(x):
        return x

LLM_WITH_TOOLS = None #global variable to hold LLM with bound tools

#creation of agent state type to be passed between nodes
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages] #stores messages sent and received by the agent

#define LLM node
def call_model(state: AgentState) -> dict:
    global LLM_WITH_TOOLS
    if LLM_WITH_TOOLS is None:
        raise RuntimeError("LLM_WITH_TOOLS is not initialized.")
    # langgraph auto handles passing entire state[messages] to LLM
    messages = state.get('messages', [])
    
    # Import and add system prompt if not already present
    from agent.agent_prompts import STUDY_ASSISTANT_SYSTEM_PROMPT
    has_system_msg = any(isinstance(m, SystemMessage) for m in messages if isinstance(m, BaseMessage))
    
    coerced = []
    # Add system message at the start if not present
    if not has_system_msg and SystemMessage is not None:
        coerced.append(SystemMessage(content=STUDY_ASSISTANT_SYSTEM_PROMPT))
    try:
        for m in messages:
            if m is None:
                continue
            # tuple/list like ('user','text')
            if isinstance(m, (list, tuple)) and len(m) >= 2:
                role = m[0]
                content = m[1]
                if HumanMessage is not None:
                    if isinstance(role, str) and role.lower() in ('user', 'human'):
                        coerced.append(HumanMessage(content=content))
                    elif isinstance(role, str) and role.lower() in ('assistant', 'ai'):
                        coerced.append(AIMessage(content=content))
                    elif isinstance(role, str) and role.lower() in ('system', 'sys'):
                        coerced.append(SystemMessage(content=content))
                    else:
                        coerced.append(HumanMessage(content=content))
                else:
                    coerced.append(m)
                continue

            # If it's already a BaseMessage subclass, pass through
            if isinstance(m, BaseMessage):
                coerced.append(m)
                continue

            # If it's a dict with content
            if isinstance(m, dict) and 'content' in m:
                content = m.get('content')
                if HumanMessage is not None:
                    coerced.append(HumanMessage(content=content))
                else:
                    coerced.append(m)
                continue

            # If it's a plain string, wrap as HumanMessage
            if isinstance(m, str):
                if HumanMessage is not None:
                    coerced.append(HumanMessage(content=m))
                else:
                    coerced.append(m)
                continue

            # Unknown type: try to stringify and wrap
            try:
                txt = str(m)
                if HumanMessage is not None:
                    coerced.append(HumanMessage(content=txt))
                else:
                    coerced.append(txt)
            except Exception:
                # skip
                continue
    except Exception:
        coerced = state['messages']

    # If nothing valid to send, create a fallback simple prompt
    if not coerced:
        coerced = [HumanMessage(content="".join(str(x) for x in messages))] if HumanMessage is not None else [""]

    response = LLM_WITH_TOOLS.invoke(coerced)
    return {'messages': [response]}

#conditional logic for agent
def should_continue(state: AgentState) -> str:
    last_message = state['messages'][-1]
    # gemini models use tool_calls, part of basemessage
    if last_message.tool_calls:
        return 'tools'
    return 'end'

def create_agent_exectutor(tools_list: List[Tool]):
    global LLM_WITH_TOOLS
    # Import heavy dependencies only when creating executor so static checks won't fail
    # Some versions of the langchain-google-genai package expose different class names.
    # Try several known names for compatibility.
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI as ChatLLMClass
    except Exception:
        try:
            from langchain_google_genai import ChatGoogleGenAI as ChatLLMClass
        except Exception:
            # Last resort: import module and try to pick a class by attribute
            import importlib as _il
            try:
                _m = _il.import_module('langchain_google_genai')
                ChatLLMClass = getattr(_m, 'ChatGoogleGenerativeAI', None) or getattr(_m, 'ChatGoogleGenAI', None)
            except Exception:
                ChatLLMClass = None
    if ChatLLMClass is None:
        raise RuntimeError('langchain_google_genai LLM class not found; please install a compatible package version')
    # import langgraph components dynamically to avoid static import resolution errors
    import importlib
    try:
        # Try importing from langgraph.prebuilt (modern versions)
        lg_prebuilt = importlib.import_module('langgraph.prebuilt')
        ToolNode = getattr(lg_prebuilt, 'ToolNode', None)
        lg_graph = importlib.import_module('langgraph.graph')
        StateGraph = getattr(lg_graph, 'StateGraph')
        START = getattr(lg_graph, 'START')
        END = getattr(lg_graph, 'END')
        print(f"DEBUG: Successfully imported ToolNode from langgraph.prebuilt")
    except Exception as e1:
        print(f"DEBUG: Prebuilt import failed: {e1}")
        try:
            # Try primary import path used by some langgraph versions
            lg_nodes = importlib.import_module('langgraph.graph.nodes.tool_node')
            ToolNode = getattr(lg_nodes, 'ToolNode')
            lg_graph = importlib.import_module('langgraph.graph')
            StateGraph = getattr(lg_graph, 'StateGraph')
            START = getattr(lg_graph, 'START')
            END = getattr(lg_graph, 'END')
            print(f"DEBUG: Successfully imported ToolNode from langgraph.graph.nodes.tool_node")
        except Exception as e2:
            print(f"DEBUG: Nodes import failed: {e2}")
            # Fallbacks for different langgraph package layouts
            try:
                lg_nodes = importlib.import_module('langgraph.graph._node')
                ToolNode = getattr(lg_nodes, 'ToolNode', None) or getattr(lg_nodes, 'Node', None)
                lg_graph = importlib.import_module('langgraph.graph')
                StateGraph = getattr(lg_graph, 'StateGraph', None) or getattr(lg_graph, 'Graph', None)
                START = getattr(lg_graph, 'START', None)
                END = getattr(lg_graph, 'END', None)
                print(f"DEBUG: Fallback import - ToolNode={ToolNode is not None}, StateGraph={StateGraph is not None}")
            except Exception as e3:
                print(f"DEBUG: All imports failed: {e3}")
                ToolNode = None
                StateGraph = None
                START = None
                END = None

    # SQLite checkpointing for chat memory
    SqliteSaver = None
    try:
        lg_checkpoint_sqlite = importlib.import_module('langgraph.checkpoint.sqlite')
        SqliteSaver = getattr(lg_checkpoint_sqlite, 'SqliteSaver')
    except Exception:
        SqliteSaver = None

    # initialize LLM and attempt to bind tools. Convert repository tool objects
    # into langchain-compatible callables/Tool instances first so modern
    # Chat LLMs that expect function-shaped tools can bind properly.
    LLM = ChatLLMClass(model="gemini-2.5-flash")
    lc_tools = to_langchain_tools(tools_list)
    try:
        LLM_WITH_TOOLS = LLM.bind_tools(lc_tools)
    except Exception as e:
        print('Warning: LLM.bind_tools failed; continuing with unbound LLM. Error:', e)
        LLM_WITH_TOOLS = LLM

    # If a high-level ToolNode/StateGraph implementation is available use it.
    if ToolNode is not None and StateGraph is not None:
        tool_node = ToolNode(lc_tools)  # Use converted tools, not original tools_list
        graph = StateGraph(AgentState)
        graph.add_node('llm', call_model)
        graph.add_node('tools', tool_node)
        graph.add_edge(START, 'llm')
        graph.add_conditional_edges('llm', should_continue, {'tools': 'tools', 'end': END})
        graph.add_edge('tools', 'llm')
        # Use SQLite for chat memory persistence (simpler and free)
        if SqliteSaver is not None:
            # Create SQLite connection and checkpointer
            import sqlite3
            conn = sqlite3.connect("chat_memory.db", check_same_thread=False)
            checkpointer = SqliteSaver(conn)
            agent = graph.compile(checkpointer=checkpointer)
            print(f"Agent Executor compiled with {len(tools_list)} tools and SQLite chat memory.")
        else:
            agent = graph.compile()
            print(f"Agent Executor compiled with {len(tools_list)} tools (no checkpointer - memory disabled).")
        return agent

    # Fallback: build a minimal executor using lower-level StateNode primitives
    try:
        lg_node_mod = importlib.import_module('langgraph.graph._node')
        StateNode = getattr(lg_node_mod, 'StateNode', None)
        Runnable = getattr(lg_node_mod, 'Runnable', None)
    except Exception:
        StateNode = None
        Runnable = None

    if StateNode is None or Runnable is None:
        raise RuntimeError('langgraph does not expose a usable StateNode/Runnable API for fallback executor.')

    # Define simple StateNodes for LLM and tools
    # Build a mapping from tool-name -> callable for the fallback executor
    tool_callable_map = {}
    for t in tools_list:
        tname = getattr(t, 'name', None) or (getattr(t, 'func', None) and getattr(t.func, '__name__', None)) or None
        tfunc = getattr(t, 'func', None) or (getattr(t, 'run', None)) or (t if callable(t) else None)
        if tname is None and tfunc is not None and hasattr(tfunc, '__name__'):
            tname = getattr(tfunc, '__name__')
        if tname and tfunc:
            tool_callable_map[str(tname)] = tfunc

    class LLMState:
        def run(self, state):
            return call_model(state)

    class ToolsState:
        def run(self, state):
            # expect the last_message contains tool_calls; execute them sequentially
            last = state['messages'][-1]
            # simple heuristic: if last has attribute tool_calls, iterate and call
            tool_calls = getattr(last, 'tool_calls', None)
            if not tool_calls:
                return {'messages': []}
            results = []
            for call in tool_calls:
                # call may be a dict (common for function_call outputs) or an object
                name = None
                inp = None
                if isinstance(call, dict):
                    name = call.get('name') or call.get('tool_name')
                    # args may be nested; try common keys
                    inp = call.get('input') or call.get('arguments') or call.get('args') or call.get('inputs')
                else:
                    name = getattr(call, 'name', None) or getattr(call, 'tool_name', None)
                    inp = getattr(call, 'input', None) or getattr(call, 'arguments', None)

                # If arguments is a dict (e.g., {'inp': '...'}), try to pick common single-field
                if isinstance(inp, dict):
                    # try to pick a primary field
                    for k in ('inp', 'input', 'query', 'text'):
                        if k in inp:
                            inp = inp[k]
                            break
                    else:
                        # fallback to JSON string
                        try:
                            import json
                            inp = json.dumps(inp)
                        except Exception:
                            inp = str(inp)

                # Ensure input is a simple string when possible (many tools expect a string)
                if inp is not None and not isinstance(inp, (str, bytes)):
                    try:
                        inp = str(inp)
                    except Exception:
                        inp = None

                out = None
                # If the call included a tool name, try direct lookup first
                if isinstance(name, str) and name in tool_callable_map:
                    try:
                        out = tool_callable_map[name](inp)
                    except Exception:
                        out = None
                else:
                    # Fallback: try substring or fuzzy match over available tool names
                    if isinstance(name, str):
                        for tname, tfunc in tool_callable_map.items():
                            if name == tname or (isinstance(tname, str) and name in tname):
                                try:
                                    out = tfunc(inp)
                                except Exception:
                                    out = None
                                break
                    # If still not found and there's only one tool, try calling it
                    if out is None and len(tool_callable_map) == 1:
                        sole = next(iter(tool_callable_map.values()))
                        try:
                            out = sole(inp)
                        except Exception:
                            out = None

                # Normalize tool output into a message-like item for the LLM
                if out is None:
                    out_text = ""
                elif isinstance(out, str):
                    out_text = out
                else:
                    try:
                        out_text = str(out)
                    except Exception:
                        out_text = ""

                if HumanMessage is not None:
                    results.append(HumanMessage(content=out_text))
                else:
                    results.append(out_text)
            # feed results back as messages
            return {'messages': results}

    # A very small executor object that mimics the compiled graph interface
    class SimpleAgent:
        def __init__(self, llm_state, tools_state):
            self.llm_state = llm_state
            self.tools_state = tools_state

        def invoke(self, input_state, config=None):
            # naive loop: call LLM then possibly tools then LLM again until should_continue==end
            state = input_state
            # run LLM
            llm_out = self.llm_state.run(state)
            state['messages'].append(llm_out['messages'][0])
            # if we need tools, run them
            if should_continue(state) == 'tools':
                tools_out = self.tools_state.run(state)
                if tools_out and 'messages' in tools_out and tools_out['messages']:
                    state['messages'].extend(tools_out['messages'])
                # run LLM again
                llm_out = self.llm_state.run(state)
                state['messages'].append(llm_out['messages'][0])
            return state

    agent = SimpleAgent(LLMState(), ToolsState())
    print('Fallback SimpleAgent executor created.')
    return agent

load_environment_variables()