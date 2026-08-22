# English Tag Taxonomy

元参照画像と、同じタスク内で完成・検証したキャラクターリファレンス画像群を基準に、恒常的な視覚特徴だけを英語で記述する。カテゴリを増減・改名せず、次の順序ですべて出力する。

## 目次

- [固定カテゴリ](#固定カテゴリ)
- [出力形式](#出力形式)
- [記述規則](#記述規則)
- [色を記述する](#色を記述する)
- [Integrated Tag String](#integrated-tag-string)
## 固定カテゴリ

1. IDENTITY
   - visually supported age group, gender presentation, species, broad body type, head-to-body proportion
2. FACE
   - face shape, brows, nose, mouth, skin features, stable facial marks
3. HAIR
   - color, length, silhouette, parting, bangs, side locks, back hair, tips, hair ornaments
4. EYES
   - color, shape, size, pupils, irises, stable highlights
5. BODY
   - height impression, build, shoulder width, torso, limb proportions
6. OUTFIT
   - garment types, silhouette, lengths, layers, structure, materials, patterns, trim
7. FOOTWEAR
   - shoes, socks, stockings, leg adornments
8. ACCESSORIES
   - jewelry, ears, horns, wings, tail, carried items, weapons, mechanical or special parts
9. COLOR PALETTE
   - part-by-part general English color names and reliable HEX codes when available
10. DISTINGUISHING FEATURES
    - the smallest set of high-value visual anchors needed to preserve identity
11. ASYMMETRY
    - every asymmetric element and its correct character-relative side; write none when symmetric

他カテゴリを新設しない。該当特徴が本当に存在しないカテゴリは none と記述し、推測で埋めない。

## 出力形式

~~~text
IDENTITY:
[English tag]
[English tag]
FACE:
[English tag]
[English tag]
HAIR:
[English tag]
[English tag]
EYES:
[English tag]
[English tag]
BODY:
[English tag]
[English tag]
OUTFIT:
[English tag]
[English tag]
FOOTWEAR:
[English tag]
[English tag]
ACCESSORIES:
[English tag]
[English tag]
COLOR PALETTE:
[part]: [general English color name] [HEX code when reliable]
DISTINGUISHING FEATURES:
[English tag]
[English tag]
ASYMMETRY:
[English description using character's left or character's right, or none]
~~~

## 記述規則

- 1行を簡潔で具体的な英語句または短文にする。
- 画像生成AIが外見を再現するために必要な形状、接続、丈、重なり、素材、装飾を記述する。
- 衣装名だけで済ませず、識別に必要な構造へ分解する。
- 同義語、重複語、価値の低い美辞麗句を列挙しない。
- 左右は必ず character's left / character's right で書く。viewer-left / viewer-right や曖昧な left / right を使わない。
- 元参照画像で見えなかった部分は、第1画像で正本化した補完デザインだけを記述する。
- 観察できない材質、民族、年齢、性別、種族を断定しない。外見から安全に述べられる presentation に留める。
- キャラクター名などの固有名詞、性格、職業、物語、能力、出身、世界観、他者との関係を含めない。
- 表情、ポーズ、動作、構図、カメラ、背景、照明、画風、画質指定、レンダリング指定、一時的状態を含めない。
- beautiful、cute、masterpiece、best quality など、同一性を定義しない評価語・品質語を含めない。
- サービス固有の制御語や重み構文を含めない。

## 色を記述する

- 髪、瞳、肌、衣装、装備の主要色を、一般的な英語色名で部位ごとに書く。
- 元画像と均一照明の正本画像から十分に判断できる場合だけ、英語色名へ HEX を併記する。
- 影、圧縮、色付き照明、半透明、反射で色が不確かな場合は、偽の精密なHEX値を作らず英語色名だけを書く。
- 色名を各形状カテゴリへ含めてもよいが、COLOR PALETTEとの無意味な重複列挙は避ける。

## Integrated Tag String

辞書の主要項目だけを、重要度の高い恒常的特徴から次の順で並べる。

1. identity
2. face
3. hair
4. eyes
5. body
6. outfit
7. footwear
8. accessories
9. distinguishing features
10. asymmetry

1本のカンマ区切り英語タグ列を1つの text コードブロックに入れる。

- タグ辞書にない情報を追加しない。
- 主要色は対応する髪、瞳、衣装、装備のタグへ含め、独立した重複色列を増やさない。
- 表情、ポーズ、動作、構図、カメラ、背景、照明、画風、画質、レンダリング、一時状態を含めない。
- 六表情を列挙しない。
- snake_caseへ変換せず、自然な英語句を使う。
- 同義語と重複を削り、少数の高識別タグを優先する。
