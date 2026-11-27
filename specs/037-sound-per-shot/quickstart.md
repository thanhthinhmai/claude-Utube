# Quickstart: kiểm chứng 037

## Điều kiện

- Worktree `~/claude-Utube-037`, `tools/.venv` và `lib/lemo-opuscar/.venv` như các tính năng trước.
- Học tiếng: `sh bin/studio deps sound` (torch CPU, demucs, transformers). Mô hình htdemucs, AST, CLAP đã có trong `~/.cache/huggingface/hub`.
- Kho thật: gói Sonniss GDC 2026 + 2024 do người dùng tải bằng trình duyệt vào `E:\SoundLibrary\Sonniss` (`/mnt/e/SoundLibrary/Sonniss`). Chưa có thì dùng kho thử do `tests/filmcheck/soundfix.py` tổng hợp (có metadata kiểu UCS).
- Freesound: khoá miễn phí của người dùng trong `.env` (`FREESOUND_API_KEY`). Không có thì bỏ bước 3.

## 1. Bộ test tự động

```sh
sh tests/run.sh && sh tests/filmcheck/run.sh && sh tests/learn/run.sh && sh tests/ui/run.sh && sh tests/online/run.sh && sh tests/ae/run.sh
```
Các test mới: `tests/filmcheck/test_soundlib.py`, `test_soundplan.py`, `test_soundmix.py`, `test_freesound.py` (máy chủ giả), `tests/learn/test_sfxlearn.py` (phân loại giả), `tests/online/test_sound_scope.py`, `tests/ui/test_sound_api.py`, `tests/ui/browser_sound.cjs`.

## 2. Kho tiếng (US2, SC-007)

```sh
sh bin/studio sound lib add /mnt/e/SoundLibrary/Sonniss
sh bin/studio sound lib index          # lần 2: ≤ 1 phút, "0 new"
sh bin/studio sound lib search "glass shatter" --cat GLASS
```
Kỳ vọng: số mục = số tệp âm thanh đọc được; lần đầu ≤ 15 phút cho 10.000 tệp; `git status` sạch.

Kết quả đo (2026-11-26, kho thật `/mnt/e/SoundLibrary/Sonniss`, ổ E: qua WSL, 956 tệp âm thanh, 0 zip): `index --full` 31,3 s (≈ 33 ms/tệp, suy ra ≈ 5,5 phút cho 10.000 tệp, đạt ≤ 15 phút); `index` lần 2 2,0 s, "0 new" (đạt ≤ 1 phút); `git status` sạch. SC-007 đạt theo suy ra, chưa đo trên đủ 10.000 tệp.

## 3. Freesound CC0 (US2, SC-004)

```sh
sh bin/studio sound lib search "aquarium bubbles office" --scope cc0
```
Kỳ vọng: nếu kho thiếu → tải 1 tiếng CC0 vào `$STUDIO_DATA/sound/freesound/`, mục có `license cc0-1.0`, `url`.

## 4. Tiếng theo shot trên phim thử (US1, SC-001, SC-002, SC-009) — cần 035 đã merge

1. `ae-sleepless-test` có `timing.json`, `animatic/keys.json`, Animatic đã duyệt.
2. Chạy bước Sound (việc làm phim hoặc `sound cue add …` theo hướng dẫn `tools/ae/SOUND.md`), rồi `sh bin/studio sound mix ae-sleepless-test`.
3. `sound plan ae-sleepless-test --json`: mỗi cue `placed` lệch ≤ 1 khung so với mốc chuyển động trong `keys.json`; ≥ 90% chuyển động có tên có tiếng khi kho có tiếng hợp.
4. `animatic accept ae-sleepless-test S2` rồi `sound mix`: mọi `at` đổi đúng theo `t0` mới; cue mất có `why`.
5. Bước kiểm phim trên `out/mix.wav`: độ lớn, giọng nổi trên nền, phần trăm lặng không kém bản trộn viết tay cũ (so `checks.json` trước/sau).
6. `films/ae-sleepless-test/CREDITS` có một dòng cho mỗi tiếng đã dùng.

### Kết quả bước 4 (2026-11-26, T031, sau khi 035 merge)
- Animatic đã duyệt; bản nháp dựng lại với `keys.json` có tên chuyển động của rig (T059, trước đó 6/9 tiếng bị bỏ vì `CTRL · Point`). 9 tiếng Claude đặt từ hôm trước, neo lại theo mốc trong code shot (S1 mắt 0,55 s; S6 xem đồng hồ 2,3 s; S7 kid0 ngáp 0,3 s, nhân vật giơ tay 2,15→2,4 s).
- **SC-001: đạt một phần.** Lệch so với mốc chuyển động: 0 khung cho cả 5 tiếng neo chuyển động đã đặt (100% ≤ 1 khung). Phủ: 8/9 hành động có tiếng (89%, ngưỡng 90%): "eyes pop open" bị luật mật độ bỏ (phim 24,6 s cho tối đa 5 tiếng điểm; tiếng này nhỏ nhất), không phải vì thiếu tiếng trong kho.
- **SC-002: đạt.** Trên bản sao, S2 103 → 93 khung: mọi mốc sau S2 lùi đúng 10 khung (0 lệch), S1–S2 giữ nguyên, không sửa tay; tiếng bị bỏ đều có `why`.
- **SC-009: đạt.** `qc final` trên bản trộn mới: lặng 22% (bằng bản cũ, theo lời), không cảnh báo mới, LRA 4,2 LU (cũ 2,5); độ lớn −13,6 LUFS, đỉnh −2,5 dBFS (cũ −13,2 / −3,1); giọng cao hơn nền +6,3 dB khi đang nói (đo bằng stems, numpy, không mô hình).
- CREDITS: 8 dòng Sonniss cho 8 tiếng đã dùng (tiếng bị bỏ không ghi).

## 5. Trang Sound (US3, SC-006, SC-008)

Mở app → việc của phim → bước Sound: bấm S1 phát clip nháp với bản trộn; đổi tiếng sang gợi ý thứ 2, dời một tiếng 5 khung, xoá một tiếng. Kỳ vọng: bản trộn mới ≤ 30 s; ngoài [mốc − 60 ms, cuối + 60 ms] giống hệt từng mẫu (`tests/ui/browser_sound.cjs` đo bằng `stems`). `ae render` trước khi duyệt Sound → mã 3 kèm lý do.

### Kết quả bước 5 (2026-11-26, T048)
Trên bản sao phim trong web app (việc `job start` + `review request --kind mix`, sửa qua `/jobs/{id}/actions` như trang):
- **SC-006: đạt.** Đổi tiếng c03 sang gợi ý thứ 2: 6,6 s; dời c07 5 khung: 5,5 s; xoá c08: 5,5 s (ngưỡng 30 s). Ngoài đoạn sửa [mốc − 60 ms, hết tiếng + 60 ms] (hết tiếng = min(mốc + độ dài tệp, chỗ cắt + fade)): **0 mẫu khác** cả ba lần; độ dài bản trộn không đổi.
- **SC-008: đạt.** Bật điểm Sound, chưa duyệt: `ae render` → mã 3 "the mix review is not approved …", AE không chạy.
- Chưa chạy lượt "Send notes to Claude" thật (không thuộc bước 5; có test `tests/online/test_sound_fix_job.py`).

## 6. Học tiếng trên mẫu đã kiểm (US4, SC-003)

```sh
sh bin/studio learn sfx --file references/voice-check/a.wav --words references/voice-check/segs.json
```
Kỳ vọng: 5/5 sự kiện của `tests/learn/data/voicecheck_expect.json` (kính vỡ ~"window", lặng ≤ −50 dB ở "goes silent", đám đông ở "people cheer" tắt ≤ 0,1 s quanh điểm cắt, bóng, bọt nước) có `agree: true`, mốc lệch ≤ 0,25 s; không sự kiện `agree: false` nào được dùng làm luật. Sau đó `git status` không có tệp âm thanh mới; `references/voice-check/stems/` chỉ trên máy.

### Kết quả (2026-11-26)
Chạy thật trên máy (CPU, tách lớp đã có cache, ~14 phút cho 724 sự kiện). SC-003: **2/5, chưa đạt**. Tìm thấy: lặng, bóng. Trượt: kính vỡ (nghe thành tiếng kim loại), bọt nước và đám đông (có nhãn đúng nhưng mốc lệch 0,18 s và 0,54 s ra ngoài cửa sổ). Chi tiết và hướng chỉnh ở research R8.

Sau chỉnh (bỏ "AST thắng", AST nghe đúng lớp, luật lặng mới): voice-check **3/5** (thêm bọt nước). Bài chấm khớp hình bằng 9 tiếng Freesound CC0 trên bản sao `ae-sleepless-test`: ~1,5/9 tiếng (đồng hồ `sure` đúng), 1/2 khoảng lặng (khoảng giữa phim sau "guitar" tìm đúng; khoảng ở S9 nằm sát cuối phim nên không tách được khỏi đoạn im cuối tệp). SC-003 chưa đạt; người dùng chọn hướng A (chỉ `sure` là luật, `likely` là gợi ý; Claude chọn tiếng theo hình).
