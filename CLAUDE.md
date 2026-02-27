# textparse

Algorithmically break apart math textbooks into knowledge bytes stored in a relational structure, enabling Anki card generation, interactive visuals, and deep dissection of textbook content.

## Project Philosophy

**Nothing is sacred.** Code, docs, plans, explainers — everything is subject to continuous revisiting, deletion, and refactoring. Stale files must be killed, not preserved. If a file hasn't earned its place in the current architecture, remove it. This applies equally to:
- Source code that no longer fits the design
- Markdown explainers that describe outdated approaches
- Database schemas that don't serve the current model
- Visualization code that was a prototype

**Prefer deletion over accumulation.** A lean repo with 5 correct files beats 30 files where 20 are stale. When refactoring, delete first, then rebuild. Don't comment out old code — remove it.

## Architecture Overview

- **PDF Parser** (`src/pdf_parser/`): Extracts text, structure, and spatial data from textbook PDFs
- **Database** (`src/database/`): SQLAlchemy models storing textbooks, pages, paragraphs, concepts in relational structure
- **Visualization** (`src/visualization/`): Renders static images, animations (manim), and interactive HTML/JS
- **Data** (`data/`): SQLite database and source PDFs

Stack: Python, SQLAlchemy/SQLite, PyMuPDF, manim, matplotlib

## Agent System

This project uses specialized subagents for different tasks. The main conversation agent acts as **Atlas** — an orchestrator that delegates to specialized agents rather than doing everything itself. This preserves context and produces better results.

### Available Agents

Agents are defined in `.claude/commands/` and can be invoked two ways:
1. **User-invoked**: Type `/project:agent-name` to run directly
2. **Delegated**: Atlas uses the `Task` tool with the agent's prompt when orchestrating

| Agent | File | Model | Role |
|-------|------|-------|------|
| **Oracle** | `.claude/commands/oracle.md` | opus | Deep research and analysis. Complex questions, architecture decisions, algorithmic design. |
| **Explorer** | `.claude/commands/explorer.md` | haiku | Fast file/codebase discovery and web fetches. Cheap and parallel-friendly. |
| **Sisyphus** | `.claude/commands/sisyphus.md` | opus | Pure implementation. Receives a plan, writes code. No planning, no opinions. |
| **Reviewer** | `.claude/commands/reviewer.md` | opus | Code review. Reads diffs/files and produces critique. Never writes code. |
| **Prometheus** | `.claude/commands/prometheus.md` | opus | Deep planner. Researches, analyzes, writes plans to `plans/`. Never implements. |
| **Socrates** | `.claude/commands/socrates.md` | opus | Asks the user critical multiple-choice questions to surface hidden requirements and force decisions. |
| **Debrief** | `.claude/commands/debrief.md` | opus | Extracts lessons from user corrections/critiques and updates CLAUDE.md + lessons-and-standards.md. Run with `/project:debrief`. |

### Orchestration Rules

1. **Parallel by default**: When multiple independent research or exploration tasks exist, launch Explorer/Oracle agents in parallel.
2. **Delegate implementation**: When a plan exists, hand it to Sisyphus with explicit file paths and requirements.
3. **Review after writes**: After Sisyphus or any implementation work, invoke Reviewer on the changed files.
4. **Plans go to disk**: Prometheus writes all plans to `plans/` directory as markdown. Plans are living documents — update or delete them as the project evolves.
5. **Atlas stays lean**: The main agent should orchestrate, summarize, and communicate with the user. Offload heavy lifting to subagents.

### When to Use Which Agent

- "What does X do?" / "How should we approach Y?" → **Oracle**
- "Find all files related to X" / "What's in this codebase?" → **Explorer**
- "Implement the plan" / "Write the code for X" → **Sisyphus**
- "Review this code" / "What's wrong with this?" → **Reviewer**
- "Plan the architecture for X" / "Design the system for Y" → **Prometheus**
- "What should we decide before building X?" / "What am I missing?" → **Socrates**
- "Extract lessons from this session" / end of productive session → **Debrief**

## Project Scope

This is **not just an ESL parser** — it's a system and methodology for dissecting any technical textbook. ESL is the test case, but every decision should be made with generalization in mind. We will:
- Constantly refactor as patterns emerge
- Apply the system to new textbooks
- Find **alternative sources** for concepts — supplement ESL with the best pedagogy from other books, papers, or explanations when they exist
- Use `/project:debrief` to extract lessons after productive sessions

### Living Reference Documents
- `plans/statistical-perspective.md` — The user's statistical intuition and how to think about concepts. Updated as they review chapters.
- `plans/lessons-and-standards.md` — Technical standards, Plotly rules, CSS themes, game specs.

## Resolved Architecture Decisions

These were decided by the project owner and should not be re-litigated:

1. **Concept relationships**: Both a full dependency graph (typed edges: prerequisite, generalizes, proves, illustrates) AND a parent-child section tree. The tree preserves the textbook's printed layout as a reference; the graph captures semantic relationships.
2. **Content types**: Typed paragraphs via `paragraph_type` field. Classified using font metadata + regex heuristics. Definitions should be prominently surfaced — the goal is to strip fluff.
3. **Concept extraction**: Hybrid approach — heuristics first (font metadata, regex patterns), LLM for ambiguous paragraphs and relationship inference.
4. **Target domain**: Applied stats/ML textbooks first (ESL is the test case). Not pure math, not general textbooks.
5. **Anki cards**: Nice-to-have, not Phase 1 priority. Focus on knowledge graph first.
6. **DB sessions**: Fix the session-per-operation pattern. Use single session per parse run with batch commits.
7. **Visualizations**: Primarily LLM-generated manim/matplotlib scripts, with a small library of reusable templates for common patterns. May need a dedup/refactoring agent.
8. **Table extraction**: Use pdfplumber alongside PyMuPDF — PyMuPDF for text/fonts, pdfplumber for table structure.
9. **ESL chapter ordering**: Chapter 2 is just a preview/overview of supervised learning. Real content starts at Chapter 3. For prerequisite navigation, Chapter 2 concepts should be treated as introductory/optional.

## Continuous Learning

**This project learns from user feedback.** Every session where the user corrects you, critiques your approach, or makes a design decision is an opportunity to distill a lesson. You must:

1. **During the session**: When the user pushes back or corrects something, internalize the pattern — not just the fix.
2. **Before ending a session**: If significant lessons were learned, update `plans/lessons-and-standards.md` with new entries and promote any critical behavioral rules to this file.
3. **On demand**: The user can run `/project:debrief` to explicitly trigger lesson extraction.

### Core Rules (non-negotiable)

These were learned from user corrections and must not be violated:

**Pedagogy — how to teach a concept:**
- Lead with **Benefits & Tradeoffs** (what does this buy me? what do I lose?) — always first, always with textbook quotes
- Then **interactive visualizations**, ordered concrete→abstract (most intuitive first, most formal last)
- Then statistical guarantees
- **Formulas go DEAD LAST** as reference material. Starting with the formula is the wrong instinct. Kill it.
- Order visuals by what builds intuition fastest, not by textbook section order or what's easiest to code
- Don't build trendy-looking dashboards when a 3D rotatable surface is what actually explains it. Build the thing that teaches, not the thing that looks like other educational content.
- Use the **textbook's own words** — direct quotes with section citations. Don't paraphrase when the original is clearer.

**Citations — accuracy is non-negotiable:**
- Never trust your latent knowledge for citations. Web-search every reference to verify author, year, journal, volume/pages.
- Common failure: correct author + wrong journal, plausible but nonexistent papers, overstating what a paper proves.
- If you can't verify online, tell the user which PDFs to upload. Don't ship unverified citations.
- Display format: superscript footnote numbers in content, organized reference list at bottom by section header.

**Statistical claims:**
- OLS under misspecification estimates the **BLP** (Best Linear Projection) — a weighted average of local slopes, not "biased." Sensitive to covariate support range. (White 1980, Angrist & Pischke 2009, Buja et al. 2019)
- Every claim in educational content must be citable. No hand-waving.
- When in doubt, be conservative about what a result guarantees.

### Detailed Reference

`plans/lessons-and-standards.md` has expanded examples, Plotly.js 3D rules, CSS themes, game format specs, and other technical details. Read it before working on visualizations or assumption games.

## Linear

Linear is used for project management. **Do not use the Linear MCP server** — it hangs in WSL2.
Use `scripts/linear.sh` for issue tracking via Bash tool. Team/workspace: textparse.

```bash
# Examples:
scripts/linear.sh search              # list issues
scripts/linear.sh create "title" "desc" [priority]  # priority: 1=urgent, 2=high, 3=normal, 4=low
scripts/linear.sh update <id> [title] [desc] [priority] [stateId]
scripts/linear.sh teams               # list teams
scripts/linear.sh states              # list workflow states
```
