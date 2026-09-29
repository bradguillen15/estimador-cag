#!/usr/bin/env node
// `preinstall` guard: this repo is a pnpm workspace (one lockfile: pnpm-lock.yaml).
// npm/yarn would create a second, divergent lockfile, so they are rejected here.
const agent = process.env.npm_config_user_agent ?? ''

if (!agent.startsWith('pnpm/')) {
  const used = agent.split('/')[0] || 'another package manager'
  console.error(`\n  This project uses pnpm, not ${used}.\n  Install dependencies with:  pnpm install\n`)
  process.exit(1)
}
