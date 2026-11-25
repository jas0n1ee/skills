# Fusion MCP 连接与执行

适用于建立或排查本机 Fusion MCP 连接。这里的历史实例来自 AI 零件工作区 2026-11-09 的实测：Fusion 2706.1.17，内置服务 `http://127.0.0.1:27182/mcp`。地址是探测候选，不能证明新机器或当前进程仍使用它。

## 环境发现

- 先检查已有 Fusion 工具或本机服务配置。Fusion 未启动时可在本次设计任务内启动已安装的应用，然后探测；没有安装或需要用户登录时再说明具体缺项。
- macOS 可用 `pgrep -ifl 'Autodesk Fusion|Fusion360|Fusion 360'` 找进程，用 `lsof -nP -iTCP -sTCP:LISTEN` 核对监听端口与进程；只探测属于 Fusion 的候选地址。
- Windows 可用 PowerShell 的 `Get-Process` 找 Fusion 进程，再用 `Get-NetTCPConnection -State Listen` 按 `OwningProcess` 匹配。不要从另一台机器复制安装路径。
- 使用环回地址；跨机器协作指各机器访问自己的 Fusion，不能把上一台机器的 `127.0.0.1` 当作远程服务。若用户明确指定远程 MCP，另按其服务配置处理，随附脚本仅支持本机。
- 内置 MCP 不依赖用户 `API/AddIns` 目录的外置插件。对 `/mcp` 的 GET 可能返回 405，应通过 POST 握手判断可用性。

## 握手与只读探测

使用 Python 3.9+。从技能实际安装目录找到 `scripts/probe_fusion_mcp.py`；输出目录应位于本机临时工作目录。macOS/Linux 可执行 `python3`，Windows 按实际环境用 `py -3` 或 `python`。

```text
python3 <skill目录>/scripts/probe_fusion_mcp.py --endpoint http://127.0.0.1:27182/mcp --output-dir <临时目录>/fusion-probe
```

脚本会：

1. POST `initialize`，携带 `Content-Type: application/json` 与 `Accept: application/json, text/event-stream`。
2. 保留 `MCP-Session-Id`，后续请求带此头；返回的协议版本也用于后续请求。不将会话 ID 写入文件或 Git。
3. 发送无 `id` 的 `notifications/initialized`，然后读取 `tools/list`（包含分页）。
4. 将握手结果和工具 schema 写到指定临时目录。非 2xx、JSON-RPC error、工具 `isError` 都视为失败，不能只看 HTTP 200。

默认尝试工作区历史使用的 `2024-11-05` 协议，支持已知的 `2025-03-26`、`2025-06-18` 协商结果；需要其他版本时先核实协议并更新客户端，不盲目强行调用。

检查 `tools.json` 的 `fusion_mcp_read` schema 和说明，再准备只查询版本、活动文档或实体信息的 JSON 参数文件：

```text
python3 <skill目录>/scripts/probe_fusion_mcp.py --endpoint <本机MCP地址> --read-arguments <只读参数.json> --output-dir <临时目录>/fusion-state
```

该脚本只调用 `fusion_mcp_read`，不会运行建模脚本、打开/切换文档或导出文件。工具是否存在和参数含义以返回的 schema 为准。首次 `tools/list` 成功不代表目标文档已经验证，仍需读取状态。

若服务不提供 `fusion_mcp_read`，但实际执行工具支持只读脚本，可使用其已声明的只读模式查询状态；不要省略只读检查。脚本的失败退出不自动重试；服务不可达先定位原因，不循环请求。

## 项目中的执行客户端

建模需要在需求目录保留具体脚本和适配本机 schema 的客户端；session、原始工具响应等运行数据放工作区外的临时目录。旧项目客户端可能硬编码机器路径或使用项目内 `tmp/`，只借鉴逻辑，不原样运行。

历史实测的工具调用形式如下，仅在本机 schema 一致时使用：

```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "method": "tools/call",
  "params": {
    "name": "fusion_mcp_execute",
    "arguments": {
      "featureType": "script",
      "object": {
        "script": "import adsk.core\nimport adsk.fusion\n\ndef run(context):\n    app = adsk.core.Application.get()\n    print(app.version)\n",
        "readOnly": true
      }
    }
  }
}
```

上例只读版本；实际建模脚本必须按照工具说明明确启用写入，不能把写操作标作只读。运行前确认脚本路径、目标文档及所有导出路径指向本次需求；通过 JSON 序列化传递脚本文本，不用 shell 拼接脚本文本或带空格的路径。

## 故障与恢复

- 超时只代表没有收到完整响应，不能推断写操作没有执行。保留调用信息，只读查看文档、特征和文件，再决定是否续做。
- 服务器重启或 session 失效时重新握手、重新读取工具 schema；不得直接重放上一条写操作。
- `tools/list`、单个只读调用、建模、保存、导出、重开应分别判断成功。检查 JSON-RPC 错误和工具层错误，也检查 Fusion 特征健康与实际文件内容。
- 导出失败不能以截图充当完成；预览失败也不能否定已核验的实体导出。交付记录准确列出已完成步骤及缺项。
