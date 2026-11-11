# Data Model: Chế độ Client (018)

## App Host: `config.json` (thêm)

`share`:
- `enabled` (bool), `port` (số, mặc định 47860), `hostId` (uuid);
- `clients`: `[{id, name (≤ 80), tokenHash, firstSeen, lastSeen, removed}]`.

Mã ghép đôi không lưu ở đây: nó chỉ nằm trong bộ nhớ, kèm hạn 10 phút và số lần sai.

`share-cert.json` (quyền 600): `{cert, key, fingerprint}`, do `app cert` tạo.

## App Client: `config.json`

- `mode`: `"host"` (mặc định, 015/016) hoặc `"client"`;
- `host`: `{address: "<ip hoặc tên>:<cổng>", fingerprint, hostId, clientId, token, pairedAt}`.
