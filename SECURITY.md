# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x (Phase 1+) | ✅ Active development |
| < 0.1.0 | ❌ Pre-release |

---

## Reporting a Vulnerability

**Please do NOT file public issues for security vulnerabilities.**

Report security issues privately via:

- **Email:** security@alexj-stl.com
- **GitHub Security Advisories:** [Private vulnerability reporting](https://github.com/AlexJ-StL/epa-knowledge-graph/security/advisories/new)

Include:
1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide a timeline for fix.

---

## Security Model

### Threat Model

| Asset | Threat | Mitigation |
|-------|--------|------------|
| EPA Method PDFs | Malicious PDF exploits | PyMuPDF sandboxed; file size limits; no auto-execution |
| User Queries | Injection (SQL, Prompt) | Parameterized queries; no direct LLM prompt concatenation |
| API Keys (OpenRouter, etc.) | Exposure in logs/code | Never logged; env-only via `pydantic-settings`/`config`; `.env` in `.gitignore` |
| ChromaDB Data | Unauthorized access | Embedded mode = local-only; Cloud mode = API key + tenant isolation |
| PostgreSQL | Credential leak | Connection pooling via `sqlx`; TLS in production |
| Tauri App | Desktop injection | CSP disabled (dev); strict CSP (prod); `tauri-plugin-opener` only |

### Data Handling

| Data Type | Storage | Encryption | Retention |
|-----------|---------|------------|-----------|
| EPA Method Chunks | ChromaDB | At-rest (OS/filesystem) | Until re-ingestion |
| Embeddings | ChromaDB | At-rest | Until re-ingestion |
| Extracted Metadata | ChromaDB + PostgreSQL | At-rest | Until re-ingestion |
| User Queries | Not stored (Phase 1) | N/A | N/A |
| Audit Logs | PostgreSQL | At-rest | 7 years (commercial) |
| API Keys | Environment only | N/A | Rotated per policy |

### Network

- **Python Service:** Binds `127.0.0.1:8001` (not exposed)
- **Rust API:** Binds `127.0.0.1:8080` (configurable)
- **ChromaDB:** Embedded (no network) or `127.0.0.1:8000`
- **PostgreSQL:** Local socket or `127.0.0.1:5432`
- **Tauri:** No backend network exposure (bundled)

---

## Secure Development Practices

### Dependencies

```bash
# Rust: Audit on every CI run
cargo audit

# Python: Check for vulnerabilities
pip-audit -r python/ingestion/requirements.txt

# Node (when UI exists): Audit
npm audit
```

### Code Review Requirements

- All PRs require maintainer review
- Security-sensitive changes (auth, crypto, parsing) require **2 approvals**
- `cargo clippy -D warnings` must pass
- `ruff check` + `mypy --strict` must pass (Python)

### Secrets Management

| Environment | Method |
|-------------|--------|
| Development | `.env` file (gitignored) |
| CI/CD | GitHub Secrets / GitHub Environments |
| Production (Server) | Docker secrets / HashiCorp Vault / AWS Secrets Manager |
| Tauri Bundle | User enters in Settings → stored in OS keychain |

**Never commit:**
- `.env` files
- API keys
- Database passwords
- PGP keys
- `.pem` / `.key` files

---

## Incident Response

1. **Detect** — Monitoring, user reports, dependency alerts (`cargo audit`, `pip-audit`, Dependabot)
2. **Assess** — Severity (CVSS), affected versions, exploitability
3. **Contain** — Disable affected feature, rotate keys, deploy hotfix
4. **Resolve** — Patch, test, release
5. **Communicate** — Security advisory (GitHub), notify affected users
6. **Retrospective** — Root cause, prevent recurrence

---

## Compliance

| Standard | Status | Notes |
|----------|--------|-------|
| SOC 2 Type II | Planned (Phase 5) | Commercial tier (`epa-audit-suite`) |
| GDPR | Designed for | No PII in EPA methods; tenant data isolated |
| NIST 800-53 | Reference | Controls mapped in commercial tier |

---

## Contact

- **Security Email:** security@alexj-stl.com
- **General Issues:** [GitHub Issues](https://github.com/AlexJ-StL/epa-knowledge-graph/issues)
- **Maintainer:** Alex Johnson (@AlexJ-StL)

---

## Responsible Disclosure Hall of Fame

*Contributors who reported security issues responsibly will be listed here (with permission).*