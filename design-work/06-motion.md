# 06 · Motion system (Phase 6)

Engine: CSS transitions/keyframes on tokens (tiers 1–2) and Anime.js v4.0.2 (`static/vendor/animejs/`, MIT, 26.3 KB gz)
driven by `static/js/motion.js` (1.8 KB gz) for tier 3. Only `transform`, `opacity` (and the gauge's static conic fill)
are animated; measured CLS on six main pages = 0.0000. Under `prefers-reduced-motion: reduce` all duration tokens become
0, `motion.js` returns before animating, the `motion-pending` class is never set, and CSS keyframes are cut to 0.01 ms.
If Anime.js fails to load, everything is simply shown (a 1.6 s safety timer also removes the hidden state).

| # | Element | Trigger | Property | Duration | Easing | Library | Reduced-motion fallback |
|---|---|---|---|---|---|---|---|
| 1 | Button hover | pointer over | background | 150 ms | standard | CSS | colour change (0 ms) |
| 2 | Button press | active | translateY(edge) + scale 0.97, edge shadow | 100 ms | standard | CSS | none (colour only) |
| 3 | Hero CTA sheen | hover | translateX of a highlight | 500 ms, once per hover | standard | CSS | none |
| 4 | Input focus | focus | border colour, ring | 150 ms | standard | CSS | instant |
| 5 | Checkbox tick | checked | scale + opacity | 220 ms | spring | CSS | instant |
| 6 | Switch knob | toggle | translateX | 220 ms | spring | CSS | instant |
| 7 | Nav sheet | open/close | translateX, visibility | 350 ms in / same out | emphasized | CSS | instant |
| 8 | Scrim | open/close | opacity | 220 ms | standard | CSS | instant |
| 9 | Toast | appear / dismiss | translateY + opacity / translateX + opacity | 350 ms in, 220 ms out | emphasized / exit | CSS | instant |
| 10 | Dialog | open | translateY + scale + opacity | 350 ms | emphasized | CSS | instant |
| 11 | Dropdown | open | translateY + scale + opacity | 220 ms | emphasized | CSS | instant |
| 12 | Tooltip | hover/focus | translateY + opacity | 150 ms | standard | CSS | instant |
| 13 | Skeleton | loading | shimmer translateX | 1.4 s loop (loader only) | linear | CSS | static grey bar |
| 14 | Spinner / busy button | loading | rotate | 0.7 s loop (loader only) | linear | CSS | static ring |
| 15 | Page reveal (`[data-reveal]`) | load | opacity 0→1, translateY 10→0 | 500 ms, stagger 50 ms | standard | Anime.js `animate` + `stagger` | shown immediately |
| 16 | Pipeline connector | load | scaleX 0 → current step | 900 ms, delay 250 ms | standard | Anime.js | set to final value |
| 17 | KPI number ticker | first time in view | text count 0 → value (ends on the server text) | 900 ms, once | standard | Anime.js + IntersectionObserver | server text, no count |
| 18 | Feature / probability bars | load | scaleX 0 → 1 | 700 ms, stagger 40 ms | standard | Anime.js | final width |
| 19 | Receipt print-in | load | translateY −14 → 0, opacity | 500 ms | emphasized | Anime.js | shown |
| 20 | Decision stamp | load | scale 1.25 → 1, rotate −10° → −4°, opacity | 350 ms, delay 380 ms | emphasized | Anime.js | shown at −4° |
| 21 | Ledger chain links | scrolled into view | SVG stroke draw | 600 ms, once | standard | Anime.js + IntersectionObserver | drawn |
| 22 | Live feed new row | SSE event | translateY −6 → 0, opacity | 500 ms | standard | CSS | instant |
| 23 | Live status dot | connected | box-shadow pulse | 1.8 s loop (the one ambient live indicator) | — | CSS | static dot |
| 24 | Collapse chevron | open/close | rotate 180° | 220 ms | standard | CSS | instant |

Removed from the previous design: floating 3D cube loop, canvas particle field, cursor-glow cards and pointer tilt
(decoration without a job; the tilt also clipped KPI icons on phones).
