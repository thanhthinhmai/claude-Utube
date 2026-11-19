# Kit measurements (specs/028 T021)

Test reel: `kit/examples/try.html`, 15 shots, 56.8 s, rendered on the GPU (Intel UHD 730 through D3D12) with `sh bin/studio render kit-try --fps 30` in 71 s. Shot grammar: `kit/examples/three-min.html`, 50 shots, 180 s. Reference ranges come from `../EVIDENCE.md`.

| Measure | Kit | Reference channel | Tool | Result |
|---|---|---|---|---|
| Outline width, people in medium shots | 9 px of 1920 = 0.47% | 0.45–0.6% | `kit/tools/linewidth.py` on 5 frames | ✓ |
| Saturation, median of frames | 0.205 | 0.118 (0.067–0.317) | numpy on 13 frames | ✓ in range, above the median |
| still_ratio | 0.429 | 0.096–0.436 | `learn compare sketch-ref --clip` | ✓ |
| motion720_p50 | 0.151 | 0.107–0.392 | same | ✓ |
| moving_share | 1.0 | 0.932–1 | same | ✓ |
| Medium shots | 48% | 47% (SC-003: 40–55%) | `kit/tools/count.mjs` | ✓ |
| Longest run of one size | 2 | ≤ 4 | same | ✓ |
| Size change between shots | 88% | 66% | same | ✓ (more changes than the reference) |
| Sets in 3 minutes | 26 | 23.5 (SC-003: 20–28) | same | ✓ |
| Camera moves | push 28%, pull 30%, still 30%, follow 12% | push 33%, pull 23%, still 22%, follow 10–20% | same | close; inserts are always locked |
| Render time per frame | 16.5 ms (software, render + paint) | goal < 40 ms | page timing over 100 frames | ✓ |

First round (camera hold 30%, drift 30 px/s, faint idle motion): still_ratio 0.50, motion720_p50 0.026 and moving_share 0.893 were all outside the reference. The hold went to 20%, the drift to 60 px/s, idle head bob and breathing were made larger, and chapter cards creep closer. The second round passed all three.
