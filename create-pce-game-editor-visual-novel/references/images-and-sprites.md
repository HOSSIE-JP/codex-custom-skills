# Images and sprites

## Source production

- Use `imagegen` for original bitmap masters. Establish reusable identity and outfit anchors before expressions or stills, then generate one inspectable master per asset.
- Keep source masters outside generated PCE directories. Record prompt/anchor identifiers and source SHA-256 in the integration mapping.
- Do not ask image generation to produce a packed sheet. Generate transparent frames, inspect them, then assemble deterministically.

## Backgrounds

- Use 224x136 for the normal message-window composition and 256x224 only for an intentional full-screen scene. Confirm these values and offsets against current template assets and `importImage` before use.
- Import PNG through the checkout's `pce-asset-manager.js` `importImage`; treat its palette, tile, VRAM, and warning output as authoritative.
- Keep conversion warnings and generated-file hashes. Reject accidental crops, unreadable focal points, and palette collapse that changes story information.

## Sprite sheets

`pack_sprite_sheet.py` accepts an ordered JSON specification of exact-size transparent PNG frames. It pads dimensions to 16-pixel cells, places frames left-to-right, places rows top-to-bottom, and writes animation metadata and hashes. A `mouth` row must immediately follow its paired `normal` row and share `pairId`, so normal and lip-sync ROWs stay adjacent.

Example specification:

```json
{
  "cellSize": 16,
  "rows": [
    { "id": "default", "kind": "normal", "pairId": "talk", "frames": ["default.png"] },
    { "id": "mouth", "kind": "mouth", "pairId": "talk", "frames": ["mouth_a.png", "mouth_b.png"] }
  ]
}
```

The helper only composites pixels. It refuses non-RGBA images, mismatched frame sizes, missing adjacency, and overwrite without `--force`. Inspect the output visually, then import it through current `importImage` and verify animation `firstCell`, stride, palette, SATB, and scanline constraints in the current engine.

## Full-BG kamishibai (alternative to sprite layering)

A single flat full-BG illustration per beat is a recognized alternative to background+sprite layering for VNs where per-line portrait swapping is not the priority (e.g. horror/atmospheric tone). It does not replace the sprite-sheet workflow above, which remains right for other VNs.

- **Stage 1 — anchors.** Generate a small number of reference sheets as anchors: **character design reference sheets** (one image each, e.g. full-body front view + 3/4 close-up side-by-side on a neutral background, locking proportions/costume) and **location/background design reference sheets** (empty-of-characters wide shots establishing each recurring location's fixed architecture/color palette). When the scenario introduces wholly original characters with no attached source photo, these character design reference sheets are the origination step in place of `ai-character-reference-reconstructor` (that tool reconstructs a reference FROM attached photos of an existing character; it has nothing to reconstruct from for a brand-new invented character). Still invoke `ai-character-reference-reconstructor` first whenever usable source images of the character ARE attached to the request.
- **Stage 2 — per-beat scene stills.** Generate one complete flat illustration per meaningful narrative beat, combining whichever characters + location are relevant to that beat — not a layered composite — explicitly instructing the image tool to reference the relevant anchor sheet(s) for consistency.
- Import each still as a normal 224x136 `image`/`background` PCE asset exactly like any other background. No `sprite` assets are produced, so there is no VRAM sprite-pattern/tileBase budget to track for this content.
- Approximate scale from one real build: ~19 per-beat stills + 10 anchor sheets + 1 title still for a 15-scene / 134-line script.
- Whenever an image-prompt document is produced for a scenario with a title/scenario-select menu (see [menu-shell-and-title-screen.md](menu-shell-and-title-screen.md)), include one title/selector-still prompt referencing the same anchor sheets, so the menu still matches the rest of the scenario visually. This is a standing rule for every scenario, not a one-off.
