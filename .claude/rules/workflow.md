## Project Workflow

- 分支策略：`dev` 为开发分支，`main` 为发布分支，所有改动通过 PR
- PR 规则：feature → dev → main，不可直接 PR 到 main
- Copilot review 流程：PR 到 dev 后等待 Copilot review（Ruleset 原生触发），在同一分支 push 修复，resolve 已处理的评论，合并后删除本地分支（远程分支由 GitHub 自动删除）
- CI：push 触发 test.yml，PR 到 main 只跑来源分支检查（不跑测试）
- 所有本地分支（feat/fix/docs/ci 等）在 PR 前先 rebase 到最新 dev（`git fetch origin && git rebase origin/dev`），确保基于最新代码
- 合并方式：始终使用 merge commit（GitHub 上选 "Create a merge commit"，CLI 用 `gh pr merge --merge`），不使用 squash 或 rebase merge，保留分支历史
- commit 风格：Conventional Commits
- `.github/` 目录受保护，fork PR 不可修改
- 本地审查外部 PR 时使用 `scripts/review-pr.sh` 在隔离 Docker 容器中运行测试，不要直接在主机执行不信任的代码
- 等待 CI/Copilot review 时，使用 Bash 工具的 `run_in_background` 参数轮询状态（如 `gh pr checks --watch`），不要用 sleep 阻塞对话
