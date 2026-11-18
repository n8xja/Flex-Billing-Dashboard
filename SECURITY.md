# Security

## Reporting a problem

Please **don't** open a public issue for a security problem. Use GitHub's private reporting instead: on the project page, go to the **Security** tab and click **Report a vulnerability**.

Never paste API credentials, `.env` contents, database files or logs containing customer names into an issue or report. If you need to show an example, replace real names and IDs with made-up ones.

## How the project protects you

- **Read-only API access.** The dashboard only reads from Sophos. Create its credential with the read-only role, so a leaked secret can't change anything.
- **The secret stays on your server.** It lives in `.env`, which Git ignores. The web container is started without it; only the collector container has it.
- **Passwords are hashed.** Sign-ins are stored as bcrypt hashes in `data/users.json`, which only the dashboard's own user can read. Repeated wrong passwords are slowed down.
- **Encrypted traffic.** The proxy serves HTTPS only (TLS 1.2 and 1.3) and redirects plain HTTP. Replace the self-signed certificate with one from your own CA when you can.
- **Not exposed directly.** The dashboard itself isn't published on any port; only the proxy is.

## Recommendations

- Keep the server inside your network or behind a VPN. Don't expose it to the internet.
- Rotate the Sophos API secret on a schedule, and immediately if you think it was exposed.
- Update regularly with `bash update.sh`.
- Include the `data` folder in your server backups; it holds history that can't be re-downloaded.
