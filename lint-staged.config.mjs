// Pre-commit checks (run by .husky/pre-commit): exactly the same scripts CI runs, so a commit that
// passes locally passes CI. lint-staged hides unstaged edits while they run, so they check exactly
// what is being committed. Any staged file triggers them.
export default {
  '**': () => ['bash scripts/ci/api.sh', 'bash scripts/ci/web.sh'],
}
