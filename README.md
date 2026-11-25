# skills

把实践中积累的工作方法整理成可复用的 agent skills。每个 skill 独立存放，按任务加载需要的参考资料。

## 已有 skills

| Skill | 用途 |
| --- | --- |
| [jlc-pcb-design](skills/jlc-pcb-design/SKILL.md) | 嘉立创EDA专业版器件选型、原理图、PCB、受控阻抗、装配与制造核查，以及原生MCP工作流 |
| [fusion-part-design](skills/fusion-part-design/SKILL.md) | 通过 Fusion MCP 创建、修改与验证可编辑机械零件，覆盖 CNC、3D 打印及原生/制造文件交付 |

## 在另一台电脑安装

以Codex为例，安装第一个skill：

```sh
git clone https://github.com/jas0n1ee/skills.git
mkdir -p ~/.codex/skills
cp -R skills/skills/jlc-pcb-design ~/.codex/skills/
```

若设置了CODEX_HOME，改用其skills子目录。已有同名skill时先检查本地修改，再更新文件，避免覆盖自己的定制。让客户端重新加载skills后，可通过 `$jlc-pcb-design` 调用，也允许自动匹配相关EDA任务。

仓库使用通用SKILL.md目录格式；其它兼容客户端可将同一目录放进该客户端支持的skill目录。安装skill不会安装或启动LCEDA/MCP服务。原生编辑需要本机安装嘉立创EDA专业版，并连接相应MCP；启动命令为 `lceda-pro --mcp stdio`，调用前按skill核查连接与会话。

## Fusion skill 的 Git 同步安装

为了让默认技能目录使用 Git 管理的同一份内容，推荐把仓库放在独立本地目录，再将 `fusion-part-design` 链接到默认技能目录。仓库工作副本通过 Git 同步；“AI化零件”工作区中的 `AGENTS.md`、需求记录和设计文件继续按原约定通过坚果云同步，不搬入 skills 仓库，也不因安装 skill 改写工作区约定。

macOS/Linux 首次安装：

```sh
skill_repo="$HOME/.codex/skill-repos/skills"
skill_dir="${CODEX_HOME:-$HOME/.codex}/skills"
git clone git@github.com:jas0n1ee/skills.git "$skill_repo"
mkdir -p "$skill_dir"
ln -s "$skill_repo/skills/fusion-part-design" "$skill_dir/fusion-part-design"
```

Windows PowerShell 首次安装（目录联接）：

```powershell
$skillRepo = Join-Path $HOME '.codex\skill-repos\skills'
$skillHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
$skillDir = Join-Path $skillHome 'skills'
git clone git@github.com:jas0n1ee/skills.git $skillRepo
New-Item -ItemType Directory -Force -Path $skillDir | Out-Null
New-Item -ItemType Junction -Path (Join-Path $skillDir 'fusion-part-design') -Target (Join-Path $skillRepo 'skills\fusion-part-design')
```

已有仓库或同名技能时，先检查并保留本地改动，不直接重跑首次安装或强制覆盖。链接只涉及本技能，不移动其他技能或 Codex 的 `.system` 目录。无法使用链接时可复制技能目录安装，但后续需要显式更新副本。

后续先在仓库检查 `git status` 并处理本地修改，再执行 `git pull --ff-only`。链接安装会直接使用更新后的文件；让客户端重新加载技能后可用 `$fusion-part-design`，也允许自动匹配机械建模任务。在默认入口执行 `git -C ~/.codex/skills/fusion-part-design status` 可检查其真实 Git 工作副本。

每台机器需分别安装 Fusion 并连接本机 MCP；不能同步旧 session ID、虚拟环境或机器绝对路径代替环境发现。skill 自带的探测脚本只依赖 Python 3.9+ 标准库，连接与使用方式见 [Fusion MCP 参考](skills/fusion-part-design/references/fusion-mcp.md)。

## 使用边界

- 经验默认值可以被项目约定和用户明确决定覆盖。
- 制造参数保留核查日期和出处；新工艺、报价、优惠与订单要求需要重新确认。
- 版本相关MCP经验用于排查问题，不替代当前工具的help/API。
- 本仓库不包含项目工程、器件库数据库、厂家PDF或个人账户信息。

新增skill放在 `skills/<skill-name>/`，入口为SKILL.md，需要时添加references、scripts或agents元信息。
