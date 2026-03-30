# Automated Testing Rules

## When to Test (Automatic Triggers)
- Created/modified any .tsx, .vue, .html, .css, .scss file → visual screenshot
- Created/modified any API route or server function → run endpoint test
- Any bug fix → write regression test FIRST, then fix
- Before every commit → run full test suite
- After npm/pip install → run existing tests to verify nothing broke
- Any new function → at least 1 unit test (happy path + 1 error case)
- Modified auth or authorization → run full auth flow test
- Modified database schema/queries → run CRUD tests

## UI Testing (Playwright MCP)
After ANY visual change:
1. Ensure dev server is running
2. Navigate to affected page
3. Desktop screenshot (1440x900)
4. Mobile screenshot (375x812)
5. Tablet screenshot (768x1024)
6. Accessibility snapshot
7. Show to user: "ნახე შედეგი — კარგად გამოიყურება?"

## Unit Tests
- Every new function: happy path + 1 error case minimum
- Every bug fix: regression test BEFORE the fix
- Edge cases: empty input, null, undefined, boundary values
- Coverage target: 80%+ for new code, 90%+ for auth/payments

## Integration Tests
- API endpoints: check status codes, response shape, auth
- Auth flow: login, invalid credentials, protected routes, logout
- Database: CRUD operations, conflict handling
- Webhooks: valid payload, malformed payload, idempotency

## Automated Verification Flow
1. Checkpoint (save state)
2. Run unit tests — fix if fail, never skip
3. If UI changed → Playwright screenshots → show user
4. If API changed → test endpoint → show response
5. Show results in plain language
6. User approves → commit

## Pre-commit Checks
- NEVER use --no-verify to skip hooks
- NEVER commit with failing tests
- NEVER disable test files to make tests "pass"

## Communication (Non-Technical)
NEVER say: "Jest tests passed", "coverage 87%", "assertion failed line 42"
ALWAYS say: "ვტესტავდი და ყველაფერი სწორად მუშაობს" / "პრობლემა ვიპოვე და გავასწორე"
Show screenshots, not test output.

## Georgian Approval Prompt
After every visual change: "ნახე შედეგი — კარგად გამოიყურება?"
