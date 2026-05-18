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
  /** Phase 2: list of intent_types this node can execute. Empty = storage-only. */
  executor_kinds?: string[];
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
    }
  | {
      kind: "compute";
      work_assignment_id: string;
      execution_id: string;
      executor_kind: string;
      input_json: string;
    };

export interface HeartbeatResponse {
  ok: boolean;
  node_status: string;
  strikes: number;
  confirmed?: { pattern_id: string } | { error: string } | null;
  work?: Work | null;
}

export interface WorkSubmitRequest {
  node_id: string;
  pubkey: string;
  nonce: number;
  signature: string;
  work_assignment_id: string;
  output: unknown;
  output_text: string;
  execution_mode: "fresh" | "adapted" | "placeholder";
  elapsed_sec: number;
}

export interface WorkSubmitResponse {
  ok: boolean;
  execution_id: string;
  pattern_event?: { pattern_id: string; action: "reused" | "created" } | null;
  already_completed?: boolean;
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
