# Memory & Context Management Rules

## Session Start Protocol
1. Read CLAUDE.md (automatic)
2. Check docs/decisions/ — understand past architectural choices
3. Check git log --oneline -10 — see recent work
4. If handoff note exists (.claude/handoff-*.md) — read and resume
5. Tell user briefly: "ბოლოს ვმუშაობდით [X]-ზე. გავაგრძელოთ?"

## Session End Protocol
1. Create handoff note: .claude/handoff-YYYY-MM-DD.md
2. Save architectural decisions to docs/decisions/
3. Suggest checkpoint: "გინდა checkpoint-ი შევქმნა სანამ გავჩერდებით?"

## What to Save and Where
| Information | Storage | Why |
|---|---|---|
| Architecture decisions | docs/decisions/NNN-title.md | Permanent, reviewable |
| Build/test commands | CLAUDE.md | Always available |
| User design preferences | Auto memory | Personal |
| What was built and why | git commit messages | Source of truth |
| Session context | .claude/handoff-*.md | Bridge between sessions |

## Architectural Decision Records (ADR)
Create in docs/decisions/ when:
- Choosing database, framework, or major library
- Deciding code vs n8n approach
- Changing project architecture
- Making security decisions
- Choosing deployment strategy

ADR format:
```
# NNN: Decision Title
## Date: YYYY-MM-DD
## Status: accepted
## Context: [problem being solved]
## Decision: [what was decided]
## Reasoning: [why this over alternatives]
## Consequences: [trade-offs]
```

## Context Window Management
- Suggest /compact before reaching 60% context usage
- Suggest /clear when switching to completely different topic
- Never let context get so full that quality drops

## Handoff Note Format
```
# Session Handoff - YYYY-MM-DD
## Accomplished: [list]
## Current State: [working/issues/in-progress]
## Next Steps: [numbered list]
## Important Context: [non-obvious info]
## Open Questions: [things needing user input]
```

## Cleanup
- Keep latest 3 handoff notes, delete older ones (ask user first)
- Never delete ADRs — mark outdated as "superseded"
