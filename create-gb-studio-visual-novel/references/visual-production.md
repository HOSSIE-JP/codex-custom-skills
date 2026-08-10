# Character-consistent GBC visual production

## Contents

- Source authority
- Default style
- Proportion and silhouette locks
- Wardrobe and garment accuracy
- Image purposes and sizes
- Character continuity
- Anatomy contract
- ImageGen workflow
- Defect repair
- Visual QA

## Source authority

Keep the character bible and visual manifest, selected high-resolution masters and prompts, deterministic GBC conversions, and runtime captures as separate layers.

One cut must have one production master. Do not extract final cuts from a generated multi-panel storyboard: panel boundaries reduce resolution, encourage duplicated anatomy, and make crop policy ambiguous.

## Default style

Use this style block only as a GBC-legibility fallback when the current project does not define another direction:

> GBC-friendly flat cel illustration with thick consistent dark outlines, broad solid color regions, two or three discrete value steps per material, limited palette, simplified readable background shapes, separated silhouettes, and low-frequency detail that survives reduction to 160 pixels wide.

This fallback is not a title or genre identity. A user-defined style may replace it, but must still be tested at native 160x144 resolution. When using the fallback, avoid smooth gradients, airbrush shading, bloom, translucent glow, lens effects, photorealistic microtexture, tiny highlights, distant clutter, and low-contrast edges.

## Proportion and silhouette locks

Choose a proportion policy before production. Record head-to-body ratio, adult or child age category, shoulder and hip width, limb length, and whether comedic deformation is allowed. If proportions are fixed, repeat that prohibition in every prompt and reject all chibi, squat, widened, shortened-limb, or unintended obesity drift. A large head and short limbs are not harmless style variation when they break the locked identity.

If a project intentionally uses lower proportions for comedy, declare the eligible cuts explicitly in the manifest. Never infer that every joke should become chibi. Use expression, pose, camera, and timing for tonal contrast when the user requests one consistent proportion system.

Make recurring characters readable by silhouette at 160 pixels. Lock hair mass, sleeve length, neckline, hem length, exposed-leg region, shoe shape, and accessories. Compare the cast side by side before generating production cuts; two plausible outfits can still fail if their silhouettes are too similar.

## Wardrobe and garment accuracy

Create one anchor per wardrobe ID and describe real garment construction rather than a vague modesty category. Record neckline, straps or sleeves, opacity, support structure where relevant, waist rise relative to navel and hip bones, leg opening, hem, fastening, footwear, and exposed regions.

Never infer intimate wardrobe or sexualized presentation from genre, gender, or a previous project. When the current brief explicitly includes age-sensitive or intimate wardrobe, first verify and record exact ages, adult eligibility, agency, and content boundaries. Then preserve the requested real garment construction without substituting a different garment category or inventing additional exposure. Treat garment accuracy, age eligibility, and content boundaries as separate requirements.

## Image purposes and sizes

### Message-safe gameplay cut

- Generate at 1536x1024 (3:2).
- Compose the final background at 160x144 with art in the top 160x96 and a 48-pixel dialogue region.
- Keep faces, hands, props, and action inside a centered 5:3 safe composition.
- Never draw a caption panel, window frame, or dialogue text into the source master.

### Fullscreen event still or ending

- Generate at 1024x1024.
- Keep important content inside a centered 10:9 safe crop.
- Convert to 160x144 with no dialogue band or ending label over the CG.

### Identity and outfit anchors

- Face anchor: 1024x1024, neutral expression, clear identity details.
- Outfit anchor: 1024x1536, full body, neutral stance, unobstructed silhouette.
- Create one anchor per wardrobe ID. Do not invent later clothing from prose alone.

### Logo, title, and menu

Use deterministic raster, vector, or code-native rendering for exact Japanese. Author at 640x576 or directly at 160x144. Use ImageGen only for a text-free decorative plate when appropriate.

## Character continuity

Record concrete locks for hair, eyes, glasses, proportions, age category, body width, accessories, and outfit components. For each visual job attach the selected identity anchor, exact wardrobe anchor, and any preceding approved cut required for spatial continuity. Repeat these locks in the prompt.

Do not accept a production cut merely because each character is individually attractive. Check identity, relative height, outfit silhouette contrast, scene seriousness, and body proportions against adjacent cuts.

## Anatomy contract

Declare visible people, arms and hands per owner, the purpose of every visible hand, shoulder-to-elbow-to-wrist connection, hidden limbs and their occlusion, and forbidden normalized regions.

Use fewer visible hands when action does not require them. Reject detached or floating hands, third hands near props, duplicated wrists, merged fingers, limbs attached to the wrong body, and gestures that do not serve the beat. Manifest counts are review requirements, not proof.

## ImageGen workflow

Use the `imagegen` skill and one built-in call per cut. Label every input by role. Persist the selected output into the project before referencing it. Generate prompts with `build_vn_image_prompts.py`; do not remove style, identity, outfit, proportion, silhouette, anatomy, or no-text blocks.

On Windows, use `C:\path\image.png`, not `/C:/path/image.png`. If a local-path reference cannot load, make it visible in conversation before built-in editing. Identify the highest-resolution edit target and label GBC or emulator captures as reference-only.

## Defect repair

For a normalized coordinate annotation: identify the rejected object, remove it and broken connected anatomy, reconstruct the existing underlying surface, prohibit replacement limbs or gestures, preserve unrelated invariants, and reinspect both high resolution and native GBC output. Never keep an annotated object because it appears anatomically connected.

## Visual QA

Inspect source master, face and hands, forbidden-region crops, proportion and body width, identity and outfit against anchors, silhouette contrast, 160x96 composition, full 160x144 image, palette and tile metrics, and built-in emulator capture.

Record prompt, source, input roles, SHA-256, crop policy, manual verdicts, and rejection history. Mark rejected masters explicitly and keep them out of active manifests. A contact sheet is useful for continuity, but also inspect individual native-size cuts because a sheet can hide facial loss and palette seams.
