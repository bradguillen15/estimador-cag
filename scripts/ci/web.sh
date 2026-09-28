#!/usr/bin/env bash
# Web checks. Single source of truth: CI (`web-tests`) and the pre-commit hook both run this file.
# Dependencies must already be installed (CI: `pnpm install --frozen-lockfile`; locally: `pnpm install`).
set -euo pipefail
cd "$(dirname "$0")/../.."

pnpm lint
pnpm test:web
pnpm build   # tsc -b type-checks the app and the tests before bundling
