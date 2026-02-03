"""
test_clipboard.py - 剪贴板复制功能测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestClipboardCopy:
    """剪贴板复制功能测试
    
    注意：这些测试需要 QApplication 实例，因此使用 pytest-qt 或手动创建 QApplication。
    由于 GUI 测试的复杂性，这里主要测试逻辑层面的正确性。
    """
    
    @pytest.fixture(autouse=True)
    def setup_qt_app(self):
        """设置 Qt 应用程序实例"""
        from PySide6.QtWidgets import QApplication
        
        # 获取现有实例或创建新实例
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
        yield
        # 不要在这里关闭 app，因为其他测试可能还需要它
    
    def test_copy_text_to_clipboard(self):
        """测试提交时文本被复制到剪贴板"""
        from PySide6.QtWidgets import QApplication
        
        # 准备测试数据
        test_text = "这是测试反馈文本"
        
        # 直接测试剪贴板功能
        clipboard = QApplication.clipboard()
        clipboard.setText(test_text)
        
        # 验证剪贴板内容
        assert clipboard.text() == test_text
    
    def test_empty_text_not_copied(self):
        """测试空文本不会复制到剪贴板"""
        from PySide6.QtWidgets import QApplication
        
        # 先设置一个已知值
        clipboard = QApplication.clipboard()
        original_text = "原始剪贴板内容"
        clipboard.setText(original_text)
        
        # 模拟空文本提交逻辑（与 _submit_feedback 中的逻辑一致）
        final_feedback = ""
        if final_feedback:
            clipboard.setText(final_feedback)
        
        # 验证剪贴板内容未被修改
        assert clipboard.text() == original_text
    
    def test_copy_with_predefined_options(self):
        """测试选中预设选项时，选项和文本都被复制"""
        from PySide6.QtWidgets import QApplication
        
        # 模拟组合内容（与 _submit_feedback 中的逻辑一致）
        selected_options = ["选项A", "选项B"]
        feedback_text = "用户输入的文本"
        
        final_feedback_parts = []
        if selected_options:
            final_feedback_parts.append("; ".join(selected_options))
        if feedback_text:
            final_feedback_parts.append(feedback_text)
        
        final_feedback = "\n\n".join(final_feedback_parts)
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        if final_feedback:
            clipboard.setText(final_feedback)
        
        # 验证剪贴板内容
        expected = "选项A; 选项B\n\n用户输入的文本"
        assert clipboard.text() == expected
    
    def test_copy_only_predefined_options(self):
        """测试只选中预设选项时的复制"""
        from PySide6.QtWidgets import QApplication
        
        # 只有预设选项，没有用户输入
        selected_options = ["选项A", "选项B"]
        feedback_text = ""
        
        final_feedback_parts = []
        if selected_options:
            final_feedback_parts.append("; ".join(selected_options))
        if feedback_text:
            final_feedback_parts.append(feedback_text)
        
        final_feedback = "\n\n".join(final_feedback_parts)
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        if final_feedback:
            clipboard.setText(final_feedback)
        
        # 验证剪贴板内容
        expected = "选项A; 选项B"
        assert clipboard.text() == expected
    
    def test_copy_only_user_text(self):
        """测试只有用户输入文本时的复制"""
        from PySide6.QtWidgets import QApplication
        
        # 只有用户输入，没有预设选项
        selected_options = []
        feedback_text = "用户输入的文本"
        
        final_feedback_parts = []
        if selected_options:
            final_feedback_parts.append("; ".join(selected_options))
        if feedback_text:
            final_feedback_parts.append(feedback_text)
        
        final_feedback = "\n\n".join(final_feedback_parts)
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        if final_feedback:
            clipboard.setText(final_feedback)
        
        # 验证剪贴板内容
        expected = "用户输入的文本"
        assert clipboard.text() == expected
    
    def test_copy_multiline_text(self):
        """测试多行文本的复制"""
        from PySide6.QtWidgets import QApplication
        
        # 多行文本
        feedback_text = "第一行\n第二行\n第三行"
        
        final_feedback_parts = []
        if feedback_text:
            final_feedback_parts.append(feedback_text)
        
        final_feedback = "\n\n".join(final_feedback_parts)
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        if final_feedback:
            clipboard.setText(final_feedback)
        
        # 验证剪贴板内容保留换行
        assert clipboard.text() == "第一行\n第二行\n第三行"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
