# OM World MVP — Deployment (hetzner-ash + Cloudflare Tunnel)

Target architecture:

```
internet
   │  https://app.omworld.one
   ▼
Cloudflare edge (TLS terminates here)
   │  (cloudflared tunnel)
   ▼
hetzner-ash:3001  (om-world-mvp.service, Next.js)
   │
   ├── prisma/dev.db  (SQLite)
   └── openclaw CLI  (GPT-5.5 via ChatGPT Plus OAuth)
```

Why this setup: server `:443/tcp` is already taken by VLESS Reality VPN (runbook §11.1). Cloudflare Tunnel makes the standard `:443` URL reachable without touching the server's `:443`.

---

## Stage A — Cloudflare side (one-time, mostly browser)

1. Sign in to Cloudflare (free tier is fine).
2. **Add site → `omworld.one`**. Cloudflare will scan and import existing DNS records (the four GitHub Pages A records + the `www` CNAME). Keep them all.
3. Cloudflare shows two assigned nameservers, e.g. `xxx.ns.cloudflare.com` and `yyy.ns.cloudflare.com`. Copy them.
4. **At DynaDot**, change `omworld.one` nameservers to the two Cloudflare ones. (Registration stays at DynaDot — only NS records change.)
5. Wait for Cloudflare to show the zone as **Active** (usually 5–30 min; up to ~2 hours worst case).
6. While waiting, in the Cloudflare dashboard go to **Zero Trust → Networks → Tunnels → Create a tunnel** (Cloudflared connector).
   - Name: `om-world-mvp`
   - Copy the **tunnel token** that Cloudflare shows (`eyJ…`); you'll paste it on the server.
   - You'll add the public-hostname → service mapping after the server side is up.

## Stage B — Server side (hetzner-ash)

SSH in: `ssh hetzner-ash`. As `root`:

### B1. Install cloudflared

```bash
# official binary
curl -L --output cloudflared.deb \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
dpkg -i cloudflared.deb && rm cloudflared.deb
cloudflared --version
```

### B2. Run cloudflared as a service with the tunnel token

```bash
cloudflared service install <PASTE TUNNEL TOKEN HERE>
systemctl status cloudflared
```

This creates `/etc/systemd/system/cloudflared.service` automatically and starts it. The connector should show up in the Cloudflare dashboard within a few seconds.

### B3. Add the public-hostname rule in Cloudflare dashboard

Back in **Zero Trust → Tunnels → om-world-mvp → Public Hostname → Add a public hostname**:

- Subdomain: `app`
- Domain: `omworld.one`
- Service: `HTTP` → `localhost:3001`

Save. Cloudflare will auto-create the DNS CNAME `app.omworld.one → <tunnel-uuid>.cfargotunnel.com`.

### B4. Deploy the Next.js app

```bash
# clone + build + systemd + smoke (idempotent)
bash <(curl -fsSL https://raw.githubusercontent.com/omworldprotocol/om-world/main/scripts/deploy/install.sh)
```

Or, equivalently:

```bash
git clone https://github.com/omworldprotocol/om-world.git /root/om-world
cd /root/om-world
bash scripts/deploy/install.sh
```

### B5. Verify

```bash
# Internal (server-local):
curl http://127.0.0.1:3001/api/summary

# External (public):
curl https://app.omworld.one/api/summary
```

Both should return the dashboard summary JSON.

## Stage C — Ongoing deploys from Mac

After Stage A and B succeed:

```bash
# Mac
cd /Users/feiyang/all_bots/om-world
# make code changes, commit
bash tools/deploy.sh
```

`tools/deploy.sh`:
1. checks `git status` is clean
2. `git push origin main`
3. SSH to hetzner-ash: `git pull`, `npm ci`, `prisma db push`, `npm run build`, `systemctl restart om-world-mvp`
4. smoke-tests `http://127.0.0.1:3001/api/summary`; rolls back to previous commit on failure

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `cloudflared` connector not active in dashboard | `systemctl status cloudflared`; check journalctl. Token may be wrong — re-run `cloudflared service install …` |
| `app.omworld.one` returns Cloudflare 1033 (no origin) | Public hostname rule not added (Stage B3), or service URL wrong |
| Service starts but `/api/summary` 500 | Check `/root/om-world/.env` and `journalctl -u om-world-mvp -n 100` |
| OpenClaw call fails | `openclaw --version` ≥ 2026.5.12; per memory, **never** pass `--gateway` |
| Prisma `db push` complains about drift | `npx prisma db push --accept-data-loss --skip-generate` |
| DNS not propagating | `dig +short ns omworld.one @1.1.1.1` should return Cloudflare NS; `dig +short app.omworld.one @1.1.1.1` should return a Cloudflare IP |

Add an entry to [`HETZNER_ASH_RUNBOOK.md`](../../../HETZNER_ASH_RUNBOOK.md) §2 once live, plus a row in §3 resource table:

```
| om-world-mvp | active | <date> | :3001 + cloudflared tunnel (app.omworld.one) |
```
