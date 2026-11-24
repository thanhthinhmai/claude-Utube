# Phim After Effects: tệp

```text
films/<tên>/
├── film.json            # engine "ae", fps, size, shots, ae_files, audio  (data-model.md)
├── ae/shots_*.jsx       # chỉ hàm CU.shot<n> và hàm riêng của phim; KHÔNG chép kit/
├── <tên>.mp4, shots.json, shot-notes.json …   # như spec 029
└── out/                 # bản tổng, shot dựng lại, fix.mp4
```

Bộ dựng chung `tools/ae/kit/`: `lib.jsx` (hình, chữ, phím, máy quay), `chars.jsx` (nhân vật), `scene.jsx` (luật dàn cảnh), `persp.jsx` (chiều sâu), `build_core.jsx` (dựng danh sách shot thành MASTER, ghi mốc shot, `CU.WORK`). Gói của một yêu cầu: `kit/*.jsx` + `ae/*.jsx` theo `ae_files` + `entry.jsx` (đặt `CU.WORK`, `CU.PROJ`, gọi `CU.build([...])`, ghi `log.txt`: `START`, `CHECK …`, `DONE`).

Phim tập luyện `ae-crayon-test`: `shots_a…shots_e3.jsx` giữ lại; `lib/chars/scene/persp/build_core.jsx`, `run.sh`, `fixshots.sh`, `build_*.jsx` chuyển vào hoặc được thay bằng `tools/ae/`; đường dẫn `E:\…` thay bằng `CU.WORK`.
