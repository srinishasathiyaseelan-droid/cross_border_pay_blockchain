# 01 · Project audit (UI redesign, Phase 1)

Branch `ui-redesign` (from `ui/polish-offline-assets` @ a43d7f8 + P6 tests + P7). Screenshots: `07-screenshots/before/`.

## Stack and structure

| Item | Finding |
|---|---|
| Framework | Flask 3.1, server-rendered Jinja templates, no build step → **stack path B** (hand-built components on CSS custom properties; Anime.js + CSS transitions; no React libraries) |
| Styling | one stylesheet `static/css/style.css` (≈ 660 lines), tokens on `:root`, dark default + light via `prefers-color-scheme` / `[data-theme]` |
| Components | Jinja macros in `templates/_macros.html` (icon, tile, badges, money, pipeline, AI label); inline SVG sprite `templates/_icons.html` |
| JS | `static/js/script.js` (vanilla, FX conversion, risk preview, scenarios, AI polling, chat, NL filter, invoice, theme, glow/tilt, particles), `static/js/live.js` (SSE feed); vendored Chart.js 4.4.6; self-hosted fonts (Plus Jakarta Sans, JetBrains Mono) |
| Routes/pages | 15 templates (below) across blueprints `auth`, `kyc`, `payments`, `admin`, `api`, `ai_features` |
| Data flow | forms POST to Flask; JSON APIs for FX, risk preview, AI polling, chat, NL filter, invoice, live feed (SSE) |
| Build / test | no build; `pytest -q` → 217 passed; run with `python app.py [port]` |

## Pages, purpose and primary action

| Page | Who | Purpose | **Primary action** | Current problems |
|---|---|---|---|---|
| `/` landing | visitor | explain CrossPay | Try as demo SME / sign in | hero 3D cubes and particles compete with the CTA; on 375 px the nav "Sign in" button is clipped off-screen |
| `/login`, `/register` | visitor | access | sign in / register | fine; demo logins compete visually with the real form |
| `/kyc` | SME | submit identity | submit for review | status, demo bar and form have equal weight; 6 inline styles |
| `/payment` | SME | send a payment | **submit for risk check** | longest page; pipeline scrolls sideways on 375 px; 14 inline styles; the live preview sits beside the title instead of near the submit button |
| `/result/<tx>` | SME, officer | understand the decision | read outcome; officer: decide HOLD | 16 inline styles; hero, two tables, AI cards and decision form all similar weight |
| `/transactions` | both | find payments | open a receipt / review | filter buttons use six button styles at once (primary vs secondary toggles look like actions) |
| `/dashboard` | both | overview | new payment / open feed | stat tiles **clipped in half on phones** (3D tilt + preserve-3d); 5 equal-weight cards |
| `/blockchain` | both | verify the ledger | verify integrity | dense hashes; fine otherwise |
| `/admin/kyc` | officer | verify SMEs | verify / reject with reason | table too wide on tablet |
| `/admin/review/<tx>` | officer | decide a HOLD | release / reject with own reason | good structure; AI panel and facts visually close in weight |
| `/admin/reports` | officer | draft reports | draft, then sign off | fine |
| `/admin/ai` | officer | operate the AI layer | kill switch | fine |
| error pages | all | recover | back home | fine |

## Current UI inventory

| Aspect | Count / values | Inconsistencies |
|---|---|---|
| Colours | 69 unique hex values in CSS (tokens + gradient stops + hard-coded button faces) | button faces use raw hex (`#2ad6b1`, `#fcd34d`, `#fb8a8a`…) instead of tokens; 3 different greens for "success" |
| Fonts | Plus Jakarta Sans (UI) + JetBrains Mono (IDs, hashes) | 31 distinct `font-size` values (no type scale) |
| Spacing | 36 distinct `padding` values | no 4 px scale; many one-off `margin-bottom:20px` |
| Radii | 16 distinct `border-radius` values | 6, 8, 10, 11, 12, 13, 14, 18, 20 px all in use |
| Shadows | 25 `box-shadow` declarations | three depth styles mixed (flat, 3D edge, glow) |
| Buttons | primary, secondary, outline, ghost, success, warning, danger, ai + sm/lg/block | sizes are not on a 32/40/48 grid; heights vary 30–46 px; touch targets < 44 px for `btn-sm` |
| Inline styles | 77 `style=""` attributes across templates | layout tweaks bypass the system |
| Animation | keyframes spin, shimmer, float, live-pulse, live-in; JS tilt, cursor glow, canvas particles | particles run on phones; float loops forever; tilt causes the clipping bug |

**Total inconsistencies counted:** 69 colours + 31 font sizes + 36 paddings + 16 radii + 25 shadows + 77 inline styles,
most of which a token system collapses to ≈ 12 colours, 9 sizes, 10 spacings, 4 radii and 4 shadows.

## Product personality (from what it does and who uses it)

**Trustworthy · precise · explanatory.** SMEs move real money and need to see *why*; officers make accountable decisions
and need facts first, AI second; examiners (viva) need every claim to be verifiable. Calm confidence over spectacle.
