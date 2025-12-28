from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from agent.rag_logic.main import load_environment_variables

# Load environment variables FIRST before importing tools
load_environment_variables()

# AGENT IMPORTS
from agent.agent_core import create_agent_exectutor
from agent.tools.__init__ import TOOLS_LIST
from typing import Optional, List
import uuid # to generate session IDs
import os
import tempfile
from agent.rag_logic.data_loader import load_text, load_pdf, load_docx, split_text
from agent.rag_logic.vector_store import create_vector_store

# dictionary to hold loaded agent executor instance
AGENT_EXECUTOR_PIPELINE = {}

# dictionary will hold the loaded RAG chain instance -> keeps chain globally accessible after startup
RAG_PIPELINE = {}

# Use lifespan context manager instead of deprecated on_event
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        # create agent executor with all defined tools
        agent_executor = create_agent_exectutor(TOOLS_LIST)
        # store runnable agent instance in global state
        AGENT_EXECUTOR_PIPELINE['agent'] = agent_executor
        print("✅ Agent Executor loaded successfully. Server ready to process requests.")
    except Exception as e:
        print(f"An unexpected error occurred during initialization: {e}")
        raise RuntimeError("Failed to initialize server.")
    
    yield
    
    # Shutdown (cleanup if needed)
    print("Shutting down...")

# app initialization with lifespan
app = FastAPI(lifespan=lifespan)
origins = [
    # all localhost / frontend site urls and origins
    'http://localhost:3000',
]
# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    # defines structure of incoming query
    query: str
    session_id: Optional[str] = Field(default = None,
                                      description = 'Unique identifier for user session to maintain memory')

class SearchResponse(BaseModel):
    # define structure of outgoing response
    answer: str

# --- API Endpoint ---
@app.post("/search", response_model=SearchResponse)
async def search_rag(request: QueryRequest):
    """
    Accepts a user query and runs it through langgraph agent executor with session memory.
    """
    executor = AGENT_EXECUTOR_PIPELINE.get('agent')
    if executor is None:
        raise HTTPException(status_code=503, detail="Agent Executor not initialized.")
    #handle session id for memory (generate new id if none provided)
    session_id = request.session_id if request.session_id else str(uuid.uuid4())
    try:
        #invoke agent executor with user query and session id for memory
        result = executor.invoke(
            #input format required by langgraph agent
            {'messages': [('user', request.query)]},
            #configure session memory to find correct conversation thread
            config={'configurable': {'thread_id': session_id}}
        )
        
        # Debug: print all messages to understand the flow
        print(f"DEBUG - Total messages in result: {len(result['messages'])}")
        
        # Track tool usage
        tools_used = []
        for i, msg in enumerate(result['messages']):
            msg_type = type(msg).__name__
            has_content = hasattr(msg, 'content') and bool(msg.content)
            
            # Check for tool calls in the message
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get('name') if isinstance(tool_call, dict) else getattr(tool_call, 'name', 'unknown')
                    tools_used.append(tool_name)
                    print(f"DEBUG - Message {i}: Agent called tool '{tool_name}'")
            
            print(f"DEBUG - Message {i}: Type={msg_type}, HasContent={has_content}, Content={str(msg.content)[:100] if hasattr(msg, 'content') else 'N/A'}...")
        
        print(f"DEBUG - Tools used in this request: {tools_used if tools_used else 'None'}")
        
        # Extract content: check AIMessage, ToolMessage, and HumanMessage (which might be tool output)
        final_message = None
        tool_output = None
        
        # First pass: look for tool outputs (ToolMessage or HumanMessage with JSON)
        for msg in reversed(result['messages']):
            msg_type = type(msg).__name__
            
            # Check for ToolMessage or HumanMessage with structured content
            if msg_type in ['ToolMessage', 'HumanMessage'] and hasattr(msg, 'content') and msg.content:
                content_str = str(msg.content)
                # Check if it looks like JSON (starts with { and contains common structured keys)
                if content_str.strip().startswith('{') and any(key in content_str for key in ['list_title', 'quiz_title', 'deck_title', 'schedule_title']):
                    print(f"DEBUG - Found structured output in {msg_type}: {content_str[:200]}...")
                    tool_output = content_str
                    break
        
        # Second pass: look for AIMessage with content
        for msg in reversed(result['messages']):
            msg_type = type(msg).__name__
            if msg_type == 'AIMessage' or (hasattr(msg, 'type') and msg.type == 'ai'):
                if hasattr(msg, 'content') and msg.content:
                    # Check if content is not empty
                    content_check = msg.content
                    if isinstance(content_check, str) and content_check.strip():
                        final_message = msg
                        break
                    elif isinstance(content_check, list) and content_check:
                        final_message = msg
                        break
        
        # If we found structured output but no AI message with content, use the tool output
        if tool_output and (not final_message or not final_message.content or (isinstance(final_message.content, str) and not final_message.content.strip())):
            print(f"DEBUG - Using tool output as final answer")
            return SearchResponse(answer=tool_output)
        
        if final_message is None:
            # Last resort: use last message
            final_message = result['messages'][-1]
        
        print(f"DEBUG - Selected message type: {type(final_message).__name__}")
        print(f"DEBUG - Message content type: {type(final_message.content)}")
        print(f"DEBUG - Message content: {final_message.content}")
        
        # Extract text from the final message content
        content = final_message.content
        
        if isinstance(content, list):
            # If content is a list of message parts, extract text
            text_parts = []
            for part in content:
                if isinstance(part, dict):
                    # Handle dict with 'text' key
                    if 'text' in part:
                        text_parts.append(part['text'])
                    # Handle dict with 'content' key
                    elif 'content' in part:
                        text_parts.append(part['content'])
                elif isinstance(part, str):
                    text_parts.append(part)
            answer_text = '\n'.join(text_parts) if text_parts else str(content)
        elif isinstance(content, str):
            answer_text = content
        else:
            answer_text = str(content)
        
        print(f"DEBUG - Final answer: {answer_text}")
        return SearchResponse(answer=answer_text)
    except Exception as e:
        print(f'An error occurred while processing the query: {e}')
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the query: {e}")

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...), session_id: str = Form(...)):
    """
    Upload files to be processed and added to the RAG vector store.
    Files are associated with a session ID for conversation context.
    """
    try:
        processed_files = []
        all_documents = []
        
        for file in files:
            print(f"Processing file: {file.filename}")
            # Create a temporary file to save the upload
            suffix = os.path.splitext(file.filename)[1]
            print(f"File extension: {suffix}")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            print(f"Saved to temp file: {tmp_path}, size: {os.path.getsize(tmp_path)} bytes")
            
            try:
                # Load document based on file type
                if file.filename.endswith('.txt'):
                    print(f"Loading as text file...")
                    documents = load_text(tmp_path)
                elif file.filename.endswith('.pdf'):
                    print(f"Loading as PDF...")
                    documents = load_pdf(tmp_path)
                elif file.filename.endswith('.docx') or file.filename.endswith('.doc'):
                    print(f"Loading as DOCX...")
                    documents = load_docx(tmp_path)
                else:
                    print(f"Unsupported file type: {suffix}")
                    os.unlink(tmp_path)  # Clean up temp file
                    processed_files.append({
                        'filename': file.filename,
                        'status': 'error',
                        'error': f'Unsupported file type: {suffix}'
                    })
                    continue  # Skip unsupported file types
                
                print(f"Loaded {len(documents)} documents from {file.filename}")
                
                # Add session_id to document metadata for filtering
                for doc in documents:
                    if hasattr(doc, 'metadata'):
                        doc.metadata['session_id'] = session_id
                        doc.metadata['source_file'] = file.filename
                    else:
                        doc.metadata = {'session_id': session_id, 'source_file': file.filename}
                
                all_documents.extend(documents)
                processed_files.append({
                    'filename': file.filename,
                    'status': 'success',
                    'chunks': len(documents)
                })
            except Exception as e:
                print(f"Error processing {file.filename}: {e}")
                import traceback
                traceback.print_exc()
                processed_files.append({
                    'filename': file.filename,
                    'status': 'error',
                    'error': str(e)
                })
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        if all_documents:
            print(f"Total documents before splitting: {len(all_documents)}")
            # Split documents into chunks
            chunks = split_text(all_documents, chunk_size=1000, chunk_overlap=200)
            print(f"Total chunks after splitting: {len(chunks)}")
            
            # Add to vector store (uses the persistent vector_store directory)
            create_vector_store(chunks, persist_directory="vector_store")
            print(f"Successfully added {len(chunks)} chunks to vector store")
            
            return {
                'message': f'Successfully processed {len(processed_files)} file(s)',
                'files': processed_files,
                'total_chunks': len(chunks)
            }
        else:
            print("No valid documents to process")
            return {
                'message': 'No valid documents to process',
                'files': processed_files,
                'total_chunks': 0
            }
    
    except Exception as e:
        print(f'Error uploading files: {e}')
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing files: {e}")

# Run the server
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Study Assistant API server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
