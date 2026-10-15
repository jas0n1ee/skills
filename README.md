# skills

把实践中积累的工作方法整理成可复用的 agent skills。每个 skill 独立存放，按任务加载需要的参考资料。

## 已有 skills

| Skill | 用途 |
| --- | --- |
| [jlc-pcb-design](skills/jlc-pcb-design/SKILL.md) | 嘉立创EDA专业版器件选型、原理图、PCB、受控阻抗、装配与制造核查，以及原生MCP工作流 |

## 在另一台电脑安装

以Codex为例，安装第一个skill：

```sh
git clone https://github.com/jas0n1ee/skills.git
mkdir -p ~/.codex/skills
cp -R skills/skills/jlc-pcb-design ~/.codex/skills/
```

若设置了CODEX_HOME，改用其skills子目录。已有同名skill时先检查本地修改，再更新文件，避免覆盖自己的定制。让客户端重新加载skills后，可通过 `$jlc-pcb-design` 调用，也允许自动匹配相关EDA任务。

仓库使用通用SKILL.md目录格式；其它兼容客户端可将同一目录放进该客户端支持的skill目录。安装skill不会安装或启动LCEDA/MCP服务。原生编辑需要本机安装嘉立创EDA专业版，并连接相应MCP；启动命令为 `lceda-pro --mcp stdio`，调用前按skill核查连接与会话。

## 使用边界

- 经验默认值可以被项目约定和用户明确决定覆盖。
- 制造参数保留核查日期和出处；新工艺、报价、优惠与订单要求需要重新确认。
- 版本相关MCP经验用于排查问题，不替代当前工具的help/API。
- 本仓库不包含项目工程、器件库数据库、厂家PDF或个人账户信息。

新增skill放在 `skills/<skill-name>/`，入口为SKILL.md，需要时添加references、scripts或agents元信息。
