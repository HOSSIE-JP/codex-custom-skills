# ProTracker MOD and GB Studio integration

## Supported path

This skill supports original four-channel ProTracker MOD files with the `M.K.` signature for a GB Studio project configured for the hUGE driver. Confirm the installed GB Studio version and project driver before generation.

The deterministic generator uses empty sample headers and instrument numbers as GB/hUGE voice roles. It does not produce PCM sample payloads.

## Track specification

Each pattern contains 64 rows. The template places up to 16 musical steps every four rows. Channel roles are fixed: melody instrument 1, harmony instrument 2, bass instrument 3, and noise drums instruments 16/18.

Set BPM with `Fxx` in the first cell. End the final pattern with `B00` to jump to order zero when `loopRequired` is true.

## Resource registration

Treat project `.gbsres` ownership as authoritative. If a generator derives stable UUIDs or symbols, integrate the MOD through that generator.

`compose_mod.py --gbsres-out` is allowed only when `track-spec.json` supplies:

- a real stable resource `id`;
- resource `name` and symbol;
- project-relative `filename` matching the copied MOD;
- `type` set to `mod`.

Reject placeholder IDs. Do not patch a generated `.gbsres` while leaving its source generator stale.

## Validation layers

1. Validate JSON spec and note range.
2. Generate twice and compare SHA-256.
3. Validate `M.K.`, song length, order table, pattern byte count, `Fxx`, and `B00`.
4. Register through the project authority.
5. Export official ROM and Web builds with matching ROM hashes.
6. Test start, stop, loop, carryover, replacement, and silence through real input.
7. Listen on the built-in emulator and report physical-device audio separately.

Compilation does not prove that a cue is audible or loops cleanly.
