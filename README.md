# pos_to_vcolor

## Overview / 概要

(Japanese)

これは頂点位置やカーソル位置を頂点カラーやUVMapにコピーするためのBlenderのアドオンです。  
コピー時にバウンディングボックスを指定して正規化したり、垂直方向にUVを反転させることもできます。

(English)

This is the Blender add-on for copying the vertex position and cursor position to vertex color and UV map.  
You can also normalize by specifying a bounding box or invert UV in the vertical direction when copying.


## Supported version / 対応バージョン

Blender 2.80


## Install / インストール

(Japanese)

Blenderのメニューの"Edit" -> "Preferences" -> "Add-ons"のパネルから、"Install..."からpos_to_vcolor.pyを指定してください。

(English)

Open Blender menu: "Edit" -> "Preferences" -> "Add-ons" -> "Install..." and select pos_to_vcolor.py file.


## How to use / 使い方

(Japanese)

- UIは"Edit Mode"からCtrl+Nでサイドバーを表示してToolタブの中にあります。  
- "Add Action"ボタンを押すと、コピーするために設定を追加出来ます。  
- "Source"には、転送元を指定します。頂点の位置や3Dカーソルの位置、他のUVマップや頂点カラーを指定出来ます。  
- "Target"には、転送先を指定します。UVマップと頂点カラーを指定出来ます。<br />※ 頂点カラーやUVマップに値を転送するには、予めプロパティエディタ(Defaultで右側にあるUI)のObject Dataタブ(逆三角形みたいなアイコン)のところで、予めUVマップや頂点カラーレイヤーを追加していなければなりません。
- "Source"に"Vertex Pos"や"Cursor Pos"を選ぶと、"Normalize by bounds"というチェックボックスが表示されます。<br />これをONにすると、UIの下の方で設定するバウンディングボックスで正規化する事ができます。
- "Bounds from Object"を選ぶと、選択したオブジェクトのバウンディングボックスをサンプリング出来ます。
