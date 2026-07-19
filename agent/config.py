import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")

MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "12"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def get_model_string() -> str:
    if LLM_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. Get a free key (no credit card) at "
                "aistudio.google.com and add it to your .env file."
            )
        return f"google_genai:{GEMINI_MODEL}"
    elif LLM_PROVIDER == "groq":
        if not GROQ_API_KEY:
            raise EnvironmentError(
                "GROQ_API_KEY is not set. Get a free key (no credit card) at "
                "console.groq.com and add it to your .env file."
            )
        return f"groq:{GROQ_MODEL}"
    elif LLM_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise EnvironmentError("OPENAI_API_KEY is not set. Add it to your .env file.")
        return f"openai:{OPENAI_MODEL}"
    elif LLM_PROVIDER == "anthropic":
        if not ANTHROPIC_API_KEY:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        return f"anthropic:{ANTHROPIC_MODEL}"
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{LLM_PROVIDER}'. Use 'gemini', 'groq', 'openai', or 'anthropic'."
        )