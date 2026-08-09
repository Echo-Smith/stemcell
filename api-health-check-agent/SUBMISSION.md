# 提交说明

## 架构选择

项目使用 Node.js 22 实现确定性 API 健康检查 Agent。Node.js 的异步 I/O 和可取消 HTTP 请求适合并发检查多个微服务，同时可以在零运行时第三方依赖的前提下完成 HTTP、JSONL 和测试。

系统分为五层：JSONL Runner、运行时输入校验、HealthCheckAgent、类型化 HealthCheckTool、DiagnosisPolicy。本地 Mock Server 绑定 `127.0.0.1` 随机端口，输入只能声明结构化场景，不能控制 URL。Agent 会真实发起 HTTP 请求，将状态码、业务状态、延迟和错误归一化为证据，再由独立规则层生成引用证据 ID 的建议。

策略层在保留原有逐服务诊断的基础上，计算单次输入中 `unhealthy / total` 的错误率。达到可配置的 `alert_threshold_error_rate`（默认 0.5）时，追加 `HIGH_ERROR_RATE` 聚合诊断并引用所有不健康服务的全部尝试证据。

本项目不调用 LLM。在断网和自动评审环境中，确定性规则更便于验证超时、错误状态和证据引用。

## 运行方式

审查环境需要 Node.js 22，不需要安装依赖或编译：

```bash
node main.js
```

系统按顺序从 stdin 读取逐行 JSON，并在 stdout 为每行输入返回一行 JSON。运行日志只写入 stderr。

运行附带用例：

```bash
node main.js < evaluation/input.jsonl
```

运行测试：

```bash
node --test tests/*.test.js
```

如需修改 TypeScript 源码，可在开发环境执行：

```bash
npm install
npm run build
```

自动评审直接使用已提交的 `dist/` JavaScript，不执行上述开发构建命令。

## 可靠性策略

- 单次 HTTP 请求和整个用例分别有超时预算。
- 超时会中止实际 HTTP 请求，不只是在外层提前返回。
- 并发数有上限，但输出顺序与输入顺序一致。
- 仅 HTTP 502/503/504 和部分瞬时网络错误重试一次。
- 超时、4xx、500、非法响应和业务不健康不重试。
- 首次失败、重试恢复时仍为 `degraded/recovered`，不会被包装为完全健康。
- 单服务失败不阻断其他服务检查。

## 已知限制

- 仅模拟本地 HTTP 微服务，不包含 HTTPS、鉴权、DNS、服务发现、代理和真实跨网络问题。
- 延迟为客户端单次观测值，不代表 SLA 分位数或分布式跟踪。
- 诊断建议基于已知证据和规则，只提供排查方向，不声称已确认根因。
- 仅实现一次受控重试，未实现指数退避、抖动、熔断器和分布式重试预算。
- Mock 状态保存在单进程内存中，不支持多实例共享。
- 错误率基于单次输入的服务快照，不是时间窗口 SLO；未实现跨请求持久化、迟滞或告警抑制。

## evaluation 材料

- `evaluation/manifest.json`：声明运行时与 JSONL 启动命令。
- `evaluation/cases.json`：包含 12 个正常、异常和边界用例。
- `evaluation/io_spec.md`：说明输入输出字段、错误处理和开放式评估标准。
