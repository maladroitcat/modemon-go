import { defineConfig, devices } from "@playwright/test";
import { fileURLToPath } from "node:url";
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  use: {
    baseURL: process.env.PLAYABLE_BASE_URL ?? "http://127.0.0.1:5173",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium-mobile",
      use: {
        ...devices["iPhone 13"],
        browserName: "chromium",
        defaultBrowserType: "chromium",
      },
    },
    {
      name: "webkit-mobile",
      use: { ...devices["iPhone 13"], browserName: "webkit" },
    },
  ],
  webServer: process.env.PLAYABLE_BASE_URL
    ? undefined
    : {
        command: "npm run play:web -- --port 5173",
        cwd: fileURLToPath(new URL('..', import.meta.url)),
        url: "http://127.0.0.1:5173",
        reuseExistingServer: !process.env.CI,
        timeout: 120000,
      },
});
