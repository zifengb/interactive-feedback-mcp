# 设计文档：反馈窗口动态标题

**日期**: 2026-03-06  
**状态**: 已批准  
**作者**: AI Assistant + RowanYang

## 背景

当前反馈窗口标题固定为 `"Cursor 交互式反馈 MCP"`，无法区分不同会话的上下文。用户期望窗口标题能显示 Cursor IDE 会话的主题摘要，提升多窗口场景下的辨识度。

## 核心约束

- MCP 协议的 `tools/call` 请求只有 `name` 和 `arguments`，不携带会话标题
- Cursor IDE 的会话标题（Session Tab Title）是内部生成的，不通过 MCP 协议暴露
- AI Agent 在调用 tool 时知道当前会话上下文，可以主动填写参数

## 方案

在 MCP tool 的 `arguments` 中新增可选的 `window_title` 参数，通过参数 `description` 引导 AI Agent 填入会话主题摘要。UI 端增加标题截断和回退逻辑。

### 数据流

```
Cursor AI Agent 调用 tool
  └─ start_feedback(message, predefined_options, window_title="添加用户认证")
       └─ async_launcher.launch_and_wait(message, predefined_options, window_title)
            └─ subprocess: feedback_ui.py --prompt ... --window-title "添加用户认证"
                 └─ FeedbackUI(prompt, predefined_options, window_title)
                      └─ self.setWindowTitle("添加用户认证 - 反馈")
```

### 改动文件

| 文件 | 改动内容 |
|------|----------|
| `server_async.py` | `start_feedback` 和 `interactive_feedback` 新增 `window_title` 可选参数 |
| `server.py` | `launch_feedback_ui` 和 `interactive_feedback` 新增 `window_title` 参数 |
| `async_launcher.py` | `launch_and_wait` 和 `start_feedback_ui` 新增 `window_title` 参数，条件性传递给命令行 |
| `feedback_ui.py` | argparse 新增 `--window-title`，`FeedbackUI` 支持动态标题，新增 `_get_display_title()` 方法 |

### 各层改动详情

#### 1. MCP Tool 层（server_async.py / server.py）

新增参数定义：

```python
window_title: Optional[str] = Field(
    default=None,
    description="反馈窗口标题，建议传入当前会话的主题摘要，"
                "用于在反馈窗口标题栏显示。"
                "请保持简洁，建议不超过 30 个字符。"
)
```

#### 2. 启动器层（async_launcher.py）

`launch_and_wait()` 和 `start_feedback_ui()` 签名新增 `window_title: Optional[str] = None`。

构建命令行参数时条件性添加：

```python
if window_title:
    args.extend(["--window-title", window_title])
```

#### 3. UI 层（feedback_ui.py）

新增 `_get_display_title()` 方法：

```python
DEFAULT_TITLE = "Cursor 交互式反馈 MCP"
MAX_TITLE_LEN = 50

def _get_display_title(self, title: Optional[str]) -> str:
    if not title or not title.strip():
        return self.DEFAULT_TITLE
    
    title = title.strip()
    if len(title) > self.MAX_TITLE_LEN:
        title = title[:self.MAX_TITLE_LEN] + "..."
    
    return f"{title} - 反馈"
```

`__init__` 中调用：

```python
self.setWindowTitle(self._get_display_title(window_title))
```

argparse 新增：

```python
parser.add_argument("--window-title", default=None, help="窗口标题")
```

### 双重保障机制

1. **前端引导**：参数 description 建议 AI 保持简洁（≤30 字符）
2. **后端容错**：UI 端截断超长标题（>50 字符加 "..."），空值回退默认标题

## 测试计划

| 测试场景 | 期望结果 |
|----------|----------|
| 传入正常 title（如 "添加用户认证"） | 窗口显示 "添加用户认证 - 反馈" |
| 不传 title（None） | 窗口显示 "Cursor 交互式反馈 MCP" |
| 传入空字符串 "" | 窗口显示默认标题 |
| 传入纯空格 "   " | 窗口显示默认标题 |
| 传入超长 title（60字符） | 截断为 50字符 + "..." |
| 传入特殊字符（引号、&、<>） | 正常显示，无崩溃 |
| 传入中文标题 | 正常显示 |
| 传入英文标题 | 正常显示 |
| 同步版 server.py 传入 title | 正常显示 |
| 异步版 server_async.py 传入 title | 正常显示 |
| 命令行直接运行 feedback_ui.py --window-title | 正常显示 |

## 验收标准

1. MCP tool 新增 `window_title` 可选参数，不破坏现有调用
2. AI Agent 调用时能自动填写会话主题
3. 窗口标题正确显示传入的标题
4. 未传入时回退显示默认标题
5. 超长标题被正确截断
6. 所有现有测试通过
7. 新增测试用例覆盖以上场景

## 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| AI 不填写 window_title | 中 | 低 | 回退默认标题，功能不受影响 |
| AI 填写的标题不够准确 | 低 | 低 | 即使不完美也比固定标题好 |
| 命令行特殊字符问题 | 低 | 中 | subprocess + argparse 原生处理 + 测试覆盖 |
