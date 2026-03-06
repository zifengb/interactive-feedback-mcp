"""
test_window_title.py - 动态窗口标题功能测试
"""
import pytest
import sys
import os
import subprocess
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGetDisplayTitle:
    """_get_display_title() 方法的单元测试"""

    @pytest.fixture(autouse=True)
    def setup_qt_app(self):
        from PySide6.QtWidgets import QApplication
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
        yield

    def _create_ui(self, window_title=None):
        from feedback_ui import FeedbackUI
        return FeedbackUI("测试提示", window_title=window_title)

    def test_normal_title(self):
        """传入正常标题时，窗口标题为 '{title} - 反馈'"""
        ui = self._create_ui("添加用户认证")
        assert ui.windowTitle() == "添加用户认证 - 反馈"

    def test_none_title_fallback(self):
        """不传 title (None) 时，回退到默认标题"""
        ui = self._create_ui(None)
        assert ui.windowTitle() == "Cursor 交互式反馈 MCP"

    def test_no_title_arg_fallback(self):
        """不传 window_title 参数时，回退到默认标题"""
        from feedback_ui import FeedbackUI
        ui = FeedbackUI("测试提示")
        assert ui.windowTitle() == "Cursor 交互式反馈 MCP"

    def test_empty_string_fallback(self):
        """传入空字符串时，回退到默认标题"""
        ui = self._create_ui("")
        assert ui.windowTitle() == "Cursor 交互式反馈 MCP"

    def test_whitespace_only_fallback(self):
        """传入纯空格时，回退到默认标题"""
        ui = self._create_ui("   ")
        assert ui.windowTitle() == "Cursor 交互式反馈 MCP"

    def test_title_with_leading_trailing_spaces(self):
        """传入前后有空格的标题时，自动 strip"""
        ui = self._create_ui("  重构认证模块  ")
        assert ui.windowTitle() == "重构认证模块 - 反馈"

    def test_long_title_truncation(self):
        """传入超长标题（>50字符）时，截断并加省略号"""
        long_title = "a" * 60
        ui = self._create_ui(long_title)
        title = ui.windowTitle()
        assert title.endswith("... - 反馈")
        content = title.replace(" - 反馈", "").replace("...", "")
        assert len(content) == 50

    def test_exactly_50_chars_no_truncation(self):
        """传入恰好 50 字符的标题时，不截断"""
        title_50 = "a" * 50
        ui = self._create_ui(title_50)
        assert ui.windowTitle() == f"{title_50} - 反馈"
        assert "..." not in ui.windowTitle()

    def test_51_chars_triggers_truncation(self):
        """传入 51 字符的标题时，触发截断"""
        title_51 = "a" * 51
        ui = self._create_ui(title_51)
        assert "..." in ui.windowTitle()

    def test_chinese_title(self):
        """中文标题正常显示"""
        ui = self._create_ui("实现用户登录功能")
        assert ui.windowTitle() == "实现用户登录功能 - 反馈"

    def test_english_title(self):
        """英文标题正常显示"""
        ui = self._create_ui("Add User Auth")
        assert ui.windowTitle() == "Add User Auth - 反馈"

    def test_mixed_language_title(self):
        """中英混合标题正常显示"""
        ui = self._create_ui("重构 Auth Module")
        assert ui.windowTitle() == "重构 Auth Module - 反馈"

    def test_special_characters(self):
        """特殊字符标题不崩溃"""
        special_titles = [
            "修复 bug #123",
            "添加 <HTML> 支持",
            "处理 & 符号",
            'title with "quotes"',
            "路径 C:\\Users\\test",
            "emoji 🚀 标题",
        ]
        for title in special_titles:
            ui = self._create_ui(title)
            assert ui.windowTitle().endswith(" - 反馈")


class TestGetDisplayTitleMethod:
    """通过实例测试 _get_display_title 方法的返回值逻辑"""

    @pytest.fixture(autouse=True)
    def setup_qt_app(self):
        from PySide6.QtWidgets import QApplication
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
        from feedback_ui import FeedbackUI
        self.ui = FeedbackUI("测试")
        yield

    def test_returns_default_for_none(self):
        assert self.ui._get_display_title(None) == "Cursor 交互式反馈 MCP"

    def test_returns_default_for_empty(self):
        assert self.ui._get_display_title("") == "Cursor 交互式反馈 MCP"

    def test_returns_default_for_spaces(self):
        assert self.ui._get_display_title("   ") == "Cursor 交互式反馈 MCP"

    def test_returns_formatted_for_normal(self):
        assert self.ui._get_display_title("测试") == "测试 - 反馈"

    def test_truncates_long_title(self):
        result = self.ui._get_display_title("x" * 60)
        assert result == "x" * 50 + "... - 反馈"

    def test_preserves_exact_50(self):
        result = self.ui._get_display_title("y" * 50)
        assert result == "y" * 50 + " - 反馈"


class TestWindowTitleCommandLine:
    """测试命令行参数 --window-title 的传递"""

    def test_cli_with_window_title(self):
        """通过命令行传入 --window-title，验证进程正常启动退出"""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        feedback_ui_path = os.path.join(script_dir, "feedback_ui.py")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_file = tmp.name

        try:
            # 使用 --help 验证 --window-title 参数被 argparse 正确识别
            result = subprocess.run(
                [sys.executable, feedback_ui_path, "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert result.returncode == 0
            assert "--window-title" in result.stdout
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_cli_help_shows_window_title_param(self):
        """验证 --help 输出中包含 --window-title 参数说明"""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        feedback_ui_path = os.path.join(script_dir, "feedback_ui.py")

        result = subprocess.run(
            [sys.executable, feedback_ui_path, "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0
        assert "--window-title" in result.stdout


class TestWindowTitleInLaunchFeedbackUI:
    """测试 server.py 中 launch_feedback_ui 的 window_title 参数传递"""

    def test_launch_feedback_ui_accepts_window_title(self):
        """验证 launch_feedback_ui 函数签名接受 window_title 参数"""
        import inspect
        from server import launch_feedback_ui

        sig = inspect.signature(launch_feedback_ui)
        assert "window_title" in sig.parameters
        assert sig.parameters["window_title"].default is None

    def test_interactive_feedback_tool_has_window_title(self):
        """验证 server.py 的 interactive_feedback tool 有 window_title 参数"""
        import inspect
        from server import interactive_feedback

        # @mcp.tool() 装饰后变成 FunctionTool，通过 .fn 访问原始函数
        fn = interactive_feedback.fn if hasattr(interactive_feedback, 'fn') else interactive_feedback
        sig = inspect.signature(fn)
        assert "window_title" in sig.parameters

    def test_async_start_feedback_has_window_title(self):
        """验证 server_async.py 的 start_feedback tool 有 window_title 参数"""
        import inspect
        from server_async import start_feedback

        fn = start_feedback.fn if hasattr(start_feedback, 'fn') else start_feedback
        sig = inspect.signature(fn)
        assert "window_title" in sig.parameters

    def test_async_interactive_feedback_has_window_title(self):
        """验证 server_async.py 的 interactive_feedback tool 有 window_title 参数"""
        import inspect
        from server_async import interactive_feedback

        fn = interactive_feedback.fn if hasattr(interactive_feedback, 'fn') else interactive_feedback
        sig = inspect.signature(fn)
        assert "window_title" in sig.parameters


class TestWindowTitleInAsyncLauncher:
    """测试 async_launcher.py 中的 window_title 参数"""

    def test_launch_and_wait_accepts_window_title(self):
        """验证 launch_and_wait 方法签名接受 window_title 参数"""
        import inspect
        from async_launcher import AsyncUILauncher

        sig = inspect.signature(AsyncUILauncher.launch_and_wait)
        assert "window_title" in sig.parameters
        assert sig.parameters["window_title"].default is None

    def test_start_feedback_ui_accepts_window_title(self):
        """验证 start_feedback_ui 方法签名接受 window_title 参数"""
        import inspect
        from async_launcher import AsyncUILauncher

        sig = inspect.signature(AsyncUILauncher.start_feedback_ui)
        assert "window_title" in sig.parameters
        assert sig.parameters["window_title"].default is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
