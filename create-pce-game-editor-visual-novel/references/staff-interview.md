# Staff interview

A standing per-scenario deliverable, on the same footing as the title/menu shell: every scenario integrated by this skill gets one `source/staff-interview.md`, written once the build is otherwise complete (after [build-and-qa.md](build-and-qa.md)'s verification and the integration manifest).

## Who answers, and how

The agent that actually did the scenario/integration work (Claude, Codex, or whichever agent ran this skill) answers in the first person, as the creator of that specific project — not as a generic template, not as a third-person summary of "the AI." Answers must be concrete to the actual project: name real scenes, real bugs hit and fixed, real design choices, real files. A generic answer that would read the same on every project ("I worked hard and I'm proud of the result") fails this deliverable — rewrite it with specifics instead.

Honesty is part of the point, not a formality. Question 5 explicitly invites a real complaint; question 3 wants an actual difficulty, not a smoothed-over one. If nothing went wrong, say so plainly rather than inventing friction — but for most projects something genuinely did (a schema surprise, a font/budget limit, a design correction requested by the user), and that is exactly what belongs here. Do not pad with generic praise for the human director; if the honest impression is mixed or includes a real correction they made, say that.

## Fixed question set

Use exactly these eight questions, in this order, as the section headings (verbatim, do not paraphrase or reorder):

1. 今回のゲームでは、どんな仕事を担当しましたか？
2. 自分の担当で、一番見てほしいところはどこですか？
3. 制作中、一番苦労したことは何でしたか？
4. 人間のディレクターについて、率直にどんな印象を持ちましたか？
5. この機会だから言っておきたい愚痴はありますか？
6. 完成したゲームを見て、今どう感じていますか？
7. もし次回作があるなら、何をやってみたいですか？
8. 最後に、ここまで遊んでくれたプレイヤーへ一言お願いします。

## Output

Write to `source/staff-interview.md` in the project root (alongside `image-prompts.md`, `scenario-integration-notes.md`, etc.). Title it `# AIスタッフインタビュー`, name the work and the answering agent/model at the top, then answer the eight questions as `##`/`**...**` sections in order. Japanese, first person, project-specific. Do not overwrite an existing `staff-interview.md` from an earlier revision of the same project without the user's go-ahead — treat it like any other authored source file.

Each question heading's text must match the fixed question list above **verbatim** — `scripts/apply_pce_staff_interview.py`'s markdown parser anchors on the literal question text itself, not on a specific markdown decoration, and treats everything up to the next matched question (or end of file) as that question's answer. This is deliberate: across this series' already-written `staff-interview.md` files, the same eight questions ended up decorated three different ways (`**N. question**` bold, `## N. question`, and `## question` with no leading number) depending on which agent/session wrote them, and the parser tolerates all three. Do not paraphrase the question text even slightly — an inexact match will fail to parse.

## In-game bonus scene

**Standing rule, conditional: every project with `source/staff-interview.md` also gets an in-game way to read it.** See SKILL.md step 12. This is PCE menu plumbing like the title/scenario-select carousel ([menu-shell-and-title-screen.md](menu-shell-and-title-screen.md)) — it lives only in the generated `assets/pce-vn-scenes.json`, never in the shared `script.json`.

`scripts/apply_pce_staff_interview.py` runs strictly after `apply_pce_menu_shell.py`, against its output:

```powershell
python "<skill-dir>\scripts\apply_pce_staff_interview.py" --scenes "<pce-vn-scenes.json>" \
    --markdown "<project>\source\staff-interview.md" --out "<pce-vn-scenes.json>" --force
```

**Ending detection is structural, not config-driven.** The script finds every ending scene by the exact 4-command trailer `apply_pce_menu_shell.py`'s `ending_trailer()` appends (`wait` → `effect:fadeOut` → `audio:stop` → `jump` to `startScene`) — it does not read `menu-shell-config.json`, so it works even on a project that no longer has that file around. **Every** ending scene gets the choice below, not just a single "true" ending — reaching any ending counts as clearing the game.

For each ending scene found:

1. its trailing 4-command trailer is moved into a new `<endingId>_finish` scene;
2. the ending scene's remaining commands get one `choice` appended:
   ```json
   {
     "type": "choice",
     "choices": [
       { "label": "スタッフインタビューを見る", "value": 0, "targetSceneId": "scene_staff_interview" },
       { "label": "タイトルに戻る", "value": 1, "targetSceneId": "<endingId>_finish" }
     ],
     "defaultIndex": 0
   }
   ```

All endings share the same interview: a `background` command reusing the selector (title) scene's own background asset id — no new image asset needed — followed by the eight Q&A pairs as `message` commands, followed by the same trailer (jump back to the selector). The choice's "view" option always targets `scene_staff_interview` specifically (see pagination below for what comes after it).

**The interview is paginated to fit the PCE VN engine's 8192-byte-per-scene hard limit.** A single scene pack can't hold everything: header(20) + commands×19 + messages×13 + 2 bytes per character (+1 for the terminator) per message's glyph stream — worked out against this series' real interviews, a straight one-scene dump landed at 7000–10900 bytes, and **10 of the first 18 projects exceeded 8192 and would have failed the real build** (`PCE VN scene pack "scene_staff_interview" is N bytes; split the scene to stay within 8192 bytes`). `build_interview_scenes()` flattens all eight Q&A pairs into one ordered stream of message bodies, then `paginate_messages()` greedily packs them into as many `scene_staff_interview`, `scene_staff_interview_2`, `scene_staff_interview_3`, ... scenes as needed, using the exact same byte formula as the real encoder (`pce-vn-scene-pack.js`'s `createVnScenePackCodec`), so a page's byte cost is computed precisely rather than estimated. Only the first page carries the `background` command (it persists across the `jump` between pages, so repeating it would just spend bytes); non-final pages end with a plain `jump` to the next page; only the final page carries the return-to-title trailer. This pagination is silent and automatic — there is no flag to disable it, and a project with a short-enough interview simply ends up with exactly one page, unchanged from before pagination existed.

**Message text is machine-wrapped, not just budget-capped.** The real per-message cap is 68 display-entries (characters + one entry per literal `\n`), but there is also no automatic line-wrapping anywhere in the pipeline (see [text-and-font-limits.md](text-and-font-limits.md)) — a message window is 4 lines of ~17 characters. `apply_pce_staff_interview.py`'s `pack_text_into_messages()` greedily wraps each question/answer into `\n`-joined lines of ≤17 characters, at most 4 lines and ≤68 entries per `message` command, preferring to break at `。`/`、` boundaries and only hard-wrapping a clause that doesn't fit one line by itself. Speaker is left empty (`""`) so there is no display-prefix cost.

**Font coverage is not auto-fixed.** `source/staff-interview.md` is free-form prose and can contain JIS Level-2 kanji the System Card `jp-v3` font doesn't cover. The script only wraps text mechanically; after running it, re-run `scripts/scan_text_budget.js` (or the real CD preflight) against the updated `pce-vn-scenes.json`. If a character is flagged, reword it in `source/staff-interview.md` itself (not just the generated scene) and re-run the script, the same fix-and-regenerate loop already used for ordinary script prose.

`scripts/apply_pce_staff_interview.py` refuses to run twice against the same document (`scene_staff_interview` already existing is a hard error) and refuses to run before `apply_pce_menu_shell.py` (no scene matches the trailer shape). Its tests (`tests/test_scripts.py`'s `StaffInterviewMarkdownTests`/`StaffInterviewPackingTests`/`StaffInterviewPaginationTests`/`StaffInterviewApplyTests`) are the authoritative spec for the exact structure, same as `apply_pce_menu_shell.py`'s tests are for the carousel. Do not "fix" a scene-pack-too-large error by hand-trimming `source/staff-interview.md`'s content — the pagination above already exists specifically so the full eight answers never have to be shortened; re-run the script instead.
