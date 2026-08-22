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
