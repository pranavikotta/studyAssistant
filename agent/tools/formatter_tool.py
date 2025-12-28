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
from pydantic import BaseModel, Field
import os
import json
from datetime import datetime
# Prefer the langchain-google-genai package's classes if present
try:
    from langchain_google_genai import ChatGoogleGenerativeAI as ChatGoogleLLM
except Exception:
    try:
        # older/alternate exports
        from langchain_google_genai import ChatGoogleGenAI as ChatGoogleLLM
    except Exception:
        # fallback to langchain.chat_models if available
        try:
            from langchain.chat_models import ChatGoogleGenerativeAI as ChatGoogleLLM
        except Exception:
            ChatGoogleLLM = None
from typing import Type
from langchain_core.messages import SystemMessage
from typing import List

## 1. Quiz / Structured Question Model

class QuizQuestionModel(BaseModel):
    """A model for a single multiple-choice or short-answer question."""
    question_text: str = Field(description="The complete question text.") #field gives clear instructions to LLM on content
    options: List[str] = Field(description="List of options for a multiple-choice question. Use an empty list for short-answer.")
    correct_answer: str = Field(description="The correct answer, matching one of the options or providing the short answer.")
    explanation: str = Field(description="Brief explanation of why the answer is correct.")

class StructuredQuizModel(BaseModel):
    """The final model for a comprehensive quiz."""
    quiz_title: str = Field(description="A descriptive, academic title for the quiz.")
    questions: List[QuizQuestionModel] = Field(description="A list of generated questions.")

## 2. Flashcard Model

class FlashcardItem(BaseModel):
    """A model for a single flashcard."""
    term: str = Field(description="The term or concept that goes on the front of the flashcard.")
    definition: str = Field(description="The detailed definition, explanation, or answer that goes on the back of the flashcard.")

class FlashcardDeckModel(BaseModel):
    """The final model for a set of flashcards."""
    deck_title: str = Field(description="A descriptive title for the flashcard deck.")
    cards: List[FlashcardItem] = Field(description="A list of generated flashcards.")

## 3. To-Do List Model

class ToDoItem(BaseModel):
    """A single task or action item."""
    task_description: str = Field(description="The full description of the task.")
    priority: str = Field(description="The task's priority (e.g., 'High', 'Medium', 'Low').")
    due_date: str = Field(description="The date or time the task should be completed.")

class ToDoListModel(BaseModel):
    """The final model for a comprehensive To-Do list."""
    list_title: str = Field(description="A title for the to-do list (e.g., 'Weekly Study Tasks').")
    tasks: List[ToDoItem] = Field(description="A list of tasks to be completed.")

## 4. Schedule Model

class ScheduleActivity(BaseModel):
    """A single scheduled activity for a given day."""
    time_slot: str = Field(description="The scheduled time (e.g., '10:00 AM - 11:30 AM').")
    activity_description: str = Field(description="The activity being performed (e.g., 'CS 401 Lecture', 'Review Chapter 5 notes').")

class ScheduleModel(BaseModel):
    """The final model for a daily or weekly schedule."""
    schedule_title: str = Field(description="A descriptive title for the schedule.")
    day: str = Field(description="The specific day or date this schedule applies to.")
    activities: List[ScheduleActivity] = Field(description="A list of scheduled activities for the day.")

## 5. Email Draft Modeel

class EmailDraftModel(BaseModel):
    """A model for drafting a professional email."""
    recipient: str = Field(description="The recipient's name or email address.")
    subject: str = Field(description="The subject line of the email.")
    body: str = Field(description="The full body text of the email.")

# define a mapping of requests to models
SCHEMA_MAP = {
    "quiz": StructuredQuizModel,
    "flashcard": FlashcardDeckModel,
    "todo": ToDoListModel,
    'schedule': ScheduleModel
}

def get_base_llm():
    # Load a clean LLM instance without the other tools bound
    if ChatGoogleLLM is None:
        raise RuntimeError('No compatible Google Chat LLM available in this environment')
    return ChatGoogleLLM(model="gemini-2.5-flash", temperature=0.0)

def formatter_tool_query(request: str) -> str:
    """
    Dynamically selects the appropriate Pydantic schema and forces the LLM 
    to return a structured JSON response. Automatically saves the result to a file.
    """
    # 1. Determine the schema type based on keywords in the request
    target_schema: Type[BaseModel] = None
    file_prefix = ""
    
    request_lower = request.lower()
    
    if "quiz" in request_lower or "question" in request_lower:
        target_schema = StructuredQuizModel
        file_prefix = "quiz"
    elif "flashcard" in request_lower or "term" in request_lower:
        target_schema = FlashcardDeckModel
        file_prefix = "flashcards"
    elif "to-do" in request_lower or "tasks" in request_lower:
        target_schema = ToDoListModel
        file_prefix = "todo"
    elif 'schedule' in request_lower or 'activities' in request_lower:
        target_schema = ScheduleModel
        file_prefix = "schedule"
    elif 'email' in request_lower or 'draft' in request_lower:
        target_schema = EmailDraftModel
        file_prefix = "email"
    else:
        # If no clear schema is found, default to a general structured model or return an error message
        return f"Error: Could not identify a target structured format (Quiz, Flashcard, To-Do List, Schedule, Email) from the request: '{request}'."

    # 2. Bind the schema to the LLM
    try:
        # Get a clean LLM instance
        llm_base = get_base_llm() 
        
        # Use LangChain's .with_structured_output() to enforce the schema
        structured_llm = llm_base.with_structured_output(target_schema)
        
        # 3. Execute the chain
        # Pass the original request to the structured LLM
        response = structured_llm.invoke([
            SystemMessage(content=f"Generate the requested structured object based on the user's prompt. The output MUST strictly adhere to the {target_schema.__name__} schema."),
            request
        ])
        
        # The response is now a validated Pydantic object
        json_content = response.model_dump_json(indent=2)
        
        # 4. Create output directory in user's Downloads folder
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads", "StudyAssistant")
        output_dir = os.path.join(downloads_dir, "generated_outputs")
        os.makedirs(output_dir, exist_ok=True)
        
        # 5. Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{file_prefix}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        # 6. Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json_content)
        
        # 7. Format the content for chat display
        content_dict = json.loads(json_content)
        formatted_display = f"✅ **{file_prefix.replace('_', ' ').title()} Generated!**\n\n"
        formatted_display += f"📁 Saved to: `{filepath}`\n\n"
        formatted_display += "📋 **Content:**\n"
        formatted_display += "```json\n"
        formatted_display += json.dumps(content_dict, indent=2)[:2000]  # Show more content
        if len(json_content) > 2000:
            formatted_display += "\n...(truncated for display)"
        formatted_display += "\n```"
        
        return formatted_display

    except Exception as e:
        return f"An execution error occurred during structured generation: {e}"

# tool object definition
formatter_tool = Tool(
    name="structured_formatter",
    description="""
Tool Name: structured_formatter
Action: Generates highly reliable, structured data by forcing the LLM to output a JSON object that conforms to a specific Pydantic schema (e.g., QuizModel, ToDoListModel, FlashcardDeckModel). The tool AUTOMATICALLY SAVES the generated content to a timestamped JSON file in the user's Downloads/StudyAssistant/generated_outputs directory.
Input Constraint: The input MUST be a concise natural language request detailing the content and target format (e.g., 'Generate a 5-item to-do list for final exam week' or 'Create a flashcard deck on Chapter 2 terms').
Use Case: Use this tool **EXCLUSIVELY** when the user explicitly asks for a structured, parsable data object, including:
1. Creating a Quiz, Test, or set of Flashcards.
2. Generating a To-Do List or Study Schedule.
3. Drafting the content (Subject and Body) for an Email.
4. Structuring Study Notes into a hierarchical format.
Output Constraint: The tool saves the JSON file automatically and returns the file path along with a preview of the content.
Forbidden Use: DO NOT use this tool for answering general questions, information retrieval, or code execution.
""",
    func = formatter_tool_query
)