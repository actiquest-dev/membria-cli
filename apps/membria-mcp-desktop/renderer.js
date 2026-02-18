const { Terminal } = require("xterm");
const { FitAddon } = require("xterm-addon-fit");
const fs = require("fs");
const { ipcRenderer } = require("electron");

const terminals = new Map();
const TOKENS_PATH = "/Users/miguelaprossine/membria-cli/.config/membria-mcp/mcp-front.tokens.json";
const openedUrls = new Set();
const BROWSER_URL_FILE = "/tmp/membria-mcp-browser-url.txt";
const authModal = document.getElementById("auth-modal");
const authWebview = document.getElementById("auth-webview");
const authClose = document.getElementById("auth-modal-close");

function openAuthModal(url) {
  if (!authModal || !authWebview) return;
  authWebview.src = url;
  authModal.classList.add("open");
}

function closeAuthModal() {
  if (!authModal) return;
  authModal.classList.remove("open");
}

if (authClose) {
  authClose.addEventListener("click", closeAuthModal);
}
const EXEC = {
  openai: {
    cmd: "/opt/homebrew/bin/codex",
    args: ["mcp", "login", "membria"],
  },
  anthropic: {
    cmd: "/Users/miguelaprossine/.local/bin/claude",
    args: [
      "mcp",
      "add-json",
      "membria",
      JSON.stringify({
        type: "stdio",
        command: "python",
        args: ["/Users/miguelaprossine/membria-cli/src/membria/mcp_server.py"],
      }),
    ],
  },
  kilo: {
    cmd: "/Users/miguelaprossine/.nvm/versions/node/v22.19.0/bin/kilo",
    args: ["mcp", "connect", "membria"],
  },
};

function setStatus(element, state, text) {
  if (!element) return;
  element.classList.remove("ok", "warn", "bad");
  element.classList.add(state);
  element.textContent = text;
}

function readTokens() {
  try {
    const raw = fs.readFileSync(TOKENS_PATH, "utf-8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function hasToken(tokens, key) {
  if (!tokens || !tokens.user_tokens) return false;
  const entry = tokens.user_tokens[`membria.team@gmail.com:${key}`];
  return Boolean(entry);
}

function updateAuthState() {
  const tokens = readTokens();
  const openaiReady = hasToken(tokens, "openai-oauth") || hasToken(tokens, "openai");
  const anthropicReady = hasToken(tokens, "anthropic-oauth") || hasToken(tokens, "anthropic");
  const kiloReady = hasToken(tokens, "kilo-code");

  document.querySelectorAll(".card").forEach((card) => {
    const provider = card.dataset.provider;
    const button = card.querySelector("[data-action]");
    const statusEl = card.querySelector("[data-status]");
    let ready = false;
    if (provider === "openai") ready = openaiReady;
    if (provider === "anthropic") ready = anthropicReady;
    if (provider === "kilo") ready = kiloReady;

    if (!ready) {
      button.disabled = true;
      setStatus(statusEl, "bad", "Auth required");
    } else {
      button.disabled = false;
      if (statusEl.textContent === "Auth required") {
        setStatus(statusEl, "warn", "Not started");
      }
    }
  });
}

function setupCard(card) {
  const id = card.dataset.provider;
  const commandId = card.dataset.commandId || id;
  const exec = EXEC[commandId];
  const terminalHost = card.querySelector("[data-terminal]");
  const statusEl = card.querySelector("[data-status]");
  const button = card.querySelector("[data-action]");

  const term = new Terminal({
    convertEol: true,
    cursorBlink: true,
    theme: {
      background: "#0f1115",
      foreground: "#e6e8ee",
      cursor: "#4cc9f0",
      selection: "rgba(76,201,240,0.25)",
    },
  });
  const fitAddon = new FitAddon();
  term.loadAddon(fitAddon);
  term.open(terminalHost);
  fitAddon.fit();

  terminals.set(id, { term, fitAddon, statusEl, button });

  term.onData((data) => {
    ipcRenderer.send("terminal:input", { id, data });
  });

  button.addEventListener("click", async () => {
    if (button.disabled) {
      return;
    }
    if (!exec || !exec.cmd) {
      setStatus(statusEl, "bad", "Missing command");
      return;
    }
    setStatus(statusEl, "warn", "Starting...");
    term.writeln(`$ ${exec.cmd} ${exec.args.join(" ")}`);
    term.writeln("");
    const result = await ipcRenderer.invoke("terminal:start", { id, exec });
    if (result && result.ok) {
      setStatus(statusEl, "ok", "Running");
      const startAt = Date.now();
      setTimeout(() => {
        if (Date.now() - startAt >= 3000) {
          entry.term.writeln("[note] waiting for CLI output...");
        }
      }, 3000);
    } else {
      setStatus(statusEl, "bad", result && result.error ? result.error : "Failed");
    }
    if (!button.textContent.startsWith("Reconnect")) {
      button.textContent = button.textContent.replace("Connect", "Reconnect");
    }
    term.focus();
  });
}

ipcRenderer.on("terminal:data", (_evt, { id, data }) => {
  const entry = terminals.get(id);
  if (!entry) return;
  entry.term.write(data);
  const urls = data.match(/https?:\/\/[^\s"'<>]+/g);
  if (urls) {
    urls.forEach((url) => {
      if (url.startsWith("http://localhost:8080/oauth/") && !openedUrls.has(url)) {
        openedUrls.add(url);
        entry.term.writeln(`\r\n[opening login inside app] ${url}\r\n`);
        openAuthModal(url);
      }
    });
  }
});

ipcRenderer.on("terminal:exit", (_evt, { id, code, signal }) => {
  const entry = terminals.get(id);
  if (!entry) return;
  const suffix = typeof code === "number" ? ` (code ${code})` : signal ? ` (${signal})` : "";
  setStatus(entry.statusEl, "warn", `Exited${suffix}`);
  entry.term.writeln(`\r\n[process exited${suffix}]\r\n`);
});

document.querySelectorAll(".card[data-provider]").forEach(setupCard);
window.addEventListener("resize", () => {
  terminals.forEach(({ fitAddon }) => fitAddon.fit());
});

const tabs = document.querySelectorAll("[data-tab]");
const panels = document.querySelectorAll("[data-panel]");
tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.remove("active"));
    panels.forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    const panel = document.querySelector(`[data-panel=\"${tab.dataset.tab}\"]`);
    if (panel) panel.classList.add("active");
  });
});

const reloadButton = document.querySelector("[data-action=\"reload-webview\"]");
const webview = document.getElementById("providers-webview");
if (reloadButton && webview) {
  reloadButton.addEventListener("click", () => webview.reload());
}

updateAuthState();
setInterval(updateAuthState, 3000);

setInterval(() => {
  try {
    const raw = fs.readFileSync(BROWSER_URL_FILE, "utf-8").trim();
    if (!raw) return;
    if (!openedUrls.has(raw) && raw.startsWith("http://localhost:8080/oauth/")) {
      openedUrls.add(raw);
      openAuthModal(raw);
    }
  } catch {
    // ignore
  }
}, 1000);

if (authWebview) {
  const refreshFromAuth = (url) => {
    if (!url) return;
    if (url.includes("/oauth/") || url.includes("/my/tokens")) {
      setTimeout(updateAuthState, 500);
    }
    if (url.includes("/oauth/services") || url.includes("/my/tokens")) {
      // keep modal open but refresh status
      setTimeout(updateAuthState, 500);
    }
  };
  authWebview.addEventListener("did-navigate", (e) => refreshFromAuth(e.url));
  authWebview.addEventListener("did-navigate-in-page", (e) => refreshFromAuth(e.url));
}
