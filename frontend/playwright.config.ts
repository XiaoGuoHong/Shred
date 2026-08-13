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
      // Real FastAPI pipeline with a deterministic fake classifier and an
      // isolated SQLite file, so end-to-end tests cover the backend too.
      command:
        "python -m alembic upgrade head && python -m uvicorn shred.main:app --host 127.0.0.1 --port 8000",
      cwd: "..",
      env: {
        SHRED_E2E_FAKE_CLASSIFIER: "1",
        SHRED_DATABASE_URL: "sqlite:///./data/e2e-test.db",
      },
      port: 8000,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: "npx vite --port 5173",
      port: 5173,
      reuseExistingServer: true,
      timeout: 15_000,
    },
  ],
});
