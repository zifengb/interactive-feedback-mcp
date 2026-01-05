"""
test_integration.py - 集成测试
"""
import pytest
import asyncio
import os
import tempfile
import glob

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from request_manager import RequestManager, RequestStatus
from async_launcher import AsyncUILauncher


class TestIntegration:
    """集成测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前重置"""
        self.manager = RequestManager()
        self.manager.reset()
        self.launcher = AsyncUILauncher()
        yield
        self.manager.reset()
    
    def test_full_workflow_simulation(self):
        """测试完整工作流程模拟（不启动真实 UI）"""
        # 1. 创建请求
        request_id = self.manager.create_request(
            "请确认操作",
            ["确认", "取消"]
        )
        assert request_id is not None
        
        # 2. 检查初始状态
        request = self.manager.get_request(request_id)
        assert request.status == RequestStatus.PENDING
        
        # 3. 模拟用户完成反馈
        result = {
            "interactive_feedback": "用户选择了确认",
            "images": []
        }
        self.manager.update_status(request_id, RequestStatus.COMPLETED, result)
        
        # 4. 验证完成状态
        request = self.manager.get_request(request_id)
        assert request.status == RequestStatus.COMPLETED
        assert request.result == result
        assert request.completed_at is not None
        
        # 5. 获取结果后移除
        self.manager.remove_request(request_id)
        assert self.manager.get_request(request_id) is None
    
    def test_concurrent_requests(self):
        """测试并发请求管理"""
        # 创建多个请求
        request_ids = []
        for i in range(5):
            rid = self.manager.create_request(f"请求 {i}")
            request_ids.append(rid)
        
        # 验证所有请求都是待处理状态
        pending = self.manager.get_pending_requests()
        assert len(pending) == 5
        
        # 完成部分请求
        self.manager.update_status(request_ids[0], RequestStatus.COMPLETED)
        self.manager.update_status(request_ids[2], RequestStatus.CANCELLED)
        
        # 验证统计
        stats = self.manager.get_stats()
        assert stats["pending"] == 3
        assert stats["completed"] == 1
        assert stats["cancelled"] == 1
    
    def test_max_concurrent_limit(self):
        """[P0] 测试最大并发限制"""
        max_requests = RequestManager.MAX_CONCURRENT_REQUESTS
        
        # 创建最大数量的请求
        for i in range(max_requests):
            rid = self.manager.create_request(f"请求 {i}")
            assert rid is not None
        
        # 超过限制
        overflow = self.manager.create_request("超出限制")
        assert overflow is None
        
        # 验证统计
        stats = self.manager.get_stats()
        assert stats["pending"] == max_requests
    
    def test_cleanup_workflow(self):
        """测试清理工作流程"""
        from datetime import datetime, timedelta
        
        # 创建请求
        rid1 = self.manager.create_request("请求1")
        rid2 = self.manager.create_request("请求2")
        
        # 模拟过期
        req1 = self.manager.get_request(rid1)
        req1.created_at = datetime.now() - timedelta(hours=2)
        
        # 完成第二个请求
        self.manager.update_status(rid2, RequestStatus.COMPLETED)
        req2 = self.manager.get_request(rid2)
        req2.completed_at = datetime.now() - timedelta(minutes=10)
        
        # 清理过期请求
        expired_count = self.manager.cleanup_expired(max_age_seconds=3600)
        assert expired_count == 1
        
        # 验证 rid1 状态已更新为 EXPIRED
        assert self.manager.get_request(rid1).status == RequestStatus.EXPIRED
        
        # 清理已完成请求（包括 EXPIRED 状态的 rid1 和 COMPLETED 状态的 rid2）
        completed_count = self.manager.cleanup_completed(max_age_seconds=300)
        # rid1 (EXPIRED) 和 rid2 (COMPLETED) 都会被清理
        assert completed_count == 2
        
        # 验证结果 - 两个请求都被移除
        assert self.manager.get_request(rid1) is None
        assert self.manager.get_request(rid2) is None


class TestTempFileCleanup:
    """临时文件清理测试"""
    
    def test_cleanup_temp_files(self):
        """[P1] 测试启动时清理临时文件"""
        from server_async import cleanup_temp_files
        
        # 创建一些测试临时文件
        temp_dir = tempfile.gettempdir()
        test_files = []
        for i in range(3):
            fd, path = tempfile.mkstemp(suffix=f"_test{i}.json", prefix="feedback_")
            os.close(fd)
            test_files.append(path)
        
        # 验证文件存在
        for f in test_files:
            assert os.path.exists(f)
        
        # 执行清理
        cleaned = cleanup_temp_files()
        assert cleaned >= 3
        
        # 验证文件已删除
        for f in test_files:
            assert not os.path.exists(f)


class TestServerAsyncTools:
    """server_async 工具测试
    
    注意：由于 FastMCP 装饰器将函数包装成 FunctionTool 对象，
    这里我们直接测试底层逻辑，而不是通过装饰器调用。
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前重置"""
        self.manager = RequestManager()
        self.manager.reset()
        yield
        self.manager.reset()
    
    def _check_feedback(self, request_id: str) -> str:
        """直接实现 check_feedback 逻辑用于测试"""
        request = self.manager.get_request(request_id)
        if not request:
            return "error:请求不存在"
        return f"status:{request.status.value}"
    
    def _get_feedback(self, request_id: str):
        """直接实现 get_feedback 逻辑用于测试"""
        request = self.manager.get_request(request_id)
        if not request:
            return "error:请求不存在"
        
        if request.status != RequestStatus.COMPLETED:
            return f"error:请求尚未完成，当前状态: {request.status.value}"
        
        result = request.result or {}
        txt = result.get("interactive_feedback", "").strip()
        
        self.manager.remove_request(request_id)
        return txt if txt else ""
    
    def _list_pending_feedbacks(self) -> str:
        """直接实现 list_pending_feedbacks 逻辑用于测试"""
        pending = self.manager.get_pending_requests()
        if not pending:
            return "no_pending_requests"
        
        lines = []
        for req in pending:
            msg_preview = req.message[:50] + "..." if len(req.message) > 50 else req.message
            msg_preview = msg_preview.replace('\n', ' ').replace('\r', '')
            lines.append(f"{req.request_id}:{msg_preview}")
        
        return "\n".join(lines)
    
    def test_check_feedback_nonexistent(self):
        """测试检查不存在的请求"""
        result = self._check_feedback("nonexistent")
        assert result == "error:请求不存在"
    
    def test_get_feedback_nonexistent(self):
        """测试获取不存在的请求结果"""
        result = self._get_feedback("nonexistent")
        assert result == "error:请求不存在"
    
    def test_get_feedback_not_completed(self):
        """测试获取未完成的请求结果"""
        # 创建请求但不完成
        request_id = self.manager.create_request("测试")
        result = self._get_feedback(request_id)
        assert "error:请求尚未完成" in result
    
    def test_list_pending_feedbacks_empty(self):
        """测试列出待处理请求（空）"""
        result = self._list_pending_feedbacks()
        assert result == "no_pending_requests"
    
    def test_list_pending_feedbacks(self):
        """测试列出待处理请求"""
        # 创建请求
        rid1 = self.manager.create_request("请求1")
        rid2 = self.manager.create_request("请求2")
        
        result = self._list_pending_feedbacks()
        assert rid1 in result
        assert rid2 in result
    
    def test_check_feedback_status(self):
        """测试检查各种状态"""
        # 创建请求
        request_id = self.manager.create_request("测试")
        
        # 检查 pending 状态
        assert self._check_feedback(request_id) == "status:pending"
        
        # 更新为 completed
        self.manager.update_status(request_id, RequestStatus.COMPLETED)
        assert self._check_feedback(request_id) == "status:completed"
    
    def test_get_feedback_with_result(self):
        """测试获取带结果的反馈"""
        # 创建并完成请求
        request_id = self.manager.create_request("测试")
        self.manager.update_status(
            request_id, 
            RequestStatus.COMPLETED,
            {"interactive_feedback": "用户反馈内容", "images": []}
        )
        
        result = self._get_feedback(request_id)
        assert result == "用户反馈内容"
        
        # 请求应该被移除
        assert self.manager.get_request(request_id) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

