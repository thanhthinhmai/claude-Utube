// specs/027 T009, T010: items stay in the hand, acts are pure functions of time, hand-overs have one moment.
import test from 'node:test';
import assert from 'node:assert/strict';
import { joints, itemAt, makeItem, makeFigure, ITEMS, GRIP, ACT_LEN, ACT_BACK, POSES } from '../figure.js';
import { bodyAct, handoff, throwPath, RELEASE, BACK } from '../acting.js';
import { kindOf, parseAct, actOk, CATALOG } from '../plan.js';

const NEW_ACTS = ['run', 'jump', 'throw', 'carry', 'fall', 'push', 'type', 'give', 'high-five'];
const times = (n, end) => Array.from({ length: n }, (_, i) => (i * end) / (n - 1));

test('every catalogue item has a grip, a size and a model', () => {
  for (const [name, it] of Object.entries(CATALOG.items)) {
    assert.ok(['one', 'both'].includes(it.grip), name);
    assert.ok(it.size > 0, name);
    assert.equal(GRIP[name] === 'one' ? 'one' : 'both', it.grip, `${name}: figure.js GRIP and catalog.json agree`);
    assert.ok(ITEMS.includes(name), name);
    assert.ok(makeItem(name).children.length > 0, name);
  }
  assert.ok(Object.keys(CATALOG.items).length >= 8);                       // FR-001
});

test('a one-hand item stays within 0.05 of its hand through every act', () => {
  for (const act of NEW_ACTS.filter((a) => POSES[a])) for (const t of times(20, ACT_LEN[act] + ACT_BACK)) {
    const j = joints(act, t);
    for (const item of ['ball', 'cards', 'cash', 'keys']) for (const hand of ['right', 'left']) {
      const p = itemAt(j, item, hand), h = j.arms[hand === 'left' ? -1 : 1].hand;
      assert.ok(p.distanceTo(h) <= 0.06, `${act} ${item} ${hand} t=${t.toFixed(2)}: ${p.distanceTo(h).toFixed(3)}`);
    }
    const both = itemAt(j, 'box'), mid = j.arms[-1].hand.clone().add(j.arms[1].hand).multiplyScalar(0.5);
    assert.ok(both.distanceTo(mid) < 0.15, `${act} box between the hands`);
  }
});

test('a figure shows the item in the named hand', () => {
  const f = makeFigure();
  f.pose('stand', 0, { hold: 'ball', hand: 'left' });
  assert.ok(f.items.ball.visible);
  assert.ok(f.items.ball.position.distanceTo(f.joints.arms[-1].hand) < 0.06);
  f.pose('stand', 0, { hold: null });
  assert.ok(!f.items.ball.visible);
});

test('acts are pure: the same time gives the same joints in any order', () => {
  for (const act of NEW_ACTS) {
    const ts = times(9, 1.5), a = ts.map((t) => joints(act, t).arms[1].hand.toArray());
    const b = [...ts].reverse().map((t) => joints(act, t).arms[1].hand.toArray()).reverse();
    assert.deepEqual(a, b, act);
  }
});

test('one-shot acts start and end at the standing pose (no jump), fall stays down', () => {
  const stand = joints('stand', 0);
  for (const act of ['jump', 'throw', 'give', 'high-five']) {
    const end = joints(act, ACT_LEN[act] + ACT_BACK + 0.01);
    for (const sx of [-1, 1]) assert.ok(end.arms[sx].hand.distanceTo(stand.arms[sx].hand) < 0.03, `${act} hand back at rest`);
    assert.ok(Math.abs(end.lift - stand.lift) < 0.01, `${act} legs back`);
  }
  assert.ok(joints('fall', 5).lift < 0.2, 'fall ends on the ground');
});

test('kinds: old acts and prefixes are gestures, new ones body or pair (R5)', () => {
  for (const a of ['raise-hand', 'wave', 'point', 'shrug-up', 'hands-face', 'cheer', 'lean-in', 'nod', 'tilt-head', 'swap', 'face:happy', 'look:left', 'pose:cheer'])
    assert.equal(kindOf(a), 'gesture', a);
  for (const a of ['run', 'jump', 'throw', 'carry', 'fall', 'push', 'type', 'pose:run', 'throw:ball']) assert.equal(kindOf(a), 'body', a);
  assert.equal(kindOf('give:cash@1'), 'pair');
  assert.equal(kindOf('high-five@1'), 'pair');
  assert.ok(NEW_ACTS.filter((a) => CATALOG.act_kinds[a].kind === 'body').length >= 7);   // FR-002
});

test('a one-shot act reads in at most 1.5 s (US1 scenario 1), lengths match the figure', () => {
  for (const [name, k] of Object.entries(CATALOG.act_kinds)) {
    if (k.kind === 'gesture') continue;
    if (!k.loop) assert.ok(k.dur <= 1.5, `${name} ${k.dur}`);
    assert.equal(ACT_LEN[name], k.dur, `${name}: figure.js ACT_LEN = catalog dur`);
  }
});

test('act names with item and partner', () => {
  assert.deepEqual(parseAct('give:cash@1'), { base: 'give', item: 'cash', who: 1, prefix: null });
  assert.ok(actOk('throw:ball') && actOk('high-five@0') && actOk('face:wow'));
  assert.ok(!actOk('throw:piano') && !actOk('give:cash@x') && !actOk('face:wow@1'));
});

test('bodyAct: one-shot ends after its length and the way back, loops and holds go on', () => {
  assert.equal(bodyAct([[0.5, 'jump']], 0.4), null);
  assert.equal(bodyAct([[0.5, 'jump']], 1.0).name, 'jump');
  assert.equal(bodyAct([[0.5, 'jump']], 0.5 + 0.9 + BACK + 0.01), null);
  assert.equal(bodyAct([[0.2, 'run']], 30).name, 'run');
  assert.equal(bodyAct([[0.2, 'fall']], 30).name, 'fall');
  assert.equal(bodyAct([[0.2, 'run'], [1, 'nod']], 2).name, 'run');          // a gesture does not stop it
  assert.equal(bodyAct([[0.2, 'carry']], 1).item, 'box');
  assert.equal(bodyAct([[0.2, 'give:keys@1']], 0.5).item, 'keys');
});

test('a hand-over has exactly one moment', () => {
  const ts = times(101, 2), who = ts.map((t) => handoff(t, 0.4, 1.0));
  let changes = 0;
  for (let i = 1; i < who.length; i++) if (who[i] !== who[i - 1]) changes++;
  assert.equal(changes, 1);
  assert.equal(handoff(0.89, 0.4, 1.0), 'giver');
  assert.equal(handoff(0.9, 0.4, 1.0), 'taker');
});

test('a throw is continuous from the hand to the landing', () => {
  const from = [0, 1.2, 0], to = [0, 0.12, 4];
  let prev = null;
  for (const t of times(200, 2)) {
    const p = throwPath(t, 0.3, from, to).p;
    if (prev) assert.ok(Math.hypot(p[0] - prev[0], p[1] - prev[1], p[2] - prev[2]) < 0.2, `jump at ${t}`);
    prev = p;
  }
  assert.equal(throwPath(0.3 + RELEASE - 0.01, 0.3, from, to).state, 'hand');
  assert.equal(throwPath(5, 0.3, from, to).state, 'ground');
  assert.ok(throwPath(0.3 + RELEASE + 0.35, 0.3, from, to).p[1] > 1.3, 'it flies up first');
});
