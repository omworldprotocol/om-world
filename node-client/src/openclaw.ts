/**
 * OpenClaw GPT-5.5 subprocess wrapper for the node client.
 * Port of /Users/feiyang/all_bots/om-world/lib/openclaw.ts.
 *
 * Per memory rule (feedback_openclaw_gpt55_local_path): OpenClaw >= 2026.5.12
 * — CLI must NOT pass --gateway (5.7-5.12 reversed semantics).
 */

import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const OPENCLAW_BIN = process.env.OPENCLAW_BIN || "openclaw";
const OPENCLAW_CONFIG = join(homedir(), ".openclaw", "openclaw.json");
const DEFAULT_MODEL = "openai-codex/gpt-5.5";
const TIMEOUT_MS = Number(process.env.OPENCLAW_TIMEOUT_MS ?? 180_000);

const SKIP_PREFIXES = ["model.run ", "provider: ", "model: ", "outputs: "];

function defaultModel(): string {
  try {
    if (!existsSync(OPENCLAW_CONFIG)) return DEFAULT_MODEL;
    const cfg = JSON.parse(readFileSync(OPENCLAW_CONFIG, "utf-8"));
    return cfg?.agents?.defaults?.model?.primary ?? DEFAULT_MODEL;
  } catch {
    return DEFAULT_MODEL;
  }
}

export function chatViaOpenclaw(opts: {
  system?: string;
  user: string;
  model?: string;
}): Promise<{ text: string; model: string }> {
  const model = opts.model ?? defaultModel();
  const parts: string[] = [];
  if (opts.system) {
    parts.push(opts.system);
    parts.push("---");
  }
  parts.push(opts.user);
  const prompt = parts.join("\n\n");

  return new Promise((resolve, reject) => {
    const child = spawn(
      OPENCLAW_BIN,
      ["infer", "model", "run", "--model", model, "--prompt", prompt],
      { env: process.env },
    );

    let stdout = "";
    let stderr = "";
    const killTimer = setTimeout(() => {
      child.kill("SIGKILL");
      reject(new Error(`openclaw timeout after ${TIMEOUT_MS}ms`));
    }, TIMEOUT_MS);

    child.stdout.on("data", (d: Buffer) => { stdout += d.toString(); });
    child.stderr.on("data", (d: Buffer) => { stderr += d.toString(); });

    child.on("error", (err) => {
      clearTimeout(killTimer);
      reject(err);
    });

    child.on("close", (code) => {
      clearTimeout(killTimer);
      if (code !== 0) {
        return reject(new Error(`openclaw exited rc=${code}: ${stderr.trim().slice(0, 500)}`));
      }
      const body = stdout
        .split("\n")
        .filter((line) => !SKIP_PREFIXES.some((p) => line.startsWith(p)))
        .join("\n")
        .trim();
      if (!body) {
        return reject(new Error("openclaw returned empty body"));
      }
      resolve({ text: body, model });
    });
  });
}
