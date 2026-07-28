# Contributing to TeamNav

[English](#english) | [简体中文](#简体中文)

## English

Thank you for contributing to TeamNav.

1. Open an issue before starting a large behavioral or architectural change.
2. Fork the repository and create a focused branch from `main`.
3. Keep changes scoped and add tests for behavior changes.
4. Run the relevant checks locally:

```bash
npm run lint
npm run typecheck
npm test
npm run build

cd apps/api
../../.venv/Scripts/python -m pytest -q
../../.venv/Scripts/ruff check app tests alembic ../../deploy/aio/supervisor.py
```

Run `npm run e2e` for user-facing workflows. Docker or deployment changes should also pass the
Compose smoke tests in CI.

By submitting a contribution, you agree that it is licensed under the GNU Affero General Public
License v3.0 or later. Do not include credentials, private user data, or code you do not have the
right to contribute.

Security vulnerabilities must follow [SECURITY.md](SECURITY.md) and must not be reported in public
issues.

## 简体中文

感谢你参与 TeamNav 的开发。

1. 对较大的行为或架构修改，请先创建 Issue 讨论。
2. Fork 仓库，从 `main` 创建一个目标明确的分支。
3. 保持修改范围清晰，并为行为变化补充测试。
4. 在本地运行上面的代码检查；涉及用户流程时还需运行 `npm run e2e`，涉及 Docker 或部署时应确保 CI 中的 Compose 冒烟测试通过。

提交贡献即表示你同意按 GNU Affero General Public License v3.0 或更高版本授权该贡献。请勿提交凭证、用户私密数据或无权贡献的代码。

安全漏洞必须按照 [SECURITY.md](SECURITY.md) 私密报告，不要发布到公开 Issue。
