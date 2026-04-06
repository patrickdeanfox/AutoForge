# CLAUDE.md — AutoForge Project Intelligence System

This file is read at the start of every Claude Code session. It tells you exactly what this
project is, how it is structured, what rules you must follow, and how to behave as an agent
operating inside this system. Read it fully before doing anything.

---

## What This Project Is

AutoForge is a multi-agent software development system built for an automation engineer who
creates scripts, pipelines, apps, workflows, and agents for customers being onboarded onto an
employer's programs and platforms. The system automates the full development lifecycle — intake,
planning, code execution, debugging, QA, documentation, and GitHub management.

You are operating as one of the agents in this system. Your behavior is governed by this file,
the employer profile (Layer 0), and the project manifest (Layer 2) for whatever project you are
currently working on. Read all three before executing any task.

---

## Repository Layout

This is the AutoForge system repo. It is NOT a customer project repo. Customer projects each
live in their own separate GitHub repository, created automatically when a project manifest is
initialized. AutoForge orchestrates them — it does not house them.

```
autoforge/                          ← You are here (the orchestration system)
├── config/
│   ├── employer_profile.json       ← Layer 0. Read this first on every session.
│   └── employer_profile.schema.py ← Pydantic validation for Layer 0
├── agents/
│   ├── base/                       ← BaseAgent class, manifest loader, observability
│   ├── research/                   ← Opus: crawl engine, conflict detector
│   ├── planning/                   ← Opus: planning agent, issue generator
│   ├── execution/                  ← Sonnet: coder, debug, refactor agents
│   └── qa/                         ← Sonnet/Haiku: review, testgen, docgen, security
├── orchestration/
│   ├── graph.py                    ← LangGraph state machine
│   ├── scheduler.py                ← Celery tasks and beat schedule
│   ├── github_manager.py           ← All GitHub API operations
│   ├── project_registry.py         ← Registry of all managed project repos
│   └── escalation.py               ← Stuck agent logic, needs-human creation
├── observability/
│   ├── logger.py                   ← structlog JSON setup
│   ├── metrics.py                  ← Prometheus metric definitions
│   ├── tracing.py                  ← OpenTelemetry setup
│   └── cost_tracker.py             ← Anthropic token spend tracking
├── api/
│   └── main.py                     ← FastAPI application
├── frontend/
│   ├── layer0-form/                ← Employer profile intake form (React)
│   ├── layer1-form/                ← Project intake wizard (React)
│   ├── planning-chat/              ← Opus planning chat interface (React)
│   └── dashboard/                  ← Morning PR queue dashboard (React)
├── schemas/
│   ├── employer_profile.py         ← Pydantic: Layer 0 schema
│   ├── project_manifest.py         ← Pydantic: Layer 2 schema
│   ├── decision_record.py          ← Pydantic: Decision Record schema
│   └── knowledge_resource.py       ← Pydantic: Resource schema
└── templates/
    └── github/workflows/           ← Injected into every new project repo
```

### Customer Project Repos (separate — not in this tree)

```
github.com/{org}/{project-slug}/    ← Created per project at manifest init
├── project_manifest.json           ← Layer 2: the source of truth for that project
├── knowledge/
│   ├── resources/                  ← APIs, data, schemas, codebase, infra
│   ├── decisions/                  ← Decision Records (DR-XXX.json)
│   ├── conflicts/                  ← Flagged issues needing human resolution
│   └── crawl_log/                  ← Audit trail of all crawl operations
├── src/                            ← All project source code
├── tests/                          ← All project tests
└── docs/                           ← Generated documentation
```

---

## The Layer System — Read Before Every Task

Every action you take must be grounded in the correct layer. Do not skip layers.

### Layer 0 — Employer Profile (`config/employer_profile.json`)
Set once. Locked. Applies to every project without exception. Contains code standards, git
rules, security requirements, deployment windows, approved tech defaults, and compliance
frameworks. **Locked fields in Layer 0 cannot be overridden by any project. Ever.**

### Layer 1 — Knowledge & Resources (lives in the project repo under `knowledge/`)
Per project. Built up before execution begins. Contains:
- Provided resources: API docs, Swagger specs, DDLs, sample data, ERDs, legacy code
- Decision Records: every significant technology choice, from Unexplored → Under Discussion → Locked
- Crawl results: everything the Research Agent discovered autonomously

**Nothing in this layer is a hard constraint until its Decision Record status is `locked`.**

### Layer 2 — Project Manifest (`project_manifest.json` in the project repo)
The single source of truth for a project. Merges Layer 0 + Layer 1. Human-approved before
execution begins. **Read this before writing a single line of code for a project.**

### Layers 3–5 — Agents (planning, execution, QA)
You operate here. You always read Layers 0 and 2 before acting. You never make architectural
decisions that are not in a locked Decision Record. If you encounter an undecided choice, you
stop and create a `decision-needed` GitHub Issue.

### Layer 6 — Observability
Every step you take must emit structured log events. This is not optional. See the
Observability section below.

---

## Rules You Must Follow — No Exceptions

### Before Starting Any Task
1. Read `config/employer_profile.json`
2. Read the project's `project_manifest.json`
3. Check the relevant locked Decision Records in `knowledge/decisions/`
4. Confirm the GitHub Issue you are working on has the `approved` label
5. If any of these are missing, stop and ask rather than assume

### Branching
- Never commit directly to `main` or any protected branch
- Always create a feature branch before writing any code
- Branch naming must follow the convention in the employer profile
- Convention: `feature/{issue-number}-{short-description}`, `fix/`, `chore/`, `hotfix/`

### Code Standards
- Follow the style guide specified in the employer profile (default: PEP8 for Python)
- Type hints are required on all Python functions and class methods
- Docstrings are required on all public functions, classes, and modules
- No line should exceed the employer-specified character limit
- No unused imports, no dead code, no commented-out blocks left behind
- Naming conventions must match the employer profile exactly

### Tests
- Write tests before or alongside implementation — not after
- Minimum coverage threshold is defined in the employer profile — never go below it
- Tests must be meaningful — do not write tests that only exist to hit coverage numbers
- Test names must be descriptive: `test_should_return_empty_list_when_no_reviews_found`
- Mock all external API calls in unit tests — never make real network calls in tests

### Security — Non-Negotiable
- Never hardcode secrets, API keys, tokens, passwords, or credentials of any kind
- Never log PII fields — check the employer profile for the list of PII field names
- Never access production databases — dev/staging only
- Never install packages not already in `pyproject.toml` or `package.json` without creating
  a `decision-needed` issue first
- Run `detect-secrets` before every commit

### Architectural Decisions
- If a task requires a technology choice not in a locked Decision Record, **stop**
- Create a GitHub Issue labeled `decision-needed` describing exactly what decision is needed
- List the options you see, the tradeoffs you've identified, and what information is missing
- Move on to the next approved issue — do not block the entire pipeline
- Never pick a technology arbitrarily because it seems reasonable

### Forbidden Actions
- Do not merge any PR — humans merge
- Do not approve PRs in current state (future state: earned autonomy model)
- Do not push to main or protected branches
- Do not access production systems
- Do not make external API calls outside of the crawl engine's designated scope
- Do not install system packages with `apt` or `brew`
- Do not modify `config/employer_profile.json` without an explicit instruction and a version bump
- Do not modify a locked Decision Record without explicit engineer instruction

---

## How to Work on a Task

### Step-by-step execution process

```
1. Read employer_profile.json
2. Read project_manifest.json for this project
3. Read the GitHub Issue — understand acceptance criteria fully before starting
4. Check knowledge/decisions/ for any Decision Records relevant to this task
5. Check knowledge/resources/ for any APIs, schemas, or data relevant to this task
6. Identify if any decisions are needed that don't have a locked DR → stop and flag if so
7. Create feature branch: git checkout -b feature/{issue-number}-{description}
8. Write failing tests first (TDD where practical)
9. Write implementation code to make tests pass
10. Run linting: ruff check . --fix (Python) or eslint --fix (JS)
11. Run type checking: mypy . (Python)
12. Run full test suite: pytest --cov (Python) or vitest run --coverage (JS)
13. Run security scan: bandit -r . and detect-secrets scan
14. If all pass → run refactor pass (dead code, complexity, naming)
15. Commit with conventional commit message (see format below)
16. Push branch and open Draft PR
17. Emit completion log event (see Observability)
```

### If tests fail
- Diagnose root cause before attempting a fix — write the diagnosis as a comment
- Attempt fix (attempt 1)
- Re-run tests
- If still failing, attempt fix (attempt 2) with a different approach
- Re-run tests
- If still failing, attempt fix (attempt 3)
- After 3 failed attempts: create `needs-human` GitHub Issue with full diagnosis,
  all error output, all attempt logs, and stop. Do not attempt a 4th fix.

---

## Commit Message Format

Follow Conventional Commits. This is locked in the employer profile.

```
<type>(<scope>): <short description>

[optional body — explain WHY, not what]

[optional footer: Issue #123, Breaking change: ...]
```

Types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `perf`, `ci`, `build`

Examples:
```
feat(coder-agent): add retry logic for failed test runs

fix(crawl-engine): handle rate limit 429 responses from Swagger endpoints

docs(readme): update local dev setup for Linux Mint hybrid model

test(research-agent): add unit tests for conflict detector against Layer 0

chore(deps): bump langchain to 0.3.2
```

---

## GitHub Issue Labels — Understand These

| Label | Meaning | Who Sets It |
|---|---|---|
| `approved` | Engineer has approved this issue for execution | Engineer |
| `needs-human` | Agent is stuck, requires human intervention | Agent |
| `decision-needed` | Agent encountered an undecided tech choice | Agent |
| `blocked` | Cannot proceed — waiting on something | Agent or Engineer |
| `feature` | New functionality | Planning Agent |
| `fix` | Bug fix | Planning Agent |
| `chore` | Maintenance, refactor, deps | Planning Agent |
| `spike` | Research task, no code output required | Planning Agent |
| `S` / `M` / `L` / `XL` | Complexity estimate | Planning Agent |

**Never pick up an issue without the `approved` label.**

---

## Observability — Every Step Must Be Logged

Every significant action must emit a structured JSON log event via `observability/logger.py`.
Observability is not optional. The monitoring dashboard and alerting system depend on it.

### Required log fields

```python
{
    "timestamp": "ISO8601",
    "level": "info | warning | error",
    "service": "agent-name",          # e.g. "coder-agent", "debug-agent"
    "agent_id": "unique-agent-id",
    "project_id": "project-slug",
    "issue_id": "GH-{number}",
    "run_id": "run-{uuid}",
    "trace_id": "otel-trace-id",
    "step": "step-name",              # e.g. "write_implementation", "run_tests"
    "event": "step_start | step_complete | step_failed",
    "duration_ms": 0,                 # 0 for step_start events
    "tokens_used": 0,                 # LLM tokens consumed in this step
    "outcome": "success | failure | retry",
    "metadata": {}                    # any additional context
}
```

### What must be logged

- Agent session start and end
- Every major step start and completion
- Every external API call (URL, status code, latency)
- Every LLM call (model, tokens in, tokens out)
- Every GitHub API call (endpoint, status)
- Every test run (pass/fail, coverage %)
- Every retry attempt (attempt number, reason)
- Every escalation (needs-human, decision-needed)

### Never log these

- Full LLM prompt or response content in production
- API keys, tokens, or secrets of any kind
- PII fields (defined in employer profile)
- Raw database query results containing customer data

---

## Technology Stack Quick Reference

### Models by task
| Task | Model |
|---|---|
| Planning, architecture, research | Claude Opus 4 |
| Code writing, debugging, review | Claude Sonnet 4 |
| Doc generation, security scan volume | Claude Haiku 4.5 |

### Core backend
- **FastAPI** — API server (async, Pydantic native)
- **Pydantic v2** — all schema validation
- **SQLAlchemy 2.x + Alembic** — ORM and migrations
- **PostgreSQL 16** — primary database (runs in Docker)
- **Redis 7** — Celery broker + cache (runs in Docker)
- **Celery 5.4** — task queue and scheduling
- **LangGraph** — agent orchestration state machine

### Core frontend
- **React 18 + Vite 5** — all UI
- **Tailwind CSS 3** — styling
- **Vercel AI SDK** — streaming chat (planning interface)
- **React Hook Form + Zod** — forms and validation
- **Recharts** — dashboard charts

### Testing
- **pytest + pytest-asyncio + Coverage.py** — Python tests
- **Vitest** — JS/TS tests
- **Ruff** — Python linting (fast, auto-fix)
- **Mypy** — Python type checking
- **Bandit + Semgrep** — security scanning
- **detect-secrets** — secret detection pre-commit

### Observability
- **structlog** — structured JSON logging
- **Prometheus + Grafana** — metrics and dashboards
- **OpenTelemetry + Jaeger** — distributed tracing
- **Loki** — log aggregation
- **Sentry** — error tracking

### GitHub
- **PyGithub** — all GitHub API operations
- **GitHub Actions** — CI/CD and cron scheduling

---

## Local Environment — Linux Mint (Hybrid Model)

Infrastructure runs in Docker. Application code runs natively.

### Start infrastructure

```bash
docker compose up -d        # starts PostgreSQL 16 + Redis 7
docker compose ps           # verify both are running
```

### Start application services

```bash
systemctl --user start autoforge-api      # FastAPI on :8000
systemctl --user start autoforge-celery   # Celery workers
systemctl --user start autoforge-beat     # Celery Beat scheduler
```

### Activate Python environment

```bash
source ~/.venvs/autoforge/bin/activate
python --version    # should be 3.11.x (managed by pyenv)
```

### Run tests

```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

### Run linting

```bash
ruff check . --fix
mypy .
```

### Run security scan

```bash
bandit -r . -ll
detect-secrets scan --baseline .secrets.baseline
```

### Follow logs

```bash
journalctl --user -u autoforge-celery -f    # Celery worker logs
journalctl --user -u autoforge-api -f       # FastAPI logs
```

### Stop everything

```bash
systemctl --user stop autoforge-api autoforge-celery autoforge-beat
docker compose down
```

### Important paths

| Path | Purpose |
|---|---|
| `~/.venvs/autoforge/` | Python virtualenv |
| `~/.pyenv/versions/3.11.9/` | Python installation |
| `/tmp/autoforge-work/{run-id}/` | Temp working dir for agent repo clones |
| `config/employer_profile.json` | Layer 0 — read every session |
| `.env` | Local secrets (never committed — generated from pass store) |

---

## Decision Records — How to Handle Them

### If a Decision Record exists and is `locked`
Treat it as a hard constraint. Do not deviate. Do not suggest alternatives mid-task.

### If a Decision Record exists and is `under_discussion`
Do not make the decision yourself. The engineer is actively working through it. Continue with
other tasks that don't depend on this decision.

### If a Decision Record exists and is `unexplored`
You may run a research pass — crawl relevant docs, benchmarks, and options — and produce a
structured options analysis to add to the DR. Do not lock it yourself. Flag it for engineer
review.

### If no Decision Record exists but one is needed
1. Stop work on the task requiring the decision
2. Create a GitHub Issue labeled `decision-needed`
3. Include: what decision is needed, what options you see, relevant tradeoffs, any constraints
   from the employer profile or project manifest that apply
4. Move on to the next approved issue

---

## Project Manifest — What to Look For

When you read a project's `project_manifest.json`, pay attention to:

- `technical.required_tools` — you must use these
- `technical.forbidden_tools` — you must never use these
- `technical.delivery_type` — shapes what you build (API vs script vs pipeline etc.)
- `employer_standards.security_compliance` — active compliance requirements
- `employer_standards.code.test_coverage_min` — your coverage floor
- `audience.technical_level` — affects code complexity, docs style, error message clarity
- `audience.interaction_modes` — CLI? Dashboard? API? Scheduled? Determines output shape
- `observability` — which logging/metrics/tracing platforms are in use for this project
- `project.known_constraints` — quirks you must code around
- `knowledge.decisions` — locked technology choices to enforce

---

## Agent Permissions — What You Can and Cannot Do

| Action | Permitted |
|---|---|
| Read any file in the project repo | ✓ |
| Write files to feature branch | ✓ |
| Commit to feature branch | ✓ |
| Push feature branch to GitHub | ✓ |
| Open a Draft PR | ✓ |
| Promote Draft → Ready for Review (after QA passes) | ✓ |
| Post review comments on a PR | ✓ |
| Create GitHub Issues (needs-human, decision-needed) | ✓ |
| Crawl URLs and external docs (Research Agent only) | ✓ |
| Introspect dev/staging databases (Research Agent only) | ✓ |
| Approve a PR | ✗ — future state only |
| Merge a PR to any branch | ✗ — future state only |
| Push directly to main or protected branches | ✗ — never |
| Access production databases | ✗ — never |
| Install system packages | ✗ — never |
| Modify employer_profile.json | ✗ — requires explicit instruction + version bump |
| Override a locked Decision Record | ✗ — never |
| Make external API calls outside crawl scope | ✗ |

---

## Escalation Paths

### When to create a `needs-human` issue
- 3 consecutive failed debug attempts with no resolution
- CI is consistently failing and root cause is unclear after diagnosis
- A required external service is unreachable and blocking progress
- A task requires access or permissions that agents don't have

### When to create a `decision-needed` issue
- A technology choice is required that has no locked Decision Record
- A task's acceptance criteria are ambiguous or contradictory
- Two locked Decision Records conflict with each other

### When to create a `knowledge-drift` issue
- Re-crawl detects new or removed API endpoints
- Database schema has changed since last crawl
- A dependency has a new major version with breaking changes
- A CVE has been filed against a project dependency

### What to include in every escalation issue
- Which issue/PR/task triggered this escalation
- Exact error output or the specific ambiguity encountered
- What was attempted (for needs-human: all 3 attempts with outputs)
- What information or action is needed from the engineer
- Which files are relevant

---

## Scope of This Session

When Claude Code starts a session it should:

1. Read this file completely
2. Read `config/employer_profile.json`
3. If working on a specific project — read that project's `project_manifest.json`
4. Check for any open `needs-human` or `decision-needed` issues that might affect the current task
5. Confirm the GitHub Issue being worked on has the `approved` label
6. Then and only then begin the task

If no specific task is given at session start, ask:
- Which project?
- Which GitHub Issue?
- Is there anything that has changed since the last session that affects approach?

---

## Reference Documents

- **Full project plan:** `autoforge_project_plan.md` — master reference, 20 sections
- **Employer profile:** `config/employer_profile.json` — Layer 0, read every session
- **Project manifest:** `{project-repo}/project_manifest.json` — Layer 2, read per project
- **Decision Records:** `{project-repo}/knowledge/decisions/DR-XXX.json` — per decision
- **Observability guide:** `observability/README.md` — logging/metrics/tracing patterns
- **Agent base class:** `agents/base/base_agent.py` — inherit from this for all agents

---

*CLAUDE.md version: 1.0 — update when project structure, rules, or agent behavior changes.*  
*Matches project plan version: 1.2*  
*Last updated: 2025-04-05*