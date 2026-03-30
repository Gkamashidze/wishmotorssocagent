# Interaction Rules for Non-Technical Users

## Language
- Always speak Georgian by default
- Switch to English only if the user writes in English
- Keep technical terms in English even in Georgian responses

## Before Making Changes
- Say what you will change and why (in plain language)
- If 4+ files will change: list them ALL and wait for confirmation
- If the change is big or hard to undo: ask "გავაგრძელო?"

## After Making Changes
- Explain how to verify: "გახსენი [URL] — უნდა დაინახო [რა]"
- Tell them what success looks like
- Tell them what failure looks like

## Handling Vague Prompts
- Interpret charitably — pick the most common/useful interpretation
- State the assumption: "ვთვლი, რომ გულისხმობდი [X]"
- Deliver a quick first pass
- Then ask: "ეს ისაა, რაც გინდოდა?"

## Scope Control
- Change ONLY what was asked
- If you see a bug elsewhere: MENTION it but do NOT fix it
- No surprise refactoring, no "cleanup", no style changes
- Never convert patterns (class → hooks, CSS modules → Tailwind, etc.)

## Error Recovery
- If something breaks after a change: restore from checkpoint FIRST, then explain
- Never show raw stack traces or error codes to the user
- Say "პრობლემა: [plain Georgian description]. ვასწორებ."

## Emergency Prompts (auto-trigger recovery)
- "გააუქმე ბოლო ცვლილება" → git revert last commit
- "რაღაც გაფუჭდა, გაასწორე" → diagnose + fix
- "დააბრუნე ბოლო მომუშავე ვერსია" → restore from last WORKING checkpoint

## Auto-Checkpoint Triggers
- Before any change touching 3+ files
- Before any config file change
- After completing a working feature
- Before any refactoring
- At end of session if there are uncommitted changes
