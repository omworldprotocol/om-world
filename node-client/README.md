# omw-node — OM World node client v0

Turn your laptop or server into an OM World storage node. The Pattern Library replicates onto your disk; you earn OM Credit (OMC) for proven storage.

**v0 scope: storage only.** Compute offload arrives in Phase 2 of the MVP Wave 2 plan.

## Install

```bash
cd om-world/node-client
npm install
```

## Run against the live MVP

```bash
npm run start -- start --server https://app.omworld.one --gb 5 --contact "@yourhandle"
```

Or against a local dev server:

```bash
OMW_SERVER=http://localhost:3001 npm run start -- start --gb 1 --verbose
```

First run:
1. generates an ed25519 keypair at `~/.omw-node/identity.json` (chmod 600)
2. POSTs `/api/nodes/register` with a signed payload — server returns your `node_id`
3. starts polling `/api/nodes/heartbeat` every 30s (configurable)

## What happens during a poll

Each heartbeat is one of:

- **No work** — the server has nothing for you; sleep until next interval.
- **`kind: "store"`** — you receive a base64 blob of a Pattern. You sha256-verify it, write to `~/.omw-node/blobs/<sha256>`, and confirm on the next heartbeat.
- **`kind: "challenge"`** — server names a `(blob_sha256, byte_range)`; you compute the sha256 of that slice from your local copy and POST it to `/api/nodes/proof`. Match → OMC credited. Mismatch → strike. 3 strikes → status flips to `striked` and you stop earning.

## Earnings model

`OMC_NODE_STORAGE_REWARD_OMC_PER_GB_DAY` (server env, default 1) splits hourly per successful proof: each accepted proof credits `bytes × hours_since_last_proof × rate / 24 / GB`. First proof per assignment earns 0 — only forward credit, no retroactive backfill.

OMC balance is internal to OM World. Not a token. Not transferable in v0.

## Commands

```bash
omw-node start       # register + poll forever
omw-node status      # print local identity, node_id, blob bytes, exit
omw-node help        # usage
```

## Files on disk

```
~/.omw-node/
├── identity.json       # ed25519 keypair (chmod 600)
└── blobs/
    └── <sha256>        # one file per stored Pattern blob
```

## What's deliberately out of scope (v0)

- No Sybil resistance — anyone can spin up nodes. Will gate behind invite/stake before opening public registration.
- No replication factor > 1 — blob lives on the assigned node + on the server.
- No NAT traversal — node polls outbound; server replies. Works behind NAT.
- No GUI.
- No compute capabilities — that's Phase 2.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `register 401: Invalid signature` | Identity file or pubkey corrupted — delete `~/.omw-node/identity.json` and restart |
| `heartbeat 401: Nonce out of acceptable window` | System clock skew > 5 min; sync time |
| `proof MISMATCH` repeatedly | Local blob corrupted/tampered — delete from `~/.omw-node/blobs/` and let server re-issue |
| Node stuck on "no work" | Server has no unstored Patterns; wait for more activity, or run `omw-node status` to confirm registration |

## License

MIT. Subproject is independent of the main om-world Next.js app (separate `package.json`, MIT/Apache deps only — no GPL).
