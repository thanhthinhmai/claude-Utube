# Contract: tệp

## `films/<phim>/lines.json` (mở rộng, tương thích ngược)

```json
[
 {"id": "l01", "para": "P01", "text": "What if you never needed sleep again?"},
 {"id": "l14", "para": "P05", "text": "Is that a real fish?", "speaker": "hero", "emotion": "neutral"},
 {"id": "l40", "para": "P12", "text": "I can't say no to him.", "speaker": "mom", "fx": "wall"},
 {"id": "l61", "para": "P18", "text": "Who invited this kid?", "speaker": "president", "role": "man"}
]
```

- Câu không có `speaker`, `voice` → giọng người kể. Câu cũ có `voice` không tiền tố → `kokoro:<voice>`.
- Kiểm (`script.py`): `speaker` là `narrator` hoặc khớp `[a-z0-9-]{1,32}`; người nói không có trong cast phải có `role`; `emotion`, `fx` thuộc tập cho phép.

## `<owner>/channels/<kênh>/voice.json`

```json
{
 "version": 1,
 "narrator": {"mode": "own", "voice": "el:pNInz6obpgDQGcFmaJgB", "speed": 1.05,
              "el": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.2},
              "approved": {"at": "2026-11-26T10:00:00Z", "by": "owner"}},
 "roles": {
  "boy": [{"mode": "narrator", "pitch": 4, "speed": 1.08}],
  "girl": [{"mode": "narrator", "pitch": 5, "speed": 1.08}],
  "woman": [{"mode": "narrator", "pitch": 3}, {"mode": "own", "voice": "el:EXAVITQu4vr4xnSDxMaL"}],
  "man": [{"mode": "narrator", "pitch": -2, "speed": 0.95}],
  "old_man": [{"mode": "narrator", "pitch": -3, "speed": 0.9}],
  "old_woman": [{"mode": "narrator", "pitch": 2, "speed": 0.9}]
 }
}
```

- Thiếu tệp → bộ mặc định trên, `narrator` = null (phim đầu của kênh phải chọn, FR-011).
- Tên tệp thật: `channels/<kênh>/VOICE.json` dưới gốc kênh (app: thư mục dữ liệu của xưởng; lệnh: repo, vào git, không có khoá). Kênh trước 036 chưa có tệp: `voice`/`speed` của `channel.json` là người kể.

## `films/<phim>/cast/cast.json → characters[]` (thêm vào 034)

```json
{"id": "mom", "speaks": 4,
 "voice": {"mode": "narrator", "pitch": 3, "speed": 1.0, "emotion": "neutral"},
 "voice_options": [
  {"setting": {"mode": "own", "voice": "el:EXAVITQu4vr4xnSDxMaL"}, "why": "ấm, ~40 tuổi, mệt mỏi nhẹ", "sample_line": "l40", "sample": "cast/voices/mom/0.wav"},
  {"setting": {"mode": "narrator", "pitch": 3}, "why": "người kể đóng vai, giữ chất kênh", "sample_line": "l40", "sample": "cast/voices/mom/1.wav"}
 ]}
```

## `films/<phim>/voices/`

| Tệp | Ai ghi | Nội dung |
|---|---|---|
| `<id>.wav` | voice make | 24 kHz mono, đã áp cao độ và hiệu ứng |
| `.raw/<id>.wav` | voice make | bản trước hậu kỳ (để đổi fx/cao độ không phải đọc lại, không tốn ký tự) |
| `dur.json` | voice make | như cũ |
| `align.json` | voice make (EL) | `{<id>: {chars:[…], start:[…], end:[…], source: "el"\|"asr"}}` |
| `speakers.json` | voice make / voice check | bảng người nói ↔ giọng đã giải |
| `usage.json` | voice make | ký tự ElevenLabs theo phim |
| `.made.json` | voice make | khoá câu mở rộng (data-model) |

## `.env` (gốc dự án, git bỏ qua) — chỉ dùng khi chạy bằng lệnh

```
ELEVENLABS_API_KEY=…
ELEVENLABS_MODEL=eleven_multilingual_v2
TTS_PROVIDER=elevenlabs        # tuỳ chọn: ưu tiên đề xuất giọng ElevenLabs
```

## `$STUDIO_DATA/secrets/` (app)

- `.key` (Fernet, 0600), `elevenlabs.json` (mã hoá, 0600); thư mục 0700. `app import` và sao lưu **không** chép thư mục này.
