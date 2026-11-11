# Contract: tệp của chọn đề

Mọi tệp dưới đây bị git bỏ qua (R7).

- `channels/<slug>/topics.json`: data-model.md, phần Topic.
- `channels/<slug>/references.json`: data-model.md, phần Reference channels.
- `channels/<slug>/TOPICS.md`: viết lại sau mỗi lần ghi.

```markdown
# Topics: <tên kênh>

Updated 2026-11-11 · YouTube units used today: 1840 / 9000

## Queue
| # | Verdict | Total | Demand | Heat | Competition | Overlap | Fit | Type | Strongest video | Age |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | PRIORITY | 41 | 9 | 9 | 6 | 9 | 8 | explainer | [The honey in the pharaoh's tomb](https://youtu.be/…) · 2.1M | 12 d |

## Blocked or skipped
- #5 "Honey vs sugar": a reference channel posted it 9 days ago

## Dropped
- #6 "Bee dances" 21/50
```

- **`work/topics-result.json`** (việc online loại `topics`): `{"topics": [Topic…], "units": int, "stopped": null | "youtube_quota"}`.
- **Khoá:**
  - local: `~/.config/claude-utube/youtube.key` (quyền 600, ngoài repo), hoặc biến môi trường `YOUTUBE_API_KEY`;
  - online: `$STUDIO_DATA/secrets/youtube.key` (quyền 600).
