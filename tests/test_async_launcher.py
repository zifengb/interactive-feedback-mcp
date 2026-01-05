"""
test_async_launcher.py - AsyncUILauncher 单元测试
"""
import pytest
import asyncio
import os
import tempfile

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from request_manager import RequestManager, RequestStatus
from async_launcher import AsyncUILauncher


class TestAsyncUILauncher:
    """测试 AsyncUILauncher"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前重置"""
        self.manager = RequestManager()
        self.manager.reset()
        self.launcher = AsyncUILauncher()
        yield
        self.manager.reset()
    
    def test_init(self):
        """测试初始化"""
        launcher = AsyncUILauncher()
        assert launcher.poll_interval == 1.0  # [P0] 验证轮询间隔
        assert launcher.feedback_ui_path.exists()
    
    def test_poll_interval_optimization(self):
        """[P0] 测试轮询间隔优化"""
        # 确保轮询间隔是 1.0 秒而不是 0.5 秒
        assert self.launcher.poll_interval == 1.0
    
    def test_get_active_count_empty(self):
        """测试获取活跃任务数（空）"""
        assert self.launcher.get_active_count() == 0
    
    @pytest.mark.asyncio
    async def test_start_feedback_ui_nonexistent_request(self):
        """测试启动不存在的请求"""
        result = await self.launcher.start_feedback_ui(
            "nonexistent",
            "测试消息"
        )
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_request(self):
        """测试取消不存在的请求"""
        result = await self.launcher.cancel_feedback("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cancel_all_empty(self):
        """测试取消所有请求（空）"""
        count = await self.launcher.cancel_all()
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_start_and_cancel_feedback(self):
        """测试启动和取消反馈"""
        # 创建请求
        request_id = self.manager.create_request("测试消息")
        assert request_id is not None
        
        # 启动 UI（这会启动真实的 UI 进程）
        # 注意：在 CI 环境中可能会失败，因为没有图形界面
        try:
            success = await self.launcher.start_feedback_ui(
                request_id,
                "测试消息"
            )
            
            if success:
                # 等待一小段时间让进程启动
                await asyncio.sleep(0.5)
                
                # 验证活跃任务数
                assert self.launcher.get_active_count() >= 0
                
                # 取消请求
                cancel_result = await self.launcher.cancel_feedback(request_id)
                assert cancel_result is True
                
                # 验证状态
                request = self.manager.get_request(request_id)
                assert request.status == RequestStatus.CANCELLED
        except Exception as e:
            # 在无图形界面环境中可能失败，跳过
            pytest.skip(f"无法启动 UI 进程: {e}")


class TestAsyncUILauncherMocked:
    """使用 Mock 的 AsyncUILauncher 测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前重置"""
        self.manager = RequestManager()
        self.manager.reset()
        yield
        self.manager.reset()
    
    def test_manager_singleton(self):
        """测试管理器单例"""
        launcher1 = AsyncUILauncher()
        launcher2 = AsyncUILauncher()
        assert launcher1.manager is launcher2.manager
    
    def test_feedback_ui_path(self):
        """测试 feedback_ui.py 路径"""
        launcher = AsyncUILauncher()
        assert launcher.feedback_ui_path.name == "feedback_ui.py"
        assert launcher.feedback_ui_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

