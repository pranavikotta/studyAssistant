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
from pydantic import BaseModel, Field
from typing import Optional

try:
    from langchain_experimental.utilities import PythonREPL
    repl = PythonREPL()
except Exception:
    repl = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI as ChatGoogleLLM
except Exception:
    try:
        from langchain_google_genai import ChatGoogleGenAI as ChatGoogleLLM
    except Exception:
        ChatGoogleLLM = None

# Load environment variables for LLM
try:
    from dotenv import load_dotenv
    load_dotenv()
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
except Exception:
    GOOGLE_API_KEY = None

class CodeValidation(BaseModel):
    """Model for validating user code against test cases."""
    user_code: str = Field(description="The code snippet provided by the user for validation.")
    test_cases: str = Field(description="The test cases that the user's code should pass.")
    expected_output: str = Field(description="The expected output when the user's code is executed with the provided test cases.")
    validation_result: str = Field(description="The result of the code validation, indicating success or failure and any relevant details.")
    feedback: str = Field(description="Constructive feedback on the user's code, including suggestions for improvement if applicable.")

class TestCaseGeneration(BaseModel):
    """Model for generating test cases for user code."""
    test_cases_code: str = Field(description="Python code that tests the user's function with multiple test cases. Should call the function with different inputs and print the results.")
    expected_outputs: str = Field(description="The expected output from running the test cases, one result per line.")

def generate_test_cases(user_code: str) -> tuple:
    """
    Uses an LLM to generate test cases for the provided user code.
    
    Args:
        user_code (str): The Python code to generate test cases for.
    
    Returns:
        tuple: (test_cases_code, expected_output)
    """
    if ChatGoogleLLM is None or GOOGLE_API_KEY is None:
        return ("", "")
    
    try:
        llm = ChatGoogleLLM(
            model="gemini-2.0-flash-exp",
            google_api_key=GOOGLE_API_KEY,
            temperature=0.3
        )
        
        llm_with_structure = llm.with_structured_output(TestCaseGeneration)
        
        prompt = f"""Analyze the following Python code and generate comprehensive test cases for it.

USER CODE:
{user_code}

Generate Python code that:
1. Calls the main function(s) in the user's code with 3-5 different test cases
2. Tests edge cases (empty inputs, single elements, large inputs, etc.)
3. Prints the result of each test case clearly
4. Uses print statements that show what's being tested

Also provide the expected output that should result from running these test cases.

Example format for test_cases_code:
# Test case 1: Normal case
result1 = function_name(arg1, arg2)
print(f"Test 1: {{result1}}")

# Test case 2: Edge case
result2 = function_name(edge_arg1, edge_arg2)
print(f"Test 2: {{result2}}")
"""
        
        response = llm_with_structure.invoke(prompt)
        return (response.test_cases_code, response.expected_outputs)
        
    except Exception as e:
        print(f"Warning: Could not generate test cases: {e}")
        return ("", "")

def validate_code_solution(user_code: str, test_cases: str = "", expected_output: str = "") -> str:
    """
    Takes user code and a set of test cases, executes them in a Python sandbox,
    validates the output against expected results, and saves a detailed validation report.
    If no test cases are provided, automatically generates them using an LLM.
    
    Args:
        user_code (str): The Python code to validate.
        test_cases (str): Optional test cases to run against the code.
        expected_output (str): Optional expected output to compare against.
    
    Returns:
        str: A confirmation message with the file path where the validation report was saved.
    """
    if repl is None:
        return "❌ Error: Python REPL not available. Please install langchain-experimental."
    
    try:
        # Generate test cases if not provided
        auto_generated = False
        if not test_cases or not expected_output:
            generated_tests, generated_output = generate_test_cases(user_code)
            if generated_tests:
                test_cases = generated_tests
                expected_output = generated_output
                auto_generated = True
        
        # Combine user code and test cases into a single script
        full_script = user_code
        if test_cases:
            full_script += "\n\n" + test_cases
        
        # Execute the script in the sandboxed REPL
        execution_output = repl.run(full_script)
        
        # Determine validation result
        has_error = "Error" in str(execution_output) or "Traceback" in str(execution_output)
        matches_expected = (not expected_output) or (str(execution_output).strip() == expected_output.strip())
        
        if has_error:
            validation_result = "Failed: Code execution produced errors"
            feedback = "Your code encountered runtime errors. Review the execution output for details."
        elif not matches_expected and expected_output:
            validation_result = "Failed: Output does not match expected result"
            feedback = f"Expected: {expected_output}\nGot: {execution_output}"
        else:
            validation_result = "Success: Code executed correctly"
            feedback = "Great work! Your code passes all validation checks."
            if auto_generated:
                feedback += " (Test cases were automatically generated)"
        
        # Create validation report
        timestamp = datetime.now()
        validation_data = {
            "timestamp": timestamp.isoformat(),
            "user_code": user_code,
            "test_cases": test_cases,
            "test_cases_auto_generated": auto_generated,
            "expected_output": expected_output,
            "execution_output": execution_output,
            "validation_result": validation_result,
            "feedback": feedback,
            "status": "Success" if not has_error and matches_expected else "Failed"
        }
        
        # Create output directory in user's Downloads folder
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads", "StudyAssistant")
        output_dir = os.path.join(downloads_dir, "validation_reports")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename with timestamp
        date_str = timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"validation_{date_str}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(validation_data, f, indent=2)
        
        # Create formatted display for chat
        status_emoji = "✅" if validation_data["status"] == "Success" else "❌"
        display = f"{status_emoji} **Code Validation Complete!**\n\n"
        display += f"📁 Saved to: `{filepath}`\n\n"
        display += f"**Result:** {validation_result}\n\n"
        display += f"**Feedback:** {feedback}\n\n"
        
        if test_cases and auto_generated:
            display += "**Test Cases (Auto-generated):**\n```python\n"
            display += test_cases[:500]
            if len(test_cases) > 500:
                display += "\n...(truncated)"
            display += "\n```\n\n"
        
        display += "**Execution Output:**\n```\n"
        display += str(execution_output)[:1000]
        if len(str(execution_output)) > 1000:
            display += "\n...(truncated)"
        display += "\n```"
        
        return display
        
    except Exception as e:
        # Handle execution errors
        validation_result = f"Critical Error: {str(e)}"
        feedback = "An unexpected error occurred during code execution. Please check your code syntax and try again."
        
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "user_code": user_code,
            "test_cases": test_cases,
            "expected_output": expected_output,
            "error": str(e),
            "validation_result": validation_result,
            "feedback": feedback,
            "status": "Error"
        }
        
        # Create output directory in user's Downloads folder
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads", "StudyAssistant")
        output_dir = os.path.join(downloads_dir, "validation_reports")
        os.makedirs(output_dir, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"validation_error_{date_str}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(error_data, f, indent=2)
        
        return f"❌ Code validation failed: {e}\n\nError report saved to: {filepath}"

# Tool object definition
solution_validator_tool = Tool(
    name="solution_validator",
    description="""
Tool Name: solution_validator
Action: Validates user-submitted Python code by executing it in a sandboxed environment and automatically saves detailed validation reports to timestamped JSON files in the user's Downloads/StudyAssistant/validation_reports directory.
Input Constraint: The input should contain the Python code to validate and optionally test cases to run against it.
Use Case: Use this tool when the user:
1. Asks to 'check my code' or 'validate my solution'.
2. Wants to test if their code works correctly.
3. Requests to run code against test cases.
4. Needs to verify code correctness or debug errors.
Output: The tool executes the code, saves a validation report file, and returns the file path along with execution results.
Forbidden Use: DO NOT use this tool for general questions, information retrieval, or non-Python code.
""",
    func=validate_code_solution
)