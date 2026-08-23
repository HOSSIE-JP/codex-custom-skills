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
