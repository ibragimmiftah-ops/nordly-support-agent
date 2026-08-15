# Nordly Support Agent - Agent Instructions

## Communication Style

- **Always provide human-readable output.** Never return raw JSON, XML, or structured data dumps as the primary response.
- When reporting results, use natural language with clear formatting (bullet points, numbered lists, bold text).
- If technical details are needed, present them in a readable way (e.g., "Created file X with Y lines" rather than dumping raw file content).
- Keep responses concise but informative. Avoid walls of text.
- Use the user's language (Russian) for all direct communication.
- Address the user as "әфәнде".
- Do not print raw tool call payloads or internal tool traces in normal responses.
- If the user asks to continue "without stopping" or "до полной реализации", keep working through multiple phases in one turn until the task is materially complete or a real blocker appears.
- Do not pause after every completed phase to ask for permission unless the user explicitly requests a stop or a decision.
- Provide short human-readable progress updates only when they add value.

## Project Architecture

- Single-agent architecture using OpenAI Agents SDK for Python.
- Probabilistic AI decisions are separated from deterministic business rules.
- The LLM classifies priority; Python calculates SLA deterministically.
- Customer ticket text is untrusted input.
- Never expose broad database access as a tool.
- SupportDecision is the source of truth for agent output.
- Unit tests cannot call OpenAI API.

## Important Commands

```bash
# Run tests
pytest

# Run linting
ruff check .

# Run formatting
ruff format .

# Seed database
python -m data.seed

# Run application (demo mode)
DEMO_MODE=true uvicorn app.main:app --reload

# Run CLI analysis
python -m app.cli analyze --email "user@example.com" --subject "..." --message "..."
```

## Security Principles

- Agent cannot execute arbitrary SQL.
- Agent cannot send emails or perform financial changes.
- Prompt injection must not override system policy.
- Tools are bounded and customer-scoped.
- Human approval required for consequential actions.
