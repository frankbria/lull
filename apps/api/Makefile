# apps/api dev tasks.
.PHONY: dev dev-tls

# Run the API locally (localhost only).
dev:
	uv run uvicorn lull_api.main:app --reload

# Serve the API over HTTPS on the tailnet so a standalone Android APK can reach it (#54, dev-only).
# Durable Tailscale-free path is #55. `make dev-tls CHECK=--check` for a dry run.
dev-tls:
	bash scripts/dev-tls.sh $(CHECK)
