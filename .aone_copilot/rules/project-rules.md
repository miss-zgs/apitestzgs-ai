---
alwaysApply: true
---

# 项目开发规则（必读）

> 本规则是 `apitestzgs` API 接口自动化测试框架的**最高优先级约束**。
> 无论是人还是 AI，在对本项目进行任何操作前，**必须先阅读并遵守本规则**。

---

## 一、操作前（必读清单）

### 1.1 必须阅读的文档

在对项目进行任何修改前，**必须按顺序阅读**以下文档：

| 顺序 | 文件 | 目的 | 必读程度 |
|------|------|------|---------|
| 1 | `README.md` | 了解项目全貌、结构、运行方式 | ⭐ 必读 |
| 2 | `CHANGELOG.md` | 了解最近做了什么改动 | ⭐ 必读 |
| 3 | `TODO.md` | 了解待办事项，避免重复开发或冲突 | ⭐ 必读 |
| 4 | `BUGFIX.md` | 了解已知 Bug 和修复历史 | ⚡ 涉及修 Bug 时必读 |
| 5 | `config/config.yaml` | 了解当前环境配置 | ⚡ 涉及请求/配置时必读 |

### 1.2 了解项目当前状态

阅读完文档后，需确认以下信息：

- **当前环境**：`config.yaml` 中的 `current_env` 字段（当前为 `test`）
- **最近版本**：`CHANGELOG.md` 中的最新条目
- **待办计划**：`TODO.md` 中未完成的 `[ ]` 项
- **已知 Bug**：`BUGFIX.md` 中状态为 `❌ 待修复` 的条目

### 1.3 项目核心结构认知

```
apitestzgs/
├── config/          → 环境配置（改动需谨慎）
├── utils/           → 核心工具模块（框架的心脏，改动需测试验证）
├── api/             → 接口层基类（一般不需要改）
├── testcases/       → 测试用例文件（最常改动的目录）
├── data/            → 用例数据文件（YAML/JSON/CSV）
├── logs/            → 日志输出（只读，不要手动修改）
├── reports/         → 测试报告（只读，自动生成）
└── docs/            → 项目文档
```

**模块依赖关系**：
```
testcases/ → 调用 utils/case_executor.py
case_executor.py → 调用 http_client.py + assertion.py + context.py
http_client.py → 读取 config/settings.py → 读取 config/config.yaml
data_loader.py → 加载 data/ 目录下的用例文件
```

---

## 二、能不能做（准入判断）

### 2.1 修改范围分级

| 级别 | 目录/文件 | 是否可自由修改 | 要求 |
|------|-----------|--------------|------|
| 🟢 自由 | `data/*.yaml/json/csv` | ✅ 可直接修改 | 格式正确即可 |
| 🟢 自由 | `testcases/test_*.py` | ✅ 可直接修改 | 遵循用例编写规范 |
| 🟡 需验证 | `utils/*.py` | ⚠️ 修改后必须跑测试 | 这是框架核心，改错影响全局 |
| 🟡 需验证 | `config/config.yaml` | ⚠️ 改后确认环境正确 | 不能误改 current_env 为 prod |
| 🟡 需验证 | `testcases/conftest.py` | ⚠️ 修改后必须跑全量测试 | fixture 影响所有用例 |
| 🟡 需验证 | `run.py` / `example_usage.py` | ⚠️ 修改后验证功能正常 | 入口文件，改动需确认运行无误 |
| 🟢 自由 | `docs/*.md` | ✅ 可直接修改 | 项目文档，保持内容准确即可 |
| 🟡 需验证 | `.aone_copilot/rules/*.md` | ⚠️ 修改需记录变更原因 | 规则文件，改动影响所有后续操作 |
| 🔴 禁止 | `logs/` | ❌ 禁止手动修改 | 日志只能由程序写入 |
| 🔴 禁止 | `reports/` | ❌ 禁止手动修改 | 报告只能由 pytest 生成 |
| 🔴 禁止 | `.env` | ❌ 禁止提交到 Git | 含敏感信息 |

### 2.2 环境安全约束

| 规则 | 说明 |
|------|------|
| **禁止在 prod 环境执行写操作** | `current_env: prod` 时，只允许 GET 请求 |
| **敏感信息不入代码** | API Key、密码、Token 必须放 `.env`，通过环境变量引用 |
| **URL 白名单** | 仅允许请求 config.yaml 中已配置的域名，禁止请求任意外部地址 |
| **测试数据不能用真实用户数据** | 用例中的手机号、身份证等必须是虚构的 |

### 2.3 功能变更判断流程

```
我要做一个改动
    ↓
Q1: 这个改动在 TODO.md 里吗？
    ├─ 是 → 继续，完成后勾选 TODO
    └─ 否 → 继续判断 ↓

Q2: 这个改动会影响现有功能吗？
    ├─ 不会（纯新增）→ 直接做，做完加 CHANGELOG
    └─ 会 → 继续判断 ↓

Q3: 影响范围有多大？
    ├─ 只影响单个用例/数据文件 → 直接做，做完跑该用例
    ├─ 影响 utils/ 核心模块 → 做完必须跑全量测试
    └─ 影响项目结构/依赖 → 需要先在 TODO.md 记录计划，评估后再做
```

### 2.4 冲突检查

在开始工作前，检查以下可能的冲突：

- 我要做的事是否和 `TODO.md` 中某个待办重复？
- 我要修改的文件是否在 `BUGFIX.md` 中有相关的待修复 Bug？
- 我要添加的功能是否和 `CHANGELOG.md` 中已有的功能重复？

---

## 三、怎么做（执行规范）

### 3.1 代码风格

| 规范 | 要求 | 示例 |
|------|------|------|
| **命名** | 变量/函数用蛇形命名，类用大驼峰 | `http_client`、`HttpClient` |
| **函数命名** | 动词开头，描述行为 | `send_request`、`load_data`、`assert_status` |
| **变量命名** | 名词，表达含义 | `response_body`、`expected_code` |
| **禁止无意义缩写** | 不允许单字母变量名或自造缩写，但通用技术缩写可保留 | ❌ `r`/`d`/`cb` → ✅ `response`/`data`/`callback`；✅ 允许：`params`/`config`/`resp`/`env`/`url` 等业界通用缩写 |
| **类型标注** | 函数参数和返回值必须标注类型 | `def get(self, url: str) -> requests.Response:` |
| **文档字符串** | 每个函数/类必须有 docstring | 说明功能、参数、返回值 |
| **日志记录** | 关键操作必须记录日志 | 请求发出、响应收到、变量提取、断言结果 |
| **异常处理** | 不允许裸 except，必须指定异常类型 | ❌ `except:` → ✅ `except ValueError as e:` |
| **import 顺序** | 标准库 → 第三方 → 项目内部，各组之间空一行 | — |

### 3.2 文件创建规范

| 文件类型 | 放置目录 | 命名格式 | 示例 |
|---------|---------|---------|------|
| 测试用例代码 | `testcases/` | `test_模块名.py` | `test_login.py` |
| 用例数据（独立接口） | `data/` | `test_功能名.yaml` | `test_order_create.yaml` |
| 用例数据（依赖编排） | `data/` | `test_功能名.yaml` | `test_dependency.yaml`、`test_fliggy_pickup.yaml` |
| 工具模块 | `utils/` | `功能名.py` | `retry_handler.py` |
| 配置文件 | `config/` | `文件名.yaml` | — |
| 文档 | `docs/` | `大写英文名.md` | `DESIGN.md` |
| 入口脚本 | 根目录 | `功能名.py` | `run.py`、`example_usage.py` |

> **历史文件说明**：项目中已存在的文件（如 `data/test_fliggy_pickup.yaml`）即使命名风格与规范略有差异，也**不要求强制重命名**，保持现状即可。新增文件必须遵循上述规范。

### 3.3 用例数据编写规范（YAML）

```yaml
# ✅ 正确示范
- case_name: "登录-正确密码"          # 必填，格式：功能-场景
  method: POST                        # 必填，大写
  url: /api/login                     # 必填，相对路径或完整URL
  headers:                            # 选填
    Content-Type: "application/json"
  json:                               # 选填，POST/PUT 时使用
    username: "testuser"
    password: "Test@123"
  extract:                            # 选填，提取变量
    token: $.data.token               # jsonpath 表达式
  expect:                             # 必填，至少校验 status_code
    status_code: 200
    jsonpath:
      $.code: 0
      $.data.token:
        not_empty: true
```

**用例命名规则**：`功能模块-测试场景`，如：
- `登录-正确密码`
- `登录-错误密码`
- `登录-账号为空`
- `下单-正常下单`
- `下单-缺少必填参数`

**强制要求**：
- 每条用例**必须有** `case_name` 和 `expect.status_code`
- `url` 使用相对路径（会自动拼接 config.yaml 中的 base_url）
- 如果接口域名和全局 `base_url` 不同，在用例中单独指定 `base_url` 字段覆盖，如：
  ```yaml
  - case_name: "飞猪查价"
    base_url: "https://test-gateway-travelswitch.fliggy.com"  # 覆盖全局域名
    method: POST
    url: /open/distribution/xxx/queryPrice
  ```
- 变量引用使用 `${变量名}` 语法
- 日期时间**禁止写死**，必须用动态变量（如 `${tomorrow}`）
- 敏感字段（密码等）使用环境变量 `${ENV_PASSWORD}`

### 3.4 依赖管理规范

| 场景 | 操作 |
|------|------|
| 新增 Python 包 | 必须同时更新 `requirements.txt`，并注明最低版本 |
| 升级已有包 | 先在独立分支验证，确认不影响现有功能 |
| 删除包 | 先全局搜索确认无引用，再从 requirements.txt 移除 |

**requirements.txt 格式**：
```
包名>=最低版本    # 用途说明
```

### 3.5 配置修改规范

修改 `config/config.yaml` 时：

| 规则 | 说明 |
|------|------|
| 不要删除已有环境 | 只能新增环境，不能删除 dev/test/pre/prod |
| 不要随意改 current_env | 特别是不能在提交时留在 prod |
| 新增配置项需加注释 | 说明用途和默认值 |
| 敏感值用环境变量 | `${ENV_VAR}` 语法引用 |

---

## 四、做完后（收尾动作）

### 4.1 测试验证（必须）

| 改动范围 | 测试要求 | 命令 |
|---------|---------|------|
| 单个用例数据文件 | 跑对应用例 | `python3 -m pytest testcases/test_demo.py::对应用例 -v` |
| testcases/ 下的文件 | 跑该测试文件 | `python3 -m pytest testcases/改动文件.py -v` |
| utils/ 下的文件 | 跑全量测试 | `python3 run.py` |
| config/ 下的文件 | 跑全量测试 | `python3 run.py` |
| conftest.py | 跑全量测试 | `python3 run.py` |

**通过标准**：
- 所有用例 PASSED 或 XFAIL（预期失败）
- 无新增 ERROR
- 日志中无意外的 WARNING/ERROR

### 4.2 文档更新

| 改动类型 | 需要更新的文档 |
|---------|--------------|
| 新增功能 | `CHANGELOG.md` 追加条目 + `README.md`（如影响使用方式） |
| 修复 Bug | `BUGFIX.md` 中对应条目状态改为 `✅ 已修复`，补充修复方案 |
| 新增待办 | `TODO.md` 追加条目 |
| 完成待办 | `TODO.md` 中对应条目勾选 `[x]` |
| 新增依赖 | `requirements.txt` + `README.md` 的前置准备部分 |

### 4.3 CHANGELOG 格式

```markdown
## vX.Y.Z（YYYY-MM-DD）

**主题概述**

- **模块名**：具体改动描述
- **模块名**：具体改动描述
```

版本号规则：
- 修 Bug / 小调整 → patch（v1.1.1）
- 新增功能 → minor（v1.2.0）
- 大重构 / 不兼容变更 → major（v2.0.0）

### 4.4 Git 提交规范

**Commit Message 格式**：
```
类型: 简短描述（不超过50字）

可选的详细说明
```

**类型列表**：

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 新增接口响应时间断言` |
| `fix` | 修复 Bug | `fix: 修复飞猪用例日期过期问题` |
| `refactor` | 重构（不影响功能） | `refactor: 合并 context 和 variable_parser 模块` |
| `docs` | 文档变更 | `docs: 更新 README 运行说明` |
| `test` | 测试相关 | `test: 新增登录接口异常用例` |
| `chore` | 杂项（配置、依赖等） | `chore: 升级 pytest 到 7.4.0` |

### 4.5 日志检查

完成修改后，运行一次测试并检查日志：

```bash
# 运行测试
python3 run.py

# 检查今天的日志有无异常
grep -i "error\|exception\|traceback" logs/$(date +%Y-%m-%d).log
```

确认无以下问题：
- 无 Traceback 堆栈（除非是预期的断言失败）
- 无敏感信息明文（密码、Token、密钥）
- 请求都有 `[R-xxxx]` 唯一标识

---

## 五、禁止事项（红线）

### 5.1 绝对禁止清单

| 编号 | 禁止行为 | 原因 |
|------|---------|------|
| ❌ 1 | 在代码中硬编码 API Key / 密码 / Token | 安全风险 |
| ❌ 2 | 将 `.env` 文件提交到 Git | 敏感信息泄露 |
| ❌ 3 | 修改 `current_env` 为 `prod` 并执行写操作 | 可能影响生产数据 |
| ❌ 4 | 删除 `utils/` 下的核心模块而不提供替代 | 框架瘫痪 |
| ❌ 5 | 手动修改 `logs/` 或 `reports/` 目录内容 | 这些是自动生成的证据记录 |
| ❌ 6 | 在用例中使用真实用户的个人信息 | 数据合规风险 |
| ❌ 7 | 不跑测试就提交代码 | 可能引入隐患 |
| ❌ 8 | 在 `data/*.yaml` 中写死日期时间 | 会过期导致全链路失败（参见 BUG-001） |
| ❌ 9 | 引入新依赖但不更新 `requirements.txt` | 其他人/环境无法运行 |
| ❌ 10 | 裸 `except:` 吞掉所有异常 | 隐藏错误，极难排查 |

### 5.2 安全底线

- **密钥管理**：所有密钥/凭证只能通过 `.env` + `python-dotenv` 加载
- **环境隔离**：prod 环境接口地址只能用于只读验证，绝不发送写请求
- **数据安全**：测试数据使用虚构信息，格式正确但内容虚假
- **日志脱敏**：如果日志中出现了密钥/Token，必须排查并修复

---

## 六、特殊场景处理

### 6.1 不确定时怎么办

```
不确定这个改动是否安全？
    ↓
1. 先在 test 环境验证（绝不直接动 prod）
2. 改动前先 git stash 或建分支，保证能回滚
3. 如果是核心模块（utils/），改动范围控制在最小
4. 留下清晰的注释说明为什么这样改
```

### 6.2 紧急修复流程

当线上出现紧急 Bug 时：

```
1. 确认问题 → 在 BUGFIX.md 记录（现象 + 影响范围）
2. 定位原因 → 通过日志 [R-xxxx] 追踪
3. 修复代码 → 最小改动原则
4. 验证修复 → 跑相关用例 + 检查日志
5. 更新文档 → BUGFIX.md 补充修复方案，标记 ✅ 已修复
6. 提交 → git commit -m "fix: 简述修复内容"
```

### 6.3 新增接口用例流程

```
1. 确认接口信息（URL、方法、参数、预期响应）
2. 在 data/ 目录创建或追加 YAML 文件
3. 包含正向用例 + 至少 2 个异常用例
4. 在 testcases/ 中添加对应的 test 函数（或复用 test_demo.py 的数据驱动）
5. 运行验证：python3 -m pytest testcases/xxx.py -v
6. 更新 CHANGELOG.md
```

### 6.4 框架模块扩展流程

要给 `utils/` 新增模块时：

```
1. 确认 TODO.md 中有对应计划（没有则先添加）
2. 在 utils/ 下创建新文件，必须包含模块级 docstring
3. 在 utils/__init__.py 中注册（如果需要）
4. 编写使用示例（可以加到 example_usage.py）
5. 跑全量测试确认无副作用
6. 更新 CHANGELOG.md + 勾选 TODO.md 对应项
```

---

## 七、规则的生效与更新

### 7.1 生效范围

本规则对以下对象有效：
- ✅ 项目所有开发者
- ✅ AI 助手（Aone Copilot 等）
- ✅ CI/CD 流程中的自动化脚本

### 7.2 规则更新流程

如需修改本规则：
1. 提出修改理由
2. 在修改后追加更新记录（文末 Appendix）
3. 通知相关人员

### 7.3 优先级

当本规则与其他文档冲突时，优先级如下：
```
本规则 > README.md > CHANGELOG.md > 代码注释
```

---

## Appendix: 更新记录

| 日期 | 版本 | 改动说明 |
|------|------|---------|
| 2026-06-01 | v1.0 | 初始版本，建立项目全流程规则 |
