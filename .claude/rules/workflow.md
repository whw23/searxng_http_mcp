## Project Workflow

- Branching: `dev` is the development branch, `main` is the release branch. All changes go through PRs.
- PR rules: feature → dev → main. Never PR directly to main.
- Copilot review flow: After PR to dev, wait for CI to pass, then confirm Copilot review is submitted (use `gh api repos/{owner}/{repo}/pulls/{number}/reviews` to verify `copilot-pull-request-reviewer[bot]` has posted a review — don't just check comment count). Fix feedback on the same branch, resolve addressed comments, then merge. Delete local branch after merge (remote branch is auto-deleted by GitHub).
- CI: push triggers test.yml. PR to main only runs source branch check (no tests).
- Rebase all local branches (feat/fix/docs/ci etc.) onto latest dev before PR (`git fetch origin && git rebase origin/dev`).
- After push, wait for push-triggered test.yml CI to pass before creating PR.
- Merge strategy: always use merge commit (GitHub: "Create a merge commit", CLI: `gh pr merge --merge`). Never use squash or rebase merge.
- Commit style: Conventional Commits.
- `.github/` directory is protected — fork PRs cannot modify it.
- Review external PRs locally using `scripts/review-pr.sh` (runs tests in isolated Docker container). Never execute untrusted code directly on the host.
- When waiting for CI/Copilot review, use Bash tool's `run_in_background` parameter to poll status (e.g., `gh run watch`). Don't block the conversation with sleep.
- Copilot review comments must be actually fixed before resolving. Never batch-resolve without fixing.
- Manage GitHub Rulesets via `gh api repos/{owner}/{repo}/rulesets` — no need for Web UI.
- Reusable workflow status check names use the format `{caller-job} / {reusable-job}` (e.g., `call-test / test`). Keep this in mind when configuring required checks.
