/**
 * OpenClaw `infer web search` subprocess wrapper.
 *
 * Mirrors the pattern of lib/openclaw.ts. Uses the same `openclaw` binary
 * (already installed everywhere we run, no extra dep, no API key — DuckDuckGo
 * via the bundled provider). Returns parsed hits with EXTERNAL_UNTRUSTED_CONTENT
 * markers stripped from titles/snippets so they're consumable by downstream
 * synthesis prompts.
 */

import { spawn } from "node:child_process";

const OPENCLAW_BIN = process.env.OPENCLAW_BIN || "openclaw";
const TIMEOUT_MS = Number(process.env.OPENCLAW_WEB_TIMEOUT_MS ?? 60_000);

const SKIP_PREFIXES = ["web.search ", "provider: ", "outputs: ", "web.fetch "];

export interface WebSearchHit {
  title: string;
  url: string;
  snippet: string;
  site_name?: string;
}

/** Strip the EXTERNAL_UNTRUSTED_CONTENT wrappers OpenClaw applies to search results. */
function stripUntrusted(s: string): string {
  return s
    .replace(/<<<EXTERNAL_UNTRUSTED_CONTENT[^>]*>>>/g, "")
    .replace(/<<<END_EXTERNAL_UNTRUSTED_CONTENT[^>]*>>>/g, "")
    .replace(/^\s*Source:[^\n]*\n---\s*/gm, "")
    .replace(/\s+/g, " ")
    .trim();
}

interface RawHit {
  title?: string;
  url?: string;
  snippet?: string;
  siteName?: string;
}

interface WebSearchOutput {
  result?: {
    results?: RawHit[];
  };
}

/**
 * Run a web search via OpenClaw. Returns up to `limit` hits.
 * Throws on subprocess failure or empty body.
 */
const PROVIDER = process.env.OPENCLAW_WEB_PROVIDER || "duckduckgo";

export function webSearch(opts: { query: string; limit?: number }): Promise<WebSearchHit[]> {
  const limit = opts.limit ?? 5;

  return new Promise((resolve, reject) => {
    const child = spawn(
      OPENCLAW_BIN,
      ["infer", "web", "search", "--provider", PROVIDER, "--query", opts.query, "--limit", String(limit), "--json"],
      { env: process.env },
    );

    let stdout = "";
    let stderr = "";
    const killTimer = setTimeout(() => {
      child.kill("SIGKILL");
      reject(new Error(`openclaw web search timeout after ${TIMEOUT_MS}ms`));
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
        return reject(new Error(`openclaw web search exited rc=${code}: ${stderr.trim().slice(0, 500)}`));
      }
      const body = stdout
        .split("\n")
        .filter((line) => !SKIP_PREFIXES.some((p) => line.startsWith(p)))
        .join("\n")
        .trim();
      if (!body) return reject(new Error("openclaw web search returned empty body"));

      try {
        const parsed = JSON.parse(body) as WebSearchOutput;
        const raw = parsed.result?.results ?? [];
        const hits: WebSearchHit[] = raw
          .filter((r) => typeof r.url === "string")
          .map((r) => ({
            title: stripUntrusted(r.title ?? ""),
            url: r.url as string,
            snippet: stripUntrusted(r.snippet ?? ""),
            site_name: r.siteName,
          }));
        resolve(hits);
      } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        reject(new Error(`openclaw web search JSON parse failed: ${message}; body: ${body.slice(0, 500)}`));
      }
    });
  });
}

/**
 * Run multiple queries, dedup by URL, cap to maxTotal hits.
 * Sequential (not parallel) to avoid hammering DuckDuckGo's rate limits.
 */
const INTER_QUERY_DELAY_MS = Number(process.env.OPENCLAW_WEB_INTER_QUERY_MS ?? 2500);

export async function multiSearch(opts: {
  queries: string[];
  perQueryLimit?: number;
  maxTotal?: number;
}): Promise<WebSearchHit[]> {
  const perQuery = opts.perQueryLimit ?? 5;
  const maxTotal = opts.maxTotal ?? 12;
  const seen = new Set<string>();
  const out: WebSearchHit[] = [];
  for (let i = 0; i < opts.queries.length; i++) {
    if (out.length >= maxTotal) break;
    const q = opts.queries[i];
    // Space out queries to reduce DuckDuckGo bot-detection trips.
    if (i > 0 && INTER_QUERY_DELAY_MS > 0) {
      await new Promise((r) => setTimeout(r, INTER_QUERY_DELAY_MS));
    }
    let hits: WebSearchHit[] = [];
    try {
      hits = await webSearch({ query: q, limit: perQuery });
    } catch (e) {
      console.warn(`[web] query "${q.slice(0, 60)}" failed:`, e instanceof Error ? e.message : e);
      continue;
    }
    for (const h of hits) {
      if (out.length >= maxTotal) break;
      if (seen.has(h.url)) continue;
      seen.add(h.url);
      out.push(h);
    }
  }
  return out;
}
