"""
Builds the LangChain agent (create_agent + tools) and runs it against a
user's request, then parses the resulting message transcript into a clean
result object the UI can render.

Follow-up questions: a single InMemorySaver checkpointer is created once per
uploaded file (in Streamlit's session state) and reused across calls to
run_copilot with the same thread_id, so the agent retains the conversation
across multiple questions about the same file. A new file upload should get
a new checkpointer and thread_id, since the dataframe bound into the tools
changes and old conversation history would refer to stale data.
"""
import json
from dataclasses import dataclass, field

import pandas as pd
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from agent.config import MAX_AGENT_STEPS, OUTPUT_DIR, get_model_string
from agent.data_loader import basic_clean
from agent.prompts import SYSTEM_PROMPT
from agent.tools import make_tools


@dataclass
class ToolStep:
    tool_name: str
    tool_input: dict
    tool_output: dict


@dataclass
class CopilotResult:
    success: bool
    insights: str = ""
    chart_paths: list = field(default_factory=list)
    cleaning_log: list = field(default_factory=list)
    steps: list = field(default_factory=list)
    error: str = None


def _parse_transcript(messages):
    steps = []
    chart_paths = []
    pending_calls = {}

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for call in msg.tool_calls:
                pending_calls[call["id"]] = (call["name"], call["args"])
        elif isinstance(msg, ToolMessage):
            name, args = pending_calls.get(msg.tool_call_id, (msg.name, {}))
            try:
                parsed_output = json.loads(msg.content)
            except (json.JSONDecodeError, TypeError):
                parsed_output = {"raw": msg.content}
            steps.append(ToolStep(tool_name=name, tool_input=args, tool_output=parsed_output))
            if isinstance(parsed_output, dict) and parsed_output.get("chart_paths"):
                chart_paths.extend(parsed_output["chart_paths"])

    return steps, chart_paths


def new_checkpointer() -> InMemorySaver:
    """Creates a fresh in-memory checkpointer -- call this once per uploaded
    file and reuse it across every run_copilot call for that same file."""
    return InMemorySaver()


def run_copilot(
    df: pd.DataFrame,
    user_request: str = "Explore this dataset, surface the most important patterns, "
                        "and create the single most informative chart.",
    output_dir: str = None,
    max_steps: int = None,
    checkpointer: InMemorySaver = None,
    thread_id: str = "default",
) -> CopilotResult:
    output_dir = output_dir or OUTPUT_DIR
    max_steps = max_steps or MAX_AGENT_STEPS

    cleaned_df, cleaning_log = basic_clean(df)
    tools = make_tools(cleaned_df, output_dir, timeout=30)

    agent_kwargs = {"model": get_model_string(), "tools": tools, "system_prompt": SYSTEM_PROMPT}
    if checkpointer is not None:
        agent_kwargs["checkpointer"] = checkpointer

    agent = create_agent(**agent_kwargs)
    invoke_config = {"recursion_limit": max_steps * 2}
    if checkpointer is not None:
        invoke_config["configurable"] = {"thread_id": thread_id}

    # llama-3.3-70b-versatile on Groq occasionally emits its tool call in a
    # malformed textual format ("<function=...>") instead of a proper tool
    # call, which Groq's API rejects with a 400 tool_use_failed error. This
    # is stochastic -- retrying the same request often succeeds -- so we
    # retry a couple of times before surfacing a real failure to the user.
    last_error = None
    for attempt in range(2):
        try:
            result = agent.invoke(
                {"messages": [{"role": "user", "content": user_request}]},
                config=invoke_config,
            )
            break
        except Exception as e:
            last_error = e
            if "tool_use_failed" not in str(e) and "Failed to call a function" not in str(e):
                return CopilotResult(success=False, cleaning_log=cleaning_log, error=str(e))
    else:
        return CopilotResult(
            success=False, cleaning_log=cleaning_log,
            error=f"The model repeatedly failed to format a tool call correctly. "
                  f"Last error: {last_error}",
        )


    all_messages = result["messages"]

    last_human_idx = 0
    for i, msg in enumerate(all_messages):
        if msg.__class__.__name__ == "HumanMessage":
            last_human_idx = i
    this_turn_messages = all_messages[last_human_idx:]

    steps, chart_paths = _parse_transcript(this_turn_messages)

    final_message = all_messages[-1]
    final_text = final_message.content if isinstance(final_message, AIMessage) else ""

    any_success = any(
        isinstance(s.tool_output, dict) and s.tool_output.get("status") == "success"
        for s in steps if s.tool_name == "run_python_code"
    )
    if not steps and final_text.strip():
        any_success = True

    return CopilotResult(
        success=any_success,
        insights=final_text,
        chart_paths=chart_paths,
        cleaning_log=cleaning_log,
        steps=steps,
        error=None if any_success else "The agent did not produce a successful code execution.",
    )