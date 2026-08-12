---
name: ai-clothing-reference-reconstructor
description: >-
  Generate clothing-only character reference sheets from one or more reference images,
  with separate four-direction views for outerwear, inner outfits, and age-appropriate
  underwear. Use for clothing-setting sheets, clothing turnarounds, invisible or transparent-torso
  garment references, layered costume breakdowns, and requests to remove the character
  while preserving the costume's construction, colors, patterns, and asymmetry.
---

# Clothing Reference Reconstructor

## Purpose

Turn a character image into independent, reusable garment-setting sheets. Preserve the
reference costume's construction and visual language while removing the character,
anatomy, pose, background, and scene. Use the built-in image generation tool by default.

## Output contract

Create one image file per clothing stage; never combine all stages into one collage.
The default three files are:

1. clothing_reference_01_outer_layer_four_directions.png
2. clothing_reference_02_inner_outfit_four_directions.png
3. clothing_reference_03_underwear_four_directions.png

Each file must contain exactly four evenly spaced views labeled FRONT, LEFT, BACK,
and RIGHT. Keep identical scale, camera height, neutral upright garment volume,
orthographic-like projection, and a white or near-white setting-sheet background. Use
an invisible/transparent mannequin concept: show garment volume and drape, but no skin,
anatomy, mannequin surface, face, hair, or character.

The requested output may be adapted when the user explicitly asks for a different
number of layers. Add a fourth key-parts sheet only when a large bow, armor assembly,
mechanism, detachable prop, or important asymmetric detail cannot be understood from
the three standard sheets.

## Workflow

### 1. Read and normalize the input

- Treat attached images as the primary reference. If a local path is malformed, such
  as /C:/..., normalize it to a Windows path before attempting access.
- If the local path cannot be read by the image tool, use the image visible in the
  conversation with num_last_images_to_include; do not pretend the local file was
  inspected.
- Use a local generated sheet as a later reference only when it is readable. Otherwise
  preserve continuity through the original attachment and an explicit written design
  summary.
- Treat the user's explicit layer or garment instructions as higher priority than
  inferred details.

### 2. Establish the garment canon

Before generating, internally record:

- silhouette, proportions, hem lengths, sleeve shapes, collars, cuffs, and closures;
- main and accent colors, fabric appearance, patterns, trims, ruffles, and buttons;
- front, side, and rear attachment points;
- character-left and character-right asymmetries;
- visible legwear, footwear, gloves, detachable panels, tails, sashes, or ornaments;
- conservative inferences needed for cropped or hidden areas.

Do not average conflicting details. Prefer the clearest view and the user's explicit
description. Infer unseen construction conservatively from the established silhouette,
material, color ratio, decoration density, and physical attachment points. Do not add
unrequested logos, weapons, jewelry, symbols, or decorative complexity.

Exclude hair, head accessories, facial features, and earrings from clothing sheets by
default. Include them only in a requested accessory sheet or when they are physically
part of a costume layer and cannot be separated.

### 3. Select the stages

Use these defaults:

- Outer layer: coat, cardigan, jacket, cape, hood, overskirt, detachable sash, large
  back ribbons, shoulder ornaments, gloves, boots, or other removable costume pieces
  that sit on top. Keep related pieces together when they attach as one layer.
- Inner outfit: blouse, shirt, bodice, vest, collar, neck bow, waistcoat, base
  skirt/dress, apron panel, socks, stockings, and other garments worn beneath the
  outer layer.
- Underwear: an opaque, practical, character-matched undergarment set. Keep it
  separate from the visible outfit and never show it on a body.

If there are multiple clearly separable outer layers, create one independent sheet per
layer only when the user requests stage-by-stage separation or the construction would
otherwise be ambiguous. If underwear is explicitly excluded, omit that sheet and state
that it was omitted.

For characters who appear underage or teenaged, keep the underwear technical, opaque,
non-sexual, and age-appropriate. A simple bra-style top and ordinary briefs may be used
when requested, but do not add erotic framing, exposed anatomy, sheer fabric, thong
shapes, garters, cleavage emphasis, or lingerie styling. If the user requests
sexualization of a minor, decline that part and offer a neutral garment-only reference.

### 4. Generate in dependency order

Generate one built-in image-generation call per stage:

1. Generate the outer layer from the original reference. Treat it as the silhouette,
   color, scale, and asymmetry canon.
2. Generate the inner outfit from the original reference plus the completed outer
   sheet. Explicitly prohibit the outer layer from appearing.
3. Generate the underwear from the original reference plus the established sheets.
   Explicitly prohibit all outer and inner clothing from appearing.

Use the smallest num_last_images_to_include value that includes every required
reference image. Label each input role in the prompt: original costume reference,
outer-layer canon, or inner-outfit canon. When editing a previous sheet, preserve the
layout and change only the requested garment design.

### 5. Use a stable prompt structure

Every stage prompt should state:

- Use case: clothing-only technical reference;
- Input images: original reference and any canonical sheets;
- Subject: the exact layer and garments to show;
- Composition: exactly four full-length FRONT / LEFT / BACK / RIGHT views;
- Style: preserve the source's linework, palette, material language, and rendering;
- Constraints: invisible mannequin, no character or body, no scene, no extra text;
- Avoid: omitted layers, unrequested props, perspective drama, mirrored asymmetry,
  watermarks, and prompt/tag text.

Describe the back and side construction explicitly. Do not rely on a simple horizontal
mirror for LEFT and RIGHT; define both using the character's own left and right.
Require all hems, sleeves, tails, ruffles, shoes, and labels to remain inside the canvas.

### 6. Inspect and iterate

Visually inspect every generated sheet before presenting it. If a major invariant fails,
regenerate with one targeted correction instead of changing the whole design. Check:

- exactly four views and correct labels;
- no character, skin, anatomy, mannequin surface, scene, or unintended layer;
- consistent scale, color palette, material, silhouette, and line style;
- correct character-left / character-right placement;
- physically coherent front, side, and back attachment;
- complete garment edges, cuffs, hems, tails, ruffles, gloves, and footwear;
- no extra text, watermark, logo, or prompt tag embedded in the image.

For dense costumes, a focused key-parts sheet is justified only if the main sheets do
not clearly communicate a critical attachment, asymmetry, or detachable structure.

## Handoff

Present each image as an independent file with a full absolute local path or clickable
local-file link. Keep the generated default copy unless the user explicitly requests
replacement. If the asset is meant for a project and the user names a destination,
copy the selected final files into that project before finishing; do not leave
project-bound assets only under the default generated-images directory.

Use short stage names in the final response and state when the optional fourth sheet was
not necessary. Do not embed an English tag dictionary or integrated tag string into the
images. Provide those as copyable text only when the user asks for them or requests
full character-reference parity.

If the user asks for true alpha transparency of the background, distinguish it from an
invisible mannequin. Follow the image-generation skill's built-in chroma-key workflow
for simple transparent-background output; do not silently switch to an unapproved CLI
or native-transparency fallback.
