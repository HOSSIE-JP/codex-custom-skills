# Usage Examples

## 基本

~~~text
Use $ai-character-reference-reconstructor to reconstruct the character shown in
the images attached to this request. Use only those attachments as the absolute
visual source. Generate the three required sheets separately, add the fourth
sheet only if essential, and finish with the English tag dictionary and
integrated tag string.
~~~

## 現在の複数添付を相互補完する

~~~text
$ai-character-reference-reconstructor
現在添付した3枚だけを使ってください。各画像を同一キャラクターの相互補完資料として確認し、最も明瞭で一貫した特徴を採用してください。過去画像や既存設定は使わず、中間確認なしで全成果物を完成させてください。
~~~

## 参照が上半身だけでも全身を完成させる

~~~text
$ai-character-reference-reconstructor
添付画像は上半身だけですが、見えている衣装、素材、配色、装飾密度、デザイン言語から見えない部分だけを補完し、第1画像を省略しないでください。
~~~

## 第4画像を必要性で判定する

~~~text
$ai-character-reference-reconstructor
添付画像だけを正本に3枚の標準シートを生成し、通常表示では潰れる重要な固有構造がある場合だけ第4画像を追加してください。
~~~

## このスキルを使わない例

- 文章だけから新規キャラクターを作る
- 添付のない過去キャラクターを記憶から再現する
- 写真の背景だけを消す
- 既存画像を別画風へ変換する
- 一般的な画像の高解像度化だけを行う
