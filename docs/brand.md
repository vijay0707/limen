# limen Brand Kit

**Brand idea:** Typed decisions with an explicit threshold — act, abstain, or escalate.

## Brand essence
- **Purpose:** Make model-driven decisions explicit, reviewable, and calibrated.
- **Personality:** Precise, calm, technical, trustworthy, pragmatic.
- **Core metaphor:** A threshold or portal between a model's signal and an allowed action.
- **Voice:** Direct and developer-friendly. Prefer clear explanations over hype.

## Logo
The portal mark represents crossing a decision threshold. Use the full wordmark for README headers, docs, and presentations; use the symbol alone for avatars and compact placements.

### Clear space and sizing
- Keep clear space around the logo at least the height of the “i” stem.
- Use the full wordmark at a size where `limen` remains readable.
- Use `limen-symbol.png` for small avatars where the wordmark would be too small.
- Do not stretch, rotate, outline, add effects to, or recolor the logo.

### Backgrounds
- Preferred: white or very light neutral backgrounds.
- On dark backgrounds, use the transparent logo only if contrast remains strong; a dedicated reversed logo is not included in this starter kit.
- Avoid placing the logo over busy imagery.

## Color palette

| Token | Hex | Suggested use |
|---|---|---|
| Ink Navy | `#111426` | Primary text, wordmark, dark UI |
| Threshold Blue | `#3768D8` | Links, active states, technical accents |
| Signal Violet | `#8050F5` | Highlight, secondary accent |
| Soft Lavender | `#C9A2FF` | Subtle glow, background tint |
| Mist | `#F6F7FB` | Page backgrounds and panels |
| White | `#FFFFFF` | Primary canvas |

### CSS variables
```css
:root {
  --limen-ink: #111426;
  --limen-blue: #3768D8;
  --limen-violet: #8050F5;
  --limen-lavender: #C9A2FF;
  --limen-mist: #F6F7FB;
  --limen-white: #FFFFFF;
}
```

## Typography
- **Preferred:** Inter for UI and documentation headings.
- **Fallback:** system-ui, -apple-system, "Segoe UI", sans-serif.
- **Code:** JetBrains Mono or SFMono-Regular, Consolas, monospace.
- Use sentence case for headings. Keep technical copy concise.

## Logo usage
**Do**
- Preserve proportions and generous whitespace.
- Use the navy wordmark with blue/violet accents.
- Keep the mark and wordmark together for primary branding.

**Don't**
- Recreate the mark with emoji or text characters.
- Add unapproved taglines inside the logo.
- Use low-contrast combinations or place the logo on a cluttered background.

## Messaging
**Primary descriptor:** Typed decisions with an explicit threshold — act, abstain, or escalate.

**Short description:** `limen` is a decision-policy layer for calibrated model probabilities, with explicit thresholds, abstention, escalation, and decision logging.

**Brand principles**
1. The model answers; your code decides.
2. Ambiguity is a valid outcome.
3. Thresholds should be explicit and reviewable.
4. Failure behavior should be intentional.
5. Decisions should leave an audit trail.

## Asset inventory

All paths relative to `docs/`.

| Asset | Use |
|---|---|
| `assets/brand/limen-logo.png` | Full lockup, white background. README header, docs, slides. |
| `assets/brand/limen-mark.svg` | **Vector master** of the portal mark. Brand palette, no filters. |
| `assets/brand/limen-mark-small.svg` | Flat mark for anything under ~64px. Favicon source. |
| `assets/brand/limen-symbol.png` | Portal mark, centred with padding. |
| `assets/brand/avatar-460.png` | GitHub org / social avatar. |
| `assets/brand/social-preview.png` | 1280×640. Upload via repo Settings → Social preview. |
| `assets/brand/limen-color-palette.svg` | Palette reference sheet. |
| `assets/favicon.ico`, `assets/icon-*.png`, `assets/apple-touch-icon.png` | Docs site icons. |

### Known limitations

- **No dark-background lockup exists.** The original transparent export was keyed by
  luminance, which left ~55% of pixels at partial alpha — a grey film across the canvas
  and halos around the letterforms — and the navy wordmark is near-invisible on dark
  regardless. It has been removed rather than shipped. A dark lockup must be rendered
  from source; it cannot be extracted from the light version, because the glow is white
  and so is the background. Until one exists, use the light logo on white only.
- **The full artwork has no vector master.** `limen-mark.svg` is a faithful vector of
  the mark's geometry on brand tokens, but it does not reproduce the volumetric glow —
  SVG blur renders inconsistently across engines and GitHub strips part of it. Use the
  raster logo wherever the glow matters, and the vector wherever size or crispness does.
- The guidance above says not to recreate the mark, while also calling for a vector
  master. `limen-mark.svg` is that master; treat it as the exception, not a licence to
  redraw.
