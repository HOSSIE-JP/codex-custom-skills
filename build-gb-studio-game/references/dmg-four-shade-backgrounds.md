# DMG four-shade background conversion

## Target and invariants

Use this workflow for DMG-only backgrounds and the monochrome branch of a `Color + Monochrome` project. The output must satisfy all of these independently:

- 160 by 144 pixels unless the project deliberately uses another valid background size;
- only `#E0F8CF`, `#86C06C`, `#306850`, and `#071821` for DMG artwork;
- at most 192 unique 8 by 8 tiles for a DMG scene, confirmed again by the target GB Studio build;
- visible ordering and separation of dark features at native resolution;
- meaningful use of all four shades in the artwork region;
- unchanged GBC master art, verified by source hashes when a color branch exists.

Palette cardinality, tile count, and visual fidelity are separate gates. Four listed colors do not prove that a face or dark background retains four useful tone groups.

## Adaptive conversion workflow

1. Preserve the source and identify the final 160 by 144 composition before quantization. Apply any deliberate crop or special ending-screen downsample first.
2. Define an analysis mask containing the artwork whose contrast matters. Exclude uniform message bands, letterbox bars, and large UI panels from threshold estimation. Continue to render the whole image through the selected thresholds.
3. Composite transparency against the intended background, then compute perceptual luminance. A deterministic integer Rec. 709 form is:

       Y = (2126 * R + 7152 * G + 722 * B + 5000) // 10000

4. Build the luminance histogram from the analysis mask and find three deterministic four-class multi-Otsu thresholds for that image. Map the four ascending luminance bins to darkest through lightest DMG colors.
5. Render the complete image, then record exact shade counts for both the full output and the analysis mask.
6. Split the result into 8 by 8 index tiles and count unique tiles. Also run the project converter because engine-side deduplication and reservations are the final authority.
7. If the image exceeds 192 unique tiles, blend the adaptive thresholds toward a conservative baseline such as `[64, 128, 192]` in 0.05 steps:

       threshold[i] = round(a * otsu[i] + (1 - a) * baseline[i])

   Test `a` from 1.00 downward and keep the largest value that fits. Enforce strictly ascending thresholds after rounding. This retains as much per-image adaptation as the tile budget permits.
8. If even the baseline does not fit, simplify only measured high-frequency regions, crop nonessential detail, or use a deliberate composition-specific downsample. Do not reduce every background preemptively.

One fixed threshold triplet across an entire project is unsafe. Dark teal, night, or low-key scenes often occupy a narrow luminance range and collapse into two or three effective shades even though brighter scenes look acceptable.

## Meaningful four-shade validation

Validate the analysis region rather than allowing a dialogue band or isolated pixel to satisfy the rule.

- Require all four exact palette entries to occur in the analysis region.
- Apply a configurable minimum to every shade. A useful initial regression floor for a 160 by 96 artwork region is `max(16 pixels, 0.1 percent)`, then raise it when the composition warrants stronger separation.
- Record pixel counts and percentages for each shade. Reject a fourth shade represented only by fringe noise.
- Check luminance-order preservation with a rank or linear correlation against the source analysis region. Establish the acceptance floor from representative project images instead of treating one universal coefficient as proof of quality.
- Inspect local contrast at faces, eyes, glasses, hands, silhouettes, clothing boundaries, event-still focal points, and transitions into the message band.

Use a native-resolution contact sheet that places source/GBC and DMG versions side by side. Include the darkest scenes explicitly; a montage dominated by bright scenes can hide the failure this workflow is intended to catch.

## Tile-budget cautions

Ordered or error-diffusion dithering can make gradients look richer in isolation while creating many distinct 8 by 8 tiles, unstable texture, and poor compression. Leave dithering off by default. Accept it only after measuring the exact tile and bank cost and inspecting it in motion.

Count tiles after every operation that can change pixels, including palette mapping, UI-band composition, cropping, and nearest-neighbor scaling. Report both the script-side count and the official GB Studio result when they differ.

Custom pixel-art titles may use hand-authored flat regions and the exact palette instead of photographic thresholding. Full-screen ending art may use a composition-preserving downsample before adaptive tone mapping. Record these as explicit per-image methods rather than silent exceptions.

## Manifest and regression evidence

For each converted background, record:

- source and output paths plus SHA-256 values;
- conversion method and analysis-mask bounds;
- exact palette and chosen thresholds;
- adaptive blend factor and fallback operation, if any;
- full-image and artwork-region shade counts and percentages;
- unique 8 by 8 tile count and maximum colors per tile;
- a source-to-output luminance fidelity metric;
- the unchanged GBC source hash for mixed-mode projects.

Run the static asset checks, then build official ROM and Web outputs with the intended GB Studio version. For mixed mode, verify the compatible CGB flag and force both DMG and GBC execution in an emulator. Capture native-resolution evidence for dark scenes and exercise normal input through representative branches.

Background compression or loading changes can shift emulator frame timing without changing game logic. Recalibrate prerecorded input demos against observable scene transitions after asset regeneration; do not treat an old frame schedule as a stable runtime oracle.

## Failure patterns to reject

- averaging RGB channels instead of using perceptual luminance;
- deriving thresholds from a dominant dark UI or message band;
- using one fixed threshold set for unrelated scenes;
- declaring success because four RGB values appear somewhere in the PNG;
- adding dithering without measuring unique tiles and banks;
- degrading spatial resolution before a measured budget failure;
- overwriting the GBC master while producing the DMG derivative;
- validating only a contact sheet, only the resource schema, or only a successful build.
