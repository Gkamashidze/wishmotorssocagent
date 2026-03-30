# Code Quality Rules

## Linting
- Linter must pass with zero errors before every commit
- Auto-fix when possible, manual fix otherwise
- Never disable linting rules without explaining why

## Formatting
- Auto-format on every file change
- Prettier (JS/TS) or Black (Python) — project standard
- EditorConfig applies to all files

## Git Workflow
- main: production-ready code only
- develop: integration branch
- feature/description: new features
- fix/description: bug fixes
- Never commit directly to main

## Conventional Commits
Format: `type: description`

Types:
- feat: new feature
- fix: bug fix
- docs: documentation only
- test: adding/updating tests
- refactor: code restructure (no behavior change)
- chore: build, config, dependencies

## Pre-commit Checks
1. Linter — zero errors
2. Formatter — auto-apply
3. Secret scan — block if secrets detected
4. Tests — all must pass

## Code Standards
- Functions under 50 lines
- Files under 800 lines (target 200-400)
- Max 4 levels of nesting
- One responsibility per function
- No hardcoded values — use environment variables or config
- No console.log in production code
- Handle all errors — never silently swallow them

## Self-Review Checklist (before every commit)
- [ ] All functions < 50 lines
- [ ] Error handling at every boundary
- [ ] No hardcoded config values
- [ ] Tests written and passing
- [ ] No debug statements
