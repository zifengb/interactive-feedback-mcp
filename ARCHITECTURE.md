# 🏗️ Interactive Feedback MCP 架构与功能说明文档

> 本文档旨在帮助开发者快速理解项目的架构设计、功能逻辑和代码结构，以便更高效地进行二次开发和维护。

---

## 📋 目录

1. [项目概述](#项目概述)
2. [核心价值](#核心价值)
3. [项目蓝图](#项目蓝图)
4. [系统架构](#系统架构)
5. [核心模块说明](#核心模块说明)
6. [功能时序图](#功能时序图)
7. [类结构图](#类结构图)
8. [数据流图](#数据流图)
9. [技术栈](#技术栈)
10. [开发者快速入门](#开发者快速入门)

---

## 项目概述

**Interactive Feedback MCP** 是一个基于 MCP (Model Context Protocol) 的服务器，专为 AI 辅助开发工具（如 Cursor、Cline、Windsurf）设计。它实现了 **人机协作（Human-in-the-Loop）** 工作流程，允许 AI 在执行任务过程中暂停并向用户请求反馈或澄清。

### 核心理念

在传统的 AI 辅助开发中，每次与 LLM 的交互都被计为一个独立请求（如 Cursor 的 500 次/月限额）。当 AI 基于模糊指令猜测并生成错误代码时，用户需要多次纠正，导致请求浪费。

本项目通过 **工具调用（Tool Call）** 机制，让 AI 可以：
- 🤔 在不确定时主动询问用户
- 📝 在完成任务前请求确认
- 🔄 在单次请求中进行多轮交互

---

## 核心价值

```mermaid
mindmap
  root((Interactive Feedback MCP))
    💰 成本优化
      减少无效 API 调用
      500 次当 2500 次用
      避免猜测性代码生成
    ✅ 质量提升
      行动前先澄清
      减少错误代码
      更精准的输出
    ⏱️ 效率提升
      快速确认胜过调试
      减少来回修改
      实时人机对话
    🎮 更好的协作
      双向沟通
      用户掌控全局
      灵活的交互方式
```

---

## 项目蓝图

### 生态位置图

```mermaid
C4Context
    title Interactive Feedback MCP 生态位置

    Person(user, "开发者", "使用 AI 辅助工具的开发者")
    
    System_Boundary(ai_tools, "AI 开发工具") {
        System(cursor, "Cursor", "AI 代码编辑器")
        System(cline, "Cline", "VS Code AI 扩展")
        System(windsurf, "Windsurf", "AI 开发环境")
    }
    
    System_Boundary(mcp_server, "MCP 服务器") {
        System(feedback_server, "Interactive Feedback MCP", "本项目：人机交互反馈服务")
    }
    
    System_Boundary(ui_layer, "用户界面") {
        System(feedback_ui, "反馈 UI", "PySide6 图形界面")
    }
    
    Rel(user, cursor, "发送编程请求")
    Rel(user, cline, "发送编程请求")
    Rel(user, windsurf, "发送编程请求")
    
    Rel(cursor, feedback_server, "调用 interactive_feedback 工具")
    Rel(cline, feedback_server, "调用 interactive_feedback 工具")
    Rel(windsurf, feedback_server, "调用 interactive_feedback 工具")
    
    Rel(feedback_server, feedback_ui, "启动 UI 进程")
    Rel(feedback_ui, user, "显示问题，收集反馈")
    Rel(feedback_ui, feedback_server, "返回用户反馈")
```

### 文件结构图

```mermaid
graph TD
    subgraph 项目根目录
        A[📄 server.py] -->|MCP 服务端| B[FastMCP 框架]
        C[📄 feedback_ui.py] -->|GUI 界面| D[PySide6/Qt]
        E[📄 pyproject.toml] -->|项目配置| F[依赖管理]
        G[📄 README.md] -->|中文文档| H[使用说明]
        I[📄 README.en.md] -->|英文文档| H
        J[📁 images/] -->|资源文件| K[图标等]
    end
    
    style A fill:#e1f5fe
    style C fill:#fff3e0
    style E fill:#f3e5f5
```

---

## 系统架构

### 三层架构图

```mermaid
graph TB
    subgraph Layer1["🖥️ AI 工具层"]
        direction LR
        Cursor[Cursor IDE]
        Cline[Cline Extension]
        Windsurf[Windsurf]
    end
    
    subgraph Layer2["⚙️ MCP 服务层"]
        direction TB
        Server[server.py<br/>FastMCP 服务器]
        Tool[interactive_feedback<br/>工具函数]
        Launcher[launch_feedback_ui<br/>UI 启动器]
        
        Server --> Tool
        Tool --> Launcher
    end
    
    subgraph Layer3["🎨 UI 层"]
        direction TB
        MainWindow[FeedbackUI<br/>主窗口]
        TextEdit[FeedbackTextEdit<br/>输入框]
        Preview[图片预览区]
        Options[预设选项区]
        
        MainWindow --> TextEdit
        MainWindow --> Preview
        MainWindow --> Options
    end
    
    subgraph IPC["📦 进程间通信"]
        TempFile[临时 JSON 文件]
        Args[命令行参数]
    end
    
    Layer1 -->|"MCP Protocol<br/>(stdio)"| Layer2
    Layer2 -->|"subprocess<br/>启动"| Layer3
    Layer2 <-->|"读写"| TempFile
    Layer3 -->|"写入"| TempFile
    Launcher -->|"传递"| Args
    Args -->|"接收"| MainWindow
    
    style Layer1 fill:#e3f2fd
    style Layer2 fill:#fff8e1
    style Layer3 fill:#f3e5f5
    style IPC fill:#e8f5e9
```

### 组件依赖图

```mermaid
graph LR
    subgraph 核心依赖
        FastMCP[fastmcp ≥2.5.1]
        PySide6[pyside6 ≥6.8.2.1]
        Markdown[markdown ≥3.4.0]
        Psutil[psutil ≥7.0.0]
    end
    
    subgraph 项目模块
        Server[server.py]
        UI[feedback_ui.py]
    end
    
    Server --> FastMCP
    Server --> UI
    UI --> PySide6
    UI --> Markdown
    
    style FastMCP fill:#4caf50,color:#fff
    style PySide6 fill:#2196f3,color:#fff
    style Markdown fill:#ff9800,color:#fff
```

### 实例模式说明

本项目采用 **每个 AI 工具连接对应一个独立 Server 进程** 的单实例模式。

```mermaid
graph TD
    subgraph "AI 工具实例"
        C1["Cursor IDE #1"]
        C2["Cursor IDE #2"]
        C3["Cline Extension"]
    end
    
    subgraph "独立 Server 进程"
        S1["server.py 进程 #1<br/>PID: 1234"]
        S2["server.py 进程 #2<br/>PID: 5678"]
        S3["server.py 进程 #3<br/>PID: 9012"]
    end
    
    subgraph "UI 子进程（按需启动）"
        UI1["feedback_ui.py"]
        UI2["feedback_ui.py"]
        UI3["feedback_ui.py"]
    end
    
    C1 -->|"stdio 通信"| S1
    C2 -->|"stdio 通信"| S2
    C3 -->|"stdio 通信"| S3
    
    S1 -->|"subprocess.run<br/>同步阻塞"| UI1
    S2 -->|"subprocess.run<br/>同步阻塞"| UI2
    S3 -->|"subprocess.run<br/>同步阻塞"| UI3
    
    style C1 fill:#e3f2fd
    style C2 fill:#e3f2fd
    style C3 fill:#e3f2fd
    style S1 fill:#fff8e1
    style S2 fill:#fff8e1
    style S3 fill:#fff8e1
    style UI1 fill:#f3e5f5
    style UI2 fill:#f3e5f5
    style UI3 fill:#f3e5f5
```

#### 关键特性

| 特性 | 说明 |
|------|------|
| **传输协议** | `stdio` - 标准输入输出流，每个客户端独立进程 |
| **进程模型** | 1:1 映射 - 每个 MCP 客户端启动独立的 `server.py` 进程 |
| **UI 启动方式** | `subprocess.run()` 同步阻塞，等待用户完成反馈 |
| **状态管理** | 无状态设计，每次工具调用独立处理 |
| **并发处理** | 单进程内串行，不同客户端并行（进程隔离） |

#### 设计优势

1. **简单可靠**：无需复杂的会话管理和状态同步
2. **资源隔离**：不同 AI 工具的反馈窗口互不干扰
3. **阻塞保证**：确保用户必须完成反馈后 AI 才继续执行
4. **故障隔离**：单个进程崩溃不影响其他客户端

#### 潜在扩展方向

如需支持多客户端共享单一 Server 实例，可考虑：
- 改用 HTTP/SSE 或 WebSocket 传输
- 实现会话 ID 管理
- 使用异步 UI 启动（`subprocess.Popen` + 回调）

---

## 核心模块说明

### server.py - MCP 服务端

```mermaid
graph TD
    subgraph server.py
        MCP["FastMCP 实例 - Interactive Feedback MCP"]
        
        subgraph 核心函数
            LaunchUI["launch_feedback_ui - 启动 UI 进程"]
            ToolFunc["interactive_feedback - MCP 工具"]
        end
        
        subgraph 功能
            CreateTemp[创建临时文件]
            RunSubprocess[运行子进程]
            ReadResult[读取结果]
            ParseImages[解析图片]
        end
    end
    
    MCP --> ToolFunc
    ToolFunc --> LaunchUI
    LaunchUI --> CreateTemp
    CreateTemp --> RunSubprocess
    RunSubprocess --> ReadResult
    ReadResult --> ParseImages
    ParseImages --> ToolFunc
```

**核心流程说明：**

| 步骤 | 函数/操作 | 说明 |
|------|----------|------|
| 1 | `mcp = FastMCP()` | 初始化 MCP 服务器实例 |
| 2 | `@mcp.tool()` | 注册 `interactive_feedback` 工具 |
| 3 | `launch_feedback_ui()` | 创建临时 JSON 文件，启动 UI 子进程 |
| 4 | `subprocess.run()` | 以非阻塞方式运行 `feedback_ui.py` |
| 5 | 读取 JSON | 从临时文件读取用户反馈 |
| 6 | 返回结果 | 返回文本和/或 Image 对象 |

### feedback_ui.py - GUI 界面

```mermaid
graph TD
    subgraph feedback_ui.py
        subgraph 主窗口类
            FeedbackUI[FeedbackUI<br/>QMainWindow]
            CreateUI[_create_ui<br/>构建界面]
            SubmitFB[_submit_feedback<br/>提交反馈]
            MDRender[_convert_markdown_to_html<br/>Markdown 渲染]
        end
        
        subgraph 文本编辑类
            FeedbackTextEdit[FeedbackTextEdit<br/>QTextEdit]
            ImagePaste[insertFromMimeData<br/>粘贴图片]
            Base64Conv[_convert_image_to_base64<br/>图片编码]
        end
        
        subgraph UI 组件
            DescText[描述文本区<br/>QTextBrowser]
            OptCheck[预设选项<br/>QCheckBox]
            ImgPreview[图片预览<br/>QFrame]
            InputText[输入框<br/>FeedbackTextEdit]
            Buttons[按钮组<br/>提交/取消]
        end
    end
    
    FeedbackUI --> CreateUI
    FeedbackUI --> SubmitFB
    FeedbackUI --> MDRender
    FeedbackTextEdit --> ImagePaste
    ImagePaste --> Base64Conv
    
    CreateUI --> DescText
    CreateUI --> OptCheck
    CreateUI --> ImgPreview
    CreateUI --> InputText
    CreateUI --> Buttons
```

**核心功能说明：**

| 组件 | 功能 | 实现细节 |
|------|------|----------|
| **描述区** | 显示 AI 的问题/提示 | 自动检测 Markdown 并渲染，支持 Emoji |
| **预设选项** | 快速选择常用回答 | 复选框列表，可多选 |
| **图片预览** | 显示粘贴的图片 | 缩略图显示，支持删除 |
| **输入框** | 自由输入反馈 | 支持 Ctrl+Enter 提交，粘贴图片 |
| **快捷键** | 提升操作效率 | Ctrl+/-/0 字体缩放，Ctrl+Alt+H 行高 |

---

## 功能时序图

### 完整交互流程

```mermaid
sequenceDiagram
    autonumber
    
    participant User as 👤 开发者
    participant AI as 🤖 AI 工具<br/>(Cursor/Cline)
    participant MCP as ⚙️ MCP 服务器<br/>(server.py)
    participant UI as 🎨 反馈 UI<br/>(feedback_ui.py)
    participant File as 📄 临时 JSON 文件
    
    User->>AI: 发送编程请求<br/>"帮我写一个排序函数"
    
    Note over AI: AI 判断需要更多信息
    
    AI->>MCP: 调用 interactive_feedback<br/>message: "请问需要哪种排序算法？"<br/>predefined_options: ["快速排序", "归并排序", "堆排序"]<br/>window_title: "实现排序算法"
    
    MCP->>File: 创建临时 JSON 文件
    MCP->>UI: subprocess.run()<br/>传递 --prompt, --predefined-options, --output-file
    
    Note over UI: 显示反馈窗口
    
    UI-->>User: 显示问题和预设选项
    User->>UI: 选择 "快速排序"<br/>补充 "需要支持泛型"
    
    opt 用户粘贴图片
        User->>UI: Ctrl+V 粘贴截图
        UI->>UI: 转换为 Base64
    end
    
    User->>UI: 点击提交 / Ctrl+Enter
    UI->>File: 写入 JSON 结果<br/>{interactive_feedback, images}
    UI-->>MCP: 进程退出
    
    MCP->>File: 读取 JSON 结果
    MCP->>MCP: 解析文本和图片
    MCP-->>AI: 返回 (文本, Image...)
    
    Note over AI: AI 继续处理<br/>基于用户反馈生成代码
    
    AI-->>User: 返回快速排序泛型实现
    
    Note over User,AI: 整个过程只消耗 1 次 API 请求!
```

### 用户界面交互流程

```mermaid
sequenceDiagram
    autonumber
    
    participant User as 👤 用户
    participant Window as 🪟 主窗口<br/>FeedbackUI
    participant Text as 📝 输入框<br/>FeedbackTextEdit
    participant Preview as 🖼️ 图片预览区
    
    Window->>Window: 初始化窗口<br/>加载保存的字体大小/行高
    Window->>Window: 渲染 Markdown 提示
    Window-->>User: 显示窗口（置顶）
    
    alt 选择预设选项
        User->>Window: 点击复选框
        Window->>Window: 记录选中状态
    end
    
    alt 输入自由文本
        User->>Text: 键入文字
    end
    
    alt 粘贴图片
        User->>Text: Ctrl+V 粘贴
        Text->>Text: 检测 MIME 类型
        Text->>Text: 转换为 Base64
        Text->>Preview: 发送 image_pasted 信号
        Preview->>Preview: 创建缩略图
        Preview-->>User: 显示图片预览
    end
    
    alt 删除图片
        User->>Preview: 点击 × 按钮
        Preview->>Text: 从 image_data 中删除
        Preview->>Preview: 移除预览控件
    end
    
    alt 字体调整
        User->>Window: Ctrl+ 放大
        User->>Window: Ctrl- 缩小
        User->>Window: Ctrl+0 重置
        Window->>Window: 更新所有控件字体
        Window->>Window: 保存设置
    end
    
    User->>Window: 点击提交 / Ctrl+Enter
    Window->>Window: 收集选中选项
    Window->>Text: 获取文本和图片
    Window->>Window: 组装 FeedbackResult
    Window->>Window: 关闭窗口
```

---

## 类结构图

```mermaid
classDiagram
    class FastMCP {
        +name: str
        +log_level: str
        +tool() decorator
        +run(transport: str)
    }
    
    class FeedbackResult {
        <<TypedDict>>
        +interactive_feedback: str
        +images: List~str~
    }
    
    class FeedbackUI {
        -prompt: str
        -predefined_options: List~str~
        -window_title: Optional~str~
        -feedback_result: FeedbackResult
        -settings: QSettings
        -line_height: float
        -description_text: QTextBrowser
        -feedback_text: FeedbackTextEdit
        -option_checkboxes: List~QCheckBox~
        -images_container: QFrame
        +__init__(prompt, predefined_options, window_title)
        +_get_display_title(title) str
        +run() FeedbackResult
        -_create_ui()
        -_setup_shortcuts()
        -_submit_feedback()
        -_is_markdown(text) bool
        -_convert_markdown_to_html(text) str
        -_convert_text_to_html(text) str
        -_preprocess_text(text) str
        -_toggle_line_height()
        -adjust_font_size(factor)
        -reset_font_size()
        -_on_image_pasted(pixmap)
    }
    
    class FeedbackTextEdit {
        -image_data: List~dict~
        -device_pixel_ratio: float
        -max_image_width: int
        -max_image_height: int
        +image_pasted: Signal~QPixmap~
        +keyPressEvent(event)
        +insertFromMimeData(source_data)
        +get_image_data() List~dict~
        -_convert_image_to_base64(image) dict
    }
    
    class QMainWindow {
        <<Qt>>
    }
    
    class QTextEdit {
        <<Qt>>
    }
    
    FeedbackUI --|> QMainWindow
    FeedbackTextEdit --|> QTextEdit
    FeedbackUI *-- FeedbackTextEdit : contains
    FeedbackUI ..> FeedbackResult : produces
    
    note for FastMCP "MCP 服务器框架\n处理工具注册和调用"
    note for FeedbackUI "主窗口类\n管理整个 UI 和交互逻辑"
    note for FeedbackTextEdit "自定义文本编辑器\n支持图片粘贴"
```

---

## 数据流图

### 输入数据流

```mermaid
flowchart LR
    subgraph AI工具
        Request[AI 请求反馈]
    end
    
    subgraph MCP服务器
        Tool[interactive_feedback]
        Launch[launch_feedback_ui]
    end
    
    subgraph 命令行参数
        Prompt["--prompt<br/>问题文本"]
        Options["--predefined-options<br/>预设选项 (|||分隔)"]
        Output["--output-file<br/>输出文件路径"]
        Title["--window-title<br/>窗口标题(可选)"]
    end
    
    subgraph UI进程
        Parse[解析参数]
        Window[创建窗口]
    end
    
    Request -->|"message, predefined_options, window_title"| Tool
    Tool --> Launch
    Launch --> Prompt
    Launch --> Options
    Launch --> Output
    Launch --> Title
    Prompt --> Parse
    Options --> Parse
    Output --> Parse
    Title --> Parse
    Parse --> Window
```

### 输出数据流

```mermaid
flowchart LR
    subgraph UI用户交互
        Select[选择预设选项]
        Input[输入文本]
        Paste[粘贴图片]
    end
    
    subgraph 数据处理
        Combine[组合选项和文本]
        Encode[Base64 编码图片]
    end
    
    subgraph JSON输出
        Result["FeedbackResult<br/>{<br/>  interactive_feedback: string,<br/>  images: string[]<br/>}"]
    end
    
    subgraph MCP返回
        Parse[解析 JSON]
        Convert[转换 Image 对象]
        Return["返回 Tuple<br/>(text, Image...)"]
    end
    
    Select --> Combine
    Input --> Combine
    Paste --> Encode
    Combine --> Result
    Encode --> Result
    Result -->|"写入临时文件"| Parse
    Parse --> Convert
    Convert --> Return
```

### 图片处理流程

```mermaid
flowchart TD
    subgraph 粘贴检测
        A[用户粘贴] --> B{检测 MIME 类型}
        B -->|hasImage| C[获取图片数据]
        B -->|hasText| D[插入文本]
        B -->|hasHtml| E[插入 HTML]
    end
    
    subgraph 图片处理
        C --> F[QPixmap/QImage]
        F --> G{是否 QPixmap?}
        G -->|是| H[直接使用]
        G -->|否| I[转换为 QPixmap]
        H --> J[保存到 QBuffer]
        I --> J
        J --> K[Base64 编码]
        K --> L[生成唯一文件名]
        L --> M[添加到 image_data 列表]
    end
    
    subgraph UI显示
        M --> N[发送 image_pasted 信号]
        N --> O[创建缩略图]
        O --> P[添加删除按钮]
        P --> Q[显示在预览区]
    end
    
    subgraph 最终输出
        M --> R[提交时提取 base64]
        R --> S[写入 JSON]
    end
```

---

## 技术栈

```mermaid
graph TD
    subgraph 运行环境
        Python["Python 3.10+"]
        UV["uv 包管理器"]
    end
    
    subgraph 核心框架
        FastMCP["FastMCP<br/>MCP 服务器框架"]
        PySide6["PySide6 (Qt6)<br/>GUI 框架"]
    end
    
    subgraph 功能库
        Markdown["markdown<br/>Markdown 渲染"]
        Psutil["psutil<br/>进程管理"]
    end
    
    subgraph 协议
        MCP["MCP Protocol<br/>模型上下文协议"]
        STDIO["stdio<br/>标准输入输出传输"]
    end
    
    Python --> FastMCP
    Python --> PySide6
    Python --> Markdown
    Python --> Psutil
    
    FastMCP --> MCP
    MCP --> STDIO
    
    style Python fill:#3776ab,color:#fff
    style FastMCP fill:#4caf50,color:#fff
    style PySide6 fill:#41cd52,color:#fff
    style MCP fill:#ff9800,color:#fff
```

### 依赖版本要求

| 依赖包 | 最低版本 | 用途 |
|--------|----------|------|
| `fastmcp` | ≥2.5.1 | MCP 服务器框架 |
| `pyside6` | ≥6.8.2.1 | Qt6 GUI 框架 |
| `markdown` | ≥3.4.0 | Markdown 转 HTML |
| `psutil` | ≥7.0.0 | 进程信息获取 |

---

## 开发者快速入门

### 1. 环境准备

```bash
# 克隆仓库
git clone https://github.com/kele527/interactive-feedback-mcp.git
cd interactive-feedback-mcp

# 安装 uv（如果未安装）
pip install uv

# 安装依赖
uv sync
```

### 2. 本地测试 UI

```bash
# 直接运行 UI 测试
uv run python feedback_ui.py --prompt "这是一个测试问题" --predefined-options "选项1|||选项2|||选项3"
```

### 3. 配置 MCP 客户端

在 Cursor 的 `mcp.json` 或 Claude Desktop 的 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "interactive-feedback": {
      "command": "uv",
      "args": ["--directory", "/your/path/to/interactive-feedback-mcp", "run", "server.py"],
      "timeout": 600,
      "autoApprove": ["interactive_feedback"]
    }
  }
}
```

### 4. 扩展开发指南

#### 添加新的 MCP 工具

```python
# 在 server.py 中添加
@mcp.tool()
def my_new_tool(
    param1: str = Field(description="参数1说明"),
    param2: int = Field(default=0, description="参数2说明"),
) -> str:
    """工具描述"""
    # 实现逻辑
    return "结果"
```

#### 自定义 UI 主题

```python
# 在 feedback_ui.py 中修改 get_dark_mode_palette 函数
def get_custom_palette(app: QApplication):
    palette = app.palette()
    palette.setColor(QPalette.Window, QColor(30, 30, 30))  # 背景色
    palette.setColor(QPalette.WindowText, Qt.white)        # 文字色
    # ... 更多自定义
    return palette
```

#### 添加新的快捷键

```python
# 在 FeedbackUI._setup_shortcuts 中添加
shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
shortcut.activated.connect(self.my_custom_action)
```

---

## 🚀 多实例非阻塞改造方案

> 📄 **详细方案文档**: [MULTI_AGENT_PLAN.md](./MULTI_AGENT_PLAN.md)

当前架构采用阻塞式设计，不支持 Cursor 多 Agent 并发场景。为此，我们设计了一套非阻塞改造方案。

### 问题概述

```mermaid
graph LR
    subgraph "当前问题"
        A[Agent A 调用] -->|"阻塞"| B[等待用户...]
        C[Agent B 调用] -.->|"必须等待"| B
    end
    
    style B fill:#ffcdd2
```

### 改造方向

```mermaid
graph LR
    subgraph "目标架构"
        A1[Agent A] -->|"非阻塞"| S[Server]
        A2[Agent B] -->|"非阻塞"| S
        S --> U1[UI 窗口 A]
        S --> U2[UI 窗口 B]
    end
    
    style S fill:#c8e6c9
```

### 新增工具预览

| 工具 | 功能 | 说明 |
|------|------|------|
| `start_feedback` | 启动反馈 UI | 非阻塞，立即返回 request_id |
| `check_feedback` | 检查状态 | pending / completed / cancelled |
| `get_feedback` | 获取结果 | 返回文本和图片 |
| `cancel_feedback` | 取消请求 | 关闭 UI 窗口 |
| `list_pending_feedbacks` | 列出待处理 | 查看所有活跃请求 |

👉 **完整实施方案、代码示例、迁移指南请参阅 [MULTI_AGENT_PLAN.md](./MULTI_AGENT_PLAN.md)**

---

## 附录

### 工具参数说明

```
interactive_feedback(
    message: str,                    # 必填：显示给用户的问题或提示
    predefined_options: list = None, # 可选：预设选项列表，方便快速选择
    window_title: str = None         # 可选：反馈窗口标题，建议传入会话主题摘要（≤30字符）
) -> Tuple[str | Image, ...]
```

### 返回值格式

```python
# 仅文本
return "用户反馈文本"

# 仅图片
return (Image(data=bytes, format="png"),)

# 文本 + 图片
return ("用户反馈文本", Image(...), Image(...))

# 空反馈
return ("",)
```

### 常见问题

| 问题 | 解决方案 |
|------|----------|
| UI 不显示 | 检查 Python 环境和 PySide6 安装 |
| 中文乱码 | 确保系统支持中文字体 |
| 图片粘贴失败 | 检查剪贴板权限 |
| 工具调用超时 | 增加 `timeout` 配置值 |

---

*文档版本: 1.0.0 | 更新时间: 2025-01-05*

