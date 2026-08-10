# Personal Codex skills

This repository tracks only the following custom skills from the local Codex skills directory:

- `build-gb-studio-game`
- `build-gb-studio-visual-novel`
- `compose-gb-studio-vn-bgm`
- `create-gb-studio-visual-novel`
- `geargrafx-debugging`
- `xna-to-godot-migration`

All other top-level entries are intentionally ignored, including Codex-bundled system skills and skills installed from other sources.

## Set up another Windows PC

Choose the skills directory used by that Codex installation, create it if necessary, and initialize this repository in place so unrelated installed skills can remain alongside it:

```powershell
$skillRoot = Join-Path $HOME '.codex\skills'
New-Item -ItemType Directory -Force -Path $skillRoot
git -C $skillRoot init
git -C $skillRoot remote add origin https://github.com/HOSSIE-JP/codex-custom-skills.git
git -C $skillRoot fetch origin
git -C $skillRoot switch --track -c main origin/main
```

If the destination already contains any of the six tracked skill folders, back them up or reconcile them before checking out the repository. Restart Codex if the skills do not appear automatically.

## Update workflow

```powershell
$skillRoot = Join-Path $HOME '.codex\skills'
git -C $skillRoot status --short
git -C $skillRoot add --update
git -C $skillRoot add build-gb-studio-game build-gb-studio-visual-novel compose-gb-studio-vn-bgm create-gb-studio-visual-novel geargrafx-debugging xna-to-godot-migration
git -C $skillRoot commit -m "Update custom skills"
git -C $skillRoot push
```

Review `git status` before committing. The root `.gitignore` is an allowlist, but tracked files can still contain machine-specific paths or sensitive content if added intentionally.
