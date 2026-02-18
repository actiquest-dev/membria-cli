import { app, BrowserWindow, ipcMain } from "electron";
import path from "path";
import { fileURLToPath } from "url";
import os from "os";
import pty from "node-pty";
import { execFileSync } from "child_process";
import fs from "fs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const ptys = new Map();
let cachedShellPath = "";
let browserShimPath = "";
const browserUrlFile = path.join(os.tmpdir(), "membria-mcp-browser-url.txt");

function shellEscape(value) {
  if (value === "") return "''";
  return `'${value.replace(/'/g, `'\"'\"'`)}'`;
}

function loadLoginShellPath() {
  try {
    const shell = process.env.SHELL || "/bin/zsh";
    const out = execFileSync(shell, ["-lc", "echo $PATH"], { encoding: "utf-8" });
    cachedShellPath = out.trim();
  } catch {
    cachedShellPath = "";
  }
}

function ensureBrowserShim() {
  try {
    const shimPath = path.join(os.tmpdir(), "membria-mcp-browser.sh");
    const script = `#!/bin/sh
if [ -n "$MEMBRIA_BROWSER_FILE" ]; then
  printf '%s\n' "$@" > "$MEMBRIA_BROWSER_FILE"
fi
printf '%s\n' "$@"
`;
    fs.writeFileSync(shimPath, script, { mode: 0o755 });
    browserShimPath = shimPath;
  } catch {
    browserShimPath = "";
  }
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1100,
    height: 800,
    backgroundColor: "#0f1115",
    title: "Membria MCP Server",
    webPreferences: {
      nodeIntegration: true,
      webviewTag: true,
      contextIsolation: false,
    },
  });

  win.loadFile(path.join(__dirname, "index.html"));
}

app.whenReady().then(() => {
  loadLoginShellPath();
  ensureBrowserShim();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

ipcMain.handle("terminal:start", (event, { id, command, exec }) => {
  if (ptys.has(id)) {
    try {
      ptys.get(id).kill();
    } catch {
      // Ignore kill errors; we'll replace the process anyway.
    }
    ptys.delete(id);
  }

  const shell = process.env.SHELL || "/bin/zsh";
  const cwd = os.homedir();
  const currentPath = process.env.PATH || "";
  const merged = cachedShellPath ? `${cachedShellPath}:${currentPath}` : currentPath;
  const env = { ...process.env, PATH: merged };
  if (exec && exec.cmd && exec.cmd.includes("codex") && browserShimPath) {
    env.BROWSER = browserShimPath;
    env.MEMBRIA_BROWSER_FILE = browserUrlFile;
  }
  let ptyProcess;
  if (exec && exec.cmd) {
    try {
      ptyProcess = pty.spawn(exec.cmd, exec.args || [], {
        name: "xterm-color",
        cols: 120,
        rows: 30,
        cwd,
        env,
      });
    } catch (err) {
      event.sender.send("terminal:data", {
        id,
        data: `[spawn error] ${err?.message || err}\r\n[retry] using shell fallback...\r\n`,
      });
      const cmdline = [exec.cmd, ...(exec.args || [])].map(shellEscape).join(" ");
      ptyProcess = pty.spawn(shell, ["-lc", cmdline], {
        name: "xterm-color",
        cols: 120,
        rows: 30,
        cwd,
        env,
      });
      event.sender.send("terminal:data", { id, data: "[shell fallback running]\\r\\n" });
    }
  } else {
    if (!command || command.trim().length === 0) {
      return { ok: false, error: "Missing command" };
    }
    try {
      ptyProcess = pty.spawn(shell, ["-il"], {
        name: "xterm-color",
        cols: 120,
        rows: 30,
        cwd,
        env,
      });
    } catch (err) {
      event.sender.send("terminal:data", {
        id,
        data: `[spawn error] ${err?.message || err}\r\n`,
      });
      return { ok: false, error: "Spawn failed" };
    }
    event.sender.send("terminal:data", { id, data: "[pty started]\\r\\n" });
    setTimeout(() => {
      event.sender.send("terminal:data", { id, data: "[sending command]\\r\\n" });
      ptyProcess.write("echo '[shell ready]'\n");
      ptyProcess.write(`${command}\n`);
    }, 1500);
  }

  ptyProcess.onData((data) => {
    event.sender.send("terminal:data", { id, data });
  });

  ptyProcess.onExit((ev) => {
    ptys.delete(id);
    event.sender.send("terminal:exit", { id, code: ev.exitCode, signal: ev.signal });
  });

  ptys.set(id, ptyProcess);
  return { ok: true };
});

ipcMain.on("terminal:input", (event, { id, data }) => {
  const proc = ptys.get(id);
  if (!proc) return;
  proc.write(data);
});
