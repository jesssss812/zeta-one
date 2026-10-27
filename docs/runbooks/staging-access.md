# Reaching Rho staging

Staging is reachable only from a machine on Rho's VPN, so a cloud session can't reach it. Run
staging work locally and commit summaries of what you find, never raw data or credentials.

1. Connect the OpenVPN profile Rho assigned. Keep the `.ovpn` file outside the repo; `*.ovpn` is
   gitignored anyway.
2. Copy `.env.example` to `.env` and set `RHO_API_TOKEN` to a **staging** token. Tokens are
   environment-specific: a staging token gets `401` from the production API.
3. Run `python3 scripts/staging_check.py`. It sends only GET requests, prints one line per endpoint
   with its status and record count, and writes the raw responses and a `summary.json` to
   `data/snapshots/<timestamp>/` (gitignored). The summary holds no names, emails, addresses or
   account numbers.
4. Use read endpoints only. See [../reference/rho-api.md](../reference/rho-api.md) for what is
   allowed, and record what staging holds in
   [../reference/staging-data.md](../reference/staging-data.md).

## When it fails

| Output | Cause |
| --- | --- |
| `RHO_API_TOKEN is not set in .env` | No `RHO_API_TOKEN=` line with a value in the repo's root `.env` |
| `403` with Cloudflare error 1010 | Cloudflare rejected the client signature. Send a named `User-Agent`; the script does |
| `403` with `missing required scope` | The token lacks that endpoint's scope |
| `401` | The token isn't valid for this host, for example a production token |
| `None` | No connection: check the VPN |

Staging access is temporary: Rho expects to switch it off after the hackathon. Don't assume it
still works at the Hack Fair on Friday.
