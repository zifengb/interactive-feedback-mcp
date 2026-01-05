"""
test_request_manager.py - RequestManager 单元测试
"""
import pytest
import time
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from request_manager import RequestManager, RequestStatus, FeedbackRequest


class TestRequestStatus:
    """测试 RequestStatus 枚举"""
    
    def test_status_values(self):
        """测试状态枚举值"""
        assert RequestStatus.PENDING.value == "pending"
        assert RequestStatus.COMPLETED.value == "completed"
        assert RequestStatus.CANCELLED.value == "cancelled"
        assert RequestStatus.EXPIRED.value == "expired"
        assert RequestStatus.ERROR.value == "error"


class TestFeedbackRequest:
    """测试 FeedbackRequest 数据类"""
    
    def test_create_request(self):
        """测试创建请求"""
        req = FeedbackRequest(
            request_id="test123",
            message="测试消息"
        )
        assert req.request_id == "test123"
        assert req.message == "测试消息"
        assert req.status == RequestStatus.PENDING
        assert req.result is None
        assert req.predefined_options is None
        assert isinstance(req.created_at, datetime)
    
    def test_create_request_with_options(self):
        """测试创建带预设选项的请求"""
        options = ["选项1", "选项2", "选项3"]
        req = FeedbackRequest(
            request_id="test456",
            message="选择一个选项",
            predefined_options=options
        )
        assert req.predefined_options == options


class TestRequestManager:
    """测试 RequestManager"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前重置管理器"""
        self.manager = RequestManager()
        self.manager.reset()
        yield
        self.manager.reset()
    
    def test_singleton(self):
        """测试单例模式"""
        manager1 = RequestManager()
        manager2 = RequestManager()
        assert manager1 is manager2
    
    def test_create_request(self):
        """测试创建请求"""
        request_id = self.manager.create_request("测试消息")
        assert request_id is not None
        assert len(request_id) == 8
        
        request = self.manager.get_request(request_id)
        assert request is not None
        assert request.message == "测试消息"
        assert request.status == RequestStatus.PENDING
    
    def test_create_request_with_options(self):
        """测试创建带选项的请求"""
        options = ["A", "B", "C"]
        request_id = self.manager.create_request("选择", options)
        
        request = self.manager.get_request(request_id)
        assert request.predefined_options == options
    
    def test_max_concurrent_requests(self):
        """[P0] 测试最大并发请求数限制"""
        # 创建最大数量的请求
        request_ids = []
        for i in range(RequestManager.MAX_CONCURRENT_REQUESTS):
            rid = self.manager.create_request(f"请求 {i}")
            assert rid is not None
            request_ids.append(rid)
        
        # 超过限制后应该返回 None
        overflow_id = self.manager.create_request("超出限制的请求")
        assert overflow_id is None
        
        # 完成一个请求后应该可以创建新请求
        self.manager.update_status(request_ids[0], RequestStatus.COMPLETED)
        new_id = self.manager.create_request("新请求")
        assert new_id is not None
    
    def test_get_nonexistent_request(self):
        """测试获取不存在的请求"""
        request = self.manager.get_request("nonexistent")
        assert request is None
    
    def test_update_status(self):
        """测试更新状态"""
        request_id = self.manager.create_request("测试")
        
        # 更新为完成状态
        result = self.manager.update_status(
            request_id, 
            RequestStatus.COMPLETED,
            {"interactive_feedback": "用户反馈"}
        )
        assert result is True
        
        request = self.manager.get_request(request_id)
        assert request.status == RequestStatus.COMPLETED
        assert request.result == {"interactive_feedback": "用户反馈"}
        assert request.completed_at is not None
    
    def test_update_nonexistent_request(self):
        """测试更新不存在的请求"""
        result = self.manager.update_status("nonexistent", RequestStatus.COMPLETED)
        assert result is False
    
    def test_remove_request(self):
        """测试移除请求"""
        request_id = self.manager.create_request("测试")
        assert self.manager.get_request(request_id) is not None
        
        result = self.manager.remove_request(request_id)
        assert result is True
        assert self.manager.get_request(request_id) is None
    
    def test_remove_nonexistent_request(self):
        """测试移除不存在的请求"""
        result = self.manager.remove_request("nonexistent")
        assert result is False
    
    def test_get_pending_requests(self):
        """测试获取待处理请求"""
        # 创建多个请求
        id1 = self.manager.create_request("请求1")
        id2 = self.manager.create_request("请求2")
        id3 = self.manager.create_request("请求3")
        
        # 完成其中一个
        self.manager.update_status(id2, RequestStatus.COMPLETED)
        
        pending = self.manager.get_pending_requests()
        assert len(pending) == 2
        pending_ids = [r.request_id for r in pending]
        assert id1 in pending_ids
        assert id3 in pending_ids
        assert id2 not in pending_ids
    
    def test_cleanup_expired(self):
        """测试清理过期请求"""
        # 创建请求
        request_id = self.manager.create_request("测试")
        request = self.manager.get_request(request_id)
        
        # 手动设置创建时间为过去
        request.created_at = datetime.now() - timedelta(hours=2)
        
        # 清理过期请求（1小时）
        cleaned = self.manager.cleanup_expired(max_age_seconds=3600)
        assert cleaned == 1
        
        # 检查状态已更新
        request = self.manager.get_request(request_id)
        assert request.status == RequestStatus.EXPIRED
    
    def test_cleanup_completed(self):
        """测试清理已完成请求"""
        # 创建并完成请求
        request_id = self.manager.create_request("测试")
        self.manager.update_status(request_id, RequestStatus.COMPLETED)
        
        request = self.manager.get_request(request_id)
        # 手动设置完成时间为过去
        request.completed_at = datetime.now() - timedelta(minutes=10)
        
        # 清理已完成请求（5分钟）
        cleaned = self.manager.cleanup_completed(max_age_seconds=300)
        assert cleaned == 1
        
        # 请求应该被移除
        assert self.manager.get_request(request_id) is None
    
    def test_get_stats(self):
        """测试获取统计信息"""
        # 创建不同状态的请求
        id1 = self.manager.create_request("请求1")
        id2 = self.manager.create_request("请求2")
        id3 = self.manager.create_request("请求3")
        
        self.manager.update_status(id1, RequestStatus.COMPLETED)
        self.manager.update_status(id2, RequestStatus.CANCELLED)
        
        stats = self.manager.get_stats()
        assert stats["total"] == 3
        assert stats["pending"] == 1
        assert stats["completed"] == 1
        assert stats["cancelled"] == 1
    
    def test_set_output_file(self):
        """测试设置输出文件"""
        request_id = self.manager.create_request("测试")
        
        result = self.manager.set_output_file(request_id, "/tmp/test.json")
        assert result is True
        
        request = self.manager.get_request(request_id)
        assert request.output_file == "/tmp/test.json"
    
    def test_unique_request_ids(self):
        """测试请求 ID 唯一性"""
        ids = set()
        for _ in range(100):
            rid = self.manager.create_request("测试")
            if rid:  # 可能因为并发限制返回 None
                assert rid not in ids
                ids.add(rid)
                # 立即完成以便继续创建
                self.manager.update_status(rid, RequestStatus.COMPLETED)
                self.manager.remove_request(rid)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

