# 04 · Design tokens (Phase 4)

Source of truth: `static/css/tokens.css` (CSS custom properties; light on `:root`, dark under
`prefers-color-scheme: dark` unless `[data-theme="light"]`, and under `:root[data-theme="dark"]`; scoped copies under
`[data-kit-theme]` for the UI kit). No Tailwind (stack path B). Contrast ratios are WCAG 2.x, measured against
`--surface-1`, then `--bg`.

## Colour

| Token | Light | Dark | Notes |
|---|---|---|---|
| `--bg` / `--bg-sunken` | `#F5F3EE` / `#EEEBE3` | `#0F1419` / `#0B0F13` | paper / night ledger |
| `--surface-1/2/3` | `#FFFFFF` / `#F7F5F0` / `#EFECE4` | `#161D24` / `#1A222A` / `#1D262F` | cards, sunken areas, hover |
| `--border` / `--border-strong` | `#DDD7CA` / `#8A8372` (3.8:1) | `#2B3641` / `#6B7A8A` (3.9:1) | strong = inputs and UI boundaries (≥ 3:1) |
| `--text` | `#15202B` 16.5 / 14.9 | `#ECEFF3` 14.7 / 16.1 | |
| `--text-2` | `#46505C` 8.2 / 7.4 | `#B5C0CB` 9.2 / 10.0 | |
| `--text-muted` | `#5F6873` 5.7 / 5.1 | `#93A0AD` 6.4 / 6.9 | was 4.3:1 (fail) before |
| `--brand` / hover / active / edge | `#0B6B5C` 6.4 / `#095C4F` / `#074A40` / `#063F36` | `#43C6AC` 8.0 / `#5BD3BB` / `#2FA890` / `#1E7A68` | text on brand: white 6.4 (light), ink 7.3 (dark) |
| `--accent` = `--focus` | `#34418F` (8.2 on paper) | `#9AA6F0` (8.0 on bg) | links and focus ring |
| `--success` (+hover/active/soft/edge) | `#18794E` 5.4 | `#3DD68C` 9.1 | approved, verified |
| `--warning` | `#8A5300` 6.3 | `#F5B544` 9.4 | hold, pending |
| `--danger` | `#B42318` 6.6 | `#F97066` 6.1 | blocked, failed |
| `--info` | `#1F55B3` 7.0 | `#7CB3FF` 7.9 | |
| `--neutral` | `#475467` (6.7 on its soft bg) | `#A9B4C2` (6.9) | rejected |
| `--ai` / `--ai-soft` / `--ai-border` | `#6538C4` 7.2 | `#B79CFF` 7.5 | AI-generated content only |

Status text on its own soft background: 4.8 to 6.2 (light), 6.0 to 8.3 (dark). All ≥ 4.5.

## Typography

Families: `--font-sans` Plus Jakarta Sans, `--font-mono` JetBrains Mono (tabular numbers, IDs, hashes). Both self-hosted.

| Token | Size | Use |
|---|---|---|
| `--text-xs` | 12 px | captions, badges, hints |
| `--text-sm` | 14 px | secondary text, table cells, buttons |
| `--text-base` | 15 px | body |
| `--text-md` | 17 px | card titles |
| `--text-lg` | 20 px | metric values |
| `--text-xl` | 24 px | receipt title, page titles (min) |
| `--text-2xl` | 30 px | KPI values, page titles (max) |
| `--text-3xl` | 38 px | — |
| `--text-4xl` | 48 px | landing headline, receipt amount (max) |

Line heights: `--leading-tight` 1.2, `--leading-snug` 1.35, `--leading-body` 1.55. Weights 400/500/600/700/800.

## Spacing and layout

4 px scale: `--space-1` 4 · 2 8 · 3 12 · 4 16 · 5 20 · 6 24 · 8 32 · 10 40 · 12 48 · 16 64.
`--container` 1200 px; `--gutter` 24 px (16 px under 640 px). Breakpoints: 640, 900, 1080 (nav → sheet), 1280.
Controls: `--control-sm` 32, `--control-md` 40, `--control-lg` 48; `--touch` 44.

## Shape and depth

Radius: `--radius-sm` 6, `--radius-md` 10, `--radius-lg` 14, `--radius-full`.
Elevation: `--shadow-0` none, `--shadow-1` card, `--shadow-2` popover/toast/receipt, `--shadow-3` dialog/sheet.
`--press-depth` 3 px (pressable button edge; 0 under reduced motion).

## Motion

Durations: `--dur-instant` 100 ms, `--dur-fast` 150, `--dur-base` 220, `--dur-slow` 350, `--dur-page` 500 (all 0 under
`prefers-reduced-motion`). Easings: `--ease-standard` (0.2, 0, 0, 1), `--ease-emphasized` (0.3, 0, 0, 1.15),
`--ease-exit` (0.4, 0, 1, 1), `--ease-spring` (0.34, 1.56, 0.64, 1). Stagger step `--stagger` 50 ms.
