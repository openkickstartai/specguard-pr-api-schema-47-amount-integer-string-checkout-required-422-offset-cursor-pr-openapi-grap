# 🛡️ SpecGuard

**PR-level API schema breaking change detection & design rule enforcement.**

Catch the breaking change *before* it breaks 47 paying customers.

## 🚀 Quick Start

```bash
pip install -r requirements.txt

# Detect breaking changes between two specs
python cli.py diff old-api.yaml new-api.yaml

# Lint API design rules
python cli.py lint api.yaml

# Get consistency score
python cli.py score api.yaml
```

### CI Integration (GitHub Actions)

```yaml
- run: pip install typer rich pyyaml
- run: python cli.py diff main-spec.yaml pr-spec.yaml --block
```

Exit code `1` on breaking changes → PR blocked automatically.

## ✨ What It Detects

| Change | Severity | Example |
|---|---|---|
| Endpoint removed | 🔴 Breaking | `DELETE /orders` disappeared |
| Response field removed | 🔴 Breaking | `email` dropped from `/users` |
| Field type changed | 🔴 Breaking | `amount`: integer → string |
| New required parameter | 🔴 Breaking | `tenant_id` header now required |
| Operation deprecated | 🟡 Deprecation | `GET /v1/users` marked deprecated |
| New endpoint added | 🟢 Compatible | `POST /webhooks` added |

## 🔍 Design Rules Enforced

- **Path naming**: kebab-case (`/user-profiles` not `/User_Profiles`)
- **Field naming**: snake_case (`created_at` not `createdAt`)
- **operationId**: Required on every operation
- **API version**: Must be specified in `info.version`

## 📊 Why Pay for SpecGuard?

One undetected breaking change costs:
- **4-8 hours** of incident response
- **Partner trust** damage (impossible to quantify)
- **$2,000-50,000** in SLA penalties

SpecGuard catches it in the PR for **$49/month**.

## 💰 Pricing

| Feature | Free | Pro $49/mo | Enterprise $399/mo |
|---|:---:|:---:|:---:|
| Breaking change detection | ✅ | ✅ | ✅ |
| Design rule linting | 3 rules | Unlimited | Unlimited |
| JSON output for CI | ✅ | ✅ | ✅ |
| Custom rules (YAML) | ❌ | ✅ | ✅ |
| Multi-spec consistency | ❌ | Up to 10 | Unlimited |
| PR comment bot | ❌ | ✅ | ✅ |
| Slack/Teams alerts | ❌ | ✅ | ✅ |
| GraphQL & Protobuf | ❌ | ❌ | ✅ |
| Historical trend dashboard | ❌ | ❌ | ✅ |
| SSO + audit trail | ❌ | ❌ | ✅ |
| Self-hosted option | ❌ | ❌ | ✅ |
| Support | Community | Email | Dedicated |

## License

BSL 1.1 — Free for teams ≤5. Commercial license required for larger teams.
