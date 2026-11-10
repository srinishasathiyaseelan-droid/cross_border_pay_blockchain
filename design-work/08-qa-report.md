# 08 · QA report (Phase 8)

Branch `ui-redesign`. Direction: "Signed Ledger" (`DESIGN.md`). Checked in the Claude desktop browser pane against the
local Flask server (`app.py 5001`, demo data). The anti-slop, Hallmark and UI UX Pro Max skill packages were **not
installed or executed** (third-party code); their published checklists were applied by hand, as listed below.

## Result summary

| Gate | Result | Evidence |
|---|---|---|
| Automated tests | **PASS**: full suite + 23 new UI tests (`tests/test_ui_redesign.py`) | see "Tests" |
| No horizontal scroll at 320 / 768 / 1440 px | **PASS** after 3 fixes | iframe audit of 12 pages × 3 widths |
| Touch targets | **PASS** (≥ 24 px everywhere; buttons, nav, pagination ≥ 44 px on phones) | same audit; native checkboxes are 20 px but sit in 44 px labels |
| Contrast (WCAG AA) | **PASS**: all text tokens ≥ 4.5:1, UI boundaries ≥ 3:1, light and dark | `04-tokens.md` (measured) |
| Keyboard | **PASS**: skip link, visible focus ring, sheet focus trap + Escape + focus return, native dialog | manual |
| Layout shift | **PASS**: CLS 0.0000 on `/`, `/dashboard`, `/transactions`, `/result`, `/blockchain`, `/admin/review/<id>` | PerformanceObserver |
| Reduced motion | **PASS**: all duration tokens 0, `motion.js` returns early, nothing hidden | test + manual |
| Console errors | **PASS**: none on any page | browser console |
| Lighthouse | **NOT RUN** (not available in this environment) | open item |
| Independent screenshot review (8.7) | **NOT COMPLETED**: the reviewer agent stopped on a usage limit before reporting | open item |

## Defects found and fixed during QA

| Where | Problem | Fix |
|---|---|---|
| all pages, 320 px | off-canvas nav sheet widened the page | `overflow-x: clip` on `html, body` |
| `/ui-kit`, 320 px | file input's intrinsic width pushed the upload field past the edge (clipped) | `.upload { grid-template-columns: minmax(0, 1fr) }` |
| `/blockchain`, 320 px | hash grid `minmax(260px, …)` made ledger blocks 29 px wider than the column | `minmax(min(260px, 100%), 1fr)` + `minmax(0, 1fr)` column |
| `/`, phones | "How one payment moves" list kept the browser's 40 px list indent (cards off-centre, connector line misaligned) | list reset on `.flow` and `.chain` |
| officer navbar, 1081–1279 px | six links + user chip were 33 px wider than the bar; sign-out button clipped at 1200 px | user chip shrinks (name ellipsised, full name in `title`); desktop link padding 12 → 8 px. Full name shows from 1280 px |
| `/dashboard` | KPI counter could be caught mid-count if frames stall (background tab) | safety timer now stops the animation and restores the server number |
| several | small link/button targets (< 24 px) | padding on `.btn-link`, `.tx-id`, sortable headers, chat send button |
| mobile sheet | links stretched to fill the panel height | `flex: none; align-content: start` |
| templates | 77 inline styles before the redesign, 29 after the rollout | 11 left, all data-driven (bar widths, gauge value, pipeline progress) or UI-kit demos |

## Checklists

**MASTER.md pre-delivery checklist**

| Item | Result |
|---|---|
| SVG icons only (sprite), no emoji | PASS (0 emoji in templates and JS) |
| `cursor: pointer` on clickable elements | PASS (`button, [role=button], a, summary, label[for], select`, upload, sort headers) |
| Motion uses tokens; respects reduced motion | PASS |
| Text contrast ≥ 4.5:1, UI ≥ 3:1 | PASS |
| Visible focus; logical tab order | PASS |
| Badges, chips, buttons reflow without clipping | PASS |
| 375 / 768 / 1024 / 1440 px, no horizontal scroll | PASS (audited at 320 / 768 / 1254–1440) |
| Touch targets ≥ 44 px | PASS for primary controls; inline text links are ≥ 24 px (WCAG 2.2 AA minimum) |
| Works with AI off and offline | PASS (fonts, Chart.js and Anime.js self-hosted; AI pages render with AI off; tested) |

**Anti-slop checklist (applied by hand)**

| Tier | Check | Result |
|---|---|---|
| Visual | gradient text, glow shadows, particle/cube backgrounds, glassmorphism everywhere | PASS: none. Remaining gradients are functional: tile emboss, one hover sheen on the single hero button, select chevron, skeleton shimmer, receipt perforation, gauge fill |
| Visual | one signature button per page | PASS (tested on every page) |
| Copy | invented numbers, testimonials, logos, "AI-powered" filler | PASS: KPIs and model metrics are read from the database / evaluation files |
| Copy | AI output labelled and inert | PASS: "AI-generated · advisory · may be wrong" label; inserted with `textContent` only (tested) |
| Motion | infinite decorative loops | PASS: only loaders (spinner, skeleton) and the live-feed status dot loop |
| Structure | hover-only affordances | PASS: tooltips also show on focus; every action is a visible button |

**Hallmark-style floor gates**: semantic landmarks (`header`, `nav`, `main#main`, `footer`), one `h1` per page,
labelled form fields with hint/error ids, `aria-current` on the current nav link and pipeline step, `aria-live` on
async AI panels and the live feed, `aria-sort` on sortable columns. PASS by review of templates.

## Asset sizes

| Asset | Before (raw / gzip) | After (raw / gzip) |
|---|---|---|
| CSS | `style.css` 44,706 / 9,925 B | `tokens.css` 9,227 / 2,173 + `components.css` ≈ 43.5 k / ≈ 8.4 k + `pages.css` ≈ 13.5 k / ≈ 3.0 k |
| `script.js` | 23,080 / 6,388 B | 22,982 / 6,203 B |
| Motion | — | `motion.js` 5.2 k / 1.8 k + Anime.js 76,652 / 26,269 B |

Added animation JavaScript ≈ 28 KB gzipped (budget 40 KB). CSS grows from 9.9 to about 13.5 KB gzipped, for a full
component library plus a dark theme.

## Tests

- `tests/test_ui_redesign.py` (23): every page (officer, SME, public, receipt, review) loads the new CSS and motion
  files, never the old stylesheet, has the skip link and `main#main`, loads nothing from a CDN, and shows at most one
  hero button; current nav link is marked; UI kit renders both themes and the core components; Anime.js is vendored
  with its MIT licence; reduced motion zeroes every motion token; AI text is never written with `innerHTML`.
- Full suite: 242 passed, 1 deselected (the live red-team run, opt-in since commit 3f3e7e2).

## Screenshots

`07-screenshots/before/` (7) and `07-screenshots/after/` (16): landing, dashboard, payment, receipt (light, dark, AI
panel), ledger, transactions, officer review, mobile menu, UI kit; phone shots at 375 px. Missing: 768 px "after"
shots (the 768 layout was audited by script, not photographed).

## Open items

1. Run Lighthouse (performance, accessibility, best practices) in Chrome DevTools on `/`, `/payment`, `/result/<id>`.
2. Re-run the independent screenshot review (step 8.7) once the usage limit resets.
3. Copy marked TODO in templates (real company name, contact, legal footer) needs the owner's text.
4. Test with a real screen reader (NVDA on Windows) — only markup was reviewed.
