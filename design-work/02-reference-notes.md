# 02 · Reference notes (Phase 2)

Stack path **B** (Flask/Jinja): React libraries (shadcn, Magic UI, React Bits, Astryx) are studied for patterns only and
rebuilt as CSS-token components and Jinja macros. Nothing was copied.

## What each source gave

| Source | Access | Extracted |
|---|---|---|
| awwwards.com (fintech) | page read; it lists names only (VELTO, Fintech NerdCon, Contiant Open Banking, Sunbit, Hub Fintech Europe…) with no style notes, and screenshots are not readable through fetch | Pattern level only, from those names and common fintech practice: numbers set in tabular figures as the visual hero, restrained palettes with one signal colour, statement/receipt metaphors, motion used to show money "moving" through steps. No layouts copied. |
| kombai.com/gallery/web | page read; categories Dashboard (383), Forms (198), Navbar (299), Card (171), Stepper (50), Chat (50); thumbnails only | CrossPay needs: dashboard (KPI row + charts + feed), stepper (payment pipeline), forms (payment, KYC), card, chat (assistant), navbar. Dense tables were not in the gallery list. |
| github.com/meta/astryx | README read | React 19 + StyleX, 150+ components, 7 themes (neutral, butter, chocolate, matcha, stone, gothic, y2k), templates for table pages, detail pages, form wizards. **Not used as a base**: the app is Flask/Jinja, not React 19. Its "detail page" and "form wizard" templates inform the receipt and payment pages. "stone"/"matcha" are closest in mood. |
| ui.shadcn.com | known component set | Anatomy and states to mirror: Button (variants, `asChild`), Input/Label/Form message, Card header/content/footer, Badge, Tabs, Table with empty state, Sonner toast, Skeleton, Sheet (mobile nav), Dialog, Tooltip, Dropdown. Rebuilt as macros + CSS. |
| magicui.design | known components | Number ticker (for KPI counts), border beam (for the one "live" card), animated beam (for the payment pipeline connector). Max 2–3, rebuilt with Anime.js/CSS. |
| reactbits.dev | known components | Blur/split text reveal for one hero headline; subtle grid background. Rebuilt with Anime.js. |
| uiverse.io | known patterns | Pressable button with an edge (the user asked for 3D buttons), checkbox/switch micro-interactions, loader. Rewritten with tokens, no raw hex. |
| animejs.com | docs read; npm `animejs@4.0.2` inspected | v4 UMD exposes global `anime` with `animate`, `createTimeline`, `stagger`, `onScroll`; 26 KB gzipped. Chosen as the page-level motion engine; vendored under `static/vendor/animejs/` (MIT). |
| UI UX Pro Max | README read | 80 styles, 192 palettes, 74 font pairings, design-system search → `design-system/<slug>/MASTER.md`; pre-delivery checklist: SVG icons not emoji, `cursor:pointer` on clickables, platform timing, ≥ 4.5:1 text contrast, visible focus, reduced motion, chips/badges reflow without clipping, checks at 375/768/1024/1440. **Not installed or executed** (third-party code); its checklist and MASTER.md structure were applied by hand. |
| anti-slop | README read (rules text not public on the page; the local Aegis-Node folder only holds an old audit, not the skill) | 40 rules in tiers Hard Gate / Purpose-Gate / Quality Locks across UI, copy, accessibility, responsive, code comments; During/After modes; requires `DESIGN.md` for direction. **Not installed**; its tier areas are used as the QA checklist. |
| Hallmark | README read | Themes are materials (Dusk = bank reconciliation, Cobalt = webhook API, Studio…). Floor gates: contrast, focus, reduced motion, invented facts, broken phone layout. Reflex anti-patterns: eyebrow label over every heading, tracked-caps labels everywhere, one coloured word per headline, heroes that don't fit, fake "thanks" states. 8-width render check + fresh-context review. **Not installed**; floor gates applied in QA. |

## Shortlisted moods for "trustworthy · precise · explanatory"

Hallmark **Dusk** (bank reconciliation) and **Cobalt** (API) ; Astryx **stone** and **matcha**; UI UX Pro Max styles
*Minimalism / Swiss*, *Dark Mode (OLED)*, *Claymorphism* (for tactile controls, used sparingly).

## Steal list

| # | Pattern | Source | Where in CrossPay |
|---|---|---|---|
| 1 | Money as the hero: large tabular-figure amounts, currency in small caps-free text | awwwards fintech pattern | receipt hero, dashboard KPIs, payment amount |
| 2 | Statement/receipt card with a perforated edge and a ledger hash footer | fintech statement metaphor | `/result` |
| 3 | Stepper with a drawn connector that fills to the current step | kombai Stepper + Magic UI animated beam | payment pipeline on `/payment`, `/result`, `/kyc` |
| 4 | Number ticker on first view (once) | Magic UI | dashboard KPIs |
| 5 | Border beam on the one "live" element | Magic UI | live decision feed card |
| 6 | Pressable button with a physical edge, pressed state 2–3 px | Uiverse (user asked for 3D buttons) | all primary actions, one hero CTA per page |
| 7 | Embossed icon tile (subtle, not glossy) | user request (3D icons) + Claymorphism, restrained | page titles, KPI cards |
| 8 | Field + hint + error anatomy, error text tied with `aria-describedby` | shadcn Form | payment, KYC, register, login |
| 9 | Toast (Sonner-like) stack replacing inline flash bars | shadcn Sonner | flashes |
| 10 | Sheet for mobile navigation instead of a dropdown list | shadcn Sheet | navbar < 1080 px |
| 11 | Skeleton → content crossfade | shadcn Skeleton | AI explanation card, risk preview |
| 12 | Detail-page layout: facts left, actions right | Astryx detail template | `/admin/review`, `/result` |
| 13 | Segmented control for filters (not a row of buttons) | shadcn Tabs/Toggle group | `/transactions` decision filter |
| 14 | Headline blur-in, once, then still | React Bits blur text | landing hero only |
| 15 | SVG line drawing for the ledger chain links | Anime.js `svg.createDrawable` / stroke-dashoffset | `/blockchain` |
