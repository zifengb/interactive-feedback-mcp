# 🗣️ Interactive Feedback MCP

[中文文档](./README.md)

Simple [MCP Server](https://modelcontextprotocol.io/) to enable a human-in-the-loop workflow in AI-assisted development tools like [Cursor](https://www.cursor.com), [Cline](https://cline.bot) and [Windsurf](https://windsurf.com). This server allows you to easily provide feedback directly to the AI agent, bridging the gap between AI and you.

**Note:** This server is designed to run locally alongside the MCP client (e.g., Claude Desktop, VS Code), as it needs direct access to the user's operating system to display notifications.

## New Features

- Beautiful UI
- Support pasting images
- Support markdown format
- **🚀 v0.2.0: Multi-Agent Async Mode** - Support multiple AI Agents requesting user feedback simultaneously without blocking each other

## 🖼️ Example

![Interactive Feedback Example](./demo.png)

## 💡 Why Use This?

In environments like Cursor, every prompt you send to the LLM is treated as a distinct request — and each one counts against your monthly limit (e.g. 500 premium requests). This becomes inefficient when you're iterating on vague instructions or correcting misunderstood output, as each follow-up clarification triggers a full new request.

This MCP server introduces a workaround: it allows the model to pause and request clarification before finalizing the response. Instead of completing the request, the model triggers a tool call (`interactive_feedback`) that opens an interactive feedback window. You can then provide more detail or ask for changes — and the model continues the session, all within a single request.

Under the hood, it's just a clever use of tool calls to defer the completion of the request. Since tool calls don't count as separate premium interactions, you can loop through multiple feedback cycles without consuming additional requests.

Essentially, this helps your AI assistant _ask for clarification instead of guessing_, without wasting another request. That means fewer wrong answers, better performance, and less wasted API usage.

- **💰 Reduced Premium API Calls:** Avoid wasting expensive API calls generating code based on guesswork.
- **✅ Fewer Errors:** Clarification \_before\_ action means less incorrect code and wasted time.
- **⏱️ Faster Cycles:** Quick confirmations beat debugging wrong guesses.
- **🎮 Better Collaboration:** Turns one-way instructions into a dialogue, keeping you in control.

## 🛠️ Tools

This server exposes the following tools via the Model Context Protocol (MCP):

### Standard Mode (`server.py`)

- `interactive_feedback`: Asks the user a question and returns their answer. Can display predefined options. (Blocking, single Agent)

### Async Mode (`server_async.py`) - New in v0.2.0 (Recommended)

Feedback tools supporting multi-Agent concurrency:

| Tool | Description |
|------|-------------|
| `start_feedback` | Launch feedback UI and wait for user to complete, returns feedback result (supports multi-Agent concurrency) |
| `interactive_feedback` | Compatibility mode, same behavior as standard mode |

**Note**: In async mode, each Agent calling `start_feedback` will wait for its own UI window, but won't block the Server process, allowing multiple Agents to pop up their own feedback windows simultaneously.

## 📦 Installation

1.  **Prerequisites:**
    - Python 3.10+
    - [uv](https://github.com/astral-sh/uv) (Python package manager). Install it with:
      - Windows: `pip install uv`
      - Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
      - macOS: `brew install uv`
2.  **Get the code:**
    - Clone this repository:
      `git clone https://github.com/kele527/interactive-feedback-mcp.git`
    - Or download the source code.

## ⚙️ Configuration

Add the following configuration to your `claude_desktop_config.json` (Claude Desktop) or `mcp.json` (Cursor):

**Remember to change the `/path/to/interactive-feedback-mcp` path to the actual path where you cloned the repository on your system.**

### Standard Mode Configuration

```json
{
  "mcpServers": {
    "interactive-feedback": {
      "command": "uv",
      "args": ["--directory", "/path/to/interactive-feedback-mcp", "run", "server.py"],
      "timeout": 600,
      "autoApprove": ["interactive_feedback"]
    }
  }
}
```

### Async Mode Configuration (Recommended for Multi-Agent)

```json
{
  "mcpServers": {
    "interactive-feedback": {
      "command": "uv",
      "args": ["--directory", "/path/to/interactive-feedback-mcp", "run", "server_async.py"],
      "timeout": 600,
      "autoApprove": [
        "interactive_feedback",
        "start_feedback"
      ]
    }
  }
}
```

### Add AI Assistant Rules (Single Instance)

Add the following to the custom rules in your AI assistant (in Cursor Settings > Rules > User Rules):

> If requirements or instructions are unclear use the tool interactive_feedback to ask clarifying questions to the user before proceeding, do not make assumptions. Whenever possible, present the user with predefined options through the interactive_feedback MCP tool to facilitate quick decisions.

> Whenever you're about to complete a user request, call the interactive_feedback tool to request user feedback before ending the process. If the feedback is empty you can end the request and don't call the tool in loop.

### Add AI Assistant Rules (Multi Instance)

在您的 AI 助手（在 Cursor Settings > Rules > User Rules 中）的全局自定义规则中添加以下内容：

> If requirements or instructions are unclear use the tool start_feedback to ask clarifying questions to the user before proceeding, do not make assumptions. Whenever possible, present the user with predefined options through the start_feedback MCP tool to facilitate quick decisions.

> Whenever you're about to complete a user request, call the start_feedback tool to request user feedback before ending the process. If the feedback is empty you can end the request and don't call the tool in loop.

This will ensure your AI assistant always uses this MCP server to request user feedback when the prompt is unclear and before marking the task as completed.

## 🚀 Async Mode Usage

Async mode (`server_async.py`) is designed for multi-Agent concurrent scenarios:

### Features

- **Multi-window support**: Multiple Agents can pop up their own feedback UI windows simultaneously
- **Session persistence**: Each Agent calling `start_feedback` will wait for user to complete feedback, session won't be interrupted
- **Server not blocked**: Implemented with asyncio, the Server process itself won't be blocked
- **Auto cleanup**: Temporary files are automatically cleaned up

### Workflow

```
Agent A                          Agent B
   |                                |
   |-- start_feedback() -->        |
   |   [Pop up UI window A]        |-- start_feedback() -->
   |   [Waiting for user...]       |   [Pop up UI window B]
   |                               |   [Waiting for user...]
   |   [User completes A]          |
   |<-- returns user feedback      |
   |   [Agent A continues]         |   [User completes B]
   |                               |<-- returns user feedback
   |                               |   [Agent B continues]
```

Difference from standard mode:
- **Standard mode**: Uses `subprocess.run()` to wait synchronously, blocks the entire Server process
- **Async mode**: Uses `asyncio` to wait asynchronously, each Agent waits for its own UI without affecting others

## 🧪 Testing

Before configuring MCP, you can manually test whether each component is working properly.

### Test UI Interface

Run the UI test directly to check if the feedback window displays correctly:

```bash
# Navigate to project directory
cd /path/to/interactive-feedback-mcp

# Test UI (will pop up a feedback window)
uv run feedback_ui.py --prompt "This is a test message with **Markdown** support" --predefined-options "Option A|||Option B|||Option C"
```

If the window pops up normally and you can input feedback, the UI component is working correctly.

### Test MCP Server

Use `fastmcp` dev mode to test the MCP server:

```bash
# Test standard mode server
uv run fastmcp dev server.py

# Test async mode server
uv run fastmcp dev server_async.py
```

This will start an interactive MCP testing environment where you can directly call tools for testing.

### Run Unit Tests

The project includes a complete test suite:

```bash
# Install test dependencies
uv pip install pytest pytest-asyncio

# Run all tests
uv run pytest tests/ -v

# Run specific test files
uv run pytest tests/test_request_manager.py -v
uv run pytest tests/test_async_launcher.py -v
uv run pytest tests/test_integration.py -v
```

### Troubleshooting

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| UI window not showing | Missing PySide6 | Run `uv pip install pyside6` |
| Garbled text display | Font issue | Ensure system has proper fonts installed |
| MCP connection failed | Path configuration error | Check if the path in mcp.json is correct |
| Process won't start | Python environment issue | Make sure to use `uv run` to execute |

## 🙏 Acknowledgements

Developed by Fábio Ferreira ([@fabiomlferreira](https://x.com/fabiomlferreira)).

Enhanced by Pau Oliva ([@pof](https://x.com/pof)) with ideas from Tommy Tong's [interactive-mcp](https://github.com/ttommyth/interactive-mcp).

UI Optimized by kele527 ([@kele527](https://x.com/jasonya76775253))
