## Project Workflow

- 分支策略：`dev` 为开发分支，`main` 为发布分支，所有改动通过 PR
- PR 规则：feature → dev → main，不可直接 PR 到 main
- Copilot review 流程：PR 到 dev 后等待 Copilot review（Ruleset 原生触发），在同一分支 push 修复，resolve 已处理的评论，合并后删除本地分支（远程分支由 GitHub 自动删除）
- CI：push 触发 test.yml，PR 到 main 不触发 CI
- commit 风格：Conventional Commits
- `.github/` 目录受保护，fork PR 不可修改
- 本地审查外部 PR 时使用 `scripts/review-pr.sh` 在隔离 Docker 容器中运行测试，不要直接在主机执行不信任的代码
