# AutoForge — Multi-Agent Software Development System
## Comprehensive Project Plan

**Version:** 1.3  
**Date:** 2026-04-06  
**Author:** Automation Engineer  
**Status:** Planning Phase  
**Document Type:** Master Project Plan — Reference Throughout Development  
**Platform:** Linux Mint (Ubuntu-based)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Vision & Goals](#2-system-vision--goals)
3. [Architecture Overview](#3-architecture-overview)
4. [Layer Definitions](#4-layer-definitions)
   - 4.0 [Employer Profile](#40-layer-0--employer-profile)
   - 4.1 [Knowledge & Resources](#41-layer-1--knowledge--resources)
   - 4.2 [Project Manifest](#42-layer-2--project-manifest)
   - 4.3 [Planning Agent](#43-layer-3--planning-agent)
   - 4.4 [Execution Agents](#44-layer-4--execution-agents)
   - 4.5 [QA & Review Agents](#45-layer-5--qa--review-agents)
   - 4.6 [Observability Pipeline](#46-layer-6--observability-pipeline)
5. [Agent Roster & Responsibilities](#5-agent-roster--responsibilities)
6. [Complete Technology Stack](#6-complete-technology-stack)
7. [Repository Structure](#7-repository-structure)
8. [Project Repository Model](#8-project-repository-model)
9. [Human Gates & Approval Workflow](#9-human-gates--approval-workflow)
10. [Agent PR Approval — Current & Future State](#10-agent-pr-approval--current--future-state)
11. [Scheduling & Off-Hours Automation](#11-scheduling--off-hours-automation)
12. [Telegram Command Interface](#12-telegram-command-interface)
13. [Claude Desktop & Claude Code MCP Setup](#13-claude-desktop--claude-code-mcp-setup)
14. [Development Phases & Timeline](#14-development-phases--timeline)
15. [Build Order & Process](#15-build-order--process)
16. [Linux Mint Environment Setup](#16-linux-mint-environment-setup)
17. [Observability & Monitoring Strategy](#17-observability--monitoring-strategy)
18. [Security & Compliance Strategy](#18-security--compliance-strategy)
19. [Decision Record Framework](#19-decision-record-framework)
20. [Risk Register](#20-risk-register)
21. [Success Metrics](#21-success-metrics)
22. [Glossary](#22-glossary)

---

## 1. Executive Summary

AutoForge is a multi-agent software development system built for an automation engineer working at an employer that onboards customers onto programs and platforms. The system automates the full software development lifecycle — from business problem intake through code execution, debugging, QA, documentation, and GitHub management — with the goal of maximizing off-hours autonomous execution and reserving human on-hours time for decisions, approvals, and work requiring judgment.

The system is structured in seven layers. The bottom two layers (Employer Profile and Knowledge & Resources) are project-agnostic foundations that are configured once or built up per project respectively. The Project Manifest merges both into a customer-specific source of truth that governs all agent behavior downstream. Three agent layers handle planning, execution, and QA. A cross-cutting observability pipeline instruments every step of every layer.

The engineer interacts with the system through three interfaces: the **AutoForge web dashboard** for deep configuration and planning sessions, the **Telegram bot** for mobile command and control from anywhere at any time, and **Claude Desktop** with MCP filesystem access for high-context planning conversations directly against live project files.

**What this system is not:** A replacement for engineering judgment. Every significant decision — architectural choices, spec approval, PR merges, conflict resolution — requires human approval before execution proceeds. AutoForge removes the mechanical work so that human attention is applied only where it actually matters.

---

## 2. System Vision & Goals

### Primary Goals

- **Automate the mechanical:** Code writing, debugging, refactoring, test generation, documentation, PR creation, and routine GitHub management run autonomously without human intervention.
- **Gate the consequential:** Spec approval, architectural decisions, PR merges, and production deployments always require human sign-off.
- **Preserve business context:** Every agent that runs on a project has full awareness of the customer's business problem, the employer's standards, the chosen technology stack, compliance rules, and audience requirements — without the engineer re-explaining them.
- **Make everything observable:** No agent step runs silently. Every execution, decision, failure, retry, and outcome is logged, traced, and available in a monitoring dashboard.
- **Work while you sleep:** The system is designed so that approved tasks are picked up, executed, reviewed, and queued for your morning review during off-hours without human involvement.
- **Command from anywhere:** Human gates are reachable via Telegram on mobile. Approvals, triggers, and status checks never require sitting at a desk.

### Design Principles

- **Manifest-first:** No agent executes without reading the full project manifest. The manifest is the single source of truth.
- **Locked vs. overridable:** Employer standards are locked and cannot be overridden by projects. Project-level settings can be tailored within employer constraints.
- **Crawl before you code:** The Knowledge Layer is populated by agent-driven discovery before execution begins. Agents never make assumptions about systems they haven't explored.
- **Fail loudly:** Stuck agents create visible issues rather than silently failing or making arbitrary decisions. Ambiguity surfaces to humans — including pushing to Telegram.
- **Audit everything:** Every agent action, every decision record, every crawl result is version-controlled and auditable.
- **Mobile-first gates:** Every human gate has a corresponding Telegram interaction path. No gate requires the web dashboard if you're away from the machine.

---

## 3. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 0 — EMPLOYER PROFILE                                          │
│  Set once per employer. Version-locked. Source of all defaults.      │
│  employer_profile.json — protected branch                            │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ inherited by every project
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 1 — KNOWLEDGE & RESOURCES                                     │
│  Per project. Built up before execution begins.                      │
│  ├── Provided Resources   (APIs, schemas, DDLs, sample data)         │
│  ├── Decision Records     (Unexplored → Discussed → Locked)          │
│  └── Crawl Engine         (Agent-driven discovery + drift monitor)   │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ merged into
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 2 — PROJECT MANIFEST                                          │
│  Per customer/project. Inherits Layer 0 + Layer 1.                   │
│  All decisions locked. All resources referenced.                     │
│  Human approved before execution begins.                             │
│  project_manifest.json — protected branch                            │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ injected into all agents below
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 3 — PLANNING AGENT (Opus 4)                                   │
│  Manual trigger. Chat-driven spec creation.                          │
│  Reads full manifest as system prompt context.                       │
│  Interface: Web dashboard OR Claude Desktop (MCP)                    │
│  Produces structured GitHub Issues + milestones.                     │
│  ⛔ HUMAN GATE: Spec approval before execution                       │
│  📱 Telegram: /issues pending → /approve 42                         │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ approved GitHub Issues
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 4 — EXECUTION AGENTS (Sonnet 4 + Claude Code)                 │
│  Triggered by approved issues + cron schedule (off-hours)            │
│  ┌────────────┐   ┌─────────────┐   ┌──────────────┐               │
│  │   CODER    │   │   DEBUGGER  │   │   REFACTOR   │               │
│  │   AGENT    │──▶│   AGENT     │──▶│   AGENT      │               │
│  └────────────┘   └─────────────┘   └──────────────┘               │
│                                            │                         │
│                                            ▼                         │
│                                      Draft PR opened                 │
│  ⛔ HUMAN GATE: PR review + merge                                    │
│  📱 Telegram: /queue → review link → merge on GitHub                │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ PR opened
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 5 — QA & REVIEW AGENTS (Sonnet 4 + Haiku 4.5)                │
│  Triggered by PR opened event                                        │
│  ┌────────────┐   ┌─────────────┐   ┌──────────────┐               │
│  │    CODE    │   │    TEST     │   │     DOC      │               │
│  │   REVIEW   │   │     GEN     │   │     GEN      │               │
│  │   AGENT    │   │    AGENT    │   │    AGENT     │               │
│  └────────────┘   └─────────────┘   └──────────────┘               │
│        │                │                  │                         │
│        └────────────────┴──────────────────┘                        │
│                          │                                           │
│                   PR promoted: Draft → Ready for Review              │
│  ⛔ HUMAN GATE: Final review + merge to main                        │
│  📱 Telegram: morning summary push → /queue for PR links            │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ runs across ALL layers
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 6 — OBSERVABILITY PIPELINE                                    │
│  Every agent step: logged, traced, metriced, alerted                 │
│  Structured logs → Metrics → Distributed traces → Dashboard          │
│  📱 Telegram: critical alerts pushed in real time                   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  CONTROL INTERFACES                                                  │
│  ┌──────────────────┐  ┌────────────────────┐  ┌─────────────────┐ │
│  │  Web Dashboard   │  │  Telegram Bot      │  │ Claude Desktop  │ │
│  │  (full config,   │  │  (mobile gates,    │  │ (MCP planning,  │ │
│  │   planning chat, │  │   approvals,       │  │  manifest chat, │ │
│  │   observability) │  │   alerts, status)  │  │  DR resolution) │ │
│  └──────────────────┘  └────────────────────┘  └─────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Layer Definitions

---

### 4.0 Layer 0 — Employer Profile

**Purpose:** Define the fixed rules, standards, and defaults that apply to every project without exception. Set once per employer, version-controlled, never modified without deliberate intent.

**Trigger:** One-time setup when onboarding to a new employer. Updated only when employer standards officially change.

**Storage:** `autoforge/config/employer_profile.json` on a protected branch. Changes require a PR with explicit version bump.

**Contents:**

#### Identity
- Employer name and department
- Standards document name and version number
- Standards owner contact (for escalation)
- Date last updated

#### Code Standards (Locked)
- Language-specific style guides (PEP8, Airbnb, Google Style, internal)
- Naming conventions for variables, classes, functions, files, repos, branches
- Required files in every repo (README.md, CHANGELOG.md, .env.example, Dockerfile)
- Documentation requirements (docstrings on all public functions, README format template)
- Minimum test coverage percentage (e.g., 80%)
- Forbidden anti-patterns and code smells explicitly banned by the employer
- Maximum function complexity thresholds (cyclomatic complexity limits)

#### Git & GitHub Rules (Locked)
- Branching strategy (GitFlow / trunk-based / GitHub Flow)
- Branch naming conventions (`feature/`, `fix/`, `hotfix/`, `chore/`)
- Commit message format (Conventional Commits, custom internal)
- PR requirements (minimum reviewers, required status checks)
- Protected branches and ruleset definitions
- What can be merged without human approval vs. requires sign-off
- Squash vs. merge commit policy

#### Security Baseline (Locked — Cannot Be Overridden)
- No hardcoded secrets under any circumstances
- Required secrets management tool (Vault, AWS Secrets Manager, etc.)
- Approved credential patterns and injection methods
- Compliance frameworks that always apply (SOC2, GDPR, HIPAA, etc.)
- No PII in logs — ever
- Required OWASP Top 10 checks on every PR
- Approved authentication patterns

#### Deployment Rules (Locked)
- Approved deployment windows
- Change management process and required ticket fields
- Environments that always exist (dev, staging, prod)
- What requires CAB approval vs. can be automated
- Rollback procedure requirements

#### Default Observability Stack
- Approved logging platform and format (e.g., structured JSON to DataDog)
- Required metrics platform (Prometheus, DataDog APM, etc.)
- Alerting defaults and escalation contacts
- Required logging fields (correlation ID, service name, environment, timestamp)
- Distributed tracing requirements

#### Approved Technology Defaults
- Approved programming languages
- Approved cloud platforms and services
- Approved data stores
- Approved CI/CD tooling
- Standing forbidden technologies (with reasons)

#### Locked vs. Overridable Matrix

| Setting | Locked | Overridable | Notes |
|---|---|---|---|
| Security rules | ✓ | | Never overridden |
| No PII in logs | ✓ | | Never overridden |
| Compliance frameworks | ✓ | | Never overridden |
| Deployment windows | ✓ | | Never overridden |
| Commit message format | ✓ | | Never overridden |
| Branch protection rules | ✓ | | Never overridden |
| Test coverage minimum | ✓ | | Project can exceed, not reduce |
| Style guide | ✓ | | Never overridden |
| Preferred language | | ✓ | Customer may require different |
| Logging platform | | ✓ | Customer may have own stack |
| Cloud platform | | ✓ | Customer may require specific cloud |
| CI/CD tooling | | ✓ | Customer may have existing pipeline |
| Data store choice | | ✓ | Governed by Decision Records |

---

### 4.1 Layer 1 — Knowledge & Resources

**Purpose:** Aggregate all project-specific knowledge — existing systems, APIs, data structures, and unresolved technical decisions — before any code is written. Ensures agents work from fact, not assumption.

**Trigger:** Initiated at project creation. Continuously updated as new resources are discovered or decisions are made.

**Storage:** `project/knowledge/` directory, committed to the project repo.

**Three States of Everything in This Layer:**

```
UNEXPLORED          UNDER DISCUSSION        DECIDED & LOCKED
──────────────      ────────────────        ────────────────
Known gap.          Actively being          Choice made with
Opus Research       analyzed and            documented
Agent will          discussed with          rationale.
investigate.        engineer.               Agents treat as
                                           hard constraint.
```

#### A — Provided Resources

**API & Integration Documentation**
- OpenAPI / Swagger spec files (uploaded or URL — agents crawl the URL)
- REST API documentation (Postman collections, markdown docs)
- GraphQL schemas
- Webhook payload examples and event catalogs
- Authentication documentation (OAuth flows, API key patterns, token refresh)
- Rate limit documentation per endpoint
- SDK documentation for third-party libraries

**Data Resources**
- Sample data files (CSV, JSON, XML, Parquet)
- Anonymized real data snapshots
- Database connection details (dev/staging only — never production)
- DDL files (CREATE TABLE, CREATE INDEX statements)
- ERD diagrams (Claude Vision reads and describes structure)
- Table and column data dictionaries
- Known data quality issues, quirks, and anomalies
- Data volume estimates (record counts, growth rates)

**Existing Code & Systems**
- Legacy codebase snippets agents must integrate with or work around
- Existing utility functions and shared libraries available for reuse
- Patterns already established in the codebase
- Known technical debt items and workarounds
- Existing test suites and their coverage

**Environment & Configuration**
- Environment variable templates (.env.example)
- Config file structures
- Infrastructure diagrams and network topology notes
- Existing CI/CD pipeline definitions

#### B — Decision Records

Every significant technical choice gets a Decision Record. This is the structured log of what was considered, what was chosen, and why.

**Decision Record Schema:**
```json
{
  "id": "DR-001",
  "title": "Vector Store Selection",
  "status": "locked",
  "category": "infrastructure",
  "context": "Need semantic search on 2M+ product reviews. Running on AWS. PostgreSQL already in stack.",
  "options": [
    {
      "name": "PgVector",
      "pros": ["Already in Postgres stack", "No new infra", "Team familiarity", "ACID transactions"],
      "cons": ["Slower at scale >5M vectors", "No managed service"],
      "estimated_cost": "$0 additional"
    },
    {
      "name": "Pinecone",
      "pros": ["Fully managed", "Scales infinitely", "Best-in-class performance"],
      "cons": ["External vendor", "Data leaves infra", "SOC2 compliance question"],
      "estimated_cost": "~$70/month starter"
    }
  ],
  "decision": "PgVector",
  "rationale": "Scale is under 2M vectors for MVP. Team knows PostgreSQL. No new infra required. Migration path exists if scale demands it.",
  "locked_by": "engineer",
  "locked_date": "2025-04-05",
  "revisit_trigger": "If vectors exceed 5M or P95 query latency exceeds 500ms"
}
```

**Decision Categories:**
- `infrastructure` — databases, queues, caches, cloud services
- `library` — Python packages, JS libraries, frameworks
- `architecture` — patterns, communication styles, data flow
- `integration` — how to connect to external systems
- `data` — storage format, schema design, transformation approach

#### C — Agent-Driven Crawl Engine

The Research Agent (Opus) crawls autonomously when given a seed. Seeds can be:
- A URL (Swagger endpoint, API docs page, GitHub repo, library PyPI page)
- A database connection string (dev/staging only)
- A question ("what are the best options for scraping JavaScript-rendered pages")
- A file (DDL, CSV, ERD image, Postman collection)

**Crawl outputs:**
- Structured resource files added to `knowledge/resources/`
- Draft Decision Records for any unresolved choices encountered
- Conflict flags when findings contradict employer standards
- Gap list of things the agent couldn't determine autonomously

**Conflict Detection During Crawl:**
The Research Agent checks all findings against Layer 0 in real time:
- Forbidden technology detected in existing codebase → flagged
- PII fields found in API responses → logging strategy flagged
- Library with active CVEs or abandoned maintenance → flagged
- Technology that violates compliance requirements → flagged

**Scheduled Re-Crawl:**
Once per week, the Research Agent re-crawls all registered resource URLs and database connections to detect drift. Drift detected → `knowledge-drift` GitHub Issue created → Telegram alert sent → engineer reviews → manifest updated if needed.

---

### 4.2 Layer 2 — Project Manifest

**Purpose:** The single source of truth for a project. Merges employer defaults (Layer 0) with project-specific context and locked decisions (Layer 1). Every downstream agent reads this before doing anything.

**Trigger:** Created during project intake. Locked by engineer after review. Modified only through approved PRs.

**Storage:** `project/project_manifest.json` on protected branch. All modifications are PRs with version bumps.

**Contents:**
- Full project identity (name, client, problem statement, success metrics)
- Audience definition (primary users, technical level, interaction modes)
- Inherited employer standards from Layer 0 (locked fields immutable)
- All locked Decision Records from Layer 1
- References to all knowledge resources
- Technology stack (resolved from decisions)
- Observability configuration
- Timeline and milestone definitions
- Human gate schedule

**Validation:** Pydantic v2 models enforce schema. Locked fields from Layer 0 cannot be overridden. Any attempt to override a locked field raises a validation error before the manifest is saved.

---

### 4.3 Layer 3 — Planning Agent

**Model:** Claude Opus 4  
**Trigger:** Manual — engineer initiates a chat session  
**Interface:** Web dashboard streaming chat UI (React + Vercel AI SDK) **or** Claude Desktop with MCP filesystem access (see Section 13)

**Responsibilities:**
- Read the full project manifest and knowledge layer as system context
- Engage in natural language conversation to clarify what needs to be built
- Ask targeted questions to resolve ambiguity before spec is written
- Decompose work into discrete, actionable GitHub Issues
- Assign labels, milestones, and priority to each issue
- Identify dependencies between issues
- Flag anything that requires a Decision Record before execution can begin
- Estimate complexity and suggest sequencing

**Output per Issue:**
```markdown
Title: [clear, actionable task name]
Labels: [feature|fix|chore|spike] + [complexity: S|M|L|XL]
Milestone: [phase name]
Acceptance Criteria:
  - [ ] Specific, testable condition 1
  - [ ] Specific, testable condition 2
Technical Notes:
  - Relevant constraints from manifest
  - Decision records that apply
  - Resources from knowledge layer to use
Dependencies: [issue numbers this blocks or is blocked by]
```

**Human Gate:** Engineer reviews all generated issues. Approves by adding `approved` label via the web UI **or** via `/approve <issue-number>` in Telegram. Nothing executes until labeled.

---

### 4.4 Layer 4 — Execution Agents

**Model:** Claude Sonnet 4 + Claude Code CLI  
**Trigger:** GitHub Issue labeled `approved` + off-hours cron schedule  
**Orchestration:** LangGraph state machine + Celery task queue

#### Coder Agent

**Responsibilities:**
- Read the approved GitHub Issue and full project manifest
- Create feature branch following employer naming conventions
- Write implementation code following all style guide rules
- Write unit tests meeting minimum coverage threshold
- Run tests locally before committing
- Commit with conventional commit messages
- Open a Draft PR when tests pass

**Constraints:**
- Never commits directly to main or protected branches
- Never uses forbidden technologies from manifest
- Never makes architectural decisions not in Decision Records — creates `decision-needed` issue instead
- Stops and escalates after 3 consecutive test failures

#### Debug Agent

**Trigger:** CI test failure on a PR branch  
**Responsibilities:**
- Read the full error output, stack trace, and test failure details
- Analyze root cause before attempting fixes
- Write a diagnosis note explaining what failed and why
- Implement a targeted fix
- Re-run the failing tests
- If fix resolves the issue, commit and continue
- After 3 failed attempts, create `needs-human` issue with full diagnosis, push Telegram alert, and stop

#### Refactor Agent

**Trigger:** After Coder Agent's tests pass, before PR is promoted  
**Responsibilities:**
- Run linting tools and auto-fix where possible
- Check complexity thresholds and simplify where needed
- Remove dead code and unused imports
- Ensure naming conventions match employer standards
- Check for duplicated logic that could be extracted
- Verify type hints are present and correct (Python)
- Final pass before QA agents see the code

#### Execution Flow

```
Approved Issue picked up by Celery worker
        ↓
Coder Agent: create branch → write code → write tests → run tests
        ↓ pass                    ↓ fail (attempt 1-3)
Refactor Agent              Debug Agent: diagnose → fix → re-run
        ↓                         ↓ pass        ↓ fail after 3
Draft PR opened             Refactor Agent   needs-human issue
                                  ↓           + Telegram alert
                            Draft PR opened   (agent stops)
```

---

### 4.5 Layer 5 — QA & Review Agents

**Models:** Claude Sonnet 4 (review, test gen) + Claude Haiku 4.5 (doc gen, security scan volume)  
**Trigger:** Draft PR opened event via GitHub Actions webhook  
**Orchestration:** Parallel execution — all four agents run simultaneously

#### Code Review Agent (Sonnet 4)

**Responsibilities:**
- Verify all employer standards from Layer 0 are followed
- Check code against the project manifest's technical requirements
- Review for logic errors, edge cases, and off-by-one issues
- Check error handling completeness
- Verify API usage matches the knowledge layer documentation
- Flag any patterns that violate Decision Records
- Post inline PR comments for specific issues
- Post a summary review comment with: pass/needs-changes verdict, list of issues found, compliance check result

#### Test Generation Agent (Sonnet 4)

**Responsibilities:**
- Analyze new code for untested paths
- Write additional unit tests for uncovered edge cases
- Write integration tests for external API calls (using mocks)
- Verify tests are meaningful (not just hitting coverage numbers)
- Check that test names are descriptive and follow conventions
- Run full test suite and attach coverage report to PR
- Flag if coverage drops below employer minimum

#### Documentation Agent (Haiku 4.5)

**Responsibilities:**
- Generate or update docstrings on all modified functions and classes
- Update README if new features, setup steps, or configuration changed
- Update CHANGELOG.md with a description of changes
- Generate API documentation if new endpoints were added
- Produce two versions of release notes:
  - Technical version: for engineers (detailed, with code references)
  - Summary version: for non-technical stakeholders (plain language, impact-focused)
- Commit all documentation updates to the PR branch

#### Security Scan Agent (Haiku 4.5 + Bandit + Semgrep)

**Responsibilities:**
- Run Bandit on all Python code
- Run Semgrep with OWASP ruleset
- Check for hardcoded secrets (detect-secrets)
- Verify no PII fields appear in log statements
- Check all dependencies against known CVE databases
- Flag any new dependency that wasn't in the approved manifest
- Post security findings as PR comments with severity ratings

#### QA Flow

```
Draft PR opened
        ↓
All four agents trigger in parallel (GitHub Actions)
        ↓
Code Review + Test Gen + Doc Gen + Security Scan all run
        ↓ all complete
Results aggregated:
  - Review comments posted inline
  - Tests committed to branch
  - Docs committed to branch
  - Security report attached
        ↓
All checks pass?
  YES → PR promoted from Draft to Ready for Review
        + Telegram push: "PR #{n} ready for your review"
  NO  → PR stays Draft, issues listed, Coder Agent notified
        ↓
⛔ HUMAN GATE: Engineer reviews and merges
```

---

### 4.6 Layer 6 — Observability Pipeline

**Purpose:** Make every step of every layer visible, traceable, and alertable. Observability is not added after the fact — it is a first-class requirement baked into every agent.

Every agent emits structured events at:
- Agent start (which agent, which task, manifest version)
- Each major step within the agent (action taken, inputs, outputs)
- External API calls (URL, response code, latency, payload size)
- Errors and retries (error type, stack trace, attempt number)
- Agent completion (outcome, duration, artifacts produced)

Critical alerts are pushed to Telegram in addition to Grafana/Slack. Full details in Section 17.

---

## 5. Agent Roster & Responsibilities

| Agent | Layer | Model | Trigger | Primary Output |
|---|---|---|---|---|
| Research Agent | 1 | Opus 4 | Manual seed or scheduled re-crawl | Knowledge resources, Decision Records |
| Planning Agent | 3 | Opus 4 | Manual chat session | Approved GitHub Issues |
| Coder Agent | 4 | Sonnet 4 + Claude Code | Approved issue + cron | Feature branch + passing tests |
| Debug Agent | 4 | Sonnet 4 | CI test failure | Fixed code + diagnosis note |
| Refactor Agent | 4 | Sonnet 4 | After coder passes tests | Clean, standards-compliant code |
| Code Review Agent | 5 | Sonnet 4 | Draft PR opened | Inline review comments + verdict |
| Test Gen Agent | 5 | Sonnet 4 | Draft PR opened | Additional tests + coverage report |
| Doc Agent | 5 | Haiku 4.5 | Draft PR opened | Updated docs, README, changelog |
| Security Agent | 5 | Haiku 4.5 + tools | Draft PR opened | Security findings report |
| Drift Monitor | 1 | Sonnet 4 | Weekly cron | Knowledge drift issues |
| Telegram Bot | Control | python-telegram-bot | Engineer command / system event | Gate approvals, status, alerts |

---

## 6. Complete Technology Stack

### AI & Agent Layer

| Component | Technology | Version | Rationale |
|---|---|---|---|
| Primary reasoning (planning, research) | Claude Opus 4 | Latest | Best complex reasoning, ambiguity resolution |
| Code execution, review | Claude Sonnet 4 | Latest | Best code generation, cost-efficient for volume |
| High-volume low-complexity tasks | Claude Haiku 4.5 | Latest | Doc gen, lint checks — fast and cheap |
| Agentic code execution | Claude Code CLI | Latest | Native file system + bash, Anthropic-native |
| Agent orchestration | LangGraph | 0.2.x | Stateful graphs, retry logic, parallel branches |
| Agent framework | LangChain | 0.3.x | Tool binding, memory, chain composition |

### Backend

| Component | Technology | Version | Rationale |
|---|---|---|---|
| API server | FastAPI | 0.115.x | Async, auto-docs, Pydantic native |
| Schema validation | Pydantic v2 | 2.x | Type-safe, fast, used throughout |
| Task queue | Celery | 5.4.x | Mature, reliable, supports cron |
| Message broker | Redis | 7.x | Fast, Celery native, also used for caching |
| Database | PostgreSQL | 16.x | Primary data store — manifests, run history |
| ORM | SQLAlchemy | 2.x | Async support, Pydantic integration |
| DB migrations | Alembic | Latest | SQLAlchemy native |
| Vector search (if needed) | PgVector | Latest | Stays in PostgreSQL — Decision Record: DR-001 |

### Frontend

| Component | Technology | Version | Rationale |
|---|---|---|---|
| Framework | React | 18.x | Component-based, large ecosystem |
| Build tool | Vite | 5.x | Fast dev server, optimal builds |
| Styling | Tailwind CSS | 3.x | Consistent, fast to build |
| Form handling | React Hook Form | 7.x | Performant, uncontrolled inputs |
| Form validation | Zod | 3.x | Type-safe, matches Pydantic models |
| Chat streaming | Vercel AI SDK | 3.x | Streaming chat, tool call rendering |
| Charts / monitoring | Recharts | 2.x | Lightweight, React-native |
| State management | Zustand | 4.x | Lightweight, no boilerplate |
| HTTP client | Axios | 1.x | Interceptors, request/response transforms |

### Mobile Control Interface

| Component | Technology | Version | Rationale |
|---|---|---|---|
| Telegram bot framework | python-telegram-bot | 21.x | Async, well-maintained, command routing |
| Bot hosting | systemd user service (local) | — | Always-on, restarts on failure, logs to journald |
| Auth | Telegram chat ID whitelist | — | Only engineer's chat ID can send commands |
| Notification push | Bot.send_message() | — | Proactive alerts from FastAPI + Celery |

### GitHub & CI/CD

| Component | Technology | Rationale |
|---|---|---|
| Version control | GitHub | Primary platform |
| CI/CD | GitHub Actions | Native to repo, free for public, agent triggers |
| GitHub API client | PyGithub | Python-native GitHub SDK |
| Branch protection | GitHub Rulesets | Enforce standards programmatically |
| Project management | GitHub Projects v2 | Issue → in-progress → PR → done visualization |
| Dependency scanning | Dependabot | Automated CVE PRs |
| Secret scanning | GitHub Secret Scanning | Catches leaked credentials |

### Testing

| Component | Technology | Rationale |
|---|---|---|
| Python test framework | pytest | Industry standard, agent-writable |
| Async tests | pytest-asyncio | FastAPI + async agent tests |
| Test coverage | Coverage.py | Enforce employer minimums |
| Mocking | pytest-mock + responses | Mock external APIs cleanly |
| JS/TS testing | Vitest | Fast, Vite-native |
| Frontend coverage | Istanbul / c8 | Node-native coverage |
| Static analysis (Python) | Ruff | Fast linting + auto-fix |
| Type checking (Python) | Mypy | Catch type errors before runtime |
| Static analysis (JS) | ESLint | Standards enforcement |
| Security scanning | Bandit + Semgrep | OWASP checks, custom rule patterns |
| Secret detection | detect-secrets | Pre-commit and CI hook |
| Dependency audit | pip-audit + npm audit | CVE scanning on every PR |

### Observability

| Component | Technology | Rationale |
|---|---|---|
| Structured logging | structlog + JSON | Machine-readable, every step logged |
| Log aggregation | Loki (Grafana stack) | Pairs with Prometheus, no extra infra |
| Metrics | Prometheus | Industry standard, pull-based |
| Dashboards | Grafana | Prometheus + Loki native |
| APM / tracing | OpenTelemetry | Vendor-neutral, trace across all agents |
| Trace visualization | Jaeger | OpenTelemetry native UI |
| Alerting | Grafana Alerting + Telegram | SLA breach → Telegram push (primary) + Slack |
| Cost tracking | Anthropic Usage API + custom | Token spend per project/customer |
| Error tracking | Sentry | Exception aggregation, context capture |

### Infrastructure & Local Environment

**Development Model: Option C (Hybrid)**
Infrastructure services run in Docker Engine. Application code runs natively in a Python virtualenv. This gives clean, reproducible infrastructure with fast code iteration.

| Component | Technology | Notes |
|---|---|---|
| OS | Linux Mint (Ubuntu-based) | Native Linux — no virtualization overhead |
| Containerization | Docker Engine (via apt) | Not Docker Desktop — CLI only |
| Container management | Docker Compose plugin | `docker compose` (not standalone) |
| Infra in Docker | PostgreSQL 16 + Redis 7 | Started via `docker compose up -d` |
| App runtime | Native Python virtualenv | FastAPI + Celery run outside Docker |
| Python management | pyenv | Avoid system Python conflicts |
| Node management | nvm | Consistent Node version |
| Process management | systemd user services | API + Celery workers + Telegram bot auto-start |
| Scheduling (local) | systemd timers + Celery Beat | Replaces crontab — better logging via journald |
| Scheduling (repo) | GitHub Actions cron | Repo-scoped jobs run in GitHub infra |
| Secret storage (dev) | pass + GPG | Native Linux credential management |
| Secret storage (prod) | Infisical / AWS Secrets Manager | Team-shareable, auditable |
| Config management | Pydantic Settings + .env | Type-safe, never committed to git |
| Desktop AI interface | Claude Desktop + MCP servers | Filesystem + shell access for planning sessions |

---

## 7. Repository Structure

AutoForge and all projects it manages are **separate GitHub repositories**. AutoForge is the orchestration system. Each customer project lives in its own repo, created automatically by AutoForge when a project manifest is initialized.

### AutoForge System Repo

```
github.com/{org}/autoforge/               ← The orchestration system itself
│
├── config/
│   ├── employer_profile.json             # Layer 0 — locked employer config
│   ├── employer_profile.schema.py        # Pydantic model with locked field enforcement
│   └── STANDARDS_CHANGELOG.md           # Version history of employer standards
│
├── agents/
│   ├── base/
│   │   ├── base_agent.py                 # Shared agent base class
│   │   ├── manifest_loader.py            # Manifest injection into system prompt
│   │   └── observability.py             # Shared logging/tracing for all agents
│   ├── research/
│   │   ├── research_agent.py             # Opus — crawl, explore, decision records
│   │   ├── crawl_engine.py              # URL and DB crawling logic
│   │   └── conflict_detector.py         # Check findings against Layer 0
│   ├── planning/
│   │   ├── planning_agent.py            # Opus — chat-driven spec creation
│   │   └── issue_generator.py           # GitHub Issue creation from specs
│   ├── execution/
│   │   ├── coder_agent.py               # Sonnet + Claude Code — implementation
│   │   ├── debug_agent.py               # Sonnet — failure diagnosis and fix
│   │   └── refactor_agent.py            # Sonnet — post-implementation cleanup
│   └── qa/
│       ├── review_agent.py              # Sonnet — code review against standards
│       ├── testgen_agent.py             # Sonnet — test generation
│       ├── docgen_agent.py              # Haiku — documentation generation
│       └── security_agent.py            # Haiku + Bandit/Semgrep — security scan
│
├── orchestration/
│   ├── graph.py                          # LangGraph state machine definition
│   ├── scheduler.py                      # Celery tasks + beat schedule
│   ├── github_manager.py                 # All GitHub API operations
│   ├── project_registry.py              # Registry of all managed project repos
│   └── escalation.py                    # Stuck agent handling + needs-human logic
│
├── telegram/
│   ├── bot.py                            # Bot entrypoint + command router
│   ├── commands/
│   │   ├── queue.py                     # /queue — PR and issue queue views
│   │   ├── approve.py                   # /approve — add approved label to issue
│   │   ├── status.py                    # /status — live agent and pipeline state
│   │   ├── run.py                       # /run — manual trigger for pipelines
│   │   ├── stuck.py                     # /stuck — needs-human issue list
│   │   ├── drift.py                     # /drift — latest drift report summary
│   │   └── cost.py                      # /cost — token spend summary
│   ├── notifications/
│   │   ├── morning_summary.py           # 7am proactive summary push
│   │   ├── alert_router.py              # Route system events to Telegram messages
│   │   └── templates.py                 # Message formatting helpers
│   └── auth.py                          # Chat ID whitelist enforcement
│
├── observability/
│   ├── logger.py                         # structlog configuration
│   ├── metrics.py                        # Prometheus metric definitions
│   ├── tracing.py                        # OpenTelemetry setup
│   ├── cost_tracker.py                   # Anthropic API usage tracking
│   └── dashboard/                        # React monitoring UI
│       ├── src/
│       │   ├── PRQueue.jsx              # Morning PR review queue
│       │   ├── AgentStatus.jsx          # Live agent run status
│       │   ├── PipelineTimeline.jsx     # Step-by-step run visualization
│       │   └── CostDashboard.jsx        # Token spend tracking
│       └── package.json
│
├── api/
│   ├── main.py                           # FastAPI application
│   ├── routers/
│   │   ├── projects.py                  # Project manifest CRUD
│   │   ├── agents.py                    # Agent trigger endpoints
│   │   ├── knowledge.py                 # Knowledge layer management
│   │   └── github.py                    # GitHub webhook handlers
│   └── middleware/
│       └── auth.py                       # API authentication
│
├── frontend/
│   ├── layer0-form/                      # Employer profile intake form
│   ├── layer1-form/                      # Project intake wizard
│   ├── planning-chat/                    # Opus planning chat interface
│   └── dashboard/                        # Morning review dashboard
│
├── schemas/
│   ├── employer_profile.py              # Pydantic: Layer 0 schema
│   ├── project_manifest.py              # Pydantic: Layer 2 schema
│   ├── decision_record.py               # Pydantic: Decision Record schema
│   └── knowledge_resource.py           # Pydantic: Resource schema
│
├── templates/                            # Injected into every new project repo
│   ├── github/
│   │   └── workflows/
│   │       ├── ci.yml                   # Test + lint on every PR
│   │       ├── agent_trigger.yml        # Trigger execution agents on label
│   │       ├── qa_trigger.yml           # Trigger QA agents on PR open
│   │       └── drift_monitor.yml        # Weekly knowledge re-crawl
│   ├── .gitignore
│   ├── README.md.template
│   └── CHANGELOG.md.template
│
├── docker-compose.yml                    # Infra only: PostgreSQL + Redis
├── pyproject.toml                        # Python project config + dependencies
├── package.json                          # Root JS dependencies
└── README.md
```

### Per-Project Repos (Auto-Created by AutoForge)

```
github.com/{org}/{project-slug}/          ← Created per project at manifest init
│
├── project_manifest.json                 # Layer 2 — locked manifest for this project
├── knowledge/
│   ├── resources/
│   │   ├── apis/                         # Parsed API docs, Swagger, endpoints
│   │   ├── data/                         # Schema maps, sample data, DDLs
│   │   ├── codebase/                     # Legacy patterns, dependency inventory
│   │   └── infrastructure/               # Stack inferences, CI/CD maps
│   ├── decisions/                        # Decision Records (DR-XXX.json)
│   ├── conflicts/                        # Flagged issues needing human resolution
│   └── crawl_log/                        # Audit trail of all crawl operations
│
├── src/                                  # All project source code
├── tests/                                # All project tests
├── docs/                                 # Generated and authored documentation
├── .github/
│   └── workflows/                        # Injected from AutoForge templates
│       ├── ci.yml
│       ├── agent_trigger.yml
│       ├── qa_trigger.yml
│       └── drift_monitor.yml
├── .gitignore                            # From AutoForge template
├── README.md                             # Auto-generated from manifest
├── CHANGELOG.md                          # Maintained by Doc Agent
├── pyproject.toml / package.json         # Based on manifest tech stack
└── Dockerfile                            # Generated to match manifest environment
```

---

## 8. Project Repository Model

### How AutoForge Creates a New Project Repo

When the engineer finalizes and locks a project manifest, AutoForge's GitHub Manager automatically:

1. Creates a new GitHub repo under the configured org: `github.com/{org}/{project-slug}`
2. Sets up branch protection rules from the employer profile (main is protected, direct pushes blocked)
3. Creates the standard label set (feature, fix, chore, spike, approved, needs-human, decision-needed, blocked, S/M/L/XL)
4. Creates milestones from the manifest timeline
5. Injects workflow files from AutoForge templates into `.github/workflows/`
6. Registers a webhook pointing back to AutoForge API for event handling
7. Commits the initial project manifest and knowledge directory structure
8. Registers the repo in the AutoForge project registry

### How AutoForge Agents Interact With Project Repos

Agents never work directly in the AutoForge repo. When picking up a task:

```
Celery worker picks up job for project: powerade-review-agg
  → Looks up repo URL from project registry
  → Clones project repo to local working directory: /tmp/autoforge-work/{run-id}/
  → Reads project_manifest.json from cloned repo
  → Merges with employer_profile.json from AutoForge config
  → Executes work (write code, run tests, etc.)
  → Commits and pushes to feature branch on project repo
  → Opens PR on project repo via GitHub API
  → Cleans up local working directory
  → Logs all steps back to AutoForge observability pipeline
  → Pushes status update to Telegram if result is notable
```

### Separation of Concerns

| Lives in AutoForge Repo | Lives in Project Repo |
|---|---|
| Employer profile (Layer 0) | Project manifest (Layer 2) |
| All agent code | All project source code |
| Orchestration logic | Knowledge layer resources |
| Observability infrastructure | Decision Records |
| Frontend (forms, chat, dashboard) | Project tests and docs |
| Telegram bot code | Project-specific GitHub workflows (injected) |
| GitHub workflow templates | Project CHANGELOG and README |
| Project registry database | — |

---

## 9. Human Gates & Approval Workflow

Every human gate is a deliberate pause where no agent proceeds until explicit approval is given. Gates are enforced technically — agents cannot proceed past a gate without the required label, status, or approval being present.

| Gate | Layer | Trigger | What You Do | How Approval Works | Telegram Path |
|---|---|---|---|---|---|
| Gate 0 | Layer 0 | Employer profile created | Review all locked standards, verify accuracy | Merge PR to protected branch | N/A (one-time setup) |
| Gate 1 | Layer 1 | Research Agent delivers knowledge report | Review crawl findings, resolve conflicts, make decisions | Approve findings in UI, lock Decision Records | `/drift` to review, web UI to lock |
| Gate 2 | Layer 2 | Project manifest generated | Review full manifest, verify accuracy | Merge manifest PR to protected branch | N/A (web UI for full manifest review) |
| Gate 3 | Layer 3 | Planning Agent produces GitHub Issues | Review specs, reject/edit/approve each issue | Add `approved` label to issues | `/issues pending` → `/approve 42` |
| Gate 4 | Layer 4 | Agents open a PR for review | Review code, docs, test results | Merge PR or request changes | `/queue` → GitHub link → merge on GitHub |
| Gate 5 | Layer 4 | Agent stuck after 3 attempts | Read diagnosis, provide guidance or fix manually | Close `needs-human` issue with resolution | `/stuck` → GitHub link for details |
| Gate 6 | Layer 1 | Weekly drift report delivered | Review what changed in APIs/schemas/libraries | Approve or update manifest accordingly | Telegram alert + `/drift` for summary |

**On-Hours vs. Off-Hours Gate Cadence:**

```
MORNING (On-Hours) — via Telegram from anywhere
────────────────────────────────────────────────────────
7:00 AM: Telegram bot sends morning summary automatically:
  "Good morning. Last night: 3 PRs ready, 1 agent stuck,
   0 drift alerts. Token spend: $0.84. /queue to review."

You review:
  /queue         → See PRs ready for review (with GitHub links)
  /stuck         → See needs-human issues (with GitHub links)
  /issues pending → See issues awaiting your approval
  /approve 42    → Approve issue #42 for tonight's run
  Estimated active time: 15–30 minutes from your phone

ON-HOURS (At Desk) — Claude Desktop for deep work
────────────────────────────────────────────────────────
Planning sessions via Claude Desktop (MCP):
  Open Claude Desktop → project files loaded via MCP
  Discuss what to build, review Decision Records
  Planning Agent generates issues → approve via Telegram later

OFF-HOURS (Automated)
────────────────────────────────────────────────────────
Cron triggers execution agents
  Pick up all approved issues
  Run coder → debug → refactor pipeline
  Open Draft PRs
  Run QA agents on all Draft PRs
  Promote ready PRs to review queue
  Create needs-human issues for stuck agents
  Push Telegram alert for any critical event
Morning: You have a full queue waiting + bot summary waiting
```

---

## 10. Agent PR Approval — Current & Future State

### Current State — Human Required for All Merges

In the initial system, agents have no merge permissions. Every PR requires human review and approval before anything lands on the main branch. This is the safe default while trust and track record are being established.

| Action | Current State |
|---|---|
| Read repo | ✓ |
| Create branch | ✓ |
| Commit to feature branch | ✓ |
| Push to feature branch | ✓ |
| Open Draft PR | ✓ |
| Promote Draft → Ready | ✓ (after QA passes) |
| Post PR review comments | ✓ |
| Approve a PR | ✗ |
| Merge PR to main | ✗ |
| Merge PR to any protected branch | ✗ |

### Future State — Earned Autonomy Model

Agent merge permissions are unlocked incrementally, per PR category, based on demonstrated track record — not enabled all at once. The path to earned autonomy:

**Stage 1 — Auto-merge: Documentation and Chore PRs**
- Qualifying PRs: docs-only changes, dependency patch bumps, changelog updates, README edits
- Unlock condition: 30+ PRs reviewed with >90% human agreement on agent verdict
- Risk level: Very low — no logic changes

**Stage 2 — Auto-merge: Test-Only PRs**
- Qualifying PRs: new or updated tests with no source code changes
- Unlock condition: Stage 1 running cleanly for 4+ weeks
- Risk level: Low — tests don't affect runtime behavior

**Stage 3 — Auto-merge: Low-Complexity Features**
- Qualifying PRs: issues labeled complexity `S`, all QA checks pass, no security findings
- Unlock condition: Stage 2 established, agent PR rework rate <10% over 60 days
- Risk level: Medium — requires confidence in agent code quality

**Stage 4 — Auto-approve: Any PR Meeting All Criteria**
- Qualifying PRs: all checks pass, no security findings, review agent gives clean verdict
- Unlock condition: Stages 1–3 all running cleanly, explicit engineer decision to enable
- Risk level: Medium-High — engineer retains ability to disable at any time

### Technical Implementation of Future State

When a stage is enabled, the GitHub Manager checks PRs against the qualifying criteria before calling the merge API. Any PR that does not meet all criteria for its stage is held for human review regardless. The engineer can disable any stage at any time via the AutoForge dashboard or via `/autonomy status` in Telegram — no code change required.

---

## 11. Scheduling & Off-Hours Automation

### Scheduling Strategy — Linux Mint

Two scheduling mechanisms are used depending on the job type:

- **GitHub Actions cron** — for jobs that are repo-scoped (agent triggers, drift monitor, dependency audits). These run in GitHub's infrastructure.
- **systemd timers** — for jobs that need the local machine and the AutoForge API running (Celery Beat, morning Telegram summary, cost reporting). Preferred over crontab for reliability, logging via journald, and automatic restart on failure.
- **Celery Beat** — for programmatically-defined schedules within the application. Coordinates with systemd to ensure workers are running.

### Cron Schedule

| Job | Mechanism | Schedule | Description |
|---|---|---|---|
| Execution sweep | GitHub Actions cron | Nightly 10:00 PM local | Pick up all approved issues, run coder pipeline |
| QA sweep | GitHub Actions cron | Nightly 11:00 PM local | Run QA agents on any open Draft PRs |
| Morning Telegram summary | systemd timer | 7:00 AM daily | Push overnight results summary to Telegram |
| Knowledge drift scan | GitHub Actions cron | Sunday 8:00 AM | Re-crawl all registered URLs and DB schemas |
| Dependency audit | GitHub Actions cron | Monday 6:00 AM | Run pip-audit + npm audit on all projects |
| Cost report | systemd timer | Monday 7:00 AM | Weekly token spend summary → Telegram |
| Dead branch cleanup | GitHub Actions cron | Saturday midnight | Archive stale branches (>30 days, no activity) |
| Celery worker heartbeat | systemd service | Always running | Keep workers alive, restart on failure |
| Telegram bot | systemd service | Always running | Bot process alive, ready for commands |
| Metrics scrape | systemd timer | Every 15 seconds | Prometheus scrapes FastAPI metrics endpoint |

### Celery Task Definitions

```python
# Execution pipeline — runs as single task chain per issue
execute_issue_pipeline(issue_id)
  → coder_task → debug_task (if needed) → refactor_task → open_pr_task

# QA pipeline — runs as parallel group per PR
qa_pipeline(pr_id)
  → group(review_task, testgen_task, docgen_task, security_task)
  → aggregate_results_task → promote_or_flag_task

# Research tasks
crawl_resource(seed_url, project_id)
introspect_database(connection_string, project_id)
weekly_drift_scan(project_id)

# Notification tasks
send_morning_summary()          # Triggered by systemd timer at 7am
send_alert(event_type, payload) # Called by any agent on notable event
```

### Escalation Logic

```
Agent fails test → Debug Agent triggered (attempt 1)
Debug Agent fails → retry (attempt 2)
Debug Agent fails → retry (attempt 3)
Debug Agent fails →
  Create GitHub Issue: needs-human
  Label: blocked, needs-human
  Assign to engineer
  Include: full error, all attempt logs, diagnosis notes
  Push Telegram alert: "🔴 Agent stuck on issue #42 (project-x). /stuck to review."
  Agent stops — does not attempt again until issue is resolved
```

---

## 12. Telegram Command Interface

The Telegram bot is the **mobile command center** for AutoForge. It runs as a systemd user service and is set up during Phase 0 alongside the core infrastructure. Every human gate has a corresponding Telegram interaction path. The bot only responds to the engineer's whitelisted chat ID — no other users can send it commands.

### Setup

```bash
# 1. Create a bot via BotFather on Telegram
#    → Talk to @BotFather → /newbot → get your BOT_TOKEN

# 2. Get your personal chat ID
#    → Send /start to your new bot
#    → Hit https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
#    → Find "chat":{"id": <YOUR_CHAT_ID>} in the response

# 3. Store credentials securely
pass insert autoforge/telegram_bot_token
pass insert autoforge/telegram_chat_id

# 4. Add to .env (generated by scripts/generate_env.sh)
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...   # Your personal chat ID — whitelist enforcement

# 5. Install python-telegram-bot
pip install "python-telegram-bot[webhooks]==21.*"
```

### systemd Service

```ini
# ~/.config/systemd/user/autoforge-telegram.service
[Unit]
Description=AutoForge Telegram Bot
After=network.target autoforge-api.service

[Service]
WorkingDirectory=/home/{user}/autoforge
ExecStart=/home/{user}/.venvs/autoforge/bin/python -m telegram.bot
EnvironmentFile=/home/{user}/autoforge/.env
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable autoforge-telegram
systemctl --user start autoforge-telegram
```

### Command Reference

#### Queue & Review Commands

| Command | Description | Example Response |
|---|---|---|
| `/queue` | Show all PRs ready for review across all projects | "3 PRs ready: #12 (project-a), #7 (project-b)..." + GitHub links |
| `/queue <project>` | Show PRs for a specific project | "2 PRs ready for project-a: ..." |
| `/issues pending` | Show issues awaiting your approval | "4 issues pending approval: #23, #24, #25, #26" |
| `/issues <project>` | Pending issues for a specific project | Issues list for that project |
| `/stuck` | Show all needs-human issues | "1 stuck agent: Issue #42 (project-x) — 3 debug attempts failed" |

#### Approval Commands

| Command | Description | Notes |
|---|---|---|
| `/approve <issue>` | Add `approved` label to a GitHub issue | `/approve 42` — issue picked up next cron run |
| `/approve <issue> <project>` | Approve issue in a specific project | `/approve 42 project-x` |
| `/reject <issue> <reason>` | Add `rejected` label + comment to issue | Reason posted as GitHub comment |

#### Status Commands

| Command | Description | Example Response |
|---|---|---|
| `/status` | Current pipeline state across all projects | Running agents, queued tasks, last run time |
| `/status <project>` | Pipeline state for one project | Agent currently running, last PR opened |
| `/cost` | This week's token spend summary | Spend by model, by project |
| `/cost week` | Last 7 days spend breakdown | Table: project × model × cost |
| `/drift` | Latest knowledge drift report summary | "2 changes detected: API endpoint removed, new schema column" |

#### Trigger Commands

| Command | Description | Notes |
|---|---|---|
| `/run execution` | Manually trigger the execution sweep now | Don't wait for 10pm cron |
| `/run qa` | Manually trigger QA sweep on all open Draft PRs | — |
| `/run drift <project>` | Trigger re-crawl for a specific project | — |
| `/run research <seed>` | Start Research Agent with a seed URL | `/run research https://api.example.com/swagger.json` |

#### Autonomy Commands (Future State)

| Command | Description | Notes |
|---|---|---|
| `/autonomy status` | Show which earned autonomy stages are enabled | — |
| `/autonomy enable stage1` | Enable Stage 1 auto-merge (docs/chore PRs) | Requires meeting unlock conditions |
| `/autonomy disable` | Disable all auto-merge stages | Immediate effect |

### Proactive Notifications (Bot Pushes to You)

The bot sends messages to your chat proactively on system events. You don't need to poll — it comes to you.

| Event | Message | Urgency |
|---|---|---|
| Morning summary (7am daily) | Overnight results: PRs ready, stuck agents, drift alerts, spend | Routine |
| PR ready for review | "✅ PR #12 ready: feature/add-webhook (project-a) — [Review →]" | Routine |
| Agent stuck (needs-human) | "🔴 Agent stuck on issue #42 (project-x). 3 debug attempts failed. /stuck for details." | High |
| Security finding (HIGH/CRITICAL) | "🚨 CRITICAL security finding on PR #12. Semgrep: SQL injection risk. Review required." | Critical |
| Drift detected | "⚠️ Drift on project-x: API endpoint /v2/users removed. /drift for details." | Warning |
| Cost spike | "⚠️ Today's token spend is 2.4× your 7-day average ($12.40 vs $5.20)." | Warning |
| Pipeline completed | "🏁 Nightly run complete: 4 issues processed, 3 PRs opened, 1 failed." | Routine |
| LLM API error | "🔴 Anthropic API errors: 8% failure rate in last hour. Pipeline paused." | Critical |
| Weekly cost report (Monday) | "📊 Week summary: $24.80 spent, 18 PRs merged, $1.38/PR" | Routine |

### Bot Implementation Structure

```python
# telegram/bot.py — simplified structure
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler
from telegram.auth import whitelist_only

app = ApplicationBuilder().token(BOT_TOKEN).build()

# All handlers wrapped with @whitelist_only decorator
app.add_handler(CommandHandler("queue", queue_command))
app.add_handler(CommandHandler("approve", approve_command))
app.add_handler(CommandHandler("stuck", stuck_command))
app.add_handler(CommandHandler("status", status_command))
app.add_handler(CommandHandler("run", run_command))
app.add_handler(CommandHandler("cost", cost_command))
app.add_handler(CommandHandler("drift", drift_command))

app.run_polling()

# telegram/auth.py — chat ID enforcement
def whitelist_only(func):
    async def wrapper(update, context):
        if str(update.effective_chat.id) != TELEGRAM_CHAT_ID:
            return  # Silently ignore — don't reveal bot exists
        return await func(update, context)
    return wrapper

# telegram/notifications/alert_router.py
# Called by FastAPI/Celery when events occur
async def send_alert(event_type: str, payload: dict):
    message = format_alert(event_type, payload)
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message,
                           parse_mode="Markdown")
```

---

## 13. Claude Desktop & Claude Code MCP Setup

MCP (Model Context Protocol) gives Claude Desktop and Claude Code direct access to your local filesystem and shell. For AutoForge, this means planning sessions and research conversations happen with full live context — the actual manifest files, decision records, and knowledge resources are readable mid-conversation, not copy-pasted summaries.

### Claude Desktop MCP Configuration

Claude Desktop reads its MCP config from `~/.config/Claude/claude_desktop_config.json` on Linux.

```bash
# Create config directory if it doesn't exist
mkdir -p ~/.config/Claude

# Create the config file
cat > ~/.config/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "autoforge-files": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/home/{user}/autoforge",
        "/home/{user}/projects"
      ]
    },
    "autoforge-shell": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-shell"
      ],
      "env": {
        "ALLOWED_COMMANDS": "git,python,pytest,cat,ls,grep,journalctl,systemctl,docker,celery"
      }
    }
  }
}
```

**What this gives you in Claude Desktop:**

The filesystem server exposes `/home/{user}/autoforge` and `/home/{user}/projects` as readable paths. During a planning session, you can say "read the manifest for project-x and help me write issues for the next phase" and Claude Desktop will read `projects/project-x/project_manifest.json` directly — no copy-pasting. It can also read decision records, conflict files, and crawl outputs mid-conversation.

The shell server (with the allowlist) lets Claude Desktop run safe read-only commands: check git status, look at journald logs for the last agent run, list Celery queue depth, grep for patterns in the codebase. You define which commands are allowed — nothing destructive is on the list.

**Restart Claude Desktop after editing the config.** The MCP servers initialize at startup. You'll see them listed under Settings → MCP if they loaded correctly.

### Claude Code MCP Configuration

Claude Code uses a different config path and format. It's configured via `~/.claude/settings.json` (global) or `.claude/settings.json` within a project repo (project-scoped). Project-scoped config takes precedence and is checked into the repo so every agent session in that project inherits the same context.

#### Global Config (applies to all Claude Code sessions)

```json
// ~/.claude/settings.json
{
  "mcpServers": {
    "autoforge-files": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/home/{user}/autoforge/config",
        "/tmp/autoforge-work"
      ],
      "type": "stdio"
    }
  }
}
```

The global config gives every Claude Code session read access to the employer profile and the working directory where agents clone project repos. This means even an ad-hoc `claude` session in a terminal has the employer standards available.

#### Project-Scoped Config (checked into each project repo)

```json
// {project-repo}/.claude/settings.json
{
  "mcpServers": {
    "project-files": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "."
      ],
      "type": "stdio"
    }
  },
  "systemPromptPrefix": "You are working inside the AutoForge execution pipeline for project {project-slug}. The project manifest is at ./project_manifest.json. The employer profile is at /home/{user}/autoforge/config/employer_profile.json. Always read both before taking any action. Never commit to main. Never override locked fields from the employer profile."
}
```

The `systemPromptPrefix` is prepended to every Claude Code session in that repo. This is how execution agents running `claude` CLI commands always have manifest-first context without the orchestration layer explicitly injecting it every time.

#### How Agents Use Claude Code with MCP in Practice

When the Coder Agent runs, it does something like this in Python:

```python
import subprocess

def run_claude_code_task(task_description: str, working_dir: str) -> str:
    """
    Run a Claude Code session in the project repo.
    MCP config in .claude/settings.json is loaded automatically.
    """
    result = subprocess.run(
        ["claude", "--print", task_description],
        cwd=working_dir,           # the cloned project repo
        capture_output=True,
        text=True,
        env={**os.environ, "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY}
    )
    return result.stdout
```

Claude Code picks up `.claude/settings.json` from the working directory, loads the MCP filesystem server pointed at the project, reads the manifest and employer profile via the systemPromptPrefix, and executes with full context. The orchestration layer doesn't need to inject the manifest manually — the MCP setup handles it.

### Workflow: Claude Desktop for Planning Sessions

The typical on-hours planning workflow using Claude Desktop:

```
1. Open Claude Desktop
   → Filesystem MCP loaded: autoforge/ and projects/ readable
   → Shell MCP loaded: git, journalctl, systemctl available

2. Start a planning session:
   "Read the manifest for project-x and the open Decision Records.
    I want to plan the next sprint — what issues should we tackle
    given the current state of the knowledge layer?"

3. Claude Desktop reads:
   → projects/project-x/project_manifest.json
   → projects/project-x/knowledge/decisions/*.json
   → projects/project-x/knowledge/conflicts/*.json (if any)

4. Have a real conversation about priorities, complexity,
   dependencies. Claude Desktop can also:
   → Run: git log --oneline -20 (see recent commits)
   → Run: journalctl --user -u autoforge-celery -n 50
           (check what happened in last agent run)

5. Output: Structured issue descriptions

6. Paste issue descriptions into the AutoForge web UI
   OR use Claude Desktop shell to call the AutoForge API:
   curl -X POST http://localhost:8000/api/issues \
     -d '{"project": "project-x", "title": "...", ...}'

7. Review generated issues → /approve 42 in Telegram
```

### Security Notes for MCP

- The filesystem server only exposes the paths you list. Do not add paths containing raw secrets, `.env` files, or the `pass` store.
- The shell server's `ALLOWED_COMMANDS` env var limits what can be run. Keep it to read-only tools and project-specific CLIs.
- The shell MCP server can run arbitrary commands within the allowed list — be conservative. `rm`, `mv`, `curl`, `pip install`, and similar are not on the list.
- Claude Code's project-scoped settings are version-controlled in the repo — don't put secrets or personal paths in them.

---

## 14. Development Phases & Timeline

### Phase 0 — Foundation (Weeks 1–2)
**Goal:** Employer profile form, schema validation, manifest merge logic working end-to-end. Telegram bot and Claude Desktop MCP set up and functional.

Deliverables:
- Layer 0 employer profile form (React, 6-section wizard)
- Pydantic schemas for employer profile with locked field enforcement
- Layer 2 project intake form (React, 7-step wizard)
- Manifest merge logic (Layer 0 + project intake → project_manifest.json)
- Basic FastAPI server with project CRUD endpoints
- PostgreSQL schema and Alembic migrations
- Docker Compose local dev setup
- GitHub repo scaffolding script (creates repo, branch protection, labels from manifest)
- **Telegram bot setup** — systemd service, auth, `/status`, `/queue`, `/approve` (read-only initially, wired to GitHub API)
- **Morning summary notification** — daily 7am push with placeholder content until pipeline data exists
- **Claude Desktop MCP config** — filesystem + shell servers configured and verified
- **Claude Code global MCP config** — employer profile accessible in all sessions
- **Project-scoped `.claude/settings.json` template** — added to repo template for auto-injection

**Human gate:** Review and lock employer profile before Phase 1. Verify Telegram bot receives test message and `/status` returns correctly.

---

### Phase 1 — Knowledge Layer (Weeks 3–4)
**Goal:** Research Agent crawling, Decision Records, conflict detection working.

Deliverables:
- Research Agent (Opus 4) with crawl engine
- URL crawling (Swagger, API docs, GitHub repos, PyPI pages)
- Database schema introspection (PostgreSQL, MySQL)
- Decision Record schema and UI (create, discuss, lock)
- Conflict detector (findings vs. Layer 0)
- Knowledge layer file structure and Git integration
- Knowledge review UI (approve/reject crawl findings)
- Drift Monitor cron job (weekly re-crawl)
- **Telegram: `/drift` command and drift alert notifications**
- **Telegram: `/run research <seed>` command**

**Human gate:** Review knowledge report and lock all Decision Records before Phase 2.

---

### Phase 2 — Planning Agent (Weeks 5–6)
**Goal:** Chat-driven spec creation producing approvable GitHub Issues — via both web UI and Claude Desktop.

Deliverables:
- Planning Agent (Opus 4) with full manifest context injection
- Streaming chat UI (React + Vercel AI SDK)
- GitHub Issue generation from approved specs
- Issue schema with acceptance criteria, technical notes, dependencies
- Milestone and label management
- Issue approval workflow (engineer reviews → adds `approved` label)
- **Telegram: `/issues pending` command and issue approval via `/approve`**
- **Claude Desktop integration tested**: planning session using live manifest files via MCP

**Human gate:** Approve first batch of issues before Phase 3.

---

### Phase 3 — Execution Agents (Weeks 7–10)
**Goal:** Coder, Debug, and Refactor agents running reliably on approved issues.

Deliverables:
- Coder Agent (Sonnet 4 + Claude Code CLI integration with project-scoped MCP)
- Debug Agent (Sonnet 4) with 3-attempt retry + escalation
- Refactor Agent (Sonnet 4) with lint + complexity checks
- LangGraph state machine orchestrating the execution pipeline
- Celery task queue + Redis setup
- GitHub branch creation, commit, PR automation (PyGithub)
- Needs-human issue creation and escalation
- Off-hours cron schedule via GitHub Actions
- **Telegram: stuck agent alert push, `/stuck` command wired to live data**
- **Telegram: `/run execution` manual trigger**
- **Pipeline completion notification push**

**Human gate:** Review and merge first agent-generated PRs.

---

### Phase 4 — QA & Review Agents (Weeks 11–13)
**Goal:** Automated code review, test gen, docs, and security scan on every PR.

Deliverables:
- Code Review Agent (Sonnet 4) with standards enforcement
- Test Generation Agent (Sonnet 4)
- Documentation Agent (Haiku 4.5) — docstrings, README, CHANGELOG, dual-audience release notes
- Security Agent (Haiku 4.5 + Bandit + Semgrep + detect-secrets)
- Parallel QA execution via GitHub Actions
- PR promotion logic (Draft → Ready)
- Inline PR comment posting
- **Telegram: PR ready notification with GitHub link**
- **Telegram: security finding alert push for HIGH/CRITICAL**

**Human gate:** Review first agent-reviewed PR end-to-end.

---

### Phase 5 — Observability (Weeks 14–15)
**Goal:** Full pipeline visibility from intake to merge.

Deliverables:
- structlog integration across all agents
- Prometheus metrics for all pipeline steps
- OpenTelemetry tracing (trace from issue → PR → merge)
- Grafana dashboards (pipeline health, PR queue, agent performance)
- Grafana alerting (SLA breaches, stuck agents, failed pipelines)
- Sentry error tracking
- Cost tracking dashboard (token spend per project/customer)
- Morning review dashboard (React) — PR queue, needs-human queue, run history
- **Telegram: `/cost` and `/cost week` wired to live Prometheus data**
- **Telegram morning summary fully populated** from real pipeline metrics
- **Grafana alerts mirrored to Telegram** for all severity levels

---

### Phase 6 — Integration & Hardening (Weeks 16–18)
**Goal:** Full end-to-end workflow running reliably. Usable in production.

Deliverables:
- End-to-end integration tests (intake → manifest → planning → execution → QA → PR)
- Load testing (multiple projects running simultaneously)
- Security review of the system itself (including Telegram bot auth)
- Documentation (system README, agent configuration guide, runbook)
- Off-hours automation tuning
- Cost optimization (Haiku vs. Sonnet routing review)
- **Telegram: `/autonomy` commands and earned autonomy stage management**
- v1.0 release

---

### Timeline Summary

| Phase | Focus | Weeks | Status |
|---|---|---|---|
| 0 | Foundation + Telegram bot + MCP setup | 1–2 | Not started |
| 1 | Knowledge Layer — Crawl, decisions | 3–4 | Not started |
| 2 | Planning Agent — Chat, issue gen | 5–6 | Not started |
| 3 | Execution Agents — Code, debug, refactor | 7–10 | Not started |
| 4 | QA & Review Agents | 11–13 | Not started |
| 5 | Observability — Full pipeline visibility | 14–15 | Not started |
| 6 | Integration, hardening, v1.0 | 16–18 | Not started |

Total estimated duration: **18 weeks** from project start to v1.0.

---

## 15. Build Order & Process

### Rule: Bottom-Up, Gate-First

Always build from the bottom of the layer stack upward. Never build an agent layer before the layer it depends on is working and validated. The manifest must be accurate before execution agents are built — otherwise you're building on a broken foundation.

The Telegram bot and MCP setup are **infrastructure, not features** — they go in at the start of Phase 0, not at the end. Having mobile control from day one means every subsequent phase you build gets the gate interface for free.

### Development Process Per Component

For every component built:

```
1. Write Pydantic schema first (defines the contract)
2. Write tests before implementation (TDD where practical)
3. Implement the component
4. Run tests — must pass before moving on
5. Add observability (logging + metrics + tracing)
6. Code review against employer standards
7. Document (docstring + README update)
8. PR → merge
```

### Order of First Implementation

```
Week 1:
  employer_profile.schema.py          → Pydantic model
  employer_profile form (React)        → Layer 0 UI
  FastAPI server skeleton              → Base API
  PostgreSQL schema + migrations       → Data layer
  Docker Compose                       → Local dev
  Telegram bot skeleton                → systemd service, auth, /status stub
  Claude Desktop MCP config            → Filesystem + shell servers

Week 2:
  project_manifest.schema.py          → Pydantic model
  project intake form (React)          → Layer 1/2 UI
  manifest merge logic                 → Layer 0 + intake → manifest
  GitHub scaffolding script            → Repo creation from manifest
  Telegram /queue and /approve         → Wired to GitHub API
  Morning summary notification         → Stub with placeholder content
  Claude Code global MCP config        → Employer profile accessible
  Project .claude/settings.json template → Repo template updated

Week 3:
  crawl_engine.py                      → URL + DB crawling
  research_agent.py (Opus)             → Knowledge discovery
  conflict_detector.py                 → Standards compliance check
  decision_record.schema.py           → DR schema
  Telegram /drift command              → Wired to knowledge layer

Week 4:
  Knowledge review UI                  → Approve/reject findings
  drift_monitor.py                     → Weekly re-crawl
  knowledge layer Git integration      → Store + version knowledge
  Telegram drift alert notification    → Push on drift event

...and so on through the phases
```

---

## 16. Linux Mint Environment Setup

### Overview

AutoForge runs natively on Linux Mint (Ubuntu-based). The development environment uses a **hybrid model**: infrastructure services (PostgreSQL, Redis) run in Docker containers, while application code (FastAPI, Celery workers, agents, Telegram bot) runs natively in a Python virtualenv.

### System Prerequisites

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Core build tools
sudo apt install -y build-essential git curl wget unzip \
  libssl-dev libffi-dev libpq-dev \
  libsecret-1-dev gnupg2

# Docker Engine (not Docker Desktop)
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER   # add self to docker group
# log out and back in for group change to take effect

# Verify Docker
docker compose version
```

### Python Environment

```bash
# Install pyenv for Python version management
curl https://pyenv.run | bash

# Add to ~/.bashrc
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# Install Python 3.11
pyenv install 3.11.9
pyenv global 3.11.9

# Verify
python --version   # should show 3.11.9

# Create AutoForge virtualenv
python -m venv ~/.venvs/autoforge
source ~/.venvs/autoforge/bin/activate

# Install dependencies (includes python-telegram-bot)
pip install -r requirements.txt
```

### Node Environment

```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc

# Install Node LTS
nvm install --lts
nvm use --lts

# Verify
node --version
npm --version
```

### Infrastructure Services (Docker)

```yaml
# docker-compose.yml — infrastructure only
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: autoforge
      POSTGRES_USER: autoforge
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Application Services (Native + systemd)

All long-running application processes are managed as systemd user services. The Telegram bot is added alongside the API and Celery workers.

```ini
# ~/.config/systemd/user/autoforge-api.service
[Unit]
Description=AutoForge FastAPI Server
After=network.target

[Service]
WorkingDirectory=/home/{user}/autoforge
ExecStart=/home/{user}/.venvs/autoforge/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
EnvironmentFile=/home/{user}/autoforge/.env
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

```ini
# ~/.config/systemd/user/autoforge-celery.service
[Unit]
Description=AutoForge Celery Worker
After=network.target

[Service]
WorkingDirectory=/home/{user}/autoforge
ExecStart=/home/{user}/.venvs/autoforge/bin/celery -A orchestration.scheduler worker --loglevel=info
EnvironmentFile=/home/{user}/autoforge/.env
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

```ini
# ~/.config/systemd/user/autoforge-beat.service
[Unit]
Description=AutoForge Celery Beat Scheduler
After=network.target

[Service]
WorkingDirectory=/home/{user}/autoforge
ExecStart=/home/{user}/.venvs/autoforge/bin/celery -A orchestration.scheduler beat --loglevel=info
EnvironmentFile=/home/{user}/autoforge/.env
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

```ini
# ~/.config/systemd/user/autoforge-telegram.service
[Unit]
Description=AutoForge Telegram Bot
After=network.target autoforge-api.service

[Service]
WorkingDirectory=/home/{user}/autoforge
ExecStart=/home/{user}/.venvs/autoforge/bin/python -m telegram.bot
EnvironmentFile=/home/{user}/autoforge/.env
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

```bash
# Enable and start all services
systemctl --user daemon-reload
systemctl --user enable autoforge-api autoforge-celery autoforge-beat autoforge-telegram
systemctl --user start autoforge-api autoforge-celery autoforge-beat autoforge-telegram

# Enable lingering so services start at boot without login
loginctl enable-linger $USER

# Check status
systemctl --user status autoforge-telegram
journalctl --user -u autoforge-telegram -f   # follow bot logs
```

### Secrets Management

```bash
# Development: pass (GPG-based) for local secret storage
sudo apt install -y pass gpg

# Initialize pass with your GPG key
gpg --gen-key
pass init {your-gpg-key-id}

# Store secrets
pass insert autoforge/anthropic_api_key
pass insert autoforge/postgres_password
pass insert autoforge/github_token
pass insert autoforge/telegram_bot_token
pass insert autoforge/telegram_chat_id

# .env file for systemd services (never committed to git)
# Generated from pass store via a local script:
# scripts/generate_env.sh → writes /home/{user}/autoforge/.env
```

### Claude Code CLI

```bash
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Authenticate
claude auth login

# Verify
claude --version

# Set up global MCP config (employer profile accessible everywhere)
mkdir -p ~/.claude
cat > ~/.claude/settings.json << 'EOF'
{
  "mcpServers": {
    "autoforge-files": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/home/{user}/autoforge/config",
        "/tmp/autoforge-work"
      ],
      "type": "stdio"
    }
  }
}
EOF
```

### Claude Desktop MCP Config

```bash
# Install Claude Desktop (download .deb from claude.ai/download)
# Then configure MCP:
mkdir -p ~/.config/Claude

cat > ~/.config/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "autoforge-files": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/home/{user}/autoforge",
        "/home/{user}/projects"
      ]
    },
    "autoforge-shell": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-shell"],
      "env": {
        "ALLOWED_COMMANDS": "git,python,pytest,cat,ls,grep,journalctl,systemctl,docker,celery,curl"
      }
    }
  }
}
EOF

# Restart Claude Desktop for MCP to initialize
# Verify: Settings → MCP — should show both servers as connected
```

### Observability Stack (Docker)

```yaml
# docker-compose.observability.yml
services:
  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes:
      - ./observability/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports: ["3001:3000"]
    volumes:
      - grafana_data:/var/lib/grafana

  loki:
    image: grafana/loki:latest
    ports: ["3100:3100"]

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports: ["16686:16686", "4317:4317"]
```

### Local Development Workflow Summary

```bash
# Daily start (systemd handles this automatically at boot)
docker compose up -d                              # PostgreSQL + Redis
systemctl --user start autoforge-api              # FastAPI
systemctl --user start autoforge-celery           # Celery workers
systemctl --user start autoforge-beat             # Celery Beat
systemctl --user start autoforge-telegram         # Telegram bot

# Verify bot is up — send /status from Telegram, should respond

# Open dashboard
xdg-open http://localhost:3000                    # AutoForge React dashboard

# Follow logs
journalctl --user -u autoforge-telegram -f        # Bot activity
journalctl --user -u autoforge-celery -f          # Agent activity

# Run tests
source ~/.venvs/autoforge/bin/activate
pytest tests/ -v

# Stop everything
systemctl --user stop autoforge-api autoforge-celery autoforge-beat autoforge-telegram
docker compose down
```

---

## 17. Observability & Monitoring Strategy

### Core Principle

Every agent emits structured events at every significant step. Observability is not added after the fact — every agent class inherits from `BaseAgent` which provides logging, tracing, and metrics automatically. Critical events are pushed to Telegram in addition to Grafana.

### Structured Log Format

Every log event is JSON with required fields:

```json
{
  "timestamp": "2025-04-05T22:00:00.000Z",
  "level": "info",
  "service": "coder-agent",
  "agent_id": "coder-001",
  "project_id": "powerade-review-agg",
  "issue_id": "GH-42",
  "run_id": "run-abc123",
  "trace_id": "otel-trace-xyz",
  "step": "write_implementation",
  "event": "step_complete",
  "duration_ms": 4200,
  "tokens_used": 1840,
  "outcome": "success",
  "metadata": {}
}
```

### What Is Instrumented

| Layer | What Is Logged |
|---|---|
| Layer 0/1/2 | Manifest creation, validation results, field overrides attempted |
| Layer 1 Crawl | Every URL crawled, response codes, conflicts found, resources extracted |
| Layer 3 Planning | Session start/end, issues generated, issues approved/rejected |
| Layer 4 Execution | Branch created, files written, test runs (pass/fail), retries, PR opened |
| Layer 5 QA | Each agent start/end, findings count, coverage %, docs generated |
| All Layers | Every external API call, every LLM call, every GitHub API call |
| Telegram | Every command received, every notification sent, delivery success/failure |

### Key Metrics (Prometheus)

```
# Pipeline health
autoforge_pipeline_runs_total{project, status}
autoforge_pipeline_duration_seconds{project, agent}
autoforge_agent_failures_total{agent, reason}
autoforge_issues_approved_total{project}
autoforge_prs_opened_total{project}
autoforge_prs_merged_total{project}

# Quality metrics
autoforge_test_coverage_percent{project, run_id}
autoforge_security_findings_total{project, severity}
autoforge_review_findings_total{project, category}

# Resource metrics
autoforge_llm_tokens_total{model, agent, project}
autoforge_llm_cost_usd{model, agent, project}
autoforge_github_api_calls_total{endpoint, status}
autoforge_crawl_urls_total{project, status}

# Escalation metrics
autoforge_needs_human_issues_total{project, reason}
autoforge_debug_attempts_total{project, outcome}

# Telegram metrics
autoforge_telegram_commands_total{command}
autoforge_telegram_notifications_total{event_type}
autoforge_telegram_approvals_total{action}
```

### Grafana Dashboards

**Morning Dashboard (daily driver)**
- Open PR queue with agent review summaries
- Needs-human issues requiring action today
- Last night's pipeline run results
- Any drift alerts from weekly scan

**Pipeline Health Dashboard**
- Agent success/failure rates over time
- Average time from issue approval to PR ready
- Failure reasons breakdown
- Debug agent attempt distribution

**Cost Dashboard**
- Token spend by model per project
- Cost per PR (total tokens / PRs merged)
- Week-over-week spend trend
- Model usage distribution (Opus vs. Sonnet vs. Haiku)

### Alerting Rules

| Alert | Condition | Severity | Channel |
|---|---|---|---|
| Pipeline stalled | No progress on approved issue for >4 hours | Warning | Telegram + Slack |
| Agent stuck | needs-human issue created | High | Telegram (immediate) + Slack |
| Test coverage drop | Coverage below employer minimum | High | PR comment + Telegram |
| Security finding | Any HIGH or CRITICAL Bandit/Semgrep finding | Critical | Telegram (immediate) + Slack |
| Drift detected | API or schema change found in weekly scan | Warning | Telegram |
| Cost spike | Daily token spend >2x 7-day average | Warning | Telegram |
| LLM error rate | >5% LLM call failures in 1 hour | Critical | Telegram (immediate) + PagerDuty |
| Telegram bot down | Bot process not responding | High | Grafana alert (since bot can't self-notify) |

---

## 18. Security & Compliance Strategy

### Non-Negotiables (Applied to AutoForge Itself)

- All API keys and secrets stored in environment variables — never in code
- All LLM calls logged with token counts but never with full prompt/response content in production logs
- No customer data (DDLs, sample data, API responses) stored outside the project's designated storage
- Database connections to staging only — never production databases
- All GitHub tokens scoped to minimum required permissions
- Regular dependency audits (weekly automated via Dependabot)
- Telegram bot responds only to the whitelisted chat ID — no other user can query or control it

### Secrets Management

- Development: `pass` + GPG for local secret storage
- Production: Infisical or AWS Secrets Manager
- CI/CD: GitHub Secrets
- Agent runtime: Environment variable injection — never passed as arguments
- Telegram token treated as a high-value secret — stored in `pass`, never in version control

### What Agents Can and Cannot Do

| Action | Coder | Debugger | Refactor | Reviewer | DocGen |
|---|---|---|---|---|---|
| Read files | ✓ | ✓ | ✓ | ✓ | ✓ |
| Write files | ✓ (feature branch only) | ✓ (feature branch only) | ✓ (feature branch only) | ✗ | ✓ (branch only) |
| Commit to branch | ✓ | ✓ | ✓ | ✗ | ✓ |
| Push to main | ✗ | ✗ | ✗ | ✗ | ✗ |
| Merge PR | ✗ | ✗ | ✗ | ✗ | ✗ |
| Create issues | ✓ (needs-human only) | ✓ | ✗ | ✓ | ✗ |
| Access production DB | ✗ | ✗ | ✗ | ✗ | ✗ |
| Make external API calls | ✓ (crawl only) | ✗ | ✗ | ✗ | ✗ |
| Install packages | ✗ | ✗ | ✗ | ✗ | ✗ |
| Send Telegram messages | ✗ (via alert_router only) | ✗ | ✗ | ✗ | ✗ |

---

## 19. Decision Record Framework

All significant technical decisions are documented before execution agents touch code. This is the schema and process.

### Decision Record States

```
UNEXPLORED → UNDER DISCUSSION → DECIDED → LOCKED
     ↑                                       │
     └───────────────────────────────────────┘
           revisit trigger met (rare)
```

### Categories That Always Require a Decision Record

- Database or storage technology selection
- Message queue or task queue selection
- HTTP client library selection
- Web scraping library/approach selection
- Authentication implementation approach
- Data serialization format choice
- API design pattern (REST vs. GraphQL vs. gRPC)
- Caching strategy
- Any technology not already in the employer's approved defaults
- Any technology that requires a new infrastructure component

### How Decisions Are Made

1. Research Agent discovers or is asked about an undecided choice
2. Agent crawls relevant docs, benchmarks, GitHub repos, pricing pages
3. Agent produces a structured options analysis in draft Decision Record
4. Engineer reviews the analysis and discussion with Planning Agent (Opus) if needed — via Claude Desktop with MCP for context-rich discussion
5. Engineer makes the decision and adds rationale
6. Decision Record is locked — execution agents cannot override
7. Project manifest is updated with the locked decision
8. All future agents treat the locked decision as a hard constraint

### Execution Agent Behavior on Undecided Choices

If an execution agent encounters a situation requiring a choice that has no locked Decision Record, it:
1. Stops work on that task
2. Creates a GitHub Issue labeled `decision-needed`
3. Describes exactly what decision is needed and what options it sees
4. Assigns the issue to the engineer
5. Pushes a Telegram notification: "⚠️ Decision needed on issue #42 before work can continue"
6. Moves on to the next approved issue (does not block the entire pipeline)

---

## 20. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Agent produces code that violates employer standards | Medium | High | Code Review Agent checks against employer profile on every PR; pre-commit hooks |
| Agent makes an architectural decision without a Decision Record | Medium | High | Execution agents explicitly check for Decision Records; create decision-needed issue + Telegram alert |
| LLM API outage blocks off-hours pipeline | Low | High | Celery retry with exponential backoff; Telegram alert if pipeline hasn't run by morning |
| Token costs exceed budget | Medium | Medium | Cost dashboard with weekly budget alerts via Telegram; Haiku routing for volume tasks |
| Knowledge layer becomes stale (API changes) | Medium | Medium | Weekly drift monitor re-crawl with Telegram change alerts |
| Agent damages codebase on main branch | Very Low | Critical | Branch protection rules prevent direct pushes; agents cannot merge PRs |
| Context window exceeded on large manifests | Medium | Medium | Manifest summarization for large projects; chunk long knowledge resources |
| Crawled data contains sensitive customer information | Low | High | Crawl results reviewed before being locked; PII detection on all crawled content |
| Agent creates too many needs-human issues | Medium | Medium | Review debug failure patterns; improve agent prompts; add common fix patterns |
| Telegram bot compromised or impersonated | Low | High | Chat ID whitelist; bot token rotated if ever exposed; silent rejection of unauthorized users |
| Telegram bot down during critical pipeline event | Low | Medium | Grafana monitors bot process health; systemd restarts on failure; critical events also go to Slack |
| MCP filesystem server exposes sensitive paths | Low | High | Only non-secret project directories listed in config; `.env` and `pass` store paths excluded |
| MCP shell server executes destructive command | Low | Medium | ALLOWED_COMMANDS whitelist restricted to read-only and project-specific tools |
| Scheduling conflict (agents run during deploy window) | Low | Medium | Cron schedule respects deployment windows from employer profile |
| Linux Mint system update breaks pyenv or nvm | Low | Medium | Pin Python and Node versions; test after system updates |
| systemd user service fails to restart after reboot | Low | Medium | `loginctl enable-linger` ensures services start at boot; monitored via Grafana |
| Local machine off during scheduled off-hours job | Very Low | Low | PC assumed always on; GitHub Actions cron as secondary mechanism for repo-scoped jobs |

---

## 21. Success Metrics

### System Performance

- Time from issue approval to PR ready: target < 4 hours off-hours
- Agent success rate (issues resolved without needs-human): target > 75%
- Test coverage on agent-generated code: always meets employer minimum
- Security findings on agent PRs: target 0 HIGH/CRITICAL
- PR rework rate (PRs returned to agents after human review): target < 20%

### Engineer Productivity

- On-hours time spent on mechanical tasks: target < 30 minutes/day
- Morning review time via Telegram (reading summary + approving queue): target < 15 minutes
- Time from business problem to first working code: target < 24 hours (including off-hours)
- Documentation completeness on all PRs: 100% (agent-enforced)
- Human gates reachable without sitting at desk: 100%

### Cost Efficiency

- Cost per PR merged: track and trend over time
- Model usage distribution: target > 60% Haiku/Sonnet for volume tasks, Opus only for planning and research
- Weekly token spend per active project: establish baseline in Phase 1, optimize in Phase 6

### Telegram Interface

- Morning summary delivery: 100% (7am daily, no missed days)
- Alert-to-acknowledgement time: target < 30 minutes for HIGH/CRITICAL
- Commands that return correct data: target > 99% (monitored via Prometheus)

---

## 22. Glossary

| Term | Definition |
|---|---|
| Employer Profile | Layer 0 configuration set once per employer. Contains locked standards that apply to every project. |
| Project Manifest | The per-project JSON document that merges employer standards with customer-specific context. The source of truth for all agents. |
| Knowledge Layer | Layer 1. The collection of resources (APIs, schemas, data) and Decision Records for a specific project. |
| Decision Record | A structured document tracking a technical choice from undecided through to locked, with full rationale. |
| Locked Field | A field in the employer profile that cannot be overridden by any project manifest. |
| Human Gate | A deliberate pause in the pipeline where no agent proceeds until the engineer provides explicit approval. |
| Needs-Human Issue | A GitHub Issue created by a stuck agent that has exhausted its retry attempts. Requires engineer intervention. |
| Research Agent | The Opus-powered agent responsible for crawling resources and facilitating Decision Records. |
| Planning Agent | The Opus-powered agent that facilitates spec creation through chat and generates GitHub Issues. |
| Execution Pipeline | The Coder → Debug → Refactor sequence that turns an approved issue into a Draft PR. |
| Drift | Changes detected in external resources (API endpoints, DB schema, library versions) between weekly crawls. |
| Approved Issue | A GitHub Issue labeled `approved` by the engineer. The trigger for execution agents to begin work. |
| Off-Hours Window | The scheduled period (typically nights and weekends) when execution agents run autonomously. |
| Morning Queue | The set of PRs, needs-human issues, and drift reports awaiting engineer review at the start of the day. |
| Project Registry | The AutoForge database table tracking all managed project repos, their URLs, and their manifest versions. |
| Earned Autonomy | The incremental model by which agent merge permissions are unlocked per PR category based on demonstrated track record. |
| Option C (Hybrid) | The Linux Mint development model where infrastructure (PostgreSQL, Redis) runs in Docker and application code runs natively in a Python virtualenv. |
| systemd User Service | A systemd service running under the engineer's user account (not root) that manages long-running AutoForge processes. |
| Telegram Bot | The mobile command interface for AutoForge. Receives commands from the engineer and pushes proactive alerts from the system. |
| MCP (Model Context Protocol) | Anthropic's protocol for giving AI models access to external tools and resources. Used to give Claude Desktop and Claude Code filesystem and shell access to AutoForge project files. |
| Morning Summary | A proactive Telegram message sent at 7am daily summarizing overnight pipeline results, ready PRs, stuck agents, and cost. |
| Alert Router | The FastAPI/Celery component responsible for deciding which system events trigger Telegram notifications and formatting those messages. |
| systemPromptPrefix | A Claude Code config field that prepends context to every Claude Code session in a project repo — used to inject the manifest-first instruction automatically. |

---

*This document is the master reference for the AutoForge project. Update version and date on any significant changes. All agents, tools, and processes described here are subject to refinement as the system is built and validated.*

---

**Document version:** 1.3  
**Last updated:** 2026-04-06  
**Changes in 1.3:** Telegram Command Interface added as Section 12 (mobile command center, full command reference, proactive notifications, systemd service, auth model); Claude Desktop and Claude Code MCP setup added as Section 13 (filesystem + shell MCP for Desktop, global + project-scoped config for Claude Code, agent integration pattern, security notes); Telegram integrated into every relevant layer, gate table, phase, escalation path, alert table, repo structure, glossary, and risk register; PC always-on assumption adopted; morning summary elevated to primary review interface; Section numbering updated throughout.  
**Next review:** End of Phase 0 (Week 2)