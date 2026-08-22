# Sheet Specifications

現在の依頼に添付されたキャラクター画像だけを絶対的な視覚資料として、各シートを独立した高解像度画像にする。保存画像、過去の会話画像、記憶、既存設定を混ぜない。このタスク内で先に生成・検証したシートだけを、後続シートの補助正本として使う。

## 目次

- [共通レイアウト](#共通レイアウト)
- [方向を定義する](#方向を定義する)
- [第1画像: 全身四方向ビューシート](#第1画像-全身四方向ビューシート)
- [第2画像: 頭部六方向ビューシート](#第2画像-頭部六方向ビューシート)
- [第3画像: 厳選六表情シート](#第3画像-厳選六表情シート)
- [第4画像: 固有パーツ詳細シート](#第4画像-固有パーツ詳細シート)
## 共通レイアウト

- 各シートを1枚ずつ生成し、複数シートを統合しない。
- 内容が無理なく収まる横長キャンバスを使い、利用可能な範囲で高解像度にする。
- 背景を無地の非常に薄いニュートラルグレーにする。白、色付き背景、背景シーンを使わない。
- 照明を均一で柔らかくし、形状と本来の色を明瞭にする。
- 正投影に近い自然な視点を使う。
- 広角、魚眼、強い遠近感、俯瞰、煽り、被写界深度、ドラマチックな陰影、逆光、色付き照明、強い環境光を使わない。
- 各ビュー、表情、固有パーツの下に、内容を識別する短い英語ラベルだけを小さく置く。
- ラベルを単純で読みやすいサンセリフ体にし、キャラクターより目立たせない。
- 隣接要素の間へ、キャラクター輪郭より十分弱い細い薄灰色の区切り線を置く。二段構成では必要に応じて段間にも置く。
- 各要素の周囲へ十分な余白を設け、身体、髪、耳、衣装、装備を隣接要素、区切り線、画像端へ接触させない。
- シート全体のタイトル、キャラクター名、説明文、台詞、矢印、寸法線、身長表記、カラーチップ、装飾枠、ロゴ、透かしを追加しない。
- 参照画像本来の描画方式を維持する。アニメ、写真などの表現を別画風、3DCG、実写、コスプレ、フィギュア、ドールへ変換しない。
- 過剰な光沢、粒子、テクスチャ、エフェクト、背景物、色調補正を追加しない。

## 方向を定義する

ビューラベルは画像内でキャラクターが向く方向を表す。

- FRONT: 顔と身体をカメラへ正対させる。
- LEFT: 顔と身体を画像左方向へ向けた完全な側面にする。
- RIGHT: 顔と身体を画像右方向へ向けた完全な側面にする。
- BACK: 顔と身体をカメラの反対方向へ向けた完全な背面にする。
- 3/4 LEFT: 顔を画像左方向へ約45度向ける。
- 3/4 RIGHT: 顔を画像右方向へ約45度向ける。

衣装やアクセサリーの左右位置はビューラベルではなく、キャラクター自身を基準に character's left / character's right で管理する。LEFTとRIGHTを単純反転しない。

## 第1画像: 全身四方向ビューシート

1行4列で左から FRONT / LEFT / BACK / RIGHT を置く。

- 4体を同一人物、同一縮尺、同一頭身、同一高さ、同一立ち位置にする。
- 頭頂、顎、肩、腰、膝、足元の高さを可能な限り対応させる。
- 全ビューを自然な直立姿勢にする。
- 両腕を身体側面から少し離し、手、腕、腰、衣装、脚の輪郭を隠さない。
- 両脚を自然な間隔で平行に置き、交差させない。
- 頭頂から靴底まで欠けなく表示する。
- 顔、髪、体格、衣装丈、素材、装備位置、配色、非対称を全方向で一致させる。
- 側面・背面の髪、留め具、リボン、装備の接続を物理的に成立させる。
- 手を腰へ当てる、腕を組む、身体をひねる、脚を曲げる・交差させる、振り返る、髪や衣装をなびかせる、ビューごとに別ポーズを取る演出を禁止する。
- この画像で補完した全身と背面構造を後続画像の正本にする。

### 完成プロンプト骨格

~~~text
Use only the character images attached to the current request as the absolute
visual source. Do not use saved images, past conversations, memory, or existing
character settings. Create one standalone high-resolution, wide full-body
four-direction reference sheet, not a combined multi-sheet infographic. Place
exactly four complete views in one row from left to right: FRONT, LEFT, BACK,
RIGHT. FRONT faces the camera; LEFT faces image-left in exact profile; BACK faces
away from the camera; RIGHT faces image-right in exact profile. Show the same
character at identical scale, height, body proportions, camera height, and
neutral upright stance. Align head top, chin, shoulders, waist, knees, and soles.
Keep arms slightly away from the torso, hands relaxed and unobstructed, legs
parallel and uncrossed, and every body part fully inside the frame. Preserve the
reference character without beautifying, simplifying, redesigning, changing the
outfit, or changing the rendering method. Infer unseen areas only as needed from
the visible design language, density, materials, palette, motifs, and physical
connections, then freeze that design as canonical. Preserve every character-left
and character-right asymmetry without mirroring. Use a plain very light neutral
gray background, soft uniform lighting, orthographic-like perspective, small
sans-serif labels below each view, subtle thin light-gray separators, and ample
clear spacing. Add no overall title, character name, prose, arrows, dimensions,
height notation, color chips, frame decoration, logo, watermark, scene, prop, or
tag text. No dramatic pose, perspective, lighting, motion, or cropping.
~~~

## 第2画像: 頭部六方向ビューシート

2行3列で、上段左から FRONT / 3/4 LEFT / 3/4 RIGHT、下段左から LEFT / RIGHT / BACK を置く。

- すべて肩上または胸上の同一範囲にし、頭部を大きく明瞭に表示する。
- 頭部サイズ、目の高さ、カメラ距離、表示範囲、配置間隔を揃える。
- すべてニュートラルな無表情にし、口を自然に閉じる。
- 輪郭、目、鼻、口、顎、耳、頭蓋、前髪、横髪、後頭部を角度に応じて一貫させる。
- 髪と頭部アクセサリーの前後接続、奥行き、装着位置を明瞭にする。
- 斜め・側面で別人化させず、単純反転も使わない。
- 衣装は首元と肩周辺の確認に必要な範囲だけ表示し、顔や髪より目立たせない。
- 第1画像で確定した頭部、衣装、非対称、補完構造と矛盾させない。
- 第2画像のFRONT無表情を顔の正式な正本にする。

### 完成プロンプト骨格

~~~text
Use only the current request's attached character images and the verified first
full-body sheet generated in this task. Create one standalone high-resolution,
wide head six-direction reference sheet. Use a 2-by-3 grid. Top row from left:
FRONT, 3/4 LEFT, 3/4 RIGHT. Bottom row from left: LEFT, RIGHT, BACK. FRONT faces
the camera; 3/4 LEFT and 3/4 RIGHT turn about 45 degrees toward image-left and
image-right; LEFT and RIGHT are exact profiles facing those image directions;
BACK shows the back of the head. Show the same neutral, closed-mouth character
from shoulders-up or chest-up in every panel. Match head size, eye height, crop,
camera distance, spacing, facial identity, skull shape, hair geometry,
accessories, neckline, materials, palette, asymmetry, and rendering method.
Clearly establish nose and chin projection, ears, bangs, side locks, back hair,
and accessory depth and connections. Do not mirror one side, invent accessories,
change expression, or let clothing dominate. Use a plain very light neutral gray
background, soft uniform lighting, orthographic-like perspective, small
sans-serif labels below each panel, subtle thin light-gray separators, and ample
clear spacing. Add no overall title, name, prose, arrows, dimensions, color
chips, decorative frame, logo, watermark, scene, prop, or tag text.
~~~

## 第3画像: 厳選六表情シート

2行3列で、上段左から SOFT SMILE / JOY / ANGER、下段左から SADNESS / SURPRISE / FEAR を置く。

- 全枠を正面向きの肩上または胸上にする。
- 頭部サイズ、顔角度、目の高さ、カメラ、照明、髪型、衣装表示範囲を統一する。
- 第2画像のFRONT無表情を顔の正本にし、表情以外を変えない。
- 無表情を重複して置かない。
- SOFT SMILE: 口を閉じた穏やかな微笑み。目元と口元を自然に緩める。
- JOY: 自然に口を開いた明るい笑顔。目元にも喜びを出す。
- ANGER: 眉、目元、口元だけで明確な怒りを示す。赤面、歯の強調、怒り記号を使わない。
- SADNESS: 眉、伏せ気味の目、口元で静かな悲しみを示す。涙、鼻水、過剰な赤みを使わない。
- SURPRISE: 眉を上げ、目と口を自然に開き、緊張のない驚きを示す。
- FEAR: 眉を中央へ寄せ、目元と口元へ緊張を加え、驚きと区別する。
- 汗、涙、怒りマーク、集中線、効果線、台詞、背景演出、小物、手のポーズを加えない。

### 完成プロンプト骨格

~~~text
Use only the current request's attached character images and the verified
canonical sheets generated in this task. Create one standalone high-resolution,
wide six-expression reference sheet. Use a 2-by-3 grid. Top row from left: SOFT
SMILE, JOY, ANGER. Bottom row from left: SADNESS, SURPRISE, FEAR. Show exactly
six frontal shoulders-up or chest-up portraits of the same character. Match head
size, face angle, eye height, camera, crop, lighting, face, skull, hair,
accessories, neckline, palette, asymmetry, and rendering method in every panel.
Use the neutral FRONT view from sheet two as the facial canon and change only
the expression. SOFT SMILE is a gentle closed-mouth smile. JOY is a bright,
natural open-mouth smile with happy eyes. ANGER uses brows, eyes, and mouth
tension without red-face exaggeration, bared teeth, or symbols. SADNESS is quiet
and uses brows, lowered eyes, and mouth without tears, mucus, or heavy redness.
SURPRISE uses raised brows and naturally open eyes and mouth without fear
tension. FEAR uses inward-drawn brows, tense eyes, and a strained mouth and must
not look like simple surprise. Use a plain very light neutral gray background,
soft uniform lighting, small sans-serif labels below each panel, subtle thin
light-gray separators, and ample spacing. Add no neutral duplicate, hand pose,
sweat, tears, anger mark, focus line, effect line, dialogue, prop, scene,
overall title, character name, prose, arrows, dimensions, color chips, logo,
watermark, tag text, or style change.
~~~

## 第4画像: 固有パーツ詳細シート

第1〜第3画像だけでは構造が潰れる重要パーツがある場合だけ生成する。

- 複雑な髪飾り、アクセサリー、特殊な耳・角、翼、尻尾
- 武器、携行品、衣装固有の留め具・模様
- 機械関節、可動構造、重要な左右非対称
- 通常表示では潰れる小さな識別要素
- 表面と裏面で構造が異なるパーツ

必要なパーツだけを重複なく大きく置き、形状、配色、素材、表裏、接続方向、装着位置が分かる最小限の角度を使う。短い英語パーツラベルだけを各要素の下へ置く。全身像、表情、演出的ポーズ、世界観表現、カラーチップで枠を埋めない。

### 完成プロンプト骨格

~~~text
Use only the current request's attached character images and the verified
canonical sheets generated in this task. Create one standalone high-resolution
key-parts detail sheet only because the selected structures cannot be read
clearly in sheets one through three. Show only the necessary parts, enlarged,
unobstructed, and without duplication. Use the minimum views needed to explain
shape, colors, material, front and back, connection direction, attachment point,
and character-left or character-right placement. Preserve the exact canonical
design and rendering method. Put a short English part label below each item.
Use a plain very light neutral gray background, soft uniform lighting, subtle
thin light-gray separators, and ample spacing. Do not add full-body figures,
expressions, filler objects, poses, scenery, color chips, an overall title,
character name, prose, arrows, dimensions, logo, watermark, or tag text.
~~~

通常の人型で第1〜第3画像から必要情報を十分に確認できる場合は、第4画像を作らない。
