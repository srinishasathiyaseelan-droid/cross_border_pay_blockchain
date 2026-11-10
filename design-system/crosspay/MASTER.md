# CrossPay design system · MASTER

Structure follows UI UX Pro Max's `design-system/<project>/MASTER.md` convention. **The UI UX Pro Max tool was not
installed or executed** (third-party code); this file was written by hand from its published categories and checklist,
using CrossPay's chosen direction (`DESIGN.md`).

## Product type and pattern

Fintech / compliance tool with a marketing landing page. Pattern: *Minimalism (Swiss) + data dashboard*, light-first with
a dark variant; tactile controls (restrained claymorphism) only on buttons and icon tiles.

## Colours

See `DESIGN.md` and `static/css/tokens.css`. Semantic: success = approved, warning = hold, danger = blocked, slate =
rejected, violet = AI. All text tokens ≥ 4.5:1 on surface and background in both modes (measured).

## Typography

Plus Jakarta Sans 400/500/600/700/800 + JetBrains Mono 500/600 with `font-variant-numeric: tabular-nums`.
Scale (px): 12, 14, 15 (body), 17, 20, 24, 30, 38, 48. Line heights 1.2 (display) / 1.35 (headings) / 1.55 (body).

## Spacing, shape, depth

4 px base: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64. Container 1200 px; gutters 16 (phone) / 24 (tablet+).
Breakpoints 640 / 900 / 1080 / 1280. Radius 6 / 10 / 14 / 999. Elevation 0 (flat), 1 (card), 2 (popover), 3 (dialog).

## Effects

Pressable edge on buttons (3 px, 0 when pressed); embossed icon tile (inner top highlight + 2 px bottom edge);
perforated receipt edge; drawn SVG connectors. No gradients on text, no glow, no particles.

## Anti-patterns (do not ship)

Emoji as icons · gradient text · glow shadows · eyebrow label over every heading · tracked caps on body labels ·
invented numbers/testimonials/logos · infinite decorative loops · hover-only affordances · horizontal page scroll.

## Pre-delivery checklist

- [ ] SVG icons only (sprite), no emoji
- [ ] `cursor: pointer` on every clickable element
- [ ] Motion uses tokens; respects `prefers-reduced-motion`
- [ ] Text contrast ≥ 4.5:1 (light and dark), UI/large text ≥ 3:1
- [ ] Visible focus on every interactive element; logical tab order
- [ ] Badges, chips and buttons reflow without clipping
- [ ] Checked at 375, 768, 1024, 1440 px; no horizontal scroll
- [ ] Touch targets ≥ 44 px
- [ ] Every page works with AI off and offline (fonts, Chart.js, Anime.js self-hosted)
