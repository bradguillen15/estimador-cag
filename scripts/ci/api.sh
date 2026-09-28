#!/usr/bin/env bash
# API checks. Single source of truth: CI (`api-tests`) and the pre-commit hook both run this file.
set -euo pipefail
cd "$(dirname "$0")/../.."

uv sync --locked   # fails if uv.lock is out of date with pyproject.toml
uv run pytest
