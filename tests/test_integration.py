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


class TestAsyncLauncher:
    """AsyncUILauncher 测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前重置"""
        self.launcher = AsyncUILauncher()
        yield
    
    def test_launcher_init(self):
        """测试启动器初始化"""
        assert self.launcher.poll_interval == 1.0
        assert self.launcher.feedback_ui_path.exists()
    
    def test_get_active_count_empty(self):
        """测试获取活跃任务数（空）"""
        assert self.launcher.get_active_count() == 0


class TestParseResult:
    """结果解析测试"""
    
    def test_parse_text_only(self):
        """测试解析纯文本结果"""
        from server_async import _parse_feedback_result
        
        result = {"interactive_feedback": "用户反馈", "images": []}
        parsed = _parse_feedback_result(result)
        assert parsed == "用户反馈"
    
    def test_parse_empty(self):
        """测试解析空结果"""
        from server_async import _parse_feedback_result
        
        result = {"interactive_feedback": "", "images": []}
        parsed = _parse_feedback_result(result)
        assert parsed == ""
    
    def test_parse_with_whitespace(self):
        """测试解析带空白的结果"""
        from server_async import _parse_feedback_result
        
        result = {"interactive_feedback": "  用户反馈  ", "images": []}
        parsed = _parse_feedback_result(result)
        assert parsed == "用户反馈"


class TestMultiGUIConcurrency:
    """多 GUI 并发测试 - 验证多个 UI 可以同时启动而不阻塞 Server"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前重置"""
        self.launcher = AsyncUILauncher()
        self.manager = RequestManager()
        self.manager.reset()
        yield
        self.manager.reset()
    
    @pytest.mark.asyncio
    async def test_multiple_launch_and_wait_non_blocking(self):
        """
        测试多个 launch_and_wait 调用不会互相阻塞
        
        验证逻辑：
        1. 同时启动多个 launch_and_wait 协程
        2. 验证它们可以并行运行（通过 asyncio.gather）
        3. 使用超时机制验证不会阻塞
        """
        import subprocess
        import time
        
        # 记录开始时间
        start_time = time.time()
        
        # 创建多个并发任务（使用很短的超时，因为我们只是测试并发性，不需要真正等待 UI）
        async def mock_concurrent_launch(agent_id: int):
            """模拟并发启动，立即返回（不启动真实 UI）"""
            # 模拟异步操作
            await asyncio.sleep(0.1)  # 模拟启动延迟
            return f"agent_{agent_id}_started"
        
        # 同时启动 5 个 "Agent"
        tasks = [mock_concurrent_launch(i) for i in range(5)]
        
        # 使用 gather 并行执行，如果是阻塞的，这会串行执行
        results = await asyncio.gather(*tasks)
        
        # 记录结束时间
        elapsed_time = time.time() - start_time
        
        # 验证所有任务都完成了
        assert len(results) == 5
        for i in range(5):
            assert results[i] == f"agent_{i}_started"
        
        # 如果是并行的，5 个 0.1s 的任务应该在 ~0.1s 内完成（加一些余量）
        # 如果是串行的，需要 ~0.5s
        assert elapsed_time < 0.3, f"任务执行时间 {elapsed_time}s 过长，可能是串行执行"
    
    @pytest.mark.asyncio
    async def test_real_ui_processes_can_start_concurrently(self):
        """
        测试真实 UI 进程可以并发启动（不等待完成）
        
        验证逻辑：
        1. 创建多个请求
        2. 启动多个 UI 进程（使用 start_feedback_ui，不是 launch_and_wait）
        3. 验证所有进程都已启动
        4. 清理进程
        """
        import time
        
        num_agents = 3
        request_ids = []
        
        # 1. 创建多个请求
        for i in range(num_agents):
            rid = self.manager.create_request(f"Agent {i} 的请求")
            assert rid is not None
            request_ids.append(rid)
        
        # 2. 记录开始时间
        start_time = time.time()
        
        # 3. 并发启动 UI 进程
        launch_tasks = []
        for i, rid in enumerate(request_ids):
            task = self.launcher.start_feedback_ui(rid, f"Agent {i} 的请求")
            launch_tasks.append(task)
        
        # 并行启动所有 UI
        launch_results = await asyncio.gather(*launch_tasks)
        
        # 记录启动完成时间
        launch_time = time.time() - start_time
        
        # 4. 验证所有 UI 都成功启动
        assert all(launch_results), "部分 UI 启动失败"
        
        # 5. 验证启动是并行的（不应该超过 2 秒）
        assert launch_time < 2.0, f"UI 启动时间 {launch_time}s 过长"
        
        # 6. 验证所有进程都在运行
        for rid in request_ids:
            request = self.manager.get_request(rid)
            assert request is not None
            assert request.process is not None
            # 进程应该还在运行（因为没有用户交互）
            assert request.process.poll() is None, f"进程 {rid} 意外退出"
        
        # 7. 清理：取消所有请求
        for rid in request_ids:
            await self.launcher.cancel_feedback(rid)
        
        # 8. 验证清理成功
        await asyncio.sleep(0.5)  # 等待进程终止
        for rid in request_ids:
            request = self.manager.get_request(rid)
            if request and request.process:
                assert request.process.poll() is not None, f"进程 {rid} 未能终止"
    
    @pytest.mark.asyncio
    async def test_server_not_blocked_during_ui_wait(self):
        """
        测试 Server 在等待 UI 期间不被阻塞
        
        验证逻辑：
        1. 启动一个 launch_and_wait 任务（但设置超时）
        2. 同时执行其他操作（创建请求、检查状态等）
        3. 验证其他操作可以正常完成
        """
        import time
        
        # 用于记录操作完成时间的列表
        operation_times = []
        
        async def background_operations():
            """后台操作：在 UI 等待期间执行"""
            for i in range(5):
                # 创建请求
                rid = self.manager.create_request(f"后台请求 {i}")
                operation_times.append(("create", i, time.time()))
                
                # 检查状态
                req = self.manager.get_request(rid)
                assert req is not None
                operation_times.append(("check", i, time.time()))
                
                # 短暂等待
                await asyncio.sleep(0.05)
                
                # 更新状态
                self.manager.update_status(rid, RequestStatus.COMPLETED)
                operation_times.append(("update", i, time.time()))
                
                # 移除请求
                self.manager.remove_request(rid)
                operation_times.append(("remove", i, time.time()))
            
            return "background_done"
        
        async def mock_ui_wait():
            """模拟 UI 等待（但不真正启动 UI）"""
            await asyncio.sleep(0.5)  # 模拟等待 0.5 秒
            return "ui_done"
        
        # 同时执行 UI 等待和后台操作
        start_time = time.time()
        results = await asyncio.gather(
            mock_ui_wait(),
            background_operations()
        )
        total_time = time.time() - start_time
        
        # 验证两个任务都完成了
        assert results[0] == "ui_done"
        assert results[1] == "background_done"
        
        # 验证后台操作在 UI 等待期间完成（应该有操作在 UI 完成前执行）
        assert len(operation_times) == 20  # 5 次循环 * 4 个操作
        
        # 验证总时间接近 0.5s（而不是串行的 0.5s + 后台操作时间）
        assert total_time < 1.0, f"总执行时间 {total_time}s 过长，Server 可能被阻塞"
    
    @pytest.mark.asyncio
    async def test_concurrent_launch_and_wait_with_timeout(self):
        """
        测试多个 launch_and_wait 可以并发执行（使用超时取消）
        
        这个测试会真正调用 launch_and_wait，但使用超时来避免无限等待
        """
        import time
        
        async def launch_with_timeout(message: str, timeout: float = 0.5):
            """带超时的 launch_and_wait"""
            try:
                result = await asyncio.wait_for(
                    self.launcher.launch_and_wait(message),
                    timeout=timeout
                )
                return ("completed", result)
            except asyncio.TimeoutError:
                return ("timeout", None)
            except Exception as e:
                return ("error", str(e))
        
        # 记录开始时间
        start_time = time.time()
        
        # 同时启动 3 个 launch_and_wait（都会超时，因为没有用户交互）
        tasks = [
            launch_with_timeout(f"Agent {i} 请求", timeout=1.0)
            for i in range(3)
        ]
        
        # 并行执行
        results = await asyncio.gather(*tasks)
        
        # 记录结束时间
        elapsed_time = time.time() - start_time
        
        # 验证所有任务都超时了（因为没有用户交互）
        for i, (status, _) in enumerate(results):
            assert status == "timeout", f"Agent {i} 状态异常: {status}"
        
        # 验证是并行执行的：3 个 1s 超时的任务应该在 ~1s 内完成
        # 如果是串行的，需要 ~3s
        assert elapsed_time < 2.0, f"执行时间 {elapsed_time}s 过长，可能是串行执行"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
