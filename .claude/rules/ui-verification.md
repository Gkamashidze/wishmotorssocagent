# UI Verification Protocol

## Auto-Trigger Files
Activate visual verification when these file types change:
- .tsx, .jsx, .vue, .svelte (components)
- .html, .ejs, .hbs, .pug (templates)
- .css, .scss, .sass, .less (stylesheets)
- .module.css, .module.scss (CSS modules)
- tailwind.config.*, globals.css (global styles)
- layout.tsx, _app.tsx, +layout.svelte (layout files)
- Any image/icon/font asset change

## Verification Sequence (always in this order)
1. Ensure dev server is running (start if not)
2. Navigate to affected page
3. Desktop screenshot → width: 1440, height: 900
4. Mobile screenshot → width: 375, height: 812
5. Tablet screenshot → width: 768, height: 1024
6. Accessibility snapshot
7. Present to user → "ნახე შედეგი — კარგად გამოიყურება?"

## Accessibility Checks
- Every <img> must have alt attribute
- Only one <h1> per page
- Headings must not skip levels (h1 → h2 → h3, not h1 → h3)
- Text/background contrast: 4.5:1 minimum (WCAG AA)
- All buttons/links reachable by keyboard (Tab key)
- Visible focus indicators on every focusable element
- Modals must trap focus inside when open

## Responsive Design (minimum 3 viewports)
At each breakpoint verify:
- No horizontal scrollbar
- Text readable (min 14px mobile, 16px desktop)
- Touch targets at least 44x44px on mobile
- Navigation accessible
- Images scale properly
- Grid layouts reflow correctly

## Interactive Elements
- Every button: click → verify expected action
- Every form: fill → submit → verify feedback + error states
- Every link: navigate → verify correct page
- Modals: open, close with X, close with Escape, close with overlay click
- Dropdowns: all options selectable

## Performance Checks
- Page load < 3 seconds
- LCP < 2.5 seconds
- CLS < 0.1
- Zero console errors
- No 4xx/5xx network requests
- No broken images or missing fonts

## Before/After Comparison
When modifying existing UI:
1. Take "before" screenshot at all 3 viewports
2. Make changes
3. Take "after" screenshots
4. Show both to user: "ასე იყო → ახლა ასეა"

## Error State Verification
Test these states visually:
- Empty state (no data)
- Loading state (skeleton/spinner)
- Error state (API failure)
- 404 page
- Form validation errors
