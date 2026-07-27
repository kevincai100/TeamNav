import { existsSync, unlinkSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const apiDirectory = resolve(root, "apps", "api");
const databasePath = resolve(apiDirectory, "teamnav_e2e.db");
const bundledPython = resolve(root, ".venv", "Scripts", "python.exe");
const python = process.env.PYTHON || (existsSync(bundledPython) ? bundledPython : "python");
const environment = {
  ...process.env,
  APP_URL: "http://127.0.0.1:3011",
  CORS_ORIGINS: "http://127.0.0.1:3011",
  DATABASE_URL: `sqlite+aiosqlite:///${databasePath.replaceAll("\\", "/")}`,
  SECRET_KEY: "e2e-secret-key-with-at-least-32-characters",
  ADMIN_TOKEN: "e2e-admin-token-with-at-least-32-characters",
  CAPTCHA_REQUIRED: "true",
};

if (existsSync(databasePath)) unlinkSync(databasePath);
const migration = spawnSync(python, ["-m", "alembic", "upgrade", "head"], {
  cwd: apiDirectory,
  env: environment,
  stdio: "inherit",
});
if (migration.status !== 0) process.exit(migration.status ?? 1);

const server = spawn(
  python,
  ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8011"],
  { cwd: apiDirectory, env: environment, stdio: "inherit" },
);
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.kill(signal));
server.on("exit", (code) => process.exit(code ?? 0));
