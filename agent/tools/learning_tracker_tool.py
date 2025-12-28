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
import json
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

try:
    from langchain_google_genai import ChatGoogleGenerativeAI as ChatGoogleLLM
except Exception:
    try:
        from langchain_google_genai import ChatGoogleGenAI as ChatGoogleLLM
    except Exception:
        ChatGoogleLLM = None

try:
    from dotenv import load_dotenv
    load_dotenv()
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
except Exception:
    GOOGLE_API_KEY = None

# Global variable to maintain learning state across sessions
LEARNING_STATE_FILE = None

def get_learning_state_file():
    """Get the path to the persistent learning state file."""
    global LEARNING_STATE_FILE
    if LEARNING_STATE_FILE is None:
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads", "StudyAssistant")
        os.makedirs(downloads_dir, exist_ok=True)
        LEARNING_STATE_FILE = os.path.join(downloads_dir, "learning_state.json")
    return LEARNING_STATE_FILE

def load_learning_state() -> Dict:
    """Load the persistent learning state from file."""
    state_file = get_learning_state_file()
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_learning_state(state: Dict):
    """Save the learning state to file."""
    state_file = get_learning_state_file()
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

class LearningProgressUpdate(BaseModel):
    """Model for analyzing and updating learning progress."""
    completed_topics: List[str] = Field(description="Topics the user has just completed or mastered based on their latest message.")
    progress_notes: str = Field(description="A brief note about the user's progress in this session (what they learned, practiced, or accomplished).")
    next_steps: str = Field(description="Suggested next steps or topics to focus on.")
    overall_status: str = Field(description="Current overall status: 'Just Started', 'In Progress', 'Nearly Complete', or 'Completed'.")

def track_learning_progress(goal: str, session_context: str = "") -> str:
    """
    Tracks the user's learning progress by maintaining a persistent state of their goals,
    completed topics, and progress history. Uses LLM to analyze progress updates.
    Automatically saves progress reports to timestamped JSON files.
    
    Args:
        goal (str): The learning goal or progress update from the user.
        session_context (str): Optional context about the current study session.
        
    Returns:
        str: A confirmation message with the file path where the progress report was saved.
    """
    try:
        # Load existing learning state
        learning_state = load_learning_state()
        
        # If this is a new goal (state is empty or goal changed significantly)
        if not learning_state or "original_goal" not in learning_state:
            # Initialize new learning state
            learning_state = {
                "original_goal": goal,
                "start_date": datetime.now().isoformat(),
                "completed_topics": [],
                "progress_history": [],
                "current_status": "Just Started"
            }
        
        # Use LLM to analyze the current progress update
        progress_analysis = None
        if ChatGoogleLLM and GOOGLE_API_KEY:
            try:
                llm = ChatGoogleLLM(
                    model="gemini-2.0-flash-exp",
                    google_api_key=GOOGLE_API_KEY,
                    temperature=0.3
                )
                llm_with_structure = llm.with_structured_output(LearningProgressUpdate)
                
                prompt = f"""Analyze this learning progress update:

ORIGINAL GOAL: {learning_state['original_goal']}
ALREADY COMPLETED: {', '.join(learning_state['completed_topics']) if learning_state['completed_topics'] else 'Nothing yet'}
CURRENT UPDATE: {goal}
SESSION CONTEXT: {session_context}

Based on the user's update, identify:
1. What new topics have they completed or become familiar with?
2. A brief note about their progress in this session
3. What they should focus on next
4. Overall status toward completing their original goal
"""
                
                progress_analysis = llm_with_structure.invoke(prompt)
                
                # Update completed topics
                for topic in progress_analysis.completed_topics:
                    if topic not in learning_state['completed_topics']:
                        learning_state['completed_topics'].append(topic)
                
                # Update status
                learning_state['current_status'] = progress_analysis.overall_status
                
            except Exception as e:
                print(f"Warning: Could not analyze progress with LLM: {e}")
        
        # Create progress report for this session
        timestamp = datetime.now()
        progress_data = {
            "timestamp": timestamp.isoformat(),
            "original_goal": learning_state['original_goal'],
            "session_update": goal,
            "session_context": session_context,
            "completed_topics": learning_state['completed_topics'],
            "current_status": learning_state['current_status'],
            "progress_notes": progress_analysis.progress_notes if progress_analysis else "Progress tracked",
            "next_steps": progress_analysis.next_steps if progress_analysis else "Continue working on your goal"
        }
        
        # Add to progress history
        learning_state['progress_history'].append({
            "timestamp": timestamp.isoformat(),
            "update": goal,
            "completed_topics": progress_analysis.completed_topics if progress_analysis else []
        })
        
        # Save updated learning state
        save_learning_state(learning_state)
        
        # Save/update the main progress report file (single file, not timestamped)
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads", "StudyAssistant")
        output_dir = os.path.join(downloads_dir, "learning_progress")
        os.makedirs(output_dir, exist_ok=True)
        
        # Use a consistent filename based on the goal
        filename = "current_learning_progress.json"
        filepath = os.path.join(output_dir, filename)
        
        # Include full history in the file
        progress_data["progress_history"] = learning_state['progress_history']
        progress_data["last_updated"] = timestamp.isoformat()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2)
        
        # Create formatted display for chat
        summary = f"✅ **Learning Progress Updated!**\n\n"
        summary += f"📁 Saved to: `{filepath}`\n\n"
        summary += f"🎯 **Original Goal:** {learning_state['original_goal']}\n\n"
        
        if learning_state['completed_topics']:
            summary += f"✔️ **Completed Topics:**\n"
            for topic in learning_state['completed_topics']:
                summary += f"   • {topic}\n"
            summary += "\n"
        else:
            summary += "✔️ **Completed Topics:** None yet\n\n"
        
        summary += f"📊 **Status:** {learning_state['current_status']}\n\n"
        
        if progress_analysis:
            summary += f"📝 **This Session:**\n{progress_analysis.progress_notes}\n\n"
            summary += f"➡️ **Next Steps:**\n{progress_analysis.next_steps}"
        
        return summary
    
    except Exception as e:
        return f"❌ Error tracking learning progress: {e}"

# Tool object definition
learning_tracker_tool = Tool(
    name='learning_tracker',
    description="""
Tool Name: learning_tracker
Action: Tracks and monitors the user's learning progress over time. Automatically saves progress reports as timestamped JSON files in the user's Downloads/StudyAssistant/learning_progress directory.
Input Constraint: The input should be a learning goal or objective (e.g., 'Master Python data structures' or 'Complete Chapter 5 exercises').
Use Case: Use this tool when the user:
1. Sets a new learning goal or study objective.
2. Wants to track their progress on a specific topic.
3. Requests a progress check or learning summary.
4. Starts a new study session or milestone.
Output: The tool saves a progress report file and returns the file path along with a confirmation message.
Forbidden Use: DO NOT use this tool for general questions, content retrieval, or code execution.
""",
    func=track_learning_progress
)