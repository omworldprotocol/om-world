import { db } from "./db";
import { accountId, creditEventId } from "./ids";

// Spec §8 — OM Credit rules v0
export const OMC = {
  initialUserCredits: Number(process.env.OMC_INITIAL_USER_CREDITS ?? 100),
  intentSubmissionCost: Number(process.env.OMC_INTENT_SUBMISSION_COST ?? 1),
  capabilityReward: Number(process.env.OMC_CAPABILITY_REWARD ?? 10),
  patternCreationReward: Number(process.env.OMC_PATTERN_CREATION_REWARD ?? 5),
  patternReuseReward: Number(process.env.OMC_PATTERN_REUSE_REWARD ?? 2),
};

export type OwnerType = "user" | "provider" | "pattern_creator" | "node" | "system";
export type EventType =
  | "intent_submission_debit"
  | "capability_reward"
  | "pattern_creation_reward"
  | "pattern_reuse_reward"
  | "system_grant"
  | "manual_adjustment"
  | "node_storage_reward"
  | "node_compute_reward";

// Phase 1: node storage reward parameters
export const NODE_STORAGE = {
  rewardOmcPerGbDay: Number(process.env.OMW_NODE_STORAGE_REWARD_OMC_PER_GB_DAY ?? 1),
};

// Phase 2: node compute reward parameters
export const NODE_COMPUTE = {
  rewardOmcPerMinute: Number(process.env.OMW_NODE_COMPUTE_PER_MINUTE ?? 0.2),
  capPerJob: Number(process.env.OMW_NODE_COMPUTE_CAP_PER_JOB ?? 60),
};

/**
 * Get or create a credit account. New user accounts get OMC.initialUserCredits as a system_grant.
 */
export async function ensureAccount(ownerId: string, ownerType: OwnerType) {
  const existing = await db.creditAccount.findUnique({
    where: { ownerId_ownerType: { ownerId, ownerType } },
  });
  if (existing) return existing;

  const created = await db.creditAccount.create({
    data: {
      id: accountId(),
      ownerId,
      ownerType,
      balance: 0,
      earned: 0,
      spent: 0,
    },
  });

  if (ownerType === "user" && OMC.initialUserCredits > 0) {
    await recordEvent({
      accountId: created.id,
      amount: OMC.initialUserCredits,
      eventType: "system_grant",
      description: `Initial Genesis MVP grant of ${OMC.initialUserCredits} OMC.`,
    });
    return db.creditAccount.findUniqueOrThrow({ where: { id: created.id } });
  }

  return created;
}

/**
 * Record a credit event and update the account balance atomically.
 * `amount` is signed: positive = credit, negative = debit.
 */
export async function recordEvent(params: {
  accountId: string;
  amount: number;
  eventType: EventType;
  intentId?: string;
  patternId?: string;
  capabilityId?: string;
  executionId?: string;
  nodeId?: string;
  description?: string;
}) {
  return db.$transaction(async (tx) => {
    const account = await tx.creditAccount.findUniqueOrThrow({ where: { id: params.accountId } });
    const isCredit = params.amount >= 0;

    await tx.creditAccount.update({
      where: { id: account.id },
      data: {
        balance: account.balance + params.amount,
        earned: isCredit ? account.earned + params.amount : account.earned,
        spent: !isCredit ? account.spent + Math.abs(params.amount) : account.spent,
      },
    });

    return tx.creditEvent.create({
      data: {
        id: creditEventId(),
        accountId: account.id,
        amount: params.amount,
        eventType: params.eventType,
        intentId: params.intentId,
        patternId: params.patternId,
        capabilityId: params.capabilityId,
        executionId: params.executionId,
        nodeId: params.nodeId,
        description: params.description,
      },
    });
  });
}

// ---------- Higher-level convenience functions ----------

export async function chargeIntentSubmission(opts: {
  userContact: string; // we identify users by contact in MVP
  intentId: string;
}) {
  const account = await ensureAccount(opts.userContact, "user");
  return recordEvent({
    accountId: account.id,
    amount: -OMC.intentSubmissionCost,
    eventType: "intent_submission_debit",
    intentId: opts.intentId,
    description: `Submission cost for ${opts.intentId}`,
  });
}

export async function rewardCapabilityProvider(opts: {
  providerContact: string;
  capabilityId: string;
  executionId: string;
  intentId: string;
}) {
  const account = await ensureAccount(opts.providerContact, "provider");
  return recordEvent({
    accountId: account.id,
    amount: OMC.capabilityReward,
    eventType: "capability_reward",
    capabilityId: opts.capabilityId,
    executionId: opts.executionId,
    intentId: opts.intentId,
    description: `Reward for capability ${opts.capabilityId} on execution ${opts.executionId}`,
  });
}

export async function rewardPatternCreation(opts: {
  creatorContact: string;
  patternId: string;
  intentId: string;
}) {
  const account = await ensureAccount(opts.creatorContact, "pattern_creator");
  return recordEvent({
    accountId: account.id,
    amount: OMC.patternCreationReward,
    eventType: "pattern_creation_reward",
    patternId: opts.patternId,
    intentId: opts.intentId,
    description: `Reward for creating pattern ${opts.patternId}`,
  });
}

export async function rewardPatternReuse(opts: {
  creatorContact: string;
  patternId: string;
  intentId: string;
}) {
  const account = await ensureAccount(opts.creatorContact, "pattern_creator");
  return recordEvent({
    accountId: account.id,
    amount: OMC.patternReuseReward,
    eventType: "pattern_reuse_reward",
    patternId: opts.patternId,
    intentId: opts.intentId,
    description: `Reward for pattern ${opts.patternId} being reused on intent ${opts.intentId}`,
  });
}

/**
 * Phase 1: pay a node for storing bytes proven via a successful challenge.
 * `gbHours` is the amount earned this tick (e.g. `bytes / 1024^3 * (hours_since_last_proof)`).
 * Reward = gbHours * rewardOmcPerGbDay / 24.
 */
// Don't fire per-challenge events for fractional micropayments — accumulate
// silently inside Node.provenGb instead, and only emit a CreditEvent when
// the credit crosses 0.0001 OMC. Otherwise a tiny test blob fires 100s of
// rows per minute, which is index spam without practical value.
const STORAGE_REWARD_MIN_EMIT_OMC = Number(process.env.OMW_NODE_STORAGE_MIN_EMIT_OMC ?? 0.0001);

export async function rewardNodeStorage(opts: {
  nodeId: string;
  patternId: string;
  gbHours: number;
}) {
  if (opts.gbHours <= 0) return null;
  const account = await ensureAccount(opts.nodeId, "node");
  const amount = (opts.gbHours * NODE_STORAGE.rewardOmcPerGbDay) / 24;
  if (amount < STORAGE_REWARD_MIN_EMIT_OMC) return null;
  return recordEvent({
    accountId: account.id,
    amount,
    eventType: "node_storage_reward",
    patternId: opts.patternId,
    description: `Storage reward for node ${opts.nodeId}: ${opts.gbHours.toFixed(6)} GB-hours of pattern ${opts.patternId}`,
  });
}

/**
 * Phase 2: pay a node for completing a compute job.
 * Reward = min(elapsedMinutes * rewardOmcPerMinute, capPerJob).
 */
export async function rewardNodeCompute(opts: {
  nodeId: string;
  executionId: string;
  elapsedSec: number;
}) {
  if (opts.elapsedSec <= 0) return null;
  const account = await ensureAccount(opts.nodeId, "node");
  const minutes = opts.elapsedSec / 60;
  const amount = Math.min(minutes * NODE_COMPUTE.rewardOmcPerMinute, NODE_COMPUTE.capPerJob);
  if (amount <= 0) return null;
  return recordEvent({
    accountId: account.id,
    amount,
    eventType: "node_compute_reward",
    executionId: opts.executionId,
    description: `Compute reward for node ${opts.nodeId}: ${opts.elapsedSec.toFixed(1)}s of execution ${opts.executionId}`,
  });
}
