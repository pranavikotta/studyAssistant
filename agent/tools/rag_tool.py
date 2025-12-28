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
from agent.rag_logic.rag_chain import create_rag_chain, process_query

# assuming 'create_agent_executor' is called with the persist_directory argument
PERSIST_DIR = "vector_store"

# lazy-load the RAG chain to avoid import-time failure if the vector store is not present
RAG_CHAIN = None

def rag_tool_query(query: str) -> str:
    """
    Wrapper function that calls the main RAG processing function.
    This adheres to the Tool's expected signature (str -> str).
    """
    global RAG_CHAIN
    
    try:
        if RAG_CHAIN is None:
            # attempt to create the chain (this will raise if vector store is missing)
            # By default we reuse the persisted store so that once created it is used.
            RAG_CHAIN = create_rag_chain(persist_directory=PERSIST_DIR)

        response = process_query(RAG_CHAIN, query)

        # Normalize response into JSON-friendly structure. Different LLM wrappers
        # may return different shapes; try common attributes first.
        try:
            # If response is a LangChain/GenAI-like object with `.content` or `.message`
            text = getattr(response, 'content', None) or getattr(response, 'message', None) or str(response)
        except Exception:
            text = str(response)

        # Attempt to capture metadata if present
        meta = {}
        try:
            meta = getattr(response, 'additional_kwargs', {}) or getattr(response, 'extra', {}) or {}
        except Exception:
            meta = {}

        # Attempt to gather context used from RAG chain if available (best-effort)
        context_used = None
        try:
            # if the chain stored the last retrieved docs somewhere, access it; otherwise leave null
            if hasattr(RAG_CHAIN, 'retriever'):
                # This is a best-effort: we cannot know which docs were used, but we can run a retrieval
                docs = RAG_CHAIN.retriever.get_relevant_documents(query)
                context_used = "\n\n".join(getattr(d, 'page_content', str(d)) for d in docs)
        except Exception:
            context_used = None

        import json
        out = {
            'answer': text,
            'context': context_used,
        }
        return json.dumps(out)
    
    except Exception as e:
        import json
        import traceback
        error_msg = f"RAG Tool Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(error_msg)  # Log to console
        return json.dumps({
            'answer': f"Sorry, I encountered an error while searching your documents: {str(e)}",
            'context': None,
            'error': str(e)
        })

# tool object definition
rag_tool = Tool(
    # brief developer note (positional string is optional/descriptive)
    "declare tool name, a system prompt detailing when to use the tool, and the function to call the tool",
    name='course_knowledge_search',
    description="""
Tool Name: course_knowledge_search
Action: Searches and retrieves relevant information from the user's uploaded documents, study materials, course notes, and personal knowledge base.
Input Constraint: The input MUST be the complete user question or topic they're asking about (e.g., 'What is the IST policy for AI?', 'Explain the ReAct pattern', 'What does the syllabus say about late submissions?').
Output Constraint: Returns relevant text chunks and context from the uploaded documents.
Use Case: **USE THIS TOOL FIRST** for ANY question that could relate to:
- Course content, policies, syllabi, assignments, or handouts
- Study materials, textbooks, lecture notes, or slides
- Previously uploaded documents or files
- ANY topic the user has provided documents about
**IMPORTANT:** Even if the user asks for "updates", "latest information", or "current policy", if they uploaded a document about it, search THIS tool first before assuming you need external data.
Forbidden Use: DO NOT use this tool for real-time web data (weather, news, stock prices) or code execution. Only use for document-based information.
""",
    func=rag_tool_query,
)