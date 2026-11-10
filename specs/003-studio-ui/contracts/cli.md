# Contract: lệnh CLI

Chạy bằng `sh bin/studio …` (dùng `tools/.venv`). Chưa cài thì báo `sh bin/studio deps ui` và thoát mã 1.

## `deps ui`
Cài `tools/requirements-ui.txt` vào `tools/.venv` (tạo venv nếu chưa có). Chạy lại không cài lại khi danh sách không đổi.

## `ui [open|status|stop]`
- `open` (mặc định): bật nền nếu chưa chạy, in `URL: http://localhost:<port>/`. Mã 0; không bật được → mã 1 kèm lý do (ví dụ hết cổng 8787–8799).
- `status`: in đang chạy hay không, cổng, pid. Mã 0 nếu đang chạy, 1 nếu không.
- `stop`: tắt máy chủ của xưởng (chỉ khi `pid` trong `server.json` đúng là máy chủ của xưởng). Mã 0.

## `job`
| Lệnh | Việc làm | In ra / mã |
|---|---|---|
| `job start --kind learn\|film --name N [--set S] [--film F]` | tạo việc `running`, bật giao diện nền | dòng 1: mã việc; dòng 2: `URL: …/#/jobs/<id>`; mã 0 |
| `job step <id> "<bước>" [--progress d/t]` | đổi bước, cập nhật `updated_at`, thêm dòng nhật ký | mã 0 · 2 nếu `progress` sai |
| `job log <id> "<dòng>"` | thêm nhật ký | mã 0 |
| `job run <id> [--step "<bước>"] -- <lệnh…>` | chạy lệnh, nhịp sống 30 s, 50 dòng cuối vào nhật ký (bỏ dòng `[note] …` và dòng lặp liền nhau; `--step` trùng bước hiện tại không ghi thêm dòng) | mã thoát của lệnh con |
| `job done <id> [--style S] [--film F]` · `job fail <id> "<lỗi>"` · `job stop <id>` | trạng thái cuối | mã 0 |
| `job show <id>` | JSON của việc | mã 0 · 1 nếu không có |

Mã việc sai hoặc không có → mã 1.

## `review`
| Lệnh | Việc làm | In ra / mã |
|---|---|---|
| `review request <job> --kind style-1\|style-2 --set S --summary <file.md> [--final-round]` | tạo yêu cầu; `style-2` tự đọc `references/S/proof/compare.json`; việc → `waiting_review` | dòng 1: mã duyệt; dòng 2: `URL: …/#/reviews/<id>`; mã 0 |
| `review wait <id> [--timeout 540]` | chặn, hỏi mỗi 1 s | có quyết định: JSON quyết định, mã 0 (việc → `running`) · hết giờ: mã 3 |
| `review decide <id> --value approve\|revise\|accept_anyway\|stop [--note "…"] --source chat` | ghi quyết định từ khung chat | mã 0 · 4 nếu đã có quyết định · 2 nếu thiếu góp ý hay giá trị không hợp lệ |
| `review status <id>` | JSON yêu cầu và quyết định | mã 0 |

## Chế độ online (specs/007)
Khi có `STUDIO_MODE=online` và `STUDIO_JOB=<mã việc>` (tức là đang chạy trong container việc), các lệnh `job` và `review` không ghi `.studio/`. Thay vào đó, chúng gọi bộ chuyển tiếp ở `$STUDIO_PROXY/internal/…` bằng `ANTHROPIC_API_KEY` của việc (contracts/runner.md của 007).

| Lệnh | Khác ở chế độ online |
|---|---|
| `job start` | Bị từ chối (mã 2): việc đã có sẵn trong `STUDIO_JOB` |
| `job step`, `log`, `run` | Như trên, nhưng chỉ cho đúng việc trong `STUDIO_JOB`. `job run` gửi nhịp sống bằng cách ghi lại cùng tên bước |
| `job done <id> [--film F] [--style S]` | Chỉ báo xong. Worker kiểm chất lượng (−14 ±1 LUFS, đỉnh ≤ −1 dB, readcheck) rồi mới giao cho khách |
| `job fail <id> "<lỗi>" [--by studio\|customer]` | `--by` chỉ có ở online, mặc định `studio`. Lỗi do xưởng thì khách được trả lượt (FR-006a) |
| `review request <id> --kind question\|treatment\|style-1\|style-2 [--set S] --summary <f>` | `--set` chỉ bắt buộc với `style-1` và `style-2`. Mỗi phim hỏi tối đa 3 câu (`question`). Lệnh ghi `.review_pending`, rồi tác tử kết thúc lượt bằng mã thoát 10 |
| `review wait` | Không chờ: in "kết thúc lượt: thoát mã 10" rồi thoát mã 10 |
| `review status <id>` | Đọc qua bộ chuyển tiếp |

Lệnh `admin create <email>` cũng chỉ dùng ở chế độ online. Lệnh này tạo tài khoản quản trị duy nhất; nếu đã có thì báo lỗi, mã 1.
