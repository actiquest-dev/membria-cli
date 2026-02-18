#!/usr/bin/env node
import crypto from "node:crypto";
import process from "node:process";

const AUTHORIZE_URL = "https://claude.ai/oauth/authorize";
const TOKEN_URL = "https://console.anthropic.com/v1/oauth/token";
const REDIRECT_URI = "https://console.anthropic.com/oauth/code/callback";
const CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e";
const SCOPE = "org:create_api_key user:profile user:inference";

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

function buildAuthUrl({ verifier, challenge, state, mode }) {
  const url = new URL(mode === "console" ? "https://console.anthropic.com/oauth/authorize" : AUTHORIZE_URL);
  url.searchParams.set("code", "true");
  url.searchParams.set("client_id", CLIENT_ID);
  url.searchParams.set("redirect_uri", REDIRECT_URI);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("scope", SCOPE);
  url.searchParams.set("code_challenge", challenge);
  url.searchParams.set("code_challenge_method", "S256");
  url.searchParams.set("state", state);
  if (mode === "max") url.searchParams.set("product", "claude_max");
  return url.toString();
}

function parseCode(input) {
  const trimmed = input.trim();
  if (!trimmed) return { code: "", state: "" };
  if (trimmed.includes("code=")) {
    const url = new URL(trimmed);
    return {
      code: url.searchParams.get("code") || "",
      state: url.searchParams.get("state") || "",
    };
  }
  if (trimmed.includes("#")) {
    const [code, state] = trimmed.split("#", 2);
    return { code, state: state || "" };
  }
  return { code: trimmed, state: "" };
}

async function exchangeCode(code, verifier) {
  const parsed = parseCode(code);
  const codePart = parsed.code;
  const statePart = parsed.state || verifier;
  if (!codePart || !statePart) {
    throw new Error("missing_code_or_state");
  }
  const res = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      code: codePart,
      state: statePart,
      grant_type: "authorization_code",
      client_id: CLIENT_ID,
      redirect_uri: REDIRECT_URI,
      code_verifier: verifier,
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

function parseArgs() {
  const args = process.argv.slice(2);
  const out = { mode: "start", code: "", verifier: "", product: "max" };
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === "--start") out.mode = "start";
    if (a === "--exchange") out.mode = "exchange";
    if (a === "--code") out.code = args[++i] || "";
    if (a === "--verifier") out.verifier = args[++i] || "";
    if (a === "--max") out.product = "max";
    if (a === "--console") out.product = "console";
  }
  return out;
}

async function main() {
  const args = parseArgs();
  if (args.mode === "start") {
    const pkce = generatePkce();
    const state = pkce.verifier;
    const url = buildAuthUrl({ verifier: pkce.verifier, challenge: pkce.challenge, state, mode: args.product });
    process.stdout.write(JSON.stringify({ url, verifier: pkce.verifier, state }));
    return;
  }
  if (args.mode === "exchange") {
    if (!args.code || !args.verifier) {
      throw new Error("missing_code_or_verifier");
    }
    const parsed = parseCode(args.code);
    const code = parsed.code || args.code;
    const tokens = await exchangeCode(code, args.verifier);
    process.stdout.write(JSON.stringify(tokens));
    return;
  }
  throw new Error("unknown_mode");
}

main().catch((err) => {
  process.stderr.write(String(err?.message || err));
  process.exit(1);
});
