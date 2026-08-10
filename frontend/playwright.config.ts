import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:5173",
    headless: true,
  },
  webServer: [
    {
      command: "python -m uvicorn shred.main:app --host 127.0.0.1 --port 8000",
      cwd: "..",
      port: 8000,
      reuseExistingServer: true,
      timeout: 15_000,
    },
    {
      command: "npx vite --port 5173",
      port: 5173,
      reuseExistingServer: true,
      timeout: 15_000,
    },
  ],
});
