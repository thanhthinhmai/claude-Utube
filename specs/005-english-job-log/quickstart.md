# Quickstart: kiểm tra 005

## Tự động

```sh
sh tests/ui/run.sh
sh tests/run.sh
sh tests/learn/run.sh
```

Cả ba đều đạt; test đủ vòng mới trong `tests/ui/test_cli_events.py` kiểm SC-001.

## Bằng tay (tuỳ chọn)

```sh
JOB=$(sh bin/studio job start --kind film --name demo | head -1)
sh bin/studio job step $JOB "Music"
sh bin/studio job run $JOB --step "Render" -- sh -c 'echo hello; exit 0'
sh bin/studio job done $JOB
sh bin/studio job show $JOB
```

Kết quả mong đợi: nhật ký có `Job started`, `Music`, `Render`, `hello`, `(command exited with code 0)`, `Done`; bước hiện tại là `Done`. Mở trang việc trên giao diện: mọi chữ đều bằng tiếng Anh.

## Tài liệu (SC-002)

```sh
grep -n 'job step\|--step' CLAUDE.md .claude/skills/style-learn/SKILL.md
```

Mọi tên bước nằm trong danh sách chuẩn của FR-002 và FR-003.
