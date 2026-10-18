import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const app = JSON.parse(readFileSync(new URL('../app.json', import.meta.url), 'utf8')).expo;
const location = app.plugins.find((entry: unknown) => Array.isArray(entry) && entry[0] === 'expo-location')[1];

test('native configuration enables only foreground location, not background or motion', () => {
  for (const key of ['isIosBackgroundLocationEnabled', 'isAndroidBackgroundLocationEnabled',
    'isAndroidForegroundServiceEnabled', 'isAndroidMotionActivityEnabled', 'locationAlwaysPermission',
    'locationAlwaysAndWhenInUsePermission', 'motionUsagePermission']) {
    assert.equal(location[key], false, key);
  }
  assert.ok(location.locationWhenInUsePermission.includes('while the app is open'));
  assert.ok(app.android.blockedPermissions.includes('android.permission.ACCESS_BACKGROUND_LOCATION'));
});

test('runtime entry is Expo Router and direct dependency versions are pinned', () => {
  const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
  assert.equal(pkg.main, 'expo-router/entry');
  for (const group of [pkg.dependencies, pkg.devDependencies]) {
    for (const version of Object.values(group)) assert.match(String(version), /^\d+\.\d+\.\d+$/);
  }
});

test('app code does not import canonical analysis data or background/camera APIs', () => {
  for (const file of ['state/AppState.tsx', 'components/MapSurface.native.tsx']) {
    const source = readFileSync(new URL(`../src/${file}`, import.meta.url), 'utf8');
    for (const forbidden of ['requestBackgroundPermissionsAsync', 'startLocationUpdatesAsync',
      'expo-camera', 'data/processed', 'data/config']) assert.equal(source.includes(forbidden), false, forbidden);
  }
});
