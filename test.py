import os
import pathlib
import json
import time
from typing import Dict, Any, List

# NOTE: The full implementation requires installing the official Google Gen AI SDK:
# pip install google-genai pydantic
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# --- Configuration ---
# PASTE YOUR API KEY HERE
# In a collaborative environment like this, we leave it as an empty string.
GEMINI_API_KEY_HOLDER = "AIzaSyB6xFwULvcDFCrbLB7Vj3C3mZzj1vXdtIA"

# Define the model to use for code generation
CODE_GEN_MODEL = "gemini-2.5-flash"
BASE_DIR = "iwealth_builder"


# --- Structured Output Schema for Gemini API ---
# We define a Pydantic model to force the LLM to only return the code block.
class FileContent(BaseModel):
    """A model to hold the generated code content for a single file."""
    code: str = Field(description="The complete, generated source code for the file.")


def generate_content_with_retry(
    api_key: str,
    system_instruction: str,
    user_prompt: str,
    output_schema: BaseModel,
    max_retries: int = 3,
) -> str :
    """
    Calls the Gemini API to generate content with structured output and handles retries.
    Uses the provided API key for client initialization.
    """
    if not api_key:
        print("ERROR: API key is empty. Please set the GEMINI_API_KEY_HOLDER variable.")
        return None

    # Initialize the client using the provided API key
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"Error initializing client: {e}")
        return None

    full_prompt = (
        f"Generate the Python source code for the following file based on the system instructions. "
        f"The file should use FastAPI and SQLModel. Do not include any explanation or markdown formatting in the 'code' field. "
        f"Specific file request: {user_prompt}"
    )

    for attempt in range(max_retries):
        try:
            print(f"  -> Attempt {attempt + 1}: Generating content for prompt...")
            response = client.models.generate_content(
                model=CODE_GEN_MODEL,
                contents=full_prompt,
                  config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=output_schema,
                ),
            )

            # The response text will be a JSON string that adheres to the FileContent schema
            json_text = response.text.strip()
            content_data = FileContent.model_validate_json(json_text)
            return content_data.code

        except Exception as e:
            print(f"  -> API call failed for prompt (Attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  -> Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print("  -> Max retries reached. Skipping file generation.")
                return None
    return None

# --- Project Definition ---
# The keys are the file paths, and the values are the specific instructions for the AI.
project_structure: Dict[str, str] = {
    # Top-Level Files
    f"{BASE_DIR}/iwealth_builder_app_bk.py": "Create the main entry point (iwealth_builder_app_bk.py) that imports the FastAPI application 'app' from 'app.main'. This file should only run the application using 'uvicorn.run'.",

    # App Module Files
    f"{BASE_DIR}/app/main.py": "Create the main FastAPI application file, initializing SQLModel and creating all tables on startup. It should import and include all routers (portfolio, transactions, sips) and include necessary imports for the database setup.",
    f"{BASE_DIR}/app/database.py": "Create the SQLModel database setup file. Define an in-memory SQLite database connection (for simplicity) and the `create_db_and_tables()` function. Define the `get_session` dependency using `with Session(engine) as session:` for dependency injection.",

    # Models
    f"{BASE_DIR}/app/models/__init__.py": "# Define __init__.py for the models directory to import all models so they are registered with SQLModel. Import Investment and SIP.",
    f"{BASE_DIR}/app/models/investment.py": "Define a SQLModel class for the Investment entity named 'Investment', including fields like id, user_id (string), type (e.g., 'equity', 'debt'), amount (float), date (datetime), and status (e.g., 'completed'). It must inherit from SQLModel and use `table=True`.",
    f"{BASE_DIR}/app/models/sip.py": "Define a SQLModel class for the SIP (Systematic Investment Plan) entity named 'SIP', including fields like id, user_id (string), fund_name (string), monthly_amount (float), start_date (date), and frequency (e.g., 'monthly'). It must inherit from SQLModel and use `table=True`.",

    # Services
    f"{BASE_DIR}/app/services/__init__.py": "# empty",
    f"{BASE_DIR}/app/services/investment_service.py": "Create a Python class 'InvestmentService' using dependency injection of a SQLModel Session. It needs methods: `create_investment(investment: Investment)` and `get_investments_by_user(user_id: str)`.",
    f"{BASE_DIR}/app/services/sip_service.py": "Create a Python class 'SIPService' using dependency injection of a SQLModel Session. It needs methods: `create_sip(sip: SIP)` and `get_sips_by_user(user_id: str)`.",

    # Routers
    f"{BASE_DIR}/app/routers/__init__.py": "# empty",
    f"{BASE_DIR}/app/routers/portfolio.py": "Create a FastAPI router for portfolio endpoints. Implement a GET route at '/portfolio/value/{user_id}' that uses InvestmentService to calculate and return the total sum of investment amounts for that user.",
    f"{BASE_DIR}/app/routers/transactions.py": "Create a FastAPI router for transaction endpoints. Implement a POST route at '/transactions/' to create a new Investment (a transaction) and a GET route at '/transactions/{user_id}' to list all of a user's investments.",
    f"{BASE_DIR}/app/routers/sips.py": "Create a FastAPI router for SIP endpoints. Implement a POST route at '/sips/' to create a new SIP and a GET route at '/sips/{user_id}' to list all of a user's SIPs.",
}

# --- Main Execution ---
def create_project_structure(structure: Dict[str, str], api_key: str):
    """Creates the directories and generates/writes the content for all files."""
    print(f"--- Starting project generation in ./{BASE_DIR} ---")
    pathlib.Path(BASE_DIR).mkdir(exist_ok=True)
    system_prompt = (
        "You are an expert Python developer specialized in building modern web APIs "
        "using FastAPI and SQLModel. Your task is to generate the complete, production-ready "
        "Python code for a single file. Do not include any explanations, comments about "
        "running the code, or surrounding markdown blocks in the 'code' output field. "
        "The code must be self-contained for the specified file."
    )

    for file_path, instructions in structure.items():
        full_path = pathlib.Path(file_path)

        # 1. Create Directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if instructions.strip() == "# leave empty" or instructions.strip() == "# empty":
            # For __init__.py files that are just empty markers
            print(f"Creating empty file: {file_path}")
            full_path.touch()
            continue

        if instructions.startswith("# Define __init__.py"):
            # Handle the specific __init__.py model import logic
            print(f"Creating models/__init__.py: {file_path}")
            content = "from .investment import Investment\nfrom .sip import SIP\n"
            full_path.write_text(content)
            continue

        print(f"\nProcessing file: {file_path}")

        # 2. Generate Content using the AI
        generated_code = generate_content_with_retry(
            api_key, # Pass the key directly
            system_prompt,
            instructions,
            FileContent
        )

        # 3. Write Content to File
        if generated_code:
            try:
                full_path.write_text(generated_code, encoding="utf-8")
                print(f"  -> Successfully generated and wrote to: {file_path}")
            except Exception as e:
                print(f"  -> ERROR writing file {file_path}: {e}")
        else:
            print(f"  -> FAILED to generate content for: {file_path}")

    print("\n--- Project generation complete. Check the folder structure. ---")


if __name__ == "__main__":
    create_project_structure(project_structure, GEMINI_API_KEY_HOLDER)
