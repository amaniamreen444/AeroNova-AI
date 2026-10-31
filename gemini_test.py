
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# Load .env from the same folder as this Python file
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: GEMINI_API_KEY not found.")
    print("Check that .env is beside gemini_test.py.")
    raise SystemExit(1)

try:
    client = genai.Client(api_key=api_key)

    response = client.interactions.create(
        model="gemini-3.8-flash",
        input="Say hello to AeroNova AI in one short sentence."
    )

    print("Gemini Response:")
    print(response.output_text)

except Exception as error:
    print("Gemini test failed:", error)
