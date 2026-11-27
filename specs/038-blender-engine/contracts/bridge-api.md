# Bridge contract: Blender và lớp nhân vật AE

## Hàng đợi (`tools/ae/enginequeue.py`)

- Thư mục: `$STUDIO_DATA/<engine>/requests/<mã>/{request.json, bundle.tar, out/}`.
- `engine` ∈ {`ae`, `blender`}. Khoá, nhịp tim (60 s), `hello.json` (30 s) và giới hạn 500 MB giống specs/032.
- Tên kết quả hợp lệ:

| Engine | Tên |
|---|---|
| ae | `MASTER`, `S<n>`, và mới thêm `L<shot>-<char>-<view>` (tar của chuỗi PNG) |
| blender | `S<n>` (tar của khung PNG, hoặc mp4) |

## Đường gọi của phần lõi (khoá `x-cu-bridge`)

`/api/v1/blender/bridge/next | hello | <mã>/bundle | <mã>/progress | <mã>/result/<tên> | <mã>/finish`: cùng dạng với `/api/v1/ae/bridge/...`.

Proxy của việc: `POST /internal/blender/requests`, `GET /internal/blender/requests/<mã>`.

## `request.json` (Blender)

```json
{"id":"…","kind":"render|plan|plate|probe","film":"…","fps":24,"size":[1920,1080],
 "shots":[{"id":"S3","frames":72,"script":"blender/S3.py","layers":"layers/S3"}],"quarter":false}
```

## `log.txt`

Mỗi dòng một sự kiện:

```
START
GPU <renderer> <backend>
frame S3 12/72
shot S3 ok
ERR <code> <msg>
DONE
```

`code` ∈ {`gpu_software`, `script`, `missing_layer`, `timeout`}.

## Bundle AE loại `layers`

`entry.jsx` đặt `CU.MODE="layers"`, rồi `CU.layers(<layers.json>)` dựng mỗi (char, view) một comp trong suốt và đưa vào render queue với output module PNG Sequence RGB+Alpha.

Dòng log: `layer S3 hero 34 ok`.

## App desktop

- `blenderbridge.js` hỏi việc mỗi 5 s khi rảnh, gửi hello và nhịp tim mỗi 10 s, mỗi lúc một lượt.
- Chạy `<exe> -b --factory-startup -P <kit>/entry.py -- <request.json>`.
- `CU_FAKE_BLENDER=<script>` thay Blender khi test.
- In ra stdout:
  - `blender bridge ok`: khi hello được nhận
  - `blender build ok`: khi một lượt xong
