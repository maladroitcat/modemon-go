import { expect, test, type Page } from '@playwright/test';

const runtimeErrors = new WeakMap<Page, string[]>();
test.beforeEach(({ page }) => {
  const errors: string[] = [];
  runtimeErrors.set(page, errors);
  page.on('pageerror', (error) => errors.push(error.message));
});
test.afterEach(({ page }) => {
  expect(runtimeErrors.get(page)).toEqual([]);
});

async function acknowledge(page: Page) {
  const enter = page.getByRole('button', { name: 'Enter map', exact: true });
  await expect(enter).toBeDisabled();
  await page.getByRole('checkbox').check();
  await expect(enter).toBeEnabled();
  await enter.click();
  await expect(page.getByText('Nearby encounters', { exact: true })).toBeVisible();
}

test('denied location still permits explicit safety onboarding and all placeholder tabs', async ({ page }, info) => {
  await page.goto('/');
  await expect(page.getByText('Modémon GO', { exact: true })).toBeVisible();
  await page.screenshot({ path: info.outputPath('welcome.png'), fullPage: true });
  await page.getByRole('button', { name: 'Start Playing', exact: true }).click();
  await page.getByRole('button', { name: 'Allow foreground location', exact: true }).click();
  await expect(page.getByText(/Location is not allowed/)).toBeVisible();
  await page.getByRole('button', { name: 'Continue without location', exact: true }).click();
  await acknowledge(page);
  await expect(page.getByText(/Location is not available yet/)).toBeVisible();
  await page.screenshot({ path: info.outputPath('map-denied.png'), fullPage: true });
  await page.getByLabel('Modédex', { exact: true }).click();
  await expect(page.getByText(/Discoveries and educational entries are not available/)).toBeVisible();
  await page.getByLabel('Encounter', { exact: true }).click();
  await expect(page.getByText('No encounter selected', { exact: true })).toBeVisible();
  await page.getByLabel('Settings', { exact: true }).click();
  await page.getByRole('button', { name: 'Read the full player-safety notice' }).click();
  await expect(page.getByText('The real world comes first.', { exact: true })).toBeVisible();
  await expect(page.getByText(/Never play while driving or cycling/)).toBeVisible();
});

test('granted permission skips another request, persists safety, and retains a session reminder', async ({ page, context }, info) => {
  await context.grantPermissions(['geolocation']);
  await context.setGeolocation({ latitude: 35.7796, longitude: -78.6382, accuracy: 12 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Start Playing', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Allow foreground location', exact: true })).toHaveCount(0);
  await acknowledge(page);
  // Browser QA deliberately does not substitute a fake map for react-native-maps.
  await expect(page.getByText('Native map unavailable', { exact: true })).toBeVisible();
  await page.screenshot({ path: info.outputPath('map-web-limitation.png'), fullPage: true });
  const stored = await page.evaluate(() => localStorage.getItem('modemon-go:safety-acknowledgment'));
  expect(JSON.parse(stored ?? '{}')).toEqual({ version: 1 });
  await page.reload();
  await page.getByRole('button', { name: 'Start Playing', exact: true }).click();
  await expect(page.getByText('Nearby encounters', { exact: true })).toBeVisible();
  await expect(page.getByRole('checkbox')).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Player safety: Heads up/ })).toBeVisible();
});

test('direct gameplay links cannot bypass acknowledgment', async ({ page }) => {
  await page.goto('/encounter');
  await expect(page.getByRole('button', { name: 'Start Playing', exact: true })).toBeVisible();
  await expect(page.getByText('No encounter selected', { exact: true })).toHaveCount(0);
});

test('storage failure requires safety again and warns about session-only acknowledgment', async ({ page }) => {
  await page.addInitScript(() => {
    Storage.prototype.getItem = () => { throw new Error('Storage unavailable'); };
    Storage.prototype.setItem = () => { throw new Error('Storage unavailable'); };
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Start Playing', exact: true }).click();
  await page.getByRole('button', { name: 'Continue without location', exact: true }).click();
  await acknowledge(page);
  await expect(page.getByText(/Safety agreed for this session only/)).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: 'Start Playing', exact: true }).click();
  await page.getByRole('button', { name: 'Continue without location', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Enter map', exact: true })).toBeDisabled();
});

test('welcome and map shell remain usable at narrow mobile, landscape, and desktop sizes', async ({ page }) => {
  for (const viewport of [{ width: 320, height: 640 }, { width: 844, height: 390 }, { width: 1280, height: 800 }]) {
    await page.setViewportSize(viewport);
    await page.goto('/');
    await expect(page.getByRole('button', { name: 'Start Playing', exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.getByRole('button', { name: 'Start Playing', exact: true }).click();
    await page.getByRole('button', { name: 'Continue without location', exact: true }).click();
    await page.getByRole('checkbox').or(page.getByText('Nearby encounters', { exact: true })).first().waitFor();
    if (await page.getByRole('checkbox').isVisible()) await acknowledge(page);
    await page.getByText('No encounter data is included in this build.', { exact: true }).scrollIntoViewIfNeeded();
    const nearby = await page.getByText('No encounter data is included in this build.', { exact: true }).boundingBox();
    const mapTab = await page.getByLabel('Map', { exact: true }).boundingBox();
    expect(nearby).not.toBeNull();
    expect(mapTab).not.toBeNull();
    expect(nearby!.y + nearby!.height).toBeLessThanOrEqual(mapTab!.y + 1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
});
