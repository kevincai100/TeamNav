import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: { baseURL: "http://127.0.0.1:3011", trace: "on-first-retry", screenshot: "only-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    { command: "node scripts/start-e2e-api.mjs", url: "http://127.0.0.1:8011/health/ready", timeout: 120_000, reuseExistingServer: false },
    { command: "npm run dev --workspace @teamnav/web -- --hostname 127.0.0.1 --port 3011", url: "http://127.0.0.1:3011", env: { NEXT_PUBLIC_API_URL: "http://127.0.0.1:8011", NEXT_DIST_DIR: ".next-e2e" }, timeout: 120_000, reuseExistingServer: false },
  ],
});
