# GitLab HTTPS：Python API / MCP 运行时信任与重定向

本增量基于 `4674ed545c752cd1220c96ca62baf0d339f3a07b`，对应 Issue #10 的
Python API/MCP 运行时部分。与 PR #12 的本地 URL/workspace 迁移工具独立，
不更改用户部署、不更新真实 `.env`、不修改工作区或 Git 远端。

## 配置

对使用受公共 CA 信任证书的 GitLab，只需配置最终 HTTPS 地址并保持校验：

```dotenv
GITLAB_BASE_URL=https://gitlab.example.com
GITLAB_VERIFY_SSL=true
GITLAB_TRUST_ENV=false
```

私有 CA 可增加：

```dotenv
GITLAB_CA_BUNDLE=/absolute/path/company-ca.pem
```

也支持 `~/.config/...`，但不接受依赖当前工作目录的相对路径。PEM 文件只放
CA 证书，不放私钥；为空、不可读、无效或超过 4 MiB 时拒绝请求。
它会在公共 certifi 根证书基础上增加指定 CA，不会移除现有公共根。

CLI 和 MCP 都使用相同的显式 SSLContext。`GITLAB_TRUST_ENV` 仍控制代理
继承，不需要为了私有 CA 将它设为 true。Python 客户端不再隐式使用
`SSL_CERT_FILE` / `SSL_CERT_DIR`；曾依赖这些变量的用户应显式设置上述选项。
环境变量仍优先于 `.env`，MCP 进程需要重启后才会读取新配置。

## 覆盖范围与兼容性变化

覆盖同步 GitLab API 的 JSON/text/trace，以及异步 MCP 的 JSON/text/job-log
路径。请求发送前核对 scheme、host、port 和配置前缀下的 `/api/v4` 路径。

所有 3xx 响应都被拒绝，包括同源规范化、登录页、跨源和 HTTPS 降级。
拒绝时不读重定向响应体、不追随 Location；即便底层调用意外指定
`follow_redirects=True`，响应 hook 仍会阻止下一次请求。
需要配置最终可直接返回 API 响应的地址，不能依赖 HTTP->HTTPS 跳转。

`GITLAB_VERIFY_SSL=false` 现在会在 Python 客户端建立前报错，不再作为
绕过证书错误的方式。base URL 中的账户密码、query/fragment、特殊编码或
路径穿越会被拒绝。普通 hostname、IPv6、端口及简单 GitLab path prefix 支持。

保留显式 HTTP 配置以兼容尚未迁移的可信内网；它仍是未加密连接，原 doctor
会警告。这个增量没有把 HTTP 变安全，也没有自动升级或回退 endpoint。

## 特别注意：不等于 Native Git 已配置

**本增量的 `GITLAB_CA_BUNDLE` 只配置 Python API/MCP，不会修改 Git 的 CA、
全局 `.gitconfig`、SSL backend、remotes 或代理。** 原生 Git 的 trust store
仍独立；不能把 `actual-coder doctor` 的 API 成功理解为 fetch/push 已验证。

将同一 CA 策略接入 managed Git、验证 Windows Schannel/OpenSSL 行为，以及
正常 doctor 的分层 TLS/Git 诊断，仍是 Issue #10 后续工作。已有 workspaces 的
origin 与 saved MR URL 迁移由 PR #12 处理；它也不等于运行时 CA 配置。

本次不改变 `.actualcoder.yaml` schema，仓库 policy 不能添加 CA 或关闭校验。
不增加 MCP 写操作、模型调用、任务权限、自动 merge 或生产 GitLab 操作。
HTTP 普通错误响应的通用脱敏、OS sandbox、Git URL rewriting 等更广边界未在
本次全面重写。该限制不可被“请求守卫”等同于端到端安全保证所掩盖。

## 验证与上线顺序

测试会临时生成 CA/服务端证书和私钥，只在 loopback 上使用 dummy session，
不提交证书/密钥文件，不连接真实 GitLab。覆盖私有 CA、错误 CA、过期证书、
hostname mismatch、同源/跨源/降级重定向、前缀越界、代理隔离和实际 CLI/MCP 路径。

```bash
uv sync
uv run python -m unittest discover -s tests -v
```

审阅并合入相关 PR 后，在有备份且 workers 停止的窗口完成配置/remote 迁移，
重启 MCP，先验证 API TLS/auth，再独立验证 Git TLS/fetch，最后进行经授权的
测试分支工作流。没有根据单个 API/TLS 成功就推断整个 HTTPS 迁移完成。

## 官方依据

- HTTPX SSL / 显式 SSLContext：https://www.python-httpx.org/advanced/ssl/
- HTTPX 环境变量与 trust_env：https://www.python-httpx.org/environment_variables/
- Git 的独立 TLS 配置：https://git-scm.com/docs/git-config
