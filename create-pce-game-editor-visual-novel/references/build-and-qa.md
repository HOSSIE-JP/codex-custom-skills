# Build and QA

## CD-ROM2 required path

1. Start from the checkout's official CD VN template.
2. Inspect all generated PSG JSON with current `inspectPsgJson`, then import with `importPsgJson`. Import PNG images/sprites with `importImage`.
3. Run `inspectVnSceneDocumentBuild` (or its discovered replacement) with the proposed raw scene document, current asset document, and CD target. Save diagnostics and scene budgets.
4. Save scenes only after a clean inspection; run the real VN preparation/build route used by the editor. For a concrete non-GUI invocation recipe (including the mandatory CD-DA Track 1 warning-audio asset) see [cd-build-recipe.md](cd-build-recipe.md).
5. Run focused VN/asset tests and the repository's declared full test command (`npm test` in the current checkout).
6. Confirm the final `.cue` and every referenced track/data file exist and were produced by the current build.

## Runtime evidence

- Use the `geargrafx-debugging` skill when Geargrafx is available. Query live tool names instead of trusting stale examples.
- Test the main path and a shortest path to each declared ending. Capture path choices, reached ending ID, build hash, screenshots or frame evidence, and audio observations.
- Confirm background/sprite transitions, message readability, choice routing, state-dependent behavior, PSG start/stop/continue behavior, and return/termination behavior.
- Remaining combinatorial histories may be covered by static graph/state checks. Label them as static, not played.

## Optional HuCARD

Generate HuCARD only when requested. Re-run target-specific preflight, capacity/bank/VRAM checks, build, focused tests, and the same ending-path runtime suite against the ROM. Do not reuse CD pass results. If current limits make the target infeasible, report measured budgets and stop rather than deleting story/assets silently.

## Reporting boundaries

Report exact commands, artifacts, hashes, tests, played routes, and warnings. Physical hardware, CRT/LCD appearance, controller feel, and audible output are external gates unless actually tested. New music is PSG only; voice, ADPCM dialogue, and CD-DA authoring are outside this skill. Flag any placeholder CD-DA Track 1 warning audio (e.g. a synthesized tone rather than a real spoken warning) explicitly; see [cd-build-recipe.md](cd-build-recipe.md).
