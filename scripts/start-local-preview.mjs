import { existsSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const apiDirectory = resolve(root, "apps", "api");
const bundledPython = resolve(root, ".venv", "Scripts", "python.exe");
const python = process.env.PYTHON || (existsSync(bundledPython) ? bundledPython : "python");
const apiUrl = "http://127.0.0.1:8020";
const webUrl = "http://127.0.0.1:3020";
const apiEnvironment = {
  ...process.env,
  DATABASE_URL: "sqlite+aiosqlite:///./teamnav_preview.db",
  APP_URL: webUrl,
  CORS_ORIGINS: webUrl,
  SECRET_KEY: "preview-secret-key-with-at-least-32-characters",
  ADMIN_TOKEN: "preview-admin-token-with-at-least-32-characters",
  CAPTCHA_REQUIRED: "true",
};

const migration = spawnSync(python, ["-m", "alembic", "upgrade", "head"], {
  cwd: apiDirectory,
  env: apiEnvironment,
  stdio: "inherit",
});
if (migration.status !== 0) process.exit(migration.status ?? 1);

const api = spawn(python, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8020"], {
  cwd: apiDirectory,
  env: apiEnvironment,
  detached: true,
  windowsHide: true,
  stdio: "ignore",
});
const webCommand = process.platform === "win32" ? process.env.ComSpec || "cmd.exe" : "npm";
const webArguments = process.platform === "win32"
  ? ["/d", "/s", "/c", "npm run dev --workspace @teamnav/web -- --hostname 127.0.0.1 --port 3020"]
  : ["run", "dev", "--workspace", "@teamnav/web", "--", "--hostname", "127.0.0.1", "--port", "3020"];
const web = spawn(webCommand, webArguments, {
  cwd: root,
  env: { ...process.env, NEXT_PUBLIC_API_URL: apiUrl },
  detached: true,
  windowsHide: true,
  stdio: "ignore",
});
api.unref();
web.unref();
console.log(`API ${apiUrl} (PID ${api.pid})`);
console.log(`Web ${webUrl} (PID ${web.pid})`);
