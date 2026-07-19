"""
Executes agent-generated Python in a restricted namespace, in a separate
process, with a timeout. This is the "Python subprocess sandbox (restricted
exec environment)" called for in the project brief.
"""
import contextlib
import io
import multiprocessing
import os
import traceback
import uuid

import matplotlib
matplotlib.use("Agg")  # headless backend -- required, there is no display on a server
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Professional chart styling applied globally, once, before any agent code
# runs. This guarantees every chart looks polished regardless of what the
# agent itself writes.
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#2B2E33",
    "axes.linewidth": 1.0,
    "axes.grid": True,
    "grid.color": "#D5D8DA",
    "grid.linewidth": 0.6,
    "grid.alpha": 0.7,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.labelcolor": "#2B2E33",
    "xtick.color": "#2B2E33",
    "ytick.color": "#2B2E33",
    "font.family": "sans-serif",
    "font.size": 10,
    "legend.frameon": True,
    "legend.edgecolor": "#D5D8DA",
    "figure.dpi": 200,  # bumped from 150 -- fixes blurry multi-panel charts
})


class ExecutionResult:
    def __init__(self, success, stdout="", error=None, traceback_str=None, chart_paths=None, local_vars=None):
        self.success = success
        self.stdout = stdout
        self.error = error
        self.traceback_str = traceback_str
        self.chart_paths = chart_paths or []
        self.local_vars = local_vars or {}

    def __repr__(self):
        return f"ExecutionResult(success={self.success}, error={self.error!r})"


def _build_safe_globals(df: pd.DataFrame, output_dir: str):
    safe_builtins = {
        "len": len, "range": range, "min": min, "max": max, "sum": sum,
        "sorted": sorted, "list": list, "dict": dict, "set": set,
        "str": str, "int": int, "float": float, "bool": bool, "round": round,
        "enumerate": enumerate, "zip": zip, "abs": abs, "print": print,
        "isinstance": isinstance, "type": type, "tuple": tuple,
    }

    saved_chart_paths = []

    def save_chart(fig=None, name=None):
        if fig is not None and hasattr(fig, "figure") and not hasattr(fig, "savefig"):
            fig = fig.figure
        fig = fig or plt.gcf()

        has_content = any(
            ax.lines or ax.patches or ax.collections or ax.images or ax.containers
            for ax in fig.get_axes()
        )
        if not has_content:
            raise ValueError(
                "save_chart was called on a figure with nothing plotted on it. "
                "Call a plotting function (e.g. ax.bar(...), ax.plot(...), "
                "ax.hist(...)) on the figure or its axes before calling save_chart."
            )

        # Safety net: rotate long/overlapping x-axis category labels
        # automatically, regardless of whether the agent's code remembered
        # to do this. Only applies to text-based tick labels (categories),
        # never to numeric axes, so it never touches a line/scatter plot's
        # numeric x-axis.
        for ax in fig.get_axes():
            xticklabels = ax.get_xticklabels()
            if xticklabels:
                label_texts = [t.get_text() for t in xticklabels]
                is_categorical = any(not lbl.replace(".", "").replace("-", "").isdigit() for lbl in label_texts if lbl)
                longest_label = max((len(lbl) for lbl in label_texts), default=0)
                if is_categorical and (len(label_texts) > 5 or longest_label > 8):
                    plt.setp(xticklabels, rotation=45, ha="right")
        fig.tight_layout()

        chart_id = name or f"chart_{uuid.uuid4().hex[:8]}"
        path = os.path.join(output_dir, f"{chart_id}.png")
        fig.savefig(path, bbox_inches="tight", dpi=200)
        plt.close(fig)
        saved_chart_paths.append(path)
        return path

    env = {
        "__builtins__": safe_builtins,
        "pd": pd, "np": np, "plt": plt,
        "df": df.copy(),
        "save_chart": save_chart,
    }
    return env, saved_chart_paths


def _worker(code: str, df: pd.DataFrame, output_dir: str, queue: multiprocessing.Queue):
    stdout_buffer = io.StringIO()
    env, saved_chart_paths = _build_safe_globals(df, output_dir)
    try:
        with contextlib.redirect_stdout(stdout_buffer):
            exec(code, env)  # noqa: S102
        result_vars = {}
        for key in ("insights", "result", "summary", "output"):
            if key in env:
                try:
                    result_vars[key] = env[key]
                except Exception:
                    pass
        queue.put({"success": True, "stdout": stdout_buffer.getvalue(),
                   "chart_paths": saved_chart_paths, "local_vars": result_vars})
    except Exception as e:  # noqa: BLE001
        queue.put({"success": False, "stdout": stdout_buffer.getvalue(),
                   "error": str(e), "traceback_str": traceback.format_exc()})


def run_code(code: str, df: pd.DataFrame, output_dir: str, timeout: int = 30) -> ExecutionResult:
    os.makedirs(output_dir, exist_ok=True)
    queue = multiprocessing.Queue()
    proc = multiprocessing.Process(target=_worker, args=(code, df, output_dir, queue))
    proc.start()
    proc.join(timeout=timeout)

    if proc.is_alive():
        proc.terminate()
        proc.join()
        return ExecutionResult(success=False, error=f"Execution timed out after {timeout}s",
                                traceback_str="TimeoutError: generated code did not finish in time.")

    if queue.empty():
        return ExecutionResult(success=False, error="Process exited without a result (likely crashed).",
                                traceback_str="No traceback available -- process terminated unexpectedly.")

    result = queue.get()
    return ExecutionResult(
        success=result["success"], stdout=result.get("stdout", ""),
        error=result.get("error"), traceback_str=result.get("traceback_str"),
        chart_paths=result.get("chart_paths", []), local_vars=result.get("local_vars", {}),
    )