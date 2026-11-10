# 03 · Three directions (Phase 3)

Visual preview: `03-directions.html` (palette with measured contrast, type scale, button set, badges, receipt card, light
and dark). All contrast values below are WCAG 2.x ratios against the card surface, computed from the hex values.

## A · Signed Ledger (recommended)

Paper and ink. A light-first statement look: warm paper background, ink text, one verdigris signal colour, and amounts
set in tabular mono figures so money reads like a bank statement. Controls stay tactile, as you asked earlier for 3D
buttons and icons: buttons have a 3 px pressable edge and icon tiles are softly embossed. The page itself is flat and calm.
Motion explains money moving: connectors draw between pipeline steps, KPI figures tick once, the receipt "prints" in.

| Token | Light | Dark |
|---|---|---|
| bg / surface | `#F5F3EE` / `#FFFFFF` | `#0F1419` / `#161D24` |
| text / text-2 / muted | `#15202B` 16.5 · `#46505C` 8.2 · `#5F6873` 5.7 | `#ECEFF3` 14.7 · `#B5C0CB` 9.2 · `#93A0AD` 6.4 |
| brand (verdigris) | `#0B6B5C` 6.4 (white on it 6.4) | `#43C6AC` 8.0 (ink on it 7.3) |
| success / warning / danger / info / AI | 5.4 · 6.3 · 6.6 · 7.0 · 7.2 | 9.1 · 9.4 · 6.1 · 7.9 · 7.5 |

Fonts: Plus Jakarta Sans (UI, headings) + JetBrains Mono (amounts, IDs, hashes), both already self-hosted. Radius 6/10/14 px;
depth = hairline borders + one soft shadow; buttons get an edge, cards don't. Base: hand-built token components (path B).
Signature components: **statement receipt** (perforated edge, ledger hash footer), **drawn pipeline connector**,
**pressable button + embossed icon tile**.

## B · Control Room

Dark-first and technical: graphite surfaces, a cyan signal and lime focus ring, dense tables, monospace wherever numbers
appear. Flat controls with inner hairlines, no depth. Fast, status-driven motion (150 ms): pulses on live items, a scan
line on the feed. Radius 4/6 px. Contrast: text 15.4, brand 10.1, muted 5.2 (dark); light variant text 18.7, brand 5.4.
Signature components: **live feed ticker**, **dense data table**, **command-style filter bar**. Same font pair.

## C · Tactile Depth (current, refined)

Today's look: deep navy, glossy 3D icon tiles, thick pressable buttons, cursor glow, gradient headline, CSS 3D block chain
and particles. Most playful; also closest to generic AI-styled fintech (gradient text, glow, one coloured word per
headline: a Hallmark reflex flag), and its muted text fails AA today (4.3:1 on cards). Dark only. Signature components:
**glossy 3D tile**, **3D cube hero**, **cursor-glow card**.

## Scores (1–5; for effort and performance cost, 5 = least effort / cheapest)

| Direction | Fit to purpose | Primary-action clarity | Accessibility | Build effort | Performance cost | Distinctiveness | Total |
|---|---|---|---|---|---|---|---|
| A · Signed Ledger | 5 | 5 | 5 | 3 | 5 | 4 | **27** |
| B · Control Room | 4 | 4 | 4 | 4 | 5 | 3 | 24 |
| C · Tactile Depth | 3 | 3 | 3 | 5 | 3 | 2 | 19 |

**Recommendation: A.** CrossPay is about being trusted with money and explaining decisions. A statement-like page with
tabular figures puts the amount and the decision first, works in light (reading receipts, evidence and reports) and
dark, and keeps the tactile 3D controls you wanted without the generic glow-and-gradient look. It is the only option
where every text token passes AA in both modes with room to spare.
