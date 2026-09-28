#!/usr/bin/env node
// `preinstall` guard: this repo is a pnpm workspace (one lockfile: pnpm-lock.yaml).
// npm/yarn would create a second, divergent lockfile, so they are rejected here.
const agent = process.env.npm_config_user_agent ?? ''

if (!agent.startsWith('pnpm/')) {
  const used = agent.split('/')[0] || 'otro gestor'
  console.error(`\n  Este proyecto usa pnpm, no ${used}.\n  Instala las dependencias con:  pnpm install\n`)
  process.exit(1)
}
