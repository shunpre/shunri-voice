# 瞬理 Production Motion Bank v1

## 目的

Phase 2の軽量カメラモーションを、実際に人物が身振り手振りする8本の縦動画へ差し替える。

この8本だけを高品質化すれば、Reel renderer側はそのまま使える。

## 必須ファイル名

```text
neutral-talk.mp4
open-hand.mp4
point-up.mp4
point-side.mp4
think.mp4
small-nod.mp4
explain-both-hands.mp4
cta-forward.mp4
```

MOV / M4V / WebMでもimport時にMP4へ正規化される。

## 生成ルール

共通:
- 瞬理本人の顔を固定
- 赤茶ボブ
- メガネ必須
- 瞬LPロゴ入り衣装
- カメラ目線中心
- 9:16
- 5〜8秒程度
- 背景はシンプル
- 激しい身体移動はしない
- 手が顔を長時間隠さない
- ループ接続しても破綻しにくい
- 元動画の音声は使わない

variant:

### neutral-talk
正面。自然な会話。小さな手振り。ニュートラルな説明。

### open-hand
片手の掌を自然に開き、提案・紹介するジェスチャー。

### point-up
片手の人差し指で上部を示す。上にスクショや図解を出す前提。

### point-side
横方向を示す。左右どちらかのUIや比較図を指す前提。

### think
少し考える表情。視線をわずかに外して戻す。大げさにしない。

### small-nod
カメラ目線で小さくうなずく。肯定・結論に使う。

### explain-both-hands
両手で幅・比較・構造を説明する。胸より上を中心。

### cta-forward
カメラに少し寄る感覚。最後に視聴者へ促す。指差し過多は避ける。

## Import

8本を同じフォルダへ置く。

```bash
make import-motion-bank DIR="$HOME/Desktop/shunri-motion"
```

内部で全clipを:

```text
1080x1920
30fps
H.264
音声なし
```

へ正規化し、

```text
~/shunri-voice/assets/motion-bank-production/
```

へ保存する。

8本そろっていれば、Reel生成時にproduction bankが自動優先される。

## Lip-sync

Reel生成時、各sceneの瞬理ナレーションをscene WAVへ分割する。

```text
motion clip
+
scene narration.wav
↓
lip-sync provider
↓
synced scene clip
```

providerは固定しない。

環境変数:

```bash
export SHUNRI_LIPSYNC_COMMAND='your-command --video {video} --audio {audio} --output {output}'
```

その後:

```bash
make reel-poc-lipsync FILE="$HOME/shunri-voice/samples/reel_script.txt"
```

### OSS候補

MuseTalk 1.5:
- MIT
- 日本語対応
- input video + audio
- 高品質lip-sync
- NVIDIA GPU推奨

ユーザーのIntel MacはGPU条件を満たさないため、MuseTalkを本番採用する場合は外部GPU workerへ載せる。

ローカルMac側はprovider-neutralにしてあるため、MuseTalk、将来の別OSS、商用APIへ差し替えてもReel rendererは変更不要。
