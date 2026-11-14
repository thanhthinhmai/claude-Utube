# Quickstart: kiểm chứng 023

Điều kiện chung:
- `sh bin/studio status` sẵn sàng; `sh bin/studio deps learn --extra` (có yt-dlp, faster-whisper);
- có GPU (`status` có dòng `dựng hình`), dựng bằng phần mềm thì dừng và hỏi;
- có nhạc cụ mẫu của thư viện (`sh bin/studio deps music`).

## 0. Test tự động (mỗi giai đoạn)

```sh
sh tests/learn/run.sh       # craft.py trên video thử tổng hợp (SC-003), sound, beats, template-check, pairs, refetch ghép độ dài
sh tests/filmcheck/run.sh   # still_person, style_* mới, mispronounced, voice make (.say.json)
sh tests/render/run.sh      # kit v2: act/move/trans/frame, tất định khi gọi đảo thứ tự, CAST/MOVES
sh tests/run.sh && sh tests/ui/run.sh
```

**Kỳ vọng**: tất cả đạt. Test SC-003 in tỉ lệ đúng (≥ 90%) cho cử động, loại máy, chuyển cảnh, và độ lệch thời điểm (≤ 0,2 s).

## 1. US1: template phần hình và rà `STYLE.md` (không cần video)

```sh
sh bin/studio learn craft-summary dusk-hypothetical-3    # phần bố cục, độ sâu, ánh sáng từ shots.json và shot-sheets
sh bin/studio learn template-check dusk-hypothetical
sh bin/studio learn check-names dusk-hypothetical-3 my-styles/dusk-hypothetical/TEMPLATE.md my-styles/dusk-hypothetical/STYLE.md
```

**Kỳ vọng**:
- mục 1–10 của `TEMPLATE.md` qua `template-check`;
- 0 luật thiếu nhãn trong `STYLE.md` (SC-001);
- luật phụ đề mang `[xưởng]`.

Còn thiếu mục 11–15 và công thức nhịp, vì chúng cần US2.

## 2. US2: học phần theo thời gian (tải lại, rồi xoá)

```sh
sh bin/studio learn refetch dusk-hypothetical-3 --videos <10 URL>   # ghép 10/10 với v01–v10
sh bin/studio learn transcribe dusk-hypothetical-3
sh bin/studio learn craft dusk-hypothetical-3 --strips 80
sh bin/studio learn sound dusk-hypothetical-3
# Claude: đọc lời, ghi profile/beats.json; đọc dải, viết bảng diễn xuất; trích bằng chứng bằng learn evidence
sh bin/studio learn beats dusk-hypothetical-3 --check
sh bin/studio learn craft-summary dusk-hypothetical-3
sh bin/studio learn clean dusk-hypothetical-3
sh bin/studio learn template-check dusk-hypothetical
```

**Kỳ vọng**:
- `refetch` ghép đủ 10 video (hoặc báo rõ video nào không còn);
- `craft-summary` có `still_ratio` khớp số cũ (0,72–0,93, lệch ≤ 0,02 mỗi video);
- `template-check` đạt đủ 15 mục và 9 nhịp (SC-002);
- sau `clean`: `find references/dusk-hypothetical-3 -name '*.mp4' -o -name '*.wav' -o -name '*.m4a'` ra rỗng (SC-007).

## 3. US3: bộ dựng v2 và 4 đợt duyệt

Với từng đợt (1 nhân vật, 2 khung hình, 3 đồ hoạ, 4 chuyển động và âm thanh):

```sh
sh bin/studio kit use kit-proof --update                       # phim thử nội bộ chỉ để chụp thành phần
sh bin/studio page still kit-proof <t…> --size 1280x720
sh bin/studio page clip kit-proof --from 2 --to 6               # thành phần có chuyển động
sh bin/studio learn pairs dusk-hypothetical-3 --batch 1 --component face --ours <ảnh…> --ref <bằng chứng…>
```

**Kỳ vọng**:
- mỗi thành phần có bảng so ≥ 3 cặp;
- thành phần có chuyển động có thêm mp4 và số đo hai bên;
- người dùng duyệt, ghi vào `kit/REVIEW.md`;
- đợt sau chỉ bắt đầu khi đợt trước được duyệt (SC-004).

## 4. US4: tầng kiểm trên phim cũ

**Trước khi chép kit mới vào `films/hundred-words`**, chạy trên bản kit cũ còn trong phim:

```sh
sh bin/studio qc shots hundred-words
sh bin/studio qc hundred-words
```

**Kỳ vọng**:
- `still_person` báo ≥ 15/21 cảnh;
- `style_still_ratio` hoặc `style_motion720` báo ngoài khoảng (SC-005, nửa đầu).

Chụp khung cũ cho bảng so ba cột rồi mới chép kit mới.

## 5. US5: dựng lại phim thử

```sh
sh bin/studio kit use hundred-words --update
sh bin/studio voice make hundred-words && sh bin/studio voice asr hundred-words && sh bin/studio qc voice hundred-words
sh bin/studio qc plan hundred-words && sh bin/studio qc shots hundred-words
sh bin/studio render hundred-words --fps 60
sh bin/studio qc hundred-words
```

**Kỳ vọng**:
- `qc voice` không còn `mispronounced` ("hurt" có `say`);
- 0 `still_person`;
- `still_ratio` và `motion720_p50` trong khoảng (SC-005, nửa sau);
- dựng trên GPU, 60 fps;
- có `films/hundred-words/compare/` gồm bảng ba cột cho từng loại cảnh và `before-after.json`;
- người dùng xem và chấp nhận (SC-006).

## Kết quả

(ghi sau khi chạy: đạt, đạt một phần hoặc thất bại, kèm số)
