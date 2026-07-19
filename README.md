# Autonomous Data Science Co-Pilot

An agent that takes a CSV, Excel, or JSON file plus a plain-English question, writes and runs its own Python analysis code, and fixes its own bugs when that code fails — until it hands back a working chart and a plain-language summary. Built for my Summer 2025 data science internship, off the back of the "Autonomous Data Science Co-Pilot" project brief.

**Live demo:** https://autonomous-data-science-co-pilot-ztb2vsjgwzvnlmtyph2bhh.streamlit.app

## What it does

1. Upload a CSV, Excel, or JSON file.
2. Ask a question in plain English — or just leave it blank and it'll do a general exploratory pass on its own.
3. It looks at the actual schema first (real column names and dtypes, never guessed), writes code to answer your question, and runs it in a sandbox.
4. If the code breaks, it doesn't just retry blindly — it pulls up relevant documentation for that specific error and rewrites the code with that guidance. You can watch this happen step by step in the "Revision Log" panel.
5. Once it gets a working result, it gives you a chart plus a short plain-language write-up of what it found.
6. You can keep asking follow-up questions about the same dataset without re-uploading — it remembers the conversation.

## How it's actually put together

The short version: uploading a file kicks off cleaning + a schema profile in `data_loader.py`, then `tools.py` wraps the cleaned dataframe, the code sandbox, and the RAG lookup into three tools the agent can call. `core.py` is where the actual agent lives — it's built with LangChain's `create_agent`, backed by LangGraph, and an `InMemorySaver` checkpointer keeps the conversation alive across follow-up questions on the same file.

From there the agent is on its own. It decides, turn by turn, whether to check the schema, write and run code, search documentation after a failure, or just answer — nothing about that sequencing is hardcoded. I'll be honest about why I did it this way: I could have written a much simpler `for attempt in range(3): try/except` loop around a single LLM call and gotten similar-looking results for the happy path. But that's not really an agent, it's a retry wrapper. The whole point of using `create_agent` with real tool definitions is that the *model itself* is deciding what to do next based on what just happened, which is what actually demonstrates agent orchestration rather than me faking it with control flow.

Roughly, one turn looks like: schema check → write code → run it → if it errors, look up the error in the knowledge base → rewrite → run again → repeat until it works or it runs out of steps → final plain-language answer, with every chart path collected from whichever `run_python_code` calls actually succeeded along the way.

## Project layout

```
Co-Pilot_Project/
├── app.py                    # Streamlit UI
├── agent/
│   ├── config.py              # reads .env, builds the provider-prefixed model string
│   ├── data_loader.py          # file loading, cleaning, schema profiling
│   ├── code_executor.py        # sandboxed, timeout-bounded subprocess for running generated code
│   ├── rag_helper.py            # FAISS index + retrieval over knowledge_base/docs
│   ├── tools.py                # wraps the executor + RAG as the agent's three tools
│   ├── prompts.py              # the system prompt — basically the agent's rulebook
│   └── core.py                 # builds the agent, manages memory, parses the transcript into a result object
├── knowledge_base/docs/       # curated pandas/matplotlib/Python error references (what the RAG step searches)
├── data/                      # sample datasets for testing
├── debug_test.py              # quick CLI check that doesn't need Streamlit running
├── requirements.txt
└── .env.example
```

## Getting it running

```bash
git clone https://github.com/Katyayini-Sharma/Autonomous-Data-Science-Co-Pilot.git
cd Autonomous-Data-Science-Co-Pilot
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and set `LLM_PROVIDER` plus that provider's API key — see the table below. Then:

```bash
streamlit run app.py
```

Before poking around in the browser, it's worth running `python debug_test.py` first — it hits the agent directly from the command line and prints every step, so if there's an API key or provider issue you'll see it clearly instead of hunting through the Streamlit UI for it.

## Configuration

Everything lives in `.env` (or your platform's secrets manager if you're deploying — Streamlit Cloud reads `os.getenv()` the same way either source works). `config.py` turns a single `LLM_PROVIDER` value into the right provider-prefixed model string under the hood, so switching providers is a one-line change, no code edits.

| Variable | Notes |
|---|---|
| `LLM_PROVIDER` | `groq`, `gemini`, `openai`, or `anthropic` |
| `GROQ_API_KEY` / `GROQ_MODEL` | free, no card — console.groq.com |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | free, no card — aistudio.google.com |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | needs billing set up |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | needs billing set up |
| `MAX_AGENT_STEPS` | caps how many tool calls the agent can make per request (default 12) |
| `OUTPUT_DIR` | where generated chart PNGs land (default `outputs/`) |

I picked Groq and Gemini as the defaults specifically because they have real no-cost tiers — useful when you're iterating a lot and don't want to burn real money on test runs. Turns out that decision mattered more than expected: free tiers come with real rate limits, and being able to swap `LLM_PROVIDER` and keep going without touching any code saved me more than once while building this.

Never commit a real `.env` — it's already in `.gitignore`.

## Some of the decisions behind this, and why

**Why a subprocess instead of just `exec()`-ing the generated code in-process?**
The restricted namespace (only `pd`, `np`, `plt`, `df`, and `save_chart` exist — no `import`, no `open`, no arbitrary `exec`) covers most accidental misuse on its own, but it doesn't stop something like an infinite loop from hanging the whole app. Running it in a separate process with a hard timeout means the worst case is "this one code attempt failed," not "the entire app is frozen for everyone." I actually tested this on purpose with a deliberate `while True: pass` — it got killed cleanly at the timeout instead of taking the app down with it.

**Why local embeddings (FAISS + sentence-transformers) instead of calling an embedding API?**
The RAG lookup runs on every single failed attempt, so it needs to be fast and it needs to not depend on the same LLM key that might already be rate-limited. Keeping retrieval local means a flaky or exhausted API key never breaks the self-healing step — they're completely separate failure points.

**Why does it rerank by exact error-type match on top of semantic search, not just pure embedding similarity?**
Plain semantic search kept getting confused on short, code-heavy inputs like `KeyError: 'revenue'` — it would rank a more generic doc above the one that actually matched. I checked it wasn't a stale-cache issue by rebuilding the index from scratch, and confirmed with a simple keyword-overlap check that the right document really was distinguishable in the data — the embedding model was just weak on this particular kind of short, symbol-heavy text. So now it reranks the top semantic candidates by whether they literally contain the exception name, which fixed it.

**Why does `save_chart()` reject a figure with nothing drawn on it?**
Found this one the hard way — a generated call like `save_chart(plt.figure(figsize=(10,6)), name='chart')` creates a figure and saves it without ever putting anything on it, so you get a real PNG file, correct file size and everything, that's just blank. I only caught it by opening the saved file directly and looking at it, bypassing the UI entirely. Now `save_chart()` checks the figure actually has axes with real content — lines, bars, whatever — before it'll save, and raises an error otherwise so the agent can catch it and try again instead of silently handing back nothing.

**Why does the prompt require every number in the final answer to have actually been printed by code?**
Because early on, the agent once stated specific revenue-by-region numbers in its summary even though the code that ran never printed anything — it just... said numbers. One of them turned out to be a different region's value, mislabeled; another didn't match anything in the actual data. So now the rule is blunt: if a number's going in the final answer, it has to have come out of a real `print()` call in code that actually ran this turn, no exceptions, no "reasonable-sounding estimate."

**Why send the LLM a schema profile instead of the raw data?**
Sending raw rows would scale token cost directly with dataset size, and it's not actually necessary — dtypes, missing-value percentages, min/max/mean, and top category values are everything the model needs to *write* correct code. The code itself still runs against the full real dataframe in the sandbox, so nothing about the actual analysis is limited by this, only what gets typed into the prompt.

**Why is data cleaning conservative and logged instead of just quietly "fixing" everything?**
Silently dropping rows based on some judgment call about what counts as bad data can change what a total even means without anyone noticing. So `basic_clean()` only does the safe, boring stuff — drop exact duplicate rows, drop fully-empty columns, parse date columns that look consistently date-like — and every single thing it does gets written to a cleaning log that shows up in the UI. Nothing happens to your data invisibly.

## Known limitations

- The sandbox is process-isolated, not container-isolated — fine for a single user or small trusted group, not something I'd put in front of the public without adding real container isolation and no outbound network access.
- Conversation memory (`InMemorySaver`) lives in-process. Follow-ups work great within one running session, but restart the app and that memory's gone — there's no persistent backend behind it.
- Free-tier rate limits are a real, ongoing constraint, not just a one-time setup annoyance. Groq caps at 100k tokens/day per account; some Gemini models are capped as low as a handful of requests *per day*, not per minute, depending on which model you point `GEMINI_MODEL` at. Swapping `LLM_PROVIDER` is a one-line fix with no code changes, and I ended up doing that more than once while building and testing this.
- CSV encoding fallback is `latin-1`, not full encoding auto-detection — covers the common case (older Excel exports saved outside UTF-8) without pulling in a heavier dependency, but it's a heuristic, not a guarantee.

## Tech stack

- **Frontend:** Streamlit, custom CSS for the blueprint/architect-sheet look
- **Agent framework:** LangChain's `create_agent`, LangGraph underneath
- **LLM providers:** Groq or Gemini by default (free tiers), OpenAI/Anthropic also supported
- **Code execution:** Python subprocess sandbox, restricted namespace, hard timeout
- **RAG:** FAISS + local `sentence-transformers` embeddings, with exact-match reranking on top
- **Data handling:** pandas, NumPy, OpenPyXL
- **Charts:** Matplotlib, with automatic label rotation and a blank-figure guard built into the save step
