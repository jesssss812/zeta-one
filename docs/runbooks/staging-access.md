# Reaching Rho staging

Not yet run end to end. Update this runbook the first time it is.

Staging is reachable only from a machine on Rho's VPN, so a cloud session can't reach it. Run
staging work locally and commit summaries of what you find, never raw data or credentials.

1. Connect the OpenVPN profile Rho assigned. Keep the `.ovpn` file outside the repo; `*.ovpn` is
   gitignored anyway.
2. Copy `.env.example` to `.env` and set `RHO_API_TOKEN` to a **staging** token. Tokens are
   environment-specific: a staging token gets `401` from the production API.
3. Check access with a read call, for example `GET $RHO_API_BASE_URL/business` with
   `Authorization: Bearer $RHO_API_TOKEN`. Don't print the token or echo the header.
4. Use read endpoints only. See [../reference/rho-api.md](../reference/rho-api.md) for what is
   allowed.

Staging access is temporary: Rho expects to switch it off after the hackathon. Don't assume it
still works at the Hack Fair on Friday.
