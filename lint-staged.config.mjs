// Pre-commit checks (run by .husky/pre-commit with --hide-all): exactly the same scripts CI runs,
// so a commit that passes locally passes CI. Unstaged and untracked files are hidden so the scripts
// check exactly what is being committed. Any staged file triggers them.
export default {
  '**': () => ['bash scripts/ci/api.sh', 'bash scripts/ci/web.sh'],
}
