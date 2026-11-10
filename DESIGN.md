# DESIGN.md · CrossPay "Signed Ledger"

Chosen at checkpoint 1 (2026-11-10) from three directions (`design-work/03-directions.md`). This file is the single
source of creative direction for the UI, the motion system and the anti-slop / Hallmark-style QA.

## Product and audience

CrossPay settles cross-border SME payments. A risk model and a deterministic policy approve, hold or block each payment;
compliance officers decide holds; an optional AI layer explains but never decides. Users: SME finance staff (desktop and
phone), compliance officers (desktop, dense data), and examiners in a viva (projector).
Personality: **trustworthy · precise · explanatory.**

## Direction

Paper and ink: a page that reads like a well-kept bank statement. Warm paper background, ink text, one verdigris signal
colour. Money is the hero, set in tabular mono figures. The page is flat and quiet; the **controls** are tactile:
buttons have a short pressable edge and icon tiles are softly embossed (the 3D language the owner asked for, kept
subtle). Dark mode is a "night ledger" with the same structure.

## Rules for every page

1. **Lead with the primary action** of the page (submit payment, decide a hold, verify KYC, verify the ledger) and the
   **decision state** (APPROVED / HOLD / BLOCKED / REJECTED). Everything else is secondary.
2. **Facts before AI.** Deterministic facts first; AI text sits in a clearly labelled advisory box below or beside them,
   never above the decision.
3. **Numbers** (amounts, scores, rates, counts) use `--font-mono` with tabular figures. IDs and hashes too.
4. **One hero CTA per page at most** (the pressable primary with the signature edge). Other actions are secondary,
   outline or ghost.
5. **No decoration without a job:** no gradient text, no glow, no particles, no eyebrow label over every heading, no
   tracked-caps labels everywhere, no single coloured word in a headline, no invented numbers, logos or testimonials.
6. **Status colour is semantic only:** success = approved/verified, warning = hold/pending, danger = blocked/failed,
   neutral slate = rejected, violet = AI-generated. Never used for decoration.
7. **Motion explains state**: drawing the pipeline to the current step, a receipt printing in, a figure ticking once,
   toasts sliding in. Nothing loops except loaders and the live-feed dot. Reduced motion → instant or opacity only.

## Tokens (summary; full list in `design-work/04-tokens.md`, code in `static/css/tokens.css`)

| | Light | Dark |
|---|---|---|
| Background / surface | `#F5F3EE` / `#FFFFFF` | `#0F1419` / `#161D24` |
| Text / secondary / muted | `#15202B` / `#46505C` / `#5F6873` | `#ECEFF3` / `#B5C0CB` / `#93A0AD` |
| Brand (verdigris) | `#0B6B5C` (hover `#095C4F`, active `#074A40`) | `#43C6AC` (hover `#5BD3BB`, active `#2FA890`) |
| Accent (ink indigo, focus) | `#34418F` | `#9AA6F0` |
| Success / warning / danger / info / AI | `#18794E` / `#8A5300` / `#B42318` / `#1F55B3` / `#6538C4` | `#3DD68C` / `#F5B544` / `#F97066` / `#7CB3FF` / `#B79CFF` |

Type: Plus Jakarta Sans (UI and headings) + JetBrains Mono (figures, IDs), both self-hosted. Scale xs 12 → 5xl 48 px.
Spacing: 4 px scale. Radius: 6 / 10 / 14 / full. Depth: hairline border + one soft shadow; buttons add a 3 px edge.
Motion: instant 100 · fast 150 · base 220 · slow 350 · page 500 ms; easings standard, emphasized, exit, spring;
stagger 50 ms. Engine: CSS transitions for micro/component, Anime.js v4 for page sequences.

## Signature components

- **Statement receipt** (`/result`): perforated top edge, amount as the hero, decision stamp, ledger hash footer.
- **Drawn pipeline**: KYC → Payment → Risk model → Policy → Settlement; the connector line draws to the current step.
- **Pressable button + embossed icon tile**.

## Accessibility floor

WCAG AA (4.5:1 text, 3:1 UI and large text) in both modes; visible 2 px focus ring with offset on everything
interactive; full keyboard use (skip link, sheet/dialog focus trap, Escape closes); touch targets ≥ 44 px; semantic
HTML; `prefers-reduced-motion` honoured everywhere.
