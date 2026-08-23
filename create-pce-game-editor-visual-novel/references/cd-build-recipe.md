# CD-ROM2 build recipe

Two things not spelled out elsewhere: the mandatory CD-DA Track 1 warning-audio asset, and a concrete, verified way to trigger a real (non-dry-run) build from plain Node outside the Electron GUI. Re-confirm both against the live checkout; treat names below as an `rg` starting point.

## CD-DA Track 1 warning audio is mandatory, even with zero CD-DA music

`pce-build-system.js`'s `buildProject()` calls `assetManager.validateCddaDiscAssetDocument()` before proceeding, in both a dry run and a real build. It throws:

> CD-ROM2 build requires Track 1 warning audio. Open Sound > CD-DA and import the required warning audio.

unless the asset document contains **exactly one** asset with `type: "cdda-warning"` and the fixed id `"cdda_warning"` — see `pce-asset-manager.js`'s constants `PCE_CDDA_WARNING_ASSET_TYPE = 'cdda-warning'` and `PCE_CDDA_WARNING_ASSET_ID = 'cdda_warning'`. This applies to every CD-ROM2 project, including one with no other CD-DA tracks at all.

Import it with `pce-asset-manager.js`'s `importAudio`:

```js
await assetManager.importAudio(projectDir, {
  kind: 'cdda-warning',
  sourcePath: '<absolute path to a WAV file>',
});
```

This auto-converts the source WAV via `audioConverter.convertWavForCdda()` and registers the fixed-ID asset. The resulting Track 1 is real, audio-CD-player-safe warning audio on the actual disc — confirmed in a real build log by a `Track 1 300 sector(s)` line (300 sectors = a 4-second WAV at 75 sectors/sec).

A placeholder (e.g. a synthesized tone) is structurally fine to unblock a build, but flag it explicitly in the integration manifest and QA report for later replacement with a real spoken warning before any disc is pressed or shared.

## Triggering a real build from plain Node, outside the Electron GUI

`pce-build-system.js` exports `setProjectDir(projectDir)` (or `openProject(projectDir)`) and `buildProject(onLog, options)`, but the module does a top-level `require('electron')`, so it cannot be required directly from plain Node without a shim.

The checkout already ships two working shims — do not write a new one:

- **`tools/dev/vn-cli-build.js`** — a real, git-tracked CLI driver. It patches `Module._load` to fake `require('electron')`, with `mockApp.getPath` returning `<repo-root>/data` (matching this checkout's portable-mode `userData`), then calls `bs.setProjectDir(projectDir); bs.buildProject(log, {})` — a real build, no dry-run. Reads the project directory from `PCE_VN_PROJECT`, defaulting to `data/projects/my_pce_game`.

  ```powershell
  $env:PCE_VN_PROJECT = "<absolute path to the project dir>"
  node "<repo-root>\tools\dev\vn-cli-build.js"
  ```

- **`tests/helpers/mock-electron.js`** — the equivalent test-harness shim (`loadWithMockedElectron`), used by every build-related test in the checkout's own suite. Read this one to see exactly which Electron surface is faked; it's exercised continuously by the checkout's own CI.

### Safe, non-destructive pre-check before spending toolchain time

```js
bs.setProjectDir(projectDir);
const result = bs.buildProject(log, { dryRun: true, allowMissingToolchain: true });
```

Runs the entire Node-only generation pipeline (VN source generation, asset source generation, CD payload packing, full build-command construction) and stops right before spawning the compiler/`pce-mkcd` — exactly what the checkout's own tests use in place of a real build. It still surfaces the CD-DA warning-audio error above, since that check runs before the toolchain gate.

### Requirements for a real (non-dry-run) build

Must all resolve to real files on disk, or `buildProject` returns `{success: false, error: '...toolchain is not configured...'}` rather than throwing:

- `setupManager.getLlvmMosPceCdPath()`
- `setupManager.getPceMkcdPath()`
- a resolved `cd.iplPath` / `cd.systemCardPath`, from `project.json`'s `cd.*` fields or the global `<userData>/tools/settings.json` (portable mode: `data/tools/settings.json`)

If the toolchain isn't installed, treat `{success:false, ...}` as a normal, reportable outcome.
