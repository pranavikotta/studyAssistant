#import langchain-google-genai
import os
# langchain_google_genai has changed names across releases; try multiple fallbacks
try:
    from langchain_google_genai import ChatGoogleGenAI as ChatLLM
except Exception:
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI as ChatLLM
    except Exception:
        # try to import module and pick an attribute
        import importlib as _il
        try:
            _m = _il.import_module('langchain_google_genai')
            ChatLLM = getattr(_m, 'ChatGoogleGenAI', None) or getattr(_m, 'ChatGoogleGenerativeAI', None)
        except Exception:
            ChatLLM = None
import importlib
try:
    prompts_mod = importlib.import_module('langchain.prompts')
    PromptTemplate = getattr(prompts_mod, 'PromptTemplate')
except Exception:
    PromptTemplate = None

from langchain_core.output_parsers import StrOutputParser
from .vector_store import get_retriever

# get LLM instance
def get_llm():
    if ChatLLM is None:
        raise RuntimeError('No compatible langchain_google_genai LLM class available in this environment')
    return ChatLLM(model='gemini-2.5-flash', temperature=0.5, max_output_tokens=1024)

# format page_content of all retrieved documents into one string
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# create prompt template
def create_prompt_template():
    # Template used to build prompts; also exposed at module scope for fallbacks
    TEMPLATE = '''
You are an AI study assistant that helps students learn effectively. Use the provided context to answer the user's query.
If the context and retrieved data sources are insufficient to answer the question, do not make up an answer and inform the user that you don't have enough information.
Context:
{context}
Question: {question}
Answer in a clear manner, suitable for a student's understanding.
'''
    template = TEMPLATE
    # expose raw template string for fallbacks elsewhere in this module
    global PROMPT_TEMPLATE_STR
    PROMPT_TEMPLATE_STR = template
    if PromptTemplate is None:
        class _SimplePrompt:
            def format(self, **kwargs):
                return template.format(**kwargs)
        return _SimplePrompt()
    return PromptTemplate(
        input_variables=["context", "question"],
        template=template
    )


# create a minimal sequential RAG chain object that exposes invoke(query)
def create_rag_chain(persist_directory="vector_store"):
    llm = get_llm()
    prompt_template = create_prompt_template()
    retriever = get_retriever(persist_directory=persist_directory)

    class _SimpleRAG:
        def __init__(self, llm, prompt_template, retriever):
            self.llm = llm
            self.prompt_template = prompt_template
            self.retriever = retriever

        def invoke(self, query: str):
            docs = self.retriever.get_relevant_documents(query)
            context = format_docs(docs)
            try:
                prompt = self.prompt_template.format(context=context, question=query)
            except Exception:
                prompt = template.format(context=context, question=query)
            try:
                result = self.llm.invoke([prompt])
            except Exception:
                result = self.llm.invoke(prompt)
            return result

    return _SimpleRAG(llm, prompt_template, retriever)


# answer user query using RAG chain
def process_query(chain, query):
    response = chain.invoke(query)
    return response
