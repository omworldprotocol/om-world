#!/usr/bin/env node
/**
 * omw-node — OM World node client v0 (storage only).
 *
 * Usage:
 *   omw-node start [--server URL] [--gb N] [--contact handle] [--interval SECONDS]
 *
 * Env vars (overridden by CLI flags):
 *   OMW_SERVER           default https://app.omworld.one
 *   OMW_NODE_CLAIMED_GB  default 1
 *   OMW_NODE_CONTACT     default ""
 *   OMW_NODE_INTERVAL_S  default 30
 *   OMW_NODE_DIR         default ~/.omw-node
 */

import { loadOrCreateIdentity, signMessage } from "./identity.js";
import { putBlob, hashBlobRange, totalStoredBytes } from "./blob_store.js";
import type {
  RegisterRequest,
  RegisterResponse,
  HeartbeatRequest,
  HeartbeatResponse,
  ProofRequest,
  Work,
} from "./protocol.js";

interface Config {
  server: string;
  claimedGb: number;
  contact: string;
  intervalMs: number;
  verbose: boolean;
}

function parseArgs(argv: string[]): { command: string; cfg: Config } {
  const args = argv.slice(2);
  const command = args[0] || "help";
  const cfg: Config = {
    server: process.env.OMW_SERVER || "https://app.omworld.one",
    claimedGb: Number(process.env.OMW_NODE_CLAIMED_GB || 1),
    contact: process.env.OMW_NODE_CONTACT || "",
    intervalMs: Number(process.env.OMW_NODE_INTERVAL_S || 30) * 1000,
    verbose: false,
  };
  for (let i = 1; i < args.length; i++) {
    const a = args[i];
    if (a === "--server") cfg.server = args[++i];
    else if (a === "--gb") cfg.claimedGb = Number(args[++i]);
    else if (a === "--contact") cfg.contact = args[++i];
    else if (a === "--interval") cfg.intervalMs = Number(args[++i]) * 1000;
    else if (a === "--verbose" || a === "-v") cfg.verbose = true;
  }
  return { command, cfg };
}

function help(): void {
  console.log(`omw-node — OM World node client v0

Commands:
  start     register (if needed) then poll the server forever
  status    print local identity, node_id, blob stats, exit
  help      show this message

Flags:
  --server URL       OM World server (default https://app.omworld.one)
  --gb N             claimed storage capacity in GB (default 1)
  --contact handle   optional human contact for the node operator
  --interval SECONDS heartbeat poll interval (default 30)
  --verbose, -v      print every poll cycle

Identity + blob store live at \$OMW_NODE_DIR (default ~/.omw-node).
`);
}

async function postJson<T>(url: string, body: unknown, label: string): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) {
    throw new Error(`${label} ${res.status}: ${text.slice(0, 400)}`);
  }
  return JSON.parse(text) as T;
}

async function register(cfg: Config): Promise<string> {
  const id = loadOrCreateIdentity();
  const message = `omw-register|${id.publicKeyB64}|${cfg.claimedGb}`;
  const signature = signMessage(id, message);
  const body: RegisterRequest = {
    pubkey: id.publicKeyB64,
    claimed_gb: cfg.claimedGb,
    owner_contact: cfg.contact || null,
    signature,
  };
  const r = await postJson<RegisterResponse>(`${cfg.server}/api/nodes/register`, body, "register");
  console.log(`[omw-node] registered node_id=${r.node_id} status=${r.status} claimed_gb=${r.claimed_gb} proven_gb=${r.proven_gb}`);
  return r.node_id;
}

function buildHeartbeat(nodeId: string, cfg: Config, confirm?: { assignment_id: string; sha256: string }): HeartbeatRequest {
  const id = loadOrCreateIdentity();
  const nonce = Date.now();
  const message = `omw-heartbeat|${nodeId}|${nonce}`;
  return {
    node_id: nodeId,
    pubkey: id.publicKeyB64,
    nonce,
    signature: signMessage(id, message),
    free_gb: Math.max(0, cfg.claimedGb - Math.ceil(totalStoredBytes() / 1024 / 1024 / 1024)),
    confirm,
  };
}

async function handleWork(cfg: Config, nodeId: string, work: Work): Promise<{ confirm?: { assignment_id: string; sha256: string } }> {
  if (work.kind === "store") {
    const bytes = Buffer.from(work.blob_base64, "base64");
    if (bytes.length !== work.size_bytes) {
      console.warn(`[omw-node] size mismatch for assignment ${work.assignment_id}: got ${bytes.length}, expected ${work.size_bytes}`);
    }
    try {
      const r = putBlob(bytes, work.expected_sha256);
      console.log(`[omw-node] stored pattern ${work.pattern_id} sha256=${r.sha256.slice(0, 12)}… (${bytes.length}B)`);
      return { confirm: { assignment_id: work.assignment_id, sha256: r.sha256 } };
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      console.warn(`[omw-node] putBlob failed: ${message}`);
      return {};
    }
  }

  if (work.kind === "challenge") {
    const hash = hashBlobRange(work.sha256, work.range_start, work.range_end);
    if (!hash) {
      console.warn(`[omw-node] challenge for blob ${work.sha256.slice(0, 12)}… cannot compute (missing or out-of-range)`);
      return {};
    }
    const id = loadOrCreateIdentity();
    const nonce = Date.now();
    const message = `omw-proof|${nodeId}|${work.assignment_id}|${work.range_start}|${work.range_end}|${hash}|${nonce}`;
    const body: ProofRequest = {
      node_id: nodeId,
      pubkey: id.publicKeyB64,
      nonce,
      signature: signMessage(id, message),
      assignment_id: work.assignment_id,
      range_start: work.range_start,
      range_end: work.range_end,
      range_sha256: hash,
    };
    try {
      const res = await postJson<{ ok: boolean; matched: boolean; gb_hours_credited?: number; proven_gb?: number; strikes?: number }>(
        `${cfg.server}/api/nodes/proof`, body, "proof"
      );
      if (res.matched) {
        console.log(`[omw-node] proof OK — credited ${res.gb_hours_credited?.toFixed(6) ?? 0} gb-hours; proven=${res.proven_gb?.toFixed(6) ?? 0} GB`);
      } else {
        console.warn(`[omw-node] proof MISMATCH — strikes=${res.strikes ?? "?"}`);
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      console.warn(`[omw-node] proof submit failed: ${message}`);
    }
    return {};
  }

  return {};
}

async function poll(cfg: Config, nodeId: string, pendingConfirm?: { assignment_id: string; sha256: string }): Promise<{ confirm?: { assignment_id: string; sha256: string } }> {
  const body = buildHeartbeat(nodeId, cfg, pendingConfirm);
  let res: HeartbeatResponse;
  try {
    res = await postJson<HeartbeatResponse>(`${cfg.server}/api/nodes/heartbeat`, body, "heartbeat");
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    console.warn(`[omw-node] heartbeat failed: ${message}`);
    return {};
  }

  if (cfg.verbose) {
    console.log(`[omw-node] heartbeat status=${res.node_status} strikes=${res.strikes} confirmed=${JSON.stringify(res.confirmed)} work=${res.work?.kind ?? "none"}`);
  }

  if (res.work) {
    return handleWork(cfg, nodeId, res.work);
  }
  return {};
}

async function startLoop(cfg: Config): Promise<void> {
  console.log(`[omw-node] starting — server=${cfg.server} claimed_gb=${cfg.claimedGb} interval=${cfg.intervalMs / 1000}s`);
  const nodeId = await register(cfg);
  let pendingConfirm: { assignment_id: string; sha256: string } | undefined;
  // shutdown handling
  const shutdown = () => { console.log("\n[omw-node] shutting down"); process.exit(0); };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);

  while (true) {
    try {
      const { confirm } = await poll(cfg, nodeId, pendingConfirm);
      pendingConfirm = confirm;
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      console.warn(`[omw-node] poll cycle error: ${message}`);
    }
    await new Promise((r) => setTimeout(r, cfg.intervalMs));
  }
}

async function showStatus(cfg: Config): Promise<void> {
  const id = loadOrCreateIdentity();
  const total = totalStoredBytes();
  console.log(`Node identity:`);
  console.log(`  pubkey (b64):  ${id.publicKeyB64}`);
  console.log(`  server:        ${cfg.server}`);
  console.log(`  claimed_gb:    ${cfg.claimedGb}`);
  console.log(`  local blobs:   ${total} bytes (${(total / 1024 / 1024).toFixed(2)} MB)`);
  // Best-effort node_id lookup via GET endpoint.
  try {
    const res = await fetch(`${cfg.server}/api/nodes/register?pubkey=${encodeURIComponent(id.publicKeyB64)}`);
    if (res.ok) {
      const { node_id } = await res.json() as { node_id: string };
      console.log(`  node_id:       ${node_id}`);
    }
  } catch { /* offline OK */ }
}

const { command, cfg } = parseArgs(process.argv);
if (command === "start") {
  await startLoop(cfg);
} else if (command === "status") {
  await showStatus(cfg);
} else {
  help();
}
