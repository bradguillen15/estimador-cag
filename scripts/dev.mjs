#!/usr/bin/env node
// Runs the API (FastAPI on :8000) and the UI (Vite on :5173) together, with prefixed logs.
// Ctrl+C stops both; if either process exits, the other one is stopped too.
import { spawn } from 'node:child_process'

const PROCESSES = [
  { name: 'api', color: 36, command: 'uv', args: ['run', 'uvicorn', 'app.main:app', '--reload'] },
  { name: 'web', color: 35, command: 'pnpm', args: ['--filter', 'estimador-web', 'dev'] },
]

const children = []
let stopping = false

function pipeWithPrefix(stream, target, label) {
  let pending = ''
  stream.setEncoding('utf8')
  stream.on('data', (chunk) => {
    const lines = (pending + chunk).split('\n')
    pending = lines.pop()
    for (const line of lines) target.write(`${label} ${line}\n`)
  })
  stream.on('end', () => pending && target.write(`${label} ${pending}\n`))
}

function stopAll(exitCode) {
  if (stopping) return
  stopping = true
  process.exitCode = exitCode
  for (const child of children) {
    if (child.exitCode === null && child.signalCode === null) child.kill('SIGTERM')
  }
}

for (const { name, color, command, args } of PROCESSES) {
  const label = `\x1b[${color}m[${name}]\x1b[0m`
  const child = spawn(command, args, {
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, FORCE_COLOR: '1' },
    shell: process.platform === 'win32',
  })
  pipeWithPrefix(child.stdout, process.stdout, label)
  pipeWithPrefix(child.stderr, process.stderr, label)

  child.on('error', (error) => {
    process.stderr.write(`${label} no se pudo iniciar \`${command}\`: ${error.message}\n`)
    stopAll(1)
  })
  child.on('exit', (code, signal) => {
    if (!stopping) process.stderr.write(`${label} terminó (${signal ?? `código ${code}`}); deteniendo el resto…\n`)
    stopAll(code ?? 0)
  })
  children.push(child)
}

process.on('SIGINT', () => stopAll(0))
process.on('SIGTERM', () => stopAll(0))
