#!/usr/bin/env node
import crypto from "node:crypto";
import process from "node:process";

const CLIENT_ID = process.env.OPENAI_OAUTH_CLIENT_ID || "app_EMoamEEZ73f0CkXaXp7hrann";
const AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize";
const TOKEN_URL = "https://auth.openai.com/oauth/token";
const REDIRECT_URI = "http://localhost:1455/auth/callback";
const SCOPE = "openid profile email offline_access";

function base64url(buf) {
  return buf
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function generatePkce() {
  const verifier = base64url(crypto.randomBytes(32));
  const challenge = base64url(crypto.createHash("sha256").update(verifier).digest());
  return { verifier, challenge };
}

function createState() {
  return crypto.randomBytes(16).toString("hex");
}

function buildAuthUrl({ verifier, challenge, state }) {
  const url = new URL(AUTHORIZE_URL);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", CLIENT_ID);
  url.searchParams.set("redirect_uri", REDIRECT_URI);
  url.searchParams.set("scope", SCOPE);
  url.searchParams.set("code_challenge", challenge);
  url.searchParams.set("code_challenge_method", "S256");
  url.searchParams.set("state", state);
  url.searchParams.set("id_token_add_organizations", "true");
  url.searchParams.set("codex_cli_simplified_flow", "true");
  url.searchParams.set("originator", "codex_cli_rs");
  return url.toString();
}

async function exchangeCode(code, verifier) {
  const parsed = parseCode(code);
  const codePart = parsed.code || code;
  const res = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: CLIENT_ID,
      code: codePart,
      code_verifier: verifier,
      redirect_uri: REDIRECT_URI,
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`token_exchange_failed:${res.status}:${text}`);
  }
  const json = await res.json();
  if (!json?.access_token || !json?.refresh_token || typeof json?.expires_in !== "number") {
    throw new Error("token_response_missing_fields");
  }
  return {
    access: json.access_token,
    refresh: json.refresh_token,
    expires: Date.now() + json.expires_in * 1000,
  };
}

function parseCode(input) {
  const trimmed = input.trim();
  if (!trimmed) return { code: "" };
  if (trimmed.includes("code=")) {
    const url = new URL(trimmed);
    return {
      code: url.searchParams.get("code") || "",
    };
  }
  return { code: trimmed };
}

function parseArgs() {
  const args = process.argv.slice(2);
  const out = { mode: "start", code: "", verifier: "" };
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === "--start") out.mode = "start";
    if (a === "--exchange") out.mode = "exchange";
    if (a === "--code") out.code = args[++i] || "";
    if (a === "--verifier") out.verifier = args[++i] || "";
  }
  return out;
}

async function main() {
  const args = parseArgs();
  if (args.mode === "start") {
    const pkce = generatePkce();
    const state = createState();
    const url = buildAuthUrl({ verifier: pkce.verifier, challenge: pkce.challenge, state });
    process.stdout.write(JSON.stringify({ url, verifier: pkce.verifier, state }));
    return;
  }
  if (args.mode === "exchange") {
    if (!args.code || !args.verifier) {
      throw new Error("missing_code_or_verifier");
    }
    const tokens = await exchangeCode(args.code, args.verifier);
    process.stdout.write(JSON.stringify(tokens));
    return;
  }
  throw new Error("unknown_mode");
}

main().catch((err) => {
  process.stderr.write(String(err?.message || err));
  process.exit(1);
});
