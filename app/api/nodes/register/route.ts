import { NextResponse } from "next/server";
import { z } from "zod";
import { registerNode, verifyNodeSignature, nodeIdFromPubkey } from "@/lib/nodes";

/**
 * POST /api/nodes/register
 *
 * First-time node registration (idempotent — re-registering refreshes capacity).
 * The node proves possession of the private key by signing the literal payload
 * `"omw-register|<pubkey_base64>|<claimed_gb>"`.
 */

const RegisterSchema = z.object({
  pubkey: z.string().min(40), // base64-encoded ed25519 pubkey
  claimed_gb: z.number().int().min(1).max(100_000),
  owner_contact: z.string().max(200).optional().nullable(),
  signature: z.string().min(40), // base64 ed25519 sig over the canonical message
});

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  const parsed = RegisterSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input", details: parsed.error.format() }, { status: 400 });
  }
  const d = parsed.data;

  const message = `omw-register|${d.pubkey}|${d.claimed_gb}`;
  if (!verifyNodeSignature({ pubkeyBase64: d.pubkey, message, signatureBase64: d.signature })) {
    return NextResponse.json({ error: "Invalid signature — pubkey does not match" }, { status: 401 });
  }

  const node = await registerNode({
    pubkeyBase64: d.pubkey,
    claimedGb: d.claimed_gb,
    ownerContact: d.owner_contact,
  });

  return NextResponse.json({
    node_id: node.id,
    status: node.status,
    claimed_gb: node.claimedGb,
    proven_gb: node.provenGb,
    strikes: node.strikes,
  }, { status: 201 });
}

/**
 * GET /api/nodes/register?pubkey=... — convenience for clients to look up their
 * own node_id from a pubkey without re-registering.
 */
export async function GET(req: Request) {
  const url = new URL(req.url);
  const pubkey = url.searchParams.get("pubkey");
  if (!pubkey) {
    return NextResponse.json({ error: "Missing ?pubkey" }, { status: 400 });
  }
  return NextResponse.json({ node_id: nodeIdFromPubkey(pubkey) });
}
