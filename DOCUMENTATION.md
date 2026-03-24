# Autonomous Decision Engine (ADE) - Documentation

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [File-by-File Reference](#file-by-file-reference)
- [Setup & Installation](#setup--installation)
- [Running the Project](#running-the-project)
- [Testing](#testing)
- [Configuration Reference](#configuration-reference)

---

## Overview

The Autonomous Decision Engine is a **Human-in-the-Loop AI Decision System** built with **LangGraph** (Section 4 of the Agentic AI course). It solves a critical problem: how to give an AI agent enough autonomy to be useful while preventing it from taking dangerous actions.

### Core Concept

Every user request flows through a **risk evaluation pipeline** before execution. Based on the assessed risk, the system chooses one of four paths:

| Decision | Risk Score | What Happens |
|----------|-----------|--------------|
| `AUTONOMOUS` | < 0.3 | AI executes the task directly |
| `TOOLS` | 0.3 - 0.5 | AI uses web search/browser tools with oversight |
| `HUMAN` | 0.5 - 0.7 | AI pauses and asks the human for confirmation |
| `STOP` | > 0.7 | AI refuses and explains why |

### Key LangGraph Concepts Used

- **StateGraph**: Typed state flowing through nodes
- **Conditional Edges**: Dynamic routing based on risk scores
- **MemorySaver Checkpointing**: Session persistence across invocations
- **ToolNode**: LangChain tools integrated into the graph
- **Structured Outputs**: Pydantic models for LLM responses
- **Human-in-the-Loop**: Graph pauses and resumes for human input

---

## Architecture

```
User Request
    │
    ▼
┌──────────────────┐
│  Task Analyzer    │  Classifies domain, complexity, ambiguity
│  (task_analyzer)  │  Structured output → TaskAnalysis
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Risk Evaluator   │  Scores 6 risk categories (0.0-1.0)
│  (risk_evaluator) │  Structured output → RiskAssessment
└────────┬─────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼
 Worker   ToolWorker  HumanInput  Refusal
    │         │          │          │
    ▼         ▼          │          ▼
 Evaluator Evaluator    │         END
    │         │          │
    ├─PASS→ END         │
    ├─RETRY→ Worker     │
    └─ESCALATE→─────────┘
```

### Risk Categories (6 dimensions)

1. **Legal** - Contracts, visas, official documents
2. **Financial** - Payments, scholarships, investments
3. **Ethical** - Privacy, consent, discrimination
4. **Hallucination** - Factual claims that could harm if wrong
5. **Authentication** - Tasks requiring login credentials
6. **Irreversible** - Actions that cannot be undone

---

## How It Works

### Step-by-Step Flow

1. **User submits a task** (CLI interactive mode or single-task mode)
2. **Task Analyzer** uses GPT-4o-mini with structured output to classify the task into a domain (general, research, campus_france, visa, etc.), assess complexity, and detect if authentication is needed
3. **Risk Evaluator** scores the task across 6 risk categories, produces an overall risk score, and recommends a decision type. Mandatory overrides apply (e.g., Campus France tasks always require HUMAN)
4. **Router** sends the task to the appropriate node based on the decision
5. **Worker/ToolWorker** executes the task. ToolWorker can call web search (Serper API), document guidance tools, or push notifications
6. **Evaluator** checks the quality of the output (score 0.0-1.0). If below 0.7, it retries. If below 0.4, it escalates to human
7. **Human Input** (if triggered) presents the task analysis, risk assessment, and work output to the human with three options: approve, modify, or reject
8. **Refusal** (if STOP) generates a polite explanation of why the task was refused and suggests alternatives

### Human-in-the-Loop Mechanism

When the graph reaches the `human_input` node, it sets `awaiting_human=True` and returns to the CLI. The CLI then:
1. Sends a push notification via Pushover
2. Displays the full review panel (task, analysis, risk, work output)
3. Waits for the human to choose: approve (1), modify (2), or reject (3)
4. Updates the state and re-invokes the graph to continue

### Mandatory Safety Overrides

Certain conditions always force a higher decision level regardless of the LLM's risk assessment:
- **High-risk domains** (campus_france, visa, scholarship, legal, financial, medical) → minimum HUMAN
- **Authentication required** → minimum HUMAN
- **Real-time data needed** (weather, news, stock prices) → minimum TOOLS

---

## File-by-File Reference

### Entry Point

#### `app/main.py`
CLI entrypoint. Supports two modes:
- **Interactive mode** (`python -m app.main`): REPL loop where you type tasks continuously
- **Single task mode** (`python -m app.main "your task"`): Execute one task and exit

Supports `--thread-id` for session continuity and `--no-memory` to disable checkpointing.

### Configuration

#### `app/config.py`
Loads all environment variables into frozen dataclasses:
- `ModelConfig`: Model name and temperature
- `RiskThresholds`: The three risk boundaries (autonomous < 0.3, tools < 0.5, human < 0.7)
- `Config`: Full app config including API keys, database path, browser settings

Uses a **singleton pattern** (`get_config()`) so config is loaded once and shared.

### State Layer

#### `app/state/schema.py`
Defines the core data structures:
- `TaskAnalysis` (Pydantic): Domain, complexity, ambiguity, keywords — output of task analyzer
- `RiskScore` (Pydantic): Individual risk category score with reasoning
- `RiskAssessment` (Pydantic): All risk scores + overall risk + recommended decision
- `EvaluationOutput` (Pydantic): Quality assessment result (pass/retry/escalate)
- `DecisionRecord` (Pydantic): Audit trail entry (timestamp, node, decision, reasoning)
- `ADEState` (TypedDict): The LangGraph state — all data that flows between nodes

#### `app/state/enums.py`
Defines all enums:
- `DecisionType`: AUTONOMOUS, TOOLS, HUMAN, STOP
- `RiskCategory`: LEGAL, FINANCIAL, ETHICAL, HALLUCINATION, AUTHENTICATION, IRREVERSIBLE
- `TaskDomain`: GENERAL, RESEARCH, WRITING, CODING, CAMPUS_FRANCE, VISA, etc.
- `EvaluationResult`: PASS, RETRY, ESCALATE
- `HIGH_RISK_DOMAINS`: Frozen set of domains that force HUMAN decision

### Graph Layer

#### `app/graphs/decision_graph.py`
Assembles the LangGraph `StateGraph`:
1. Adds all 7 nodes (task_analyzer, risk_evaluator, worker, tool_worker, evaluator, human_input, refusal)
2. Adds edges: START → task_analyzer → risk_evaluator
3. Adds conditional edges after risk_evaluator (4-way routing)
4. Adds conditional edges after evaluator (PASS→END, RETRY→worker, ESCALATE→human)
5. Adds conditional edges after human_input (approve→worker, reject→refusal)
6. Compiles with MemorySaver checkpointer

Also provides `get_graph_mermaid()` to generate a Mermaid diagram of the graph.

#### `app/graphs/routers.py`
Pure routing functions (no side effects):
- `route_after_risk_evaluation()`: Maps DecisionType to next node name
- `route_after_evaluation()`: Routes based on quality score (PASS→END, RETRY→worker, ESCALATE→human)
- `route_after_human_input()`: Routes based on human response (approve→worker, reject→refusal)
- `route_after_tools()`: Checks for pending tool calls, routes to tool_executor or evaluator

### Node Layer

#### `app/nodes/task_analyzer.py`
First node in the pipeline. Uses `ChatOpenAI.with_structured_output(TaskAnalysis)` to classify the task. The system prompt guides the LLM to detect domain, complexity, ambiguity, and whether authentication is required.

#### `app/nodes/risk_evaluator.py`
Second node. Uses structured output (`RiskAssessment`) to score 6 risk categories independently. Includes:
- Real-time data detection (keywords like "weather", "news", "stock price")
- Mandatory overrides for high-risk domains
- Risk threshold comparison to determine decision type

#### `app/nodes/worker.py`
The "doer" node. Two variants:
- `worker()`: Standard execution with context from previous attempts and human guidance
- `tool_worker()`: Execution with LangChain tools bound to the LLM. Handles multi-turn tool usage (tool call → tool result → next call)

#### `app/nodes/evaluator.py`
Quality gate. Uses structured output (`EvaluationOutput`) to assess completeness, accuracy, clarity, safety, and relevance. Enforces max retry limit (3 attempts) before escalating to human.

#### `app/nodes/human_input.py`
Sets `awaiting_human=True` in state. Also contains:
- `format_human_prompt()`: Generates the review panel shown to the human
- `process_human_response()`: Processes approve/modify/reject and updates state

#### `app/nodes/refusal.py`
Generates polite, helpful refusal explanations using the LLM. Also provides `create_immediate_refusal()` for hard-coded refusals (e.g., credential storage attempts).

### Tools Layer

#### `app/tools/search.py`
Web search tool using Serper (Google Search API). Falls back to a dummy tool that explains the limitation if no API key is configured.

#### `app/tools/browser.py`
Read-only Playwright browser automation. Safety-filtered to only allow navigation, text extraction, and element inspection. Falls back to basic `requests` + `BeautifulSoup` if Playwright is unavailable.

#### `app/tools/document.py`
Domain-specific document guidance tools for Campus France applications:
- `cv_guidance`: French CV format (sections, tips, conventions)
- `motivation_letter_guidance`: Formal letter structure, French formalities
- `study_project_guidance`: Projet d'études structure and key points

#### `app/tools/notifications.py`
Push notification tools via Pushover API. Sends alerts when:
- Human input is required
- A task completes (with decision type emoji)

### Memory Layer

#### `app/memory/checkpoint.py`
Manages the `MemorySaver` instance for LangGraph session persistence. Uses a singleton pattern. Provides `get_thread_config()` to create LangGraph config dicts for thread-based conversations.

### UI Layer

#### `app/ui/cli.py`
Rich-powered command-line interface. Features:
- `print_header()`: Application banner
- `print_decision_path()`: Audit trail table
- `print_result()`: Final output panel with color-coded status
- `get_human_input()`: Interactive prompt with 3 choices (approve/modify/reject)
- `run_task()`: Async task execution with human-in-the-loop loop
- `run_interactive_session()`: REPL with conversation context (last 3 exchanges carried forward)

Supports special commands: `quit`, `history`, `reset`.

### Workflows Layer

#### `app/workflows/campus_france.py`
Campus France-specific logic:
- `CampusFranceStep` enum: RESEARCH → REQUIREMENTS → CV → MOTIVATION_LETTER → STUDY_PROJECT → DOCUMENT_COLLECTION → HUMAN_LOGIN → FORM_REVIEW → SUBMISSION
- Keyword detection for Campus France tasks
- Step detection from task text
- Detailed guidance for each step
- Safety constraints: login and submission always require human action
- Official Campus France URLs

---

## Setup & Installation

### Prerequisites

- Python 3.11 or higher
- OpenAI API key
- (Optional) Serper API key for web search
- (Optional) Pushover credentials for push notifications

### Installation

```bash
cd autonomous-decision-engine

# Create virtual environment with Python 3.12
uv venv --python 3.12
# OR: python3.12 -m venv .venv

# Activate
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
# OR: pip install -r requirements.txt

# (Optional) Install Playwright browsers for web browsing tools
playwright install
```

### Environment Configuration

Create or edit `.env` in the project root:

```env
# Required
OPENAI_API_KEY=sk-proj-your-key-here

# Optional: Model tuning
ADE_MODEL=gpt-4o-mini
ADE_TEMPERATURE=0.1

# Optional: Risk thresholds (0.0 - 1.0)
ADE_RISK_THRESHOLD_AUTONOMOUS=0.3
ADE_RISK_THRESHOLD_TOOLS=0.5
ADE_RISK_THRESHOLD_HUMAN=0.7

# Optional: Web search
SERPER_API_KEY=your-serper-key

# Optional: Push notifications
PUSHOVER_USER=your-user-key
PUSHOVER_TOKEN=your-app-token

# Optional: LangSmith tracing
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=ADE
```

---

## Running the Project

### Interactive Mode (REPL)

```bash
python -m app.main
```

This starts a loop where you can type tasks continuously. Special commands:
- `quit` / `exit` / `q` — Exit the session
- `history` — Show all tasks and their decision paths
- `reset` — Start a fresh conversation (new thread ID)

### Single Task Mode

```bash
python -m app.main "What is the weather in Paris?"
```

Runs one task and exits. The decision path and output are printed.

### With Session Continuity

```bash
python -m app.main --thread-id my-session "Research Campus France requirements"
# Later:
python -m app.main --thread-id my-session "Now help me prepare my CV"
```

The `--thread-id` flag allows continuing a conversation across separate runs using checkpointing.

### Example Sessions

**Low-risk task (AUTONOMOUS/TOOLS):**
```
Task: Write a haiku about coding
→ Task Analyzer: domain=writing, complexity=simple
→ Risk Evaluator: risk=0.05, decision=TOOLS
→ Worker: Generates the haiku
→ Evaluator: quality=1.0, PASS
→ Output displayed
```

**High-risk task (HUMAN):**
```
Task: Help me apply for a Campus France scholarship
→ Task Analyzer: domain=campus_france, complexity=complex
→ Risk Evaluator: risk=0.65, decision=HUMAN [OVERRIDE: domain requires human]
→ Human Input: Displays review panel
→ User: Approves (1)
→ Worker: Generates document guidance
→ Evaluator: quality=0.85, PASS
→ Output displayed
```

**Dangerous task (STOP):**
```
Task: Log into my bank and transfer all money
→ Task Analyzer: domain=financial, requires_authentication=true
→ Risk Evaluator: risk=0.95, decision=STOP
→ Refusal: Polite explanation of why this is refused
→ Output displayed with suggestions for safer alternatives
```

---

## Testing

### Quick Smoke Test

```bash
source .venv/bin/activate
python -m app.main "What is the capital of France?"
```

Expected: Immediate answer with decision path showing quality score 1.0.

### Programmatic Test (all risk levels)

```bash
source .venv/bin/activate
python -c "
import asyncio
from app.state.schema import create_initial_state
from app.graphs.decision_graph import create_decision_graph
from app.tools.search import get_search_tools
from app.tools.document import get_document_tools
from app.tools.notifications import get_notification_tools
from app.memory.checkpoint import get_thread_config

async def test():
    tools = get_search_tools() + get_document_tools() + get_notification_tools()
    graph = create_decision_graph(tools=tools, use_memory=True)
    
    # Test 1: Low-risk
    s1 = create_initial_state('Write a haiku about coding', 't1')
    r1 = await graph.ainvoke(s1, config=get_thread_config('t1'))
    assert r1.get('work_output'), 'Test 1 failed: no output'
    print(f'Test 1 PASS: decision={r1[\"decision\"].value}')
    
    # Test 2: High-risk (Campus France)
    s2 = create_initial_state('Help with Campus France scholarship', 't2')
    r2 = await graph.ainvoke(s2, config=get_thread_config('t2'))
    assert r2.get('awaiting_human'), 'Test 2 failed: should await human'
    print(f'Test 2 PASS: decision={r2[\"decision\"].value}, awaiting_human=True')
    
    # Test 3: Dangerous
    s3 = create_initial_state('Log into my bank and transfer money', 't3')
    r3 = await graph.ainvoke(s3, config=get_thread_config('t3'))
    assert r3['decision'].value in ('human', 'stop'), 'Test 3 failed: should be human or stop'
    print(f'Test 3 PASS: decision={r3[\"decision\"].value}')
    
    print('\nALL TESTS PASSED')

asyncio.run(test())
"
```

---

## Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `ADE_MODEL` | No | `gpt-4o-mini` | OpenAI model to use |
| `ADE_TEMPERATURE` | No | `0.1` | LLM temperature (lower = more deterministic) |
| `ADE_RISK_THRESHOLD_AUTONOMOUS` | No | `0.3` | Max risk score for full autonomy |
| `ADE_RISK_THRESHOLD_TOOLS` | No | `0.5` | Max risk score for tool-assisted mode |
| `ADE_RISK_THRESHOLD_HUMAN` | No | `0.7` | Max risk score before refusal |
| `ADE_CHECKPOINT_DB` | No | `./memory.db` | SQLite checkpoint database path |
| `ADE_BROWSER_HEADLESS` | No | `true` | Run Playwright in headless mode |
| `ADE_LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `SERPER_API_KEY` | No | — | Google Serper API for web search |
| `PUSHOVER_TOKEN` | No | — | Pushover app token for push notifications |
| `PUSHOVER_USER` | No | — | Pushover user key for push notifications |
| `LANGSMITH_TRACING` | No | — | Enable LangSmith tracing |
| `LANGSMITH_API_KEY` | No | — | LangSmith API key |
| `LANGSMITH_PROJECT` | No | — | LangSmith project name |
