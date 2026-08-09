# API 健康检查 Agent 设计

日期：2026-08-02  
状态：已确认，待实现

## 1. 目标

实现一个可在断网、限时、只读文件系统中运行的 API 健康检查 Agent。程序通过本地 Mock HTTP API 检查模拟微服务，汇总响应状态、延迟和错误，再基于实际检查证据生成确定性诊断建议。

本项目不依赖 LLM。“Agent”表现为受约束的工具调用、故障恢复、证据汇总和诊断策略，避免模型依赖、非确定输出和无法审计的建议。

## 2. 运行时与交付决策

- 运行时：Node.js 22。
- 自动评审命令：`node main.js`。
- 开发源码：TypeScript。
- 运行产物：预编译 JavaScript，随 ZIP 提交。
- 运行阶段零第三方依赖，不包含 `node_modules`。
- 测试使用 Node.js 内置测试运行器。
- `evaluation/manifest.json` 使用平台支持的 `"runtime": "node22"`。

## 3. 架构

```text
stdin JSONL
   ↓
JSONL Runner
   ↓
输入校验与策略归一化
   ↓
HealthCheckAgent
   ├─→ 并发与整体截止时间
   ├─→ HealthCheckTool
   │      ↓
   │   本地 Mock HTTP Server
   └─→ DiagnosisPolicy
          ↓
HealthCheckEvidence + DiagnosticAdvice
   ↓
stdout JSONL
```

职责边界：

- JSONL Runner：保证每个输入行对应一个输出行，将日志限定到 stderr。
- Validation：对未知 JSON 执行运行时校验，TypeScript 静态类型不被当作输入安全边界。
- Mock Server：将结构化模拟场景转换为真实本地 HTTP 响应。
- HealthCheckTool：执行 HTTP 检查并返回证据，不生成诊断建议。
- HealthCheckAgent：负责并发、超时预算、受限重试、输入顺序恢复和状态聚合。
- DiagnosisPolicy：仅根据标准化证据生成规则化诊断。

## 4. 输入契约

stdin 每行必须是一个 JSON 对象。空行、非法 JSON 或不符合契约的对象都必须返回一条结构化 `invalid_input` 结果，不能导致进程退出。

```json
{
  "version": 1,
  "request_id": "mixed-01",
  "services": [
    {
      "name": "orders",
      "mock": {
        "kind": "healthy",
        "delay_ms": 20
      }
    },
    {
      "name": "inventory",
      "mock": {
        "kind": "http_error",
        "status_code": 503,
        "delay_ms": 10
      }
    }
  ],
  "policy": {
    "timeout_ms": 200,
    "overall_timeout_ms": 2000,
    "slow_threshold_ms": 100,
    "max_concurrency": 4,
    "max_attempts": 2
  }
}
```

`mock.kind` 取值：

- `healthy`
- `degraded`
- `unhealthy`
- `http_error`
- `malformed_json`
- `connection_reset`
- `flaky`

超时不是 Mock 类型。测试用例通过使 `delay_ms` 大于 `timeout_ms` 触发真实客户端超时。

## 5. Mock HTTP Server

- 进程启动时绑定 `127.0.0.1` 的随机端口。
- 每个 JSONL 输入为各服务注册临时场景，Mock Server 返回仅供该次检查使用的 URL。
- 输入无法指定主机名、IP 或外部 URL。
- 检查完成后清理该请求的 Mock 状态，避免用例间污染。
- `flaky` 使用请求内独立的尝试计数，第一次返回 503，第二次返回健康。
- Mock Server 不向 stdout 写入访问日志。
- EOF、正常结束或信号终止时关闭服务器。

## 6. 工具契约与证据

```ts
type HealthCheckRequest = {
  service: string;
  url: URL;
  timeoutMs: number;
  attempt: number;
  signal: AbortSignal;
};

type HealthCheckEvidence = {
  evidenceId: string;
  service: string;
  attempt: number;
  latencyMs: number;
  httpStatus: number | null;
  reportedStatus: "healthy" | "degraded" | "unhealthy" | null;
  outcome: "response" | "timeout" | "network_error" | "protocol_error";
  errorCode: string | null;
};
```

HealthCheckTool 不向 Agent 抛出可预期的 HTTP、网络、超时或协议错误。这些情况被归一化为 `HealthCheckEvidence`。编程错误由 JSONL Runner 的顶层异常边界捕获，返回结构化内部错误并记录到 stderr。

## 7. 超时、并发与重试

默认策略：

```json
{
  "timeout_ms": 200,
  "overall_timeout_ms": 2000,
  "slow_threshold_ms": 100,
  "max_concurrency": 4,
  "max_attempts": 2
}
```

输入范围：

- 服务数量 1–20。
- 单次超时 20–2000 ms。
- 整体超时 100–5000 ms。
- 并发数 1–10。
- 最大尝试次数 1–2。
- `slow_threshold_ms` 必须小于 `timeout_ms`。

重试规则：

- 仅对 HTTP 502、503、504 和可识别的暂时性连接错误重试一次。
- 不重试超时、HTTP 4xx、HTTP 500、业务不健康、非法 JSON 和响应契约错误。
- 重试不得超过剩余整体时间预算。
- 第一次失败但第二次成功时，服务状态为 `degraded`，并设置 `recovered: true`。
- 并发完成顺序不影响输出顺序，`checks` 始终与输入 `services` 顺序一致。

## 8. 状态判定

```text
2xx + healthy + 延迟未超阈值  -> healthy
2xx + healthy + 慢响应        -> degraded
2xx + degraded                    -> degraded
2xx + unhealthy                   -> unhealthy
非 2xx / 超时 / 网络错误       -> unhealthy
协议错误 / 非法 JSON             -> unhealthy
首次失败、重试成功           -> degraded + recovered
```

整体状态取所有服务中的最差状态：`healthy < degraded < unhealthy`。错误 HTTP 响应、超时、协议错误和业务不健康都不得被判为健康。

## 9. 输出契约

stdout 每个输入行只输出一行 JSON。

```json
{
  "version": 1,
  "request_id": "mixed-01",
  "overall_status": "unhealthy",
  "summary": {
    "total": 2,
    "healthy": 1,
    "degraded": 0,
    "unhealthy": 1,
    "duration_ms": 47
  },
  "checks": [
    {
      "service": "inventory",
      "status": "unhealthy",
      "recovered": false,
      "attempts": [
        {
          "evidence_id": "inventory:attempt-1",
          "latency_ms": 12,
          "http_status": 503,
          "reported_status": null,
          "outcome": "response",
          "error_code": "HTTP_503"
        }
      ]
    }
  ],
  "diagnoses": [
    {
      "severity": "critical",
      "service": "inventory",
      "code": "UPSTREAM_UNAVAILABLE",
      "evidence_refs": ["inventory:attempt-1"],
      "recommendation": "inventory 在 12 ms 后返回 HTTP 503；建议检查实例状态、上游依赖和近期部署。"
    }
  ]
}
```

每条诊断建议必须：

- 指定服务名；
- 引用至少一个实际 `evidence_id`；
- 在文本中提及实际 HTTP 状态、延迟、超时或错误类型；
- 不宣称已确认根因。

全部健康时返回 `NO_ACTION_REQUIRED` 诊断，引用所有健康证据并说明最大延迟与阈值。

非法输入时返回：

```json
{
  "version": 1,
  "request_id": null,
  "overall_status": "invalid_input",
  "summary": null,
  "checks": [],
  "diagnoses": [],
  "error": {
    "code": "INVALID_INPUT",
    "message": "services must contain between 1 and 20 items",
    "path": "services"
  }
}
```

## 10. 测试策略

三层测试：

1. 工具测试：通过真实本地 HTTP 请求验证状态码、业务状态、延迟、超时、非法 JSON 和连接中断。
2. Agent 测试：验证并发上限、输入顺序、重试策略、状态聚合、`recovered/degraded` 和证据引用。
3. JSONL 测试：验证多行输入、等量输出、非法输入隔离、stdout 无日志以及后续用例不受前一用例失败影响。

`evaluation/cases.json` 提供 10 个用例：

1. 全部健康。
2. 健康与 HTTP 503 混合。
3. HTTP 200 但业务状态 `unhealthy`。
4. 延迟超过慢响应阈值。
5. 延迟超过单次请求超时。
6. 非法 JSON 响应。
7. 连接中断。
8. 503 后重试恢复。
9. 多服务并发且保持输入顺序。
10. 空服务列表或非法策略字段。

延迟和总运行时等非确定值使用 `evaluation_criteria`，不写死精确数字。

## 11. 安全边界

- 只允许程序生成的 `127.0.0.1` Mock URL，不接受用户提供的 URL。
- 不访问外网、数据库、环境密钥、真实客户数据或人工操作。
- 不写入文件系统。
- 单行输入有大小上限；服务数量、超时、并发、重试和响应体大小都有上限。
- 响应体最大 64 KiB，超过上限按协议错误处理。
- stdout 只用于 JSONL 协议输出；运行日志和意外堆栈只写 stderr。
- 不执行 shell、动态代码、用户路径或用户控制的模块加载。

## 12. 已知限制

- 仅验证本地模拟 HTTP 场景，不代表真实生产环境。
- 不覆盖 HTTPS、证书、鉴权、DNS、服务发现、代理或跨网络问题。
- 延迟是客户端单调观测值，不是分布式跟踪或 SLA 统计。
- 诊断为基于状态码、响应体、延迟和请求错误的规则建议，不证明根因。
- 仅有一次受控重试，不实现指数退避、抖动、熔断器或分布式重试预算。
- Mock 场景注册保存在单进程内存中，不用于多实例共享。

## 13. ZIP 根目录

```text
api-health-check-agent.zip
├── README.md
├── package.json
├── tsconfig.json
├── main.js
├── src/
│   ├── contracts.ts
│   ├── validation.ts
│   ├── mock-server.ts
│   ├── health-tool.ts
│   ├── health-agent.ts
│   └── diagnosis-policy.ts
├── dist/
│   └── ...预编译 JavaScript
├── tests/
│   ├── health-tool.test.js
│   ├── health-agent.test.js
│   └── jsonl-runner.test.js
└── evaluation/
    ├── manifest.json
    ├── cases.json
    └── io_spec.md
```

ZIP 根目录不再包一层项目文件夹，不包含 `node_modules`、日志、临时文件、缓存、真实密钥或个人信息。

## 14. 发布验收

发布前必须完成：

```text
node --test
node main.js < evaluation-input.jsonl
unzip -l api-health-check-agent.zip
```

同时验证：

- 所有测试通过。
- 超时用例在可控时间内返回。
- 非 2xx、业务不健康和协议错误不得判为健康。
- 诊断建议引用真实证据 ID 和检查值。
- stdout 每行都可独立解析为 JSON。
- 输出行数与输入行数一致。
- `evaluation/manifest.json`、`evaluation/cases.json` 和 `evaluation/io_spec.md` 存在且格式正确。
- manifest 命令从 ZIP 根目录执行成功。
- ZIP 小于 10 MB，第一层直接包含必需文件。
