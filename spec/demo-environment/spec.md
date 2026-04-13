# Demo Environment

Provide a one-command, self-contained local environment that demonstrates
the full SQL-to-ARC pipeline end-to-end without requiring production
credentials, mTLS certificates, or network access to external services.

## Requirements

- [ ] Start with a single command: `docker compose -f compose.demo.yaml up --build`
- [ ] Spin up PostgreSQL and import a small demo dataset (10 investigations)
      without any manual steps
- [ ] Run a mock Middleware API (`middleware-api`) that accepts ARC
      RO-Crate uploads and writes them to a local `demo_output/` directory
- [ ] Run the `sql_to_arc` converter against the demo DB and mock API
- [ ] Converter exits 0 when all 10 investigations are processed; compose
      exits with the converter's exit code (`--exit-code-from sql_to_arc`)
- [ ] Written ARC files are accessible on the host via a bind-mounted
      `demo_output/` volume
- [ ] File ownership of output files matches the host user (via
      `LOCAL_UID`/`LOCAL_GID` environment variables)
- [ ] No secrets, encrypted files, or external network calls required

## Out of Scope

Production credentials, sops-encrypted secrets, mTLS, and Edaphobase
full-dump downloads are the responsibility of the dev environment
(`compose.dev.yaml`), not this demo.

## Edge Cases

`demo.sql` is missing → `postgres` init fails; compose exits non-zero
with a clear log message.

ARC identifier in payload is unsafe (path traversal attempt) → mock API
falls back to a random ID, logs to console, does not write outside
`demo_output/`.

`demo_output/` doesn't exist → mock API creates it on first request.
