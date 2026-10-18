import assert from 'node:assert/strict';
import { test } from 'node:test';
import { acknowledgeSafety, canEnterGameplay, hasCurrentAcknowledgment, loadAcknowledgment,
  SAFETY_STORAGE_KEY, SAFETY_VERSION, stageAfterLocation } from '../src/lib/onboarding.ts';

test('missing, corrupt, old, and malformed acknowledgment never bypass safety', () => {
  for (const value of [null, '', 'bad', 'null', 'true', '[]', '{}', '{"version":0}', '{"version":"1"}']) {
    assert.equal(hasCurrentAcknowledgment(value), false);
  }
  assert.equal(hasCurrentAcknowledgment(JSON.stringify({ version: SAFETY_VERSION })), true);
});

test('a persisted acknowledgment is respected, while a storage read failure fails closed', async () => {
  const storage = { getItem: async () => JSON.stringify({ version: SAFETY_VERSION }), setItem: async () => {} };
  assert.equal((await loadAcknowledgment(storage)).acknowledged, true);
  const result = await loadAcknowledgment({ ...storage, getItem: async () => { throw new Error('unavailable'); } });
  assert.deepEqual(result, { acknowledged: false, persisted: false });
});

test('acknowledgment requires explicit agreement and stores no location or history', async () => {
  const writes: [string, string][] = [];
  const storage = { getItem: async () => null, setItem: async (k: string, v: string) => { writes.push([k, v]); } };
  await assert.rejects(acknowledgeSafety(storage, false), /Explicit/);
  assert.equal(writes.length, 0);
  assert.deepEqual(await acknowledgeSafety(storage, true), { acknowledged: true, persisted: true });
  assert.deepEqual(writes, [[SAFETY_STORAGE_KEY, JSON.stringify({ version: SAFETY_VERSION })]]);
});

test('storage write failure allows explicit agreement for this session only', async () => {
  const storage = { getItem: async () => null, setItem: async () => { throw new Error('full'); } };
  assert.deepEqual(await acknowledgeSafety(storage, true), { acknowledged: true, persisted: false });
  assert.equal((await loadAcknowledgment(storage)).acknowledged, false);
});

test('location grant or denial cannot bypass the mandatory safety gate', () => {
  assert.equal(stageAfterLocation(false), 'safety');
  assert.equal(stageAfterLocation(true), 'ready');
  for (const stage of ['loading', 'welcome', 'location', 'safety', 'ready'] as const) {
    assert.equal(canEnterGameplay(stage, false), false);
    assert.equal(canEnterGameplay(stage, true), stage === 'ready');
  }
});
