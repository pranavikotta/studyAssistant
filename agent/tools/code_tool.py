try:
    from langchain.tools import Tool
except Exception:
    # minimal local shim for Tool to match expected simple usage
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
import importlib
import subprocess
import sys
from typing import Tuple


def _run_subprocess_python(code: str, timeout: int = 5) -> str:
    """Execute code using the current Python interpreter in a subprocess and return output.

    This is a direct, real execution (not a stub). We use a short timeout and capture
    stdout/stderr. Keep this simple — it's intended for trusted test usage only.
    """
    try:
        proc = subprocess.run([
            sys.executable,
            "-c",
            code
        ], capture_output=True, text=True, timeout=timeout)
        out = proc.stdout or ""
        err = proc.stderr or ""
        if proc.returncode != 0:
            return f"ERROR (exit {proc.returncode}): {out}\n{err}"
        return out if out else (err if err else "")
    except subprocess.TimeoutExpired:
        return "ERROR: Python execution timed out"
    except Exception as e:
        return f"ERROR: Exception during python execution: {e}"


def code_tool_query(code: str) -> str:
    """
    Wrapper function that prefers the PythonREPLTool from langchain_community but
    falls back to running the code using the project's Python executable. This runs
    real Python, not a stub, so it exercises actual behaviour.
    """
    try:
        mod = importlib.import_module('langchain_community.tools.python.tool')
        PythonREPLTool = getattr(mod, 'PythonREPLTool')
        python_tool = PythonREPLTool()
        result = python_tool.run(code)
        return result
    except Exception:
        # Fallback: run code using subprocess and the current Python interpreter
        return _run_subprocess_python(code)

# tool object definition
code_tool = Tool(
    "declare tool name, a system prompt detailing when to use the tool, and the function to call the tool",
    name='python_interpreter',
    description="""
Tool Name: python_interpreter
Action: Executes single-line or multi-line Python code safely.
Input Constraint: The input MUST be the complete, valid, runnable Python code to be executed (e.g., 'print(15 * 7)'). Do NOT send natural language questions as input.
Use Case:
1. Solving complex mathematical calculations or performing precise numerical operations.
2. Generating and running basic, self-contained test cases for coding assignments.
3. Executing user-provided code snippets or checking LLM-generated code for errors.
4. Analyzing or manipulating small, provided data structures (e.g., lists, dictionaries).
Forbidden Use: DO NOT use this tool for general knowledge questions or accessing the course_knowledge_search (RAG) tool's documents.
""",
    func=code_tool_query,
)