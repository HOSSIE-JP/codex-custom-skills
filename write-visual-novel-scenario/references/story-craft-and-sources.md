# Story craft lenses and sources

These are diagnostic lenses, not a universal formula. Record which lens fits the current work, what evidence supports it, and why plausible alternatives were not selected.

## Required design questions

- What changes for the viewpoint character, and what pressure makes that change observable?
- What does each major character want now, what blocks it, what tactic changes, and what remains unresolved?
- What new meaning or consequence does each scene add?
- What does each choice express, change, or reveal? Cosmetic alternatives must be labeled as such.
- Where do branches rejoin, which state survives the join, and how does later text acknowledge it?
- Does every ending pay off earlier causes rather than only choose a final label?
- What must be shown or heard, and what can remain prose? Express this as semantic cue intent only.

## Initial primary-source bibliography

### 日本シナリオ作家協会「シナリオ講座」募集資料

- Source: https://scenario.or.jp/kouza/wp-content/themes/scenario/uploads/download-file.pdf
- Supported use: the course explicitly progresses from plot to 箱書き to scenario and includes group critique. Use this to justify separating premise/plot, scene boxes, script, and review artifacts.
- Limit: it is a course outline, not evidence that one beat count, act count, or page formula fits every interactive VN.

### Scriptnotes 403, “How to Write a Movie”

- Source: https://johnaugust.com/2019/scriptnotes-ep-403-how-to-write-a-movie-transcript
- Supported use: examine structure through character motivation, pressure, choices, and change rather than mechanically copying surface beats.
- Limit: the discussion concerns linear movies. Interactive routes require explicit state, branch, join, and ending analysis in addition.

### GDC 2018, “Writing and Narrative Design: A Relationship”

- Source: https://www.gdcvault.com/play/1025476/Writing-and-Narrative-Design-A
- Supported use: distinguish authored prose/voice from narrative-system design, while keeping them traceable to one intent.
- Limit: job boundaries vary by team. In a small project one person may perform both roles; the artifact boundary still matters.

### GDC 2025, “Get Serious About Writing Tools”

- Source: https://media.gdcvault.com/gdc2025/Slides/Horneman_Jurie_Get_serious_about.pdf
- Supported use: treat narrative data shape, validation, preview, change safety, and writer-facing workflow as design concerns rather than late export chores.
- Limit: tool investment must match project scale. Do not invent infrastructure when normalized JSON and deterministic scripts are sufficient.

### ink by inkle

- Source: https://www.inklestudios.com/ink/
- Supported use: reason explicitly about branching flow, variables, conditional content, knots/joins, and preview/testing of interactive narrative.
- Limit: this skill does not output ink syntax and must not leak ink-specific constructs into the engine-neutral schema.

## Lens selection record

In `scenario-design.json`, summarize at least two plausible approaches under `structureLensCandidates`. Select only the lenses that improve the current work. State the observable consequence of the selection; “standard” or “best practice” is not a reason.

Useful candidates include character-change pressure, mystery information control, goal-obstacle-tactic escalation, relationship negotiation, episodic accumulation, and branch-consequence convergence. A work may reject conventional transformation when constancy under pressure is the intended arc.
