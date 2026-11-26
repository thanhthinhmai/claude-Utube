# Data model: 038

## Shot plan (trong `films/<tên>/film.json`)

```json
{
  "engine": "ae",
  "shots": ["S1", "S2", "S3"],
  "default_engine": "ae",
  "shot_plan": {
    "S3": {
      "engine": "blender",
      "suggested": "blender",
      "reason": "wide + dolly in a deep set",
      "size": "wide", "cam_height": "eye", "lens": "normal",
      "depth": "deep", "layers": ["fg", "mid", "bg"], "occluder": true,
      "move": "dolly", "set": "auditorium", "people": 40,
      "transition": "cut"
    }
  }
}
```

| Trường | Kiểu | Luật |
|---|---|---|
| `engine` | `ae` \| `blender` | Bắt buộc khi có mục. Shot vắng mục thì dùng `default_engine`. |
| `suggested`, `reason` | chuỗi | Do `ae plan --suggest` ghi. Không bao giờ ghi đè `engine` mà người dùng đã đặt. |
| `size` | ecu/cu/med/wide/huge/insert | Như labeler 021. |
| `cam_height` | low/eye/high/top | |
| `lens` | wide/normal/long | Blender dùng tiêu cự 18 / 35 / 85 mm (khung 36 mm). |
| `depth` | shallow/mid/deep | |
| `layers` | tập con của fg/mid/bg/far | |
| `occluder` | bool | |
| `move` | static/push/pull/pan/dolly/orbit/track/crane | |
| `set` | tên bối cảnh của bộ dựng | Shot Blender bắt buộc có. |
| `transition` | cut/fade/dip | Fade và dip giữa hai bộ máy do ffmpeg làm lúc ghép. |

Kiểm khi đọc:
- mã shot phải có trong `shots`
- giá trị phải nằm trong danh sách trên
- shot Blender phải có `films/<tên>/blender/<id>.py`

Sai thì thoát mã 2.

## Shot marks (`shots.json` cạnh video)

Giữ định dạng của specs/029, thêm hai khoá:

```json
{"version":1,"video":"render.mp4","duration":30.0,"fps":24,"source":"mixed",
 "shots":[[0,2.5,"classroom","S1"],[2.5,5.0,"auditorium","S2"]],
 "engines":{"S1":{"engine":"ae","version":"a1b2"},"S2":{"engine":"blender","version":"c3d4","gpu":"Intel(R) UHD Graphics 730"}}}
```

`version` là dấu vân tay của các tệp tạo ra shot:
- **Shot AE**: jsx của shot cùng các hàm dùng chung mà shot gọi.
- **Shot Blender**: script shot, các tệp của bộ dựng mà shot dùng, `layers.json` của shot và sha của rig.

Rig hay động tác đổi thì `version` đổi, và `ae status` ghi "Must run again" (FR-016).

## Layers plan (`films/<tên>/out/layers/<shot>/layers.json`)

```json
{"shot":"S2","fps":24,"frames":72,
 "chars":[{"id":"hero","rig":"ball@1","height_px":620,
   "views":["front","34"],
   "track":[{"f":0,"view":"34","dir":1,"pose":"down","expr":"smile","walk":true}, {"f":40,"view":"front","dir":1,"pose":"wave","expr":"grin","walk":false}],
   "card_angle_max":38}],
 "crowd":{"pool":["kid1","kid2","kid3","kid4"],"actions":["sit","clap"],"count":40}}
```

- `track` ghi mỗi lần đổi trạng thái; các khung giữa hai mốc giữ trạng thái của mốc trước.
- Đầu ra của AE nằm ở `out/layers/<shot>/<char>-<view>/f0001.png…`.
- `card_angle_max` lớn hơn 75 thì luật `card_angle` báo.

## Style depth block (`my-styles/<slug>/shots.json` → `depth`)

```json
"depth": {"version":1,"by_size":{
  "wide":{"n":42,"cam_height":{"eye":0.6,"high":0.3,"low":0.1},"lens":{"wide":0.5,"normal":0.45,"long":0.05},
          "depth":{"deep":0.7,"mid":0.3},"layers_p25":2,"layers_p50":3,"occluder_share":0.4,
          "evidence":["vid3:S12","vid7:S4"]}}}
```

## Depth result (`checks.json` → `tiers.depth`)

```json
{"fingerprint":"…","ok":false,
 "issues":[{"shot":"S5","rule":"depth_shallow","have":{"layers":1},"want":{"layers_p25":2},"fix":"add a foreground occluder or a far wall"}],
 "warnings":[{"rule":"size_share","size":"cu","have":0.42,"want":0.25}]}
```

Miễn theo shot: `qc-exceptions.json` `[{shot, rule, reason, at, by:"user"}]`. Khi biến `STUDIO_JOB` có mặt thì lệnh từ chối ghi.

## Blender config (`~/.config/claude-utube/blender.json`)

`{"blender": "E:\\tools\\blender-5.2.5-windows-x64\\blender.exe", "work": "/mnt/e/claude-utube-ae/blender", "shotTimeoutSec": 3600, "secPerFrame": 5.5}`

## Trạng thái một shot Blender

`planned` → `layers_ready` (có nhân vật thì cần lượt AE) → `rendering` (khung PNG dựng dần, ngắt thì tiếp) → `done` (có `S<n>.mp4` và `version`) → `stale` (sửa tệp nguồn).

Lỗi `gpu_software` hoặc `no_blender` thì dừng ở trạng thái hiện tại và báo rõ, không chuyển sang AE.
