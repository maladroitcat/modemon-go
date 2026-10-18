import assert from 'node:assert/strict';
import { test } from 'node:test';
import { foregroundPermission, startForegroundWatch, validPosition } from '../src/lib/location.ts';
import type { Permission, Position } from '../src/lib/location.ts';

const flush = () => new Promise<void>((resolve) => setImmediate(resolve));
const granted: Permission = { status: 'granted', canAskAgain: true };

test('existing foreground permission is never requested again', async () => {
  let requests = 0;
  const api = { getForegroundPermissionsAsync: async () => granted,
    requestForegroundPermissionsAsync: async () => { requests++; return granted; } };
  assert.deepEqual(await foregroundPermission(api, true), granted);
  assert.equal(requests, 0);
});

test('foreground permission is requested only by an explicit user action', async () => {
  let requests = 0;
  const api = { getForegroundPermissionsAsync: async (): Promise<Permission> => ({ status: 'undetermined', canAskAgain: true }),
    requestForegroundPermissionsAsync: async () => { requests++; return granted; } };
  assert.equal((await foregroundPermission(api)).status, 'undetermined');
  assert.equal(requests, 0);
  assert.equal((await foregroundPermission(api, true)).status, 'granted');
  assert.equal(requests, 1);
});

test('blocked permission does not prompt again; denial remains a supported state', async () => {
  let requests = 0;
  const denied: Permission = { status: 'denied', canAskAgain: false };
  const api = { getForegroundPermissionsAsync: async () => denied,
    requestForegroundPermissionsAsync: async () => { requests++; return granted; } };
  assert.deepEqual(await foregroundPermission(api, true), denied);
  assert.equal(requests, 0);
});

test('location permission API failures are recoverable', async () => {
  const api = { getForegroundPermissionsAsync: async (): Promise<Permission> => { throw new Error('unsupported'); },
    requestForegroundPermissionsAsync: async () => granted };
  assert.equal((await foregroundPermission(api)).status, 'unavailable');
});

test('disabled location services do not start a watcher', async () => {
  let watches = 0, errors = 0;
  const stop = startForegroundWatch({ hasServicesEnabledAsync: async () => false,
    watch: async () => { watches++; return { remove() {} }; } }, () => {}, () => { errors++; });
  await flush();
  stop();
  assert.equal(watches, 0);
  assert.equal(errors, 1);
});

test('stopping while watch creation is pending removes the late subscription', async () => {
  let resolveWatch!: (value: { remove: () => void }) => void;
  let removals = 0;
  const stop = startForegroundWatch({ hasServicesEnabledAsync: async () => true,
    watch: () => new Promise((resolve) => { resolveWatch = resolve; }) }, () => {}, () => {});
  await flush();
  stop();
  resolveWatch({ remove: () => { removals++; } });
  await flush();
  assert.equal(removals, 1);
});

test('stopped watchers do not deliver a later fix', async () => {
  let deliver!: (fix: Position) => void;
  const fixes: Position[] = [];
  const stop = startForegroundWatch({ hasServicesEnabledAsync: async () => true,
    watch: async (callback) => { deliver = callback; return { remove() {} }; } }, (fix) => fixes.push(fix), () => {});
  await flush();
  stop();
  deliver({ latitude: 35, longitude: -78, accuracy: 10 });
  assert.equal(fixes.length, 0);
});

test('invalid coordinates are rejected instead of manufactured', () => {
  for (const [latitude, longitude] of [[91, 0], [0, 181], [NaN, 0], [0, Infinity]]) {
    assert.equal(validPosition({ latitude, longitude, accuracy: null }), false);
  }
});

test('watch startup failures produce an unavailable state', async () => {
  let errors = 0;
  const stop = startForegroundWatch({ hasServicesEnabledAsync: async () => true,
    watch: async () => { throw new Error('sensor unavailable'); } }, () => {}, () => { errors++; });
  await flush();
  stop();
  assert.equal(errors, 1);
});

test('a slow first fix reports unavailable but can recover when a valid fix arrives', async () => {
  let deliver!: (fix: Position) => void;
  let errors = 0, fixes = 0;
  const stop = startForegroundWatch({ hasServicesEnabledAsync: async () => true,
    watch: async (callback) => { deliver = callback; return { remove() {} }; } }, () => { fixes++; }, () => { errors++; }, 5);
  await new Promise((resolve) => setTimeout(resolve, 20));
  assert.equal(errors, 1);
  deliver({ latitude: 35, longitude: -78, accuracy: 20 });
  assert.equal(fixes, 1);
  stop();
});
