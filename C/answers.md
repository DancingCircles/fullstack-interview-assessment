# Task C — Xero 集成设计

## 假设与边界

- 使用当前 Xero OAuth 2.0 HTTP API；本文不绑定某个 SDK，HTTP 客户端可以替换。若后续引入 SDK，必须在依赖清单中固定版本，并以该版本对应的 API 文档重新验证请求模型。
- 连接验证和会计资源请求使用 Xero 官方文档定义的 `/connections`、`xero-tenant-id` 和 Bearer 认证约定；基础 URL、资源 ID 与 API 版本作为可配置项，不写死在业务逻辑中。
- 每个内部连接都持久化 `connection_id`、`tenant_id`、加密后的 token、同步游标和版本号。
- 每个 worker 任务只处理一个 tenant；任何日志都以内部连接 ID 为主，而非 token。

## C1：连接验证

1. 使用刚取得或刷新后的 Bearer token 调用 `GET /connections`。
2. 验证目标 `tenant_id` 是返回连接中的有效 tenant，且连接状态仍可用。
3. 以 `Authorization: Bearer <token>` 和动态的 `xero-tenant-id` 调用一个最小的会计读取接口（例如组织信息）。
4. 记录 HTTP 状态、内部 connection ID、tenant ID、token 过期时间和请求关联 ID；绝不记录 access token、refresh token 或 `Authorization` 头。

这把“token 有效”“应用确实连接了该租户”“请求头选中了正确租户”“调用账户有读取资源的权限”拆成可观察的检查。Xero 要求 API 请求带 Bearer token 和 `xero-tenant-id`；tenant 不得跨请求或跨线程全局缓存。

## C2：401 / 403 / 404 决策树

```text
401 → 检查 access token 是否过期、刷新是否原子化、刷新 token 是否已丢失
    → 刷新失败或连接不存在：标记 needs_reauthorisation，停止重试
403 → token 有效；检查 OAuth scopes、调用用户的组织权限、应用连接状态
    → 纠正 scope/权限后才恢复任务，不把它当作临时失败重试
404 → 检查基础 URL、资源 ID、API 版本和 xero-tenant-id
    → 以 /connections 验证 tenant；资源确实不存在则记录为业务结果，不重试
```

刷新使用“每个连接单飞（single-flight）”锁：一条任务刷新并原子持久化新的 access/refresh token，其余任务读取新版本。Xero access token 约 30 分钟有效；refresh token 轮换后必须同时保存新的两者。

## C3：可恢复的增量同步

每个 tenant 有一条带版本号的同步状态记录：`last_successful_modified_at`、`cursor`、`watermark`。任务用一个有意重叠的修改时间窗口读取变更，并在支持的资源请求上发送 `If-Modified-Since`，按分页处理：

1. 开始时记录本轮 `watermark = now()`，从上次成功水位减去小的重叠窗口读取。
2. 每页先把发票 upsert 到内部镜像表；唯一键为 `(tenant_id, xero_invoice_id)`。
3. 同一事务内保存页游标与处理统计；失败只会重放当前页或之后页面。
4. 完成全部页后，才把 `last_successful_modified_at` 推进到本轮 watermark。

这个设计允许重复读取但不产生重复内部记录，也避免在分页中途失败时跳过数据。大租户同步在队列中调度，而不是让用户请求同步等待完成。

## C4：429 与重试

收到 429 时，worker 会停止该 tenant 的新请求，优先遵守 `Retry-After`，再加全抖动的指数退避。每 tenant 使用并发信号量（上限不超过 Xero 的限制），并设定总重试预算和任务截止时间；超过预算时重新调度，不无限循环。

同时记录 `X-DayLimit-Remaining`、`X-MinLimit-Remaining`、`X-AppMinLimit-Remaining` 和限流原因。可重试：429、网络超时、有限次数的 5xx。不可重试：大多数 400 校验错误、401（刷新或重新授权前）、403、确定的 404。

## C5：创建发票时超时

内部订单先拥有不可变的外部引用，例如 `internal_order_id`，并持久化一次同步尝试和状态。在发出创建请求前写 `PENDING`；超时后绝不盲目再创建，而是按该外部引用/发票号码查询 Xero：

- 找到唯一匹配的 Xero 发票：关联其 ID，标记完成；
- 找不到：在退避后安全地再次尝试；
- 找到多条或字段不一致：进入人工对账队列并告警。

每次出站请求、响应和本地状态改变均有关联 ID。这个流程处理“Xero 已成功但响应在网络中丢失”的不确定状态。

## C6：可观测性与安全

**日志与指标**：结构化日志包含 internal connection ID、tenant ID、job ID、order ID、invoice ID、HTTP status、重试次数和速率限制头；指标包含同步延迟、页数、成功/失败数、429 数、token 刷新失败数和对账积压量。对连续认证失败、长时间未推进水位、重试预算耗尽和对账积压设置告警。

**禁止记录**：access token、refresh token、client secret、完整 Authorization 头、客户财务明细和不必要的个人信息。

**Secrets**：client secret 使用部署环境的 secret manager；token 以信封加密保存，密钥轮换有版本号。OAuth refresh token 被替换后，旧值立即失效并从应用状态移除。最小权限访问数据库和 secret manager。

## 参考资料

- [Xero OAuth 授权流程与 token 刷新](https://developer.xero.com/documentation/guides/oauth2/auth-flow)
- [Xero Connections 管理](https://developer.xero.com/documentation/best-practices/managing-connections/connections)
- [Xero token 与 tenant ID 管理](https://developer.xero.com/documentation/best-practices/data-integrity/managing-tokens)
- [Xero OAuth API 限流](https://developer.xero.com/documentation/guides/oauth2/limits/)
