# 05 · Components (Phase 5)

Code: `static/css/components.css` (+ page layouts in `pages.css`), Jinja macros in `templates/_macros.html`, behaviour in
`static/js/script.js`. Every variant and state is on the gallery page **`/ui-kit`** (light and dark side by side).
"Source" names the pattern studied; nothing was copied (path B: rebuilt as CSS + Jinja).

## Buttons (`.btn`)

| | Spec |
|---|---|
| Variants | `btn-primary` (brand + 3 px edge), `btn-secondary`, `btn-outline`, `btn-ghost`, `btn-destructive` (alias `btn-danger`), `btn-link`, `btn-icon` (needs `aria-label`); status variants `btn-success`, `btn-warning`; `btn-ai` for AI actions; **`btn-hero`** = signature CTA (4 px edge + one sheen sweep on hover), **once per page at most** |
| Sizes | `btn-sm` 32 px (invisible hit area extends it to 44 px), default 40 px, `btn-lg` 48 px; `btn-block` full width |
| Hover | background → hover token over `--dur-fast` |
| Pressed | moves down by the edge depth and scales to 0.97 over `--dur-instant`; edge collapses to 0 |
| Focus-visible | 2 px `--focus` ring, 3 px offset |
| Disabled | 50 % opacity, `pointer-events: none` |
| Loading | `.is-busy` / `aria-busy="true"`: label hidden (width kept), centred spinner, clicks blocked; `form[data-once]` blocks double submits |
| Success/error | `.is-done .icon-swap` pops in (spring) where an action has an outcome |
| Reduced motion | no translate/scale; colour change only (`--press-depth: 0`, durations 0) |
| Source | Uiverse pressable button (idea), shadcn Button anatomy, Magic UI shiny button (sheen, once) |

## Other components

| Component | Variants / states | Motion | Accessibility | Source |
|---|---|---|---|---|
| Input, Textarea, Select (`.input`, `.textarea`, `.select`) | default, hover, focus (ring), read-only, disabled, error (`aria-invalid`) | border/ring `--dur-fast` | label `for`, hint/error via `aria-describedby`, border 3.8:1 | shadcn Input |
| Money input (`.input-money`) | currency prefix, mono tabular | — | prefix is decorative text | custom |
| Field (`.field`, `.field-label`, `.field-hint`, `.field-error`) | hint, error with icon | — | error text tied by id | shadcn Form |
| Checkbox / Radio (`.check`) | checked, focus | tick pops (spring) | native inputs, 44 px label target | Uiverse checkbox (idea) |
| Switch (`.check.switch`) | on/off | knob spring 220 ms | `role="switch"` on native checkbox | Uiverse toggle (idea) |
| File upload (`.upload`) | default | — | native input, label, hint | custom |
| Card (`.card`, `.card-flat`) | header, title, sub, footer | page reveal | `section` + `aria-labelledby` | shadcn Card |
| KPI (`.kpi`) | tile + label + mono value | number ticker once | value text is server-rendered | Magic UI number ticker |
| Badge (`.badge-*`) | success/warning/danger/neutral/ai/info/outline + decision/risk/KYC aliases | — | text + icon, never colour alone | shadcn Badge |
| Embossed tile (`.tile`) | 7 tones × sm/md/lg | — | `aria-hidden` (decorative) | user's 3D-icon request, restrained |
| Segmented control (`.segmented`) | current (`aria-current`) | background `--dur-fast` | `nav` with label | shadcn Tabs/Toggle group |
| Navbar (`.navbar`) | desktop links with current underline; sticky, blurred paper | — | `nav aria-label`, `aria-current="page"`, skip link | shadcn blocks |
| Sheet (`.sheet` + `.scrim`) | mobile nav < 1080 px | slide 350 ms emphasized; scrim fade 220 ms | focus moves in, Tab trapped, Escape closes, focus returns, `aria-expanded` | shadcn Sheet |
| Dialog (`dialog.dialog`) | modal | rise 350 ms | native `<dialog>`: focus trap + Escape | shadcn Dialog |
| Dropdown (`details.dropdown`) | menu | pop-in 220 ms | native `details/summary`, `role="menu"` items | shadcn Dropdown |
| Tooltip (`.tooltip[data-tip]`) | top | fade/rise 150 ms | shown on hover **and** focus; the control also has `aria-label` | shadcn Tooltip |
| Toast (`.toasts`, `.toast-*`) | success/warning/danger/info | in 350 ms, out 220 ms (exit ≈ 35 % faster) | `role="status"` / `alert`; auto-dismiss 7 s paused on hover/focus; errors stay; close button | shadcn Sonner |
| Alert (`.alert-*`) | info/success/warning/danger | — | icon + text | shadcn Alert |
| Table (`.table`) | sortable headers (`data-sortable`, `aria-sort`), numeric column, empty state, hover row | row bg `--dur-fast` | `scope`, caption, buttons in headers | shadcn Table |
| Key-value table (`.kv`) | stacks label over value < 640 px | — | `th scope="row"` | Astryx detail page |
| Pagination (`.pagination`) | current | — | `nav aria-label`, 44 px targets | shadcn Pagination |
| Skeleton, Spinner, Progress | — | shimmer (disabled under reduced motion), spin | spinner has `role="status"` label | shadcn Skeleton |
| Empty / error state (`.empty`) | with tile + action | — | heading + text | custom |
| **Pipeline** (`.pipeline`) | done / current / upcoming | connector draws to the current step | `ol`, `aria-current="step"`, "(done)" for screen readers | kombai Stepper + Magic UI animated beam |
| **Receipt** (`.receipt`) | decision stamp, perforated edge, amount hero, hash footer | prints in; stamp lands | `article` + heading | statement metaphor (signature) |
| Gauge (`.gauge`) | low/med/high tone | — | `role="img"` + label with the score | custom |
| Advisory (`.advisory`) | loading (skeleton), ready, unavailable (fallback facts) | crossfade | `aria-live="polite"`; "AI-generated · advisory · may be wrong" label; text via `textContent` only | custom |
| Chat (`.chat-*`) | user / AI bubbles | — | log `aria-live`, labelled input, 44 px send | custom |
| Footer | — | — | — | custom |

Not applicable: Sidebar (navigation fits the top bar and sheet).
