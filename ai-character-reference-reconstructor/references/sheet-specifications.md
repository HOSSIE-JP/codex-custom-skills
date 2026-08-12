# Sheet Specifications

この文書は、各画像を独立したファイルとして安定生成するための詳細仕様である。

## 共通レイアウト

- 推奨比率: 横長 3:2 または 16:9
- 背景: 白、または極薄いニュートラルグレー
- 枠線: 必要なら細く控えめ
- 見出し: 1行だけ。長文説明は禁止
- ラベル: 大文字英語。各ビューの真上または真下
- 描画: 参照画像の画風を保つ
- 照明: 均一なスタジオ照明または元画風に合う均一な陰影
- 余白: 頭、髪飾り、靴、リボン、翼、尻尾が切れない安全域を確保

## 方向ラベルの定義

方向はキャラクター自身を基準とする。

- FRONT: キャラクターがカメラへ正対
- LEFT: カメラがキャラクターの左側を観察
- RIGHT: カメラがキャラクターの右側を観察
- BACK: キャラクターの背面
- 3/4 LEFT: FRONTからキャラクター左側が多く見える斜め角度
- 3/4 RIGHT: FRONTからキャラクター右側が多く見える斜め角度

## Sheet 1 Prompt Skeleton

以下の意図を満たすよう、参照キャラクター固有の説明を加えて生成する。

```text
Create one standalone full-body four-direction character turnaround sheet.
Show exactly four complete figures labeled FRONT, LEFT, BACK, RIGHT.
Keep identical scale, body proportions, neutral upright stance, ground line,
camera height, and orthographic-like projection in every view. Arms slightly
away from the torso, hands relaxed, legs uncrossed, feet fully visible. Preserve
the exact face, hairstyle, costume construction, colors, accessories, and all
character-left / character-right asymmetries from the reference images. Infer
unseen areas conservatively from the established design language and use that
inferred design consistently. White or near-white background. No scene, no
perspective drama, no alternate outfit, no pose variation, no tag dictionary,
no combined multi-sheet infographic.
```

## Sheet 2 Prompt Skeleton

```text
Create one standalone head six-direction reference sheet for the same canonical
character. Show exactly six equally sized head-and-shoulders views labeled
FRONT, 3/4 LEFT, 3/4 RIGHT, LEFT, RIGHT, BACK. Use a neutral expression in all
views. Keep identical crop, camera distance, head size, facial identity,
hairstyle geometry, accessory placement, and rendering style. Clearly establish
nose and chin projection, skull shape, ears, bangs-to-back-hair connections,
and the depth of head accessories. Preserve character-left / character-right
asymmetry; do not mirror one side to create the other. White or near-white
background. No expression changes, no alternate costume, no tag text.
```

## Sheet 3 Prompt Skeleton

```text
Create one standalone six-expression sheet for the same canonical character.
Show exactly six equally sized frontal head-and-shoulders portraits labeled
SOFT SMILE, JOY, ANGER, SADNESS, SURPRISE, FEAR. Use the same camera, crop, head
angle, face, hair, accessories, outfit neckline, and lighting in every panel.
Change only eyebrows, eyes, eyelids, cheeks, and mouth as needed for each
emotion. Distinguish SURPRISE from FEAR: surprise has lifted brows and naturally
open eyes and mouth without tension; fear has inward-raised brows, tense eyes,
and a strained mouth. Preserve the canonical identity. White or near-white
background. No neutral duplicate, no pose variation, no tag dictionary.
```

## Sheet 4 Prompt Skeleton

```text
Create one standalone key-parts detail sheet only for structures that cannot be
read clearly in the full-body and head sheets. Show enlarged, clean, unobstructed
views of the necessary parts, using only the minimum angles needed to explain
front, side, back, attachment points, or asymmetry. Keep the exact canonical
colors, materials, proportions, motifs, and character-left / character-right
placement. Short English part labels are allowed. Do not repeat full-body views,
do not add filler parts, and do not include a prompt tag dictionary or integrated
tag string inside the image.
```

## 推論の原則

見えない部分を補完する際は、次を揃える。

- 同じ形状語彙: 曲線主体、角張り主体、花、星、機械、和風など
- 同じ装飾密度
- 同じ素材感
- 同じ配色比率
- 同じ留め具や縁取りの反復
- 前面と背面の物理的な接続
- 髪束の発生位置と重なり順
- 衣装の着脱や可動が成立する構造

見えないことを理由に無地化しない。反対に、根拠のない紋章や宝石を増やさない。
