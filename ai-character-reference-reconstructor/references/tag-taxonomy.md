# English Tag Taxonomy

英語タグ辞書は、該当するカテゴリだけを使用する。空のカテゴリは出力しない。

## 推奨カテゴリ

1. `CHARACTER TYPE`
   - species, role, archetype, age presentation when visually justified
2. `BODY AND PROPORTIONS`
   - build, height impression, proportions, silhouette
3. `SKIN`
4. `FACE`
   - face shape, chin, nose, mouth, distinctive marks
5. `EYES`
   - color, shape, lashes, pupils, highlights
6. `EYEBROWS`
7. `HAIR COLOR`
8. `HAIR LENGTH`
9. `HAIR SHAPE`
   - bangs, parting, side locks, back hair, curls, braids, ponytails, tips
10. `HEAD ACCESSORIES`
11. `EARS / HORNS / HEAD FEATURES`
12. `NECK AND COLLAR`
13. `UPPER OUTFIT`
14. `SLEEVES AND ARMS`
15. `GLOVES / HAND ACCESSORIES`
16. `LOWER OUTFIT`
17. `LEGWEAR`
18. `FOOTWEAR`
19. `BACK STRUCTURES`
   - bows, capes, wings, backpacks, tails
20. `WEAPONS AND PROPS`
21. `JEWELRY AND SMALL ACCESSORIES`
22. `COLOR PALETTE`
23. `MATERIALS AND SURFACES`
24. `PATTERNS AND MOTIFS`
25. `LEFT-RIGHT ASYMMETRY`
26. `STYLE AND RENDERING`
27. `IDENTITY CONSISTENCY`

## 記述ルール

- 1行につき関連タグをカンマ区切りでまとめる。
- `blue hair, cyan hair, aqua hair, turquoise hair` のような無差別な同義語列挙をしない。最も近い1〜2語を選ぶ。
- 形だけでなく接続位置も重要な場合は自然言語で書く。
- 左右は必ずキャラクター基準で書く。

例:

```text
LEFT-RIGHT ASYMMETRY
single diagonal sash from the character's right shoulder to the character's left hip,
small hair clip on the character's left temple
```

- 観察できない材質を断定しない。
- 年齢、民族、職業などを衣装だけから過度に断定しない。
- `beautiful`, `cute`, `masterpiece`, `best quality` のような識別力の低い品質語は辞書へ入れない。
- 画像生成サービス固有の制御語は、ユーザーが対象サービスを指定した場合のみ追加する。

## 統合タグ列の構成順

1. character type / silhouette
2. face and eyes
3. hair
4. head accessories
5. upper outfit
6. lower outfit
7. arms / gloves / legwear / footwear
8. back structures / props
9. color palette / motifs / materials
10. asymmetry anchors
11. style and rendering
12. consistency anchors

統合タグ列は、同じ意味を削り、キャラクター識別に有効な語を優先する。
