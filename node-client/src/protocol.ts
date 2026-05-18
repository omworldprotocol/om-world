/**
 * Wire-level types shared with the OM World server (see app/api/nodes/*).
 * Keep in lockstep with server zod schemas.
 */

export interface RegisterRequest {
  pubkey: string;
  claimed_gb: number;
  owner_contact?: string | null;
  signature: string;
}

export interface RegisterResponse {
  node_id: string;
  status: "active" | "striked" | "retired";
  claimed_gb: number;
  proven_gb: number;
  strikes: number;
}

export interface HeartbeatRequest {
  node_id: string;
  pubkey: string;
  nonce: number;
  signature: string;
  free_gb?: number;
  confirm?: {
    assignment_id: string;
    sha256: string;
  };
}

export type Work =
  | {
      kind: "store";
      assignment_id: string;
      pattern_id: string;
      expected_sha256: string;
      size_bytes: number;
      blob_base64: string;
    }
  | {
      kind: "challenge";
      assignment_id: string;
      sha256: string;
      range_start: number;
      range_end: number;
    };

export interface HeartbeatResponse {
  ok: boolean;
  node_status: string;
  strikes: number;
  confirmed?: { pattern_id: string } | { error: string } | null;
  work?: Work | null;
}

export interface ProofRequest {
  node_id: string;
  pubkey: string;
  nonce: number;
  signature: string;
  assignment_id: string;
  range_start: number;
  range_end: number;
  range_sha256: string;
}
