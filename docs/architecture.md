I'll architect this properly before touching any code. Let me think through this as a real multi-agent system that would survive a Kaggle notebook review and hold up if extended later.

## 1. System Architecture

**Core design philosophy:** Orchestrator-led multi-agent pipeline, not a free-for-all. A central `Orchestrator` coordinates five specialist agents, each with a single responsibility, a strict input/output contract, and graceful degradation if Gemini is unavailable.

### Architectural layers

**Layer 1 — Entry / Interface**
A single entry point (CLI or notebook cell) collects a student profile (academic record, skills, interests, target roles, location preference) and hands it to the Orchestrator. This is the only layer that touches user I/O.

**Layer 2 — Orchestration**
The `Orchestrator` is the brain of the system. It does not call Gemini itself — it:
- Validates the incoming student profile against a schema
- Decides agent execution order (mostly sequential, since later agents depend on earlier outputs)
- Passes a shared `context` object between agents
- Catches agent-level failures and decides whether to retry, fallback, or abort
- Aggregates final outputs into one structured report

**Layer 3 — Agents (the five specialists)**

| Agent | Responsibility | Depends on |
|---|---|---|
| **Career Agent** | Suggests 2–3 viable career paths based on profile, interests, market trends | Student profile only |
| **Skill Gap Agent** | Compares student's current skills vs. target career's required skills | Career Agent output |
| **Internship Agent** | Recommends internship types/companies/roles that fit current skill level + target career | Career Agent + Skill Gap output |
| **Study Planner Agent** | Builds a week-by-week study plan to close identified skill gaps | Skill Gap Agent output |
| **Project Recommendation Agent** | Suggests portfolio projects that demonstrate the missing skills | Skill Gap Agent + Career Agent output |

Each agent is a class implementing the same interface: `run(context: dict) -> AgentResult`. This uniformity is what makes the orchestrator simple and makes fallback logic reusable instead of duplicated five times.

**Layer 4 — LLM Service (Gemini + Fallback)**
A single `LLMService` class wraps all Gemini calls. No agent calls the Gemini SDK directly — they all go through this service. This is the key architectural decision: it means fallback logic, retry logic, prompt logging, and rate-limit handling live in **one place**, not five.

- `LLMService.generate(prompt, schema)` → tries Gemini → on failure (timeout, quota, malformed response, API key missing) → falls back to a deterministic rule-based generator scoped per-agent
- Each agent supplies its own fallback function (e.g., Skill Gap Agent's fallback is a static skill-taxonomy lookup table, not a Gemini call)
- Fallback is **silent to the user but logged**, so the final report can optionally show "AI-enhanced" vs "rule-based" provenance per section — this is actually a nice touch for a Kaggle judge to see resilience engineering

**Layer 5 — Data / Knowledge**
Static reference data that powers both prompts (as context for Gemini) and fallbacks (as the actual answer source):
- Career → required skills mapping
- Skill taxonomy (canonical skill names, categories)
- Internship/company datasets (could be a Kaggle dataset itself — internships.csv)
- Project idea bank tagged by skill

**Layer 6 — Output**
A `ReportBuilder` takes the aggregated context and renders it as Markdown/JSON/HTML — whatever the Kaggle notebook displays. Kept separate from the Orchestrator so output format can change without touching agent logic.

---

## 2. Folder Structure & Responsibilities

```
ai-student-success-mentor/
│
├── README.md                      # Problem statement, architecture summary, how to run
├── requirements.txt                # google-generativeai, pydantic, python-dotenv, etc.
├── .env.example                    # GEMINI_API_KEY placeholder
├── config.py                       # Central config: model name, timeouts, retry counts, paths
│
├── main.py                         # Entry point — builds profile, runs Orchestrator, prints report
│
├── core/
│   ├── orchestrator.py             # Orchestrator class — sequencing, context passing, error handling
│   ├── context.py                  # Shared context/state object passed between agents (typed)
│   ├── agent_base.py               # Abstract BaseAgent class — defines run(), fallback(), interface contract
│   └── llm_service.py              # Gemini wrapper — single point of contact with the API + fallback dispatch
│
├── agents/
│   ├── career_agent.py
│   ├── skill_gap_agent.py
│   ├── internship_agent.py
│   ├── study_planner_agent.py
│   └── project_recommendation_agent.py
│   # Each file: one Agent class extending BaseAgent, its Gemini prompt template,
│   # and its own fallback() method using local data
│
├── data/
│   ├── careers.json                # Career → required skills, growth outlook
│   ├── skills_taxonomy.json        # Canonical skill list + categories
│   ├── internships.csv             # Sample internship listings (roles, companies, skill requirements)
│   └── project_bank.json           # Project ideas tagged by skill/difficulty
│
├── prompts/
│   ├── career_prompt.py
│   ├── skill_gap_prompt.py
│   ├── internship_prompt.py
│   ├── study_planner_prompt.py
│   └── project_recommendation_prompt.py
│   # Kept separate from agent logic so prompt engineering is isolated and versionable
│
├── schemas/
│   ├── student_profile_schema.py   # Pydantic model: input validation
│   └── agent_output_schemas.py     # Pydantic models: one per agent's expected output shape
│
├── output/
│   ├── report_builder.py           # Aggregates context → Markdown/JSON/HTML report
│   └── templates/
│       └── report_template.md
│
├── utils/
│   ├── logger.py                   # Structured logging (which agent ran, Gemini vs fallback, timing)
│   └── retry.py                    # Generic retry/backoff decorator used by llm_service
│
├── tests/
│   ├── test_orchestrator.py
│   ├── test_agents.py
│   └── test_llm_fallback.py        # Explicitly tests Gemini-down scenario
│
└── notebooks/
    └── ai_student_success_mentor.ipynb   # The actual Kaggle submission notebook,
                                            # imports from the package above
```

**Why this separation matters for a Kaggle submission specifically:**
- `prompts/` separated from `agents/` lets you show prompt-engineering iteration in your write-up without touching logic code
- `schemas/` gives you free input validation and makes every agent's output predictable — important when chaining 5 LLM-backed steps, since one malformed JSON response shouldn't crash the whole pipeline
- `llm_service.py` being the **only** Gemini touchpoint is what makes "Fallback mode if Gemini fails" an actual architectural property instead of a try/except sprinkled five times
- `notebooks/` stays thin — it imports the package, so the notebook reads like a clean demo, not a wall of implementation

---

## 3. Data Flow Diagram

I'll render this as a visual diagram so the flow is easy to follow.I have what I need. Here's the data flow as an architecture diagram.**How to read the flow:**

1. **Student profile** enters the system once, into the Orchestrator — no other component touches raw user input.
2. The Orchestrator runs the **five agents strictly in sequence** (Career → Skill Gap → Internship → Study Planner → Project Recommendation), because each downstream agent needs upstream output: Skill Gap needs Career's target role, Internship and Study Planner need Skill Gap's gap list, and Project Recommendation needs both Career and Skill Gap.
3. Every agent calls the **same LLM Service** rather than touching Gemini directly. That service always tries Gemini first; on any failure (timeout, quota exceeded, malformed JSON, missing key) it falls through to a **rule-based fallback** that reads from the **local data layer** (JSON/CSV files) instead. This is the part that makes "fallback mode" a real architectural guarantee rather than a single try/except.
4. All five agent outputs converge into the **Report Builder**, which is the only place that knows about output formatting — it doesn't know or care whether any given section came from Gemini or from fallback logic.

**A few design decisions worth flagging before we write code**, since they affect how the agents and fallback layer get built:

1. **Fallback data depth** — should each agent's fallback be a single static lookup table (fast, simple, but generic), or should it do light rule-based computation (e.g. set-difference between student skills and a career's required-skills list — more realistic, still no LLM)? I'd lean toward the latter for Skill Gap/Internship since it's barely more code and looks far less like a "stub."
2. **Gemini call pattern** — structured JSON output via response schema/`response_mime_type`, or freeform text parsed downstream? Structured output is more robust for chaining agents but constrains prompt style.
3. **Kaggle execution context** — will this run as a notebook with `GEMINI_API_KEY` as a Kaggle Secret, or as a standalone repo with `.env`? This affects how `config.py` and `llm_service.py` read credentials.

Want me to proceed straight into code (starting with `core/agent_base.py` and `core/llm_service.py` since everything else depends on them), or do you want to lock in answers to those three questions first?