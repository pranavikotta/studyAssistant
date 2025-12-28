# Study Assistant
An intelligent AI-powered learning companion that transforms your study experience with autonomous tools and personalized assistance. **Designed for localhost development only.**

## Features

### AI Agent with Autonomous Tools
Study Assistant uses a sophisticated AI agent powered by LangGraph and Google's Gemini API, equipped with 6 autonomous tools:

1. **RAG Search**
   - Semantic search through your personal notes and course materials
   - Powered by vector database storage
   - Upload PDFs, DOCX, and TXT files for intelligent retrieval

2. **Web Search**
   - Live Google Custom Search integration
   - Real-time information retrieval
   - Up-to-date facts and supplementary content

3. **Code Execution**
   - Execute Python code in a secure sandbox
   - Run calculations and test algorithms
   - Verify programming concepts in real-time

4. **Content Formatter**
   - Auto-generate quizzes with multiple-choice questions
   - Create flashcard decks for memorization
   - Build study schedules and to-do lists
   - Saves formatted content as timestamped JSON files

5. **Learning Tracker**
   - Monitor and track learning progress
   - Detailed progress reports with goals and status updates
   - Session summaries saved automatically

6. **Solution Validator**
   - Validate Python code against AI-generated test cases
   - Sandboxed execution environment
   - Detailed validation reports with feedback

### Conversational Interface
- Natural language interaction with the AI agent
- Persistent conversation history
- Session management for context continuity
- Beautiful, modern UI with React

## Architecture
- **Frontend**: React (localhost:3000)
- **Backend**: FastAPI with Python (localhost:8000) or run python api.py
- **AI**: Google Gemini API + LangGraph agent framework
- **Vector Store**: Chroma DB for RAG functionality

## To Run
- enter the frontend directory: npm start
- for the backend, activate a virtual env: python api.py
