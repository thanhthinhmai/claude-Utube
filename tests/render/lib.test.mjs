// Tests for tools/render/lib.mjs (specs/019 T005).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fingerprint, planChunks, isSoftware } from '../../tools/render/lib.mjs';

const film = () => {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'fp-'));
  fs.writeFileSync(path.join(d, 'index.html'), '<p>a</p>');
  fs.writeFileSync(path.join(d, 'timeline.json'), '{"dur":3}');
  fs.mkdirSync(path.join(d, 'out')); fs.mkdirSync(path.join(d, 'stills'));
  return d;
};

test('fingerprint is stable and ignores outputs', () => {
  const d = film();
  const a = fingerprint(d, 1920, 1080, 30);
  assert.equal(fingerprint(d, 1920, 1080, 30), a);
  fs.writeFileSync(path.join(d, 'out', 'video.mp4'), 'x');
  fs.writeFileSync(path.join(d, 'stills', 's.jpg'), 'x');
  fs.writeFileSync(path.join(d, 'render.log'), 'x');
  fs.writeFileSync(path.join(d, 'checks.json'), '{}');
  fs.writeFileSync(path.join(d, 'qc-exceptions.json'), '[]');   // specs/020 T002
  assert.equal(fingerprint(d, 1920, 1080, 30), a);
});

test('fingerprint changes with the source and the output shape', () => {
  const d = film();
  const a = fingerprint(d, 1920, 1080, 30);
  assert.notEqual(fingerprint(d, 1920, 1080, 24), a);
  assert.notEqual(fingerprint(d, 1280, 720, 30), a);
  assert.notEqual(fingerprint(d, 1920, 1080, 30, 10), a);
  fs.writeFileSync(path.join(d, 'timeline.json'), '{"dur":4}');
  const b = fingerprint(d, 1920, 1080, 30);
  assert.notEqual(b, a);
  fs.writeFileSync(path.join(d, 'index.html'), '<p>b</p>');
  assert.notEqual(fingerprint(d, 1920, 1080, 30), b);
});

test('planChunks covers every frame once', () => {
  for (const [N, S, n] of [[17153, 300, 58], [720, 240, 3], [30, 10, 3], [7, 10, 1]]) {
    const ch = planChunks(N, S);
    assert.equal(ch.length, n);
    let next = 0;
    for (const x of ch) { assert.equal(x.a, next); assert.ok(x.z > x.a && x.z - x.a <= S); next = x.z; }
    assert.equal(next, N);
  }
});

test('isSoftware on the renderers of research R1', () => {
  assert.equal(isSoftware('ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)'), true);
  assert.equal(isSoftware('ANGLE (Mesa, Vulkan 1.4.318 (llvmpipe (LLVM 20.1.2 256 bits) (0x00000000)), llvmpipe)'), true);
  assert.equal(isSoftware('ANGLE (Microsoft Corporation, D3D12 (Intel(R) UHD Graphics 730), OpenGL 4.1)'), false);
  assert.equal(isSoftware('ANGLE (Apple, ANGLE Metal Renderer: Apple M2, Unspecified Version)'), false);
  assert.equal(isSoftware(null), true);
});
