// Pre-commit checks (run by .husky/pre-commit). lint-staged hides unstaged edits while these
// run, so they check exactly what is being committed. Only the touched area is tested:
// the full suite (~11s) still runs in CI on every pull request.
const quote = (files) => files.map((file) => JSON.stringify(file)).join(' ')

const WEB = 'pnpm --filter estimador-web exec'

export default {
  // API code, prompt templates and Python deps: the whole pytest suite takes ~1.5s.
  '{app/**,tests/**,pyproject.toml,uv.lock}': () => 'uv run pytest -q',

  // Web source: lint the staged files and run only the Vitest tests that import them.
  'web/src/**/*.{ts,tsx}': (files) => [
    `${WEB} eslint --max-warnings=0 ${quote(files)}`,
    `${WEB} vitest related --run --passWithNoTests ${quote(files)}`,
  ],

  // Changes that can affect every web test: run the whole web suite.
  '{web/package.json,web/vite.config.ts,web/tsconfig*.json,web/index.html,web/src/index.css,pnpm-lock.yaml}': () =>
    'pnpm test:web',
}
