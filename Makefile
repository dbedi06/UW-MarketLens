# UW MarketLens — one-command runners for grader / new dev convenience.
#
# Works on Windows (with GNU make installed via chocolatey or git-bash)
# and on Unix. Where commands need PowerShell-vs-bash divergence, prefer
# the cross-platform invocation (.\.venv\Scripts\... on Windows works
# fine under git-bash and PowerShell both).

.PHONY: help dev test build smoke install ci tag-release

# --- meta ---
help:
	@echo "UW MarketLens — common commands"
	@echo ""
	@echo "  make install     pip install + npm install"
	@echo "  make test        backend pytest + frontend typecheck"
	@echo "  make build       frontend production build"
	@echo "  make dev         instructions to run both servers"
	@echo "  make smoke       hit /health on local backend"
	@echo "  make ci          run what GitHub Actions runs"
	@echo ""

# --- setup ---
install:
	cd backend && python -m pip install --upgrade pip && pip install -r requirements.txt && pip install pytest
	cd frontend && npm install

# --- test ---
test:
	cd backend && pytest -q
	cd frontend && npx tsc --noEmit

ci:
	cd backend && pytest -q
	cd frontend && npm ci && npx tsc --noEmit && npm run build

# --- build ---
build:
	cd frontend && npm run build

# --- run ---
dev:
	@echo "Two-terminal manual flow (Make can't run them concurrently across OSes cleanly):"
	@echo ""
	@echo "  Terminal 1 (backend):  cd backend && uvicorn app.main:app --reload --port 8000"
	@echo "  Terminal 2 (frontend): cd frontend && npm run dev"
	@echo ""
	@echo "Then open http://localhost:5173"

# --- ad-hoc ---
smoke:
	@curl -s http://localhost:8000/health || echo "(backend not running on :8000 yet)"
