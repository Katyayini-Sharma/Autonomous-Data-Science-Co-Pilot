import json

from langchain.tools import tool

from agent.code_executor import run_code
from agent.data_loader import profile_dataframe
from agent.rag_helper import retrieve_fix_context


def make_tools(df, output_dir: str, timeout: int):

    @tool
    def get_dataframe_schema() -> str:
        """Returns the dataframe's columns, dtypes, missing-value percentages, and basic
        stats as JSON. ALWAYS call this first, before writing any analysis code, so you
        know exactly which column names and types actually exist — never guess column names."""
        return json.dumps(profile_dataframe(df), indent=2)

    @tool
    def run_python_code(code: str) -> str:
        """Executes Python analysis/plotting code against the dataframe `df`. Only pd, np,
        plt, df, and save_chart(fig=None, name=None) are available — no other imports work.
        Never call plt.show(); always call save_chart(...) to persist any figure.

        Returns JSON. On success: {"status": "success", "stdout": ..., "chart_paths": [...]}.
        On failure: {"status": "error", "error": ..., "traceback": ...} — if you get an
        error, call search_documentation with the error message before rewriting the code."""
        result = run_code(code, df, output_dir, timeout=timeout)
        if result.success:
            return json.dumps({
                "status": "success",
                "stdout": result.stdout,
                "chart_paths": result.chart_paths,
                "insights": result.local_vars.get("insights"),
            })
        return json.dumps({
            "status": "error",
            "error": result.error,
            "traceback": result.traceback_str,
        })

    @tool
    def search_documentation(error_message: str) -> str:
        """Searches curated Python/pandas/matplotlib documentation for guidance relevant
        to a specific error message. Call this immediately after run_python_code returns
        a "status": "error" result, using that exact error message as input."""
        return retrieve_fix_context(error_message)

    return [get_dataframe_schema, run_python_code, search_documentation]