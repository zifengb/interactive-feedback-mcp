"""
async_launcher.py - 异步 UI 启动器
职责：非阻塞启动和监控 feedback_ui.py 进程

支持功能：
- 非阻塞启动 UI 进程（不阻塞 Server，但支持异步等待结果）
- 后台监控进程状态
- 收集反馈结果
- [P0] 轮询间隔优化为 1.0 秒
- [P1] 日志记录
"""
import os
import sys
import json
import asyncio
import tempfile
import subprocess
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from request_manager import RequestManager, RequestStatus

# 配置日志
logger = logging.getLogger(__name__)


class AsyncUILauncher:
    """
    异步 UI 启动器
    负责：
    - 非阻塞启动 UI 进程
    - 后台监控进程状态
    - 收集反馈结果
    """
    
    def __init__(self) -> None:
        self.manager = RequestManager()
        self.script_dir = Path(__file__).parent
        self.feedback_ui_path = self.script_dir / "feedback_ui.py"
        
        # 存储监控任务引用，便于取消
        self._monitor_tasks: Dict[str, asyncio.Task] = {}
        
        # [P0] 轮询间隔优化为 1.0 秒（原 0.5 秒）
        self.poll_interval = 1.0
        
        logger.info(f"AsyncUILauncher 初始化完成，轮询间隔: {self.poll_interval}s")
    
    async def start_feedback_ui(
        self,
        request_id: str,
        message: str,
        predefined_options: Optional[List[str]] = None,
        window_title: Optional[str] = None
    ) -> bool:
        """
        非阻塞启动反馈 UI
        
        Args:
            request_id: 请求 ID
            message: 显示给用户的消息
            predefined_options: 预设选项
            
        Returns:
            是否成功启动
        """
        # 1. 创建唯一的临时输出文件
        try:
            fd, output_file = tempfile.mkstemp(
                suffix=f"_{request_id}.json",
                prefix="feedback_"
            )
            os.close(fd)  # 关闭文件描述符，让 UI 进程可以写入
        except Exception as e:
            logger.error(f"创建临时文件失败: {e}")
            return False
        
        # 2. 更新请求的输出文件路径
        request = self.manager.get_request(request_id)
        if not request:
            # 请求不存在
            logger.warning(f"请求 {request_id} 不存在")
            if os.path.exists(output_file):
                os.unlink(output_file)
            return False
        
        self.manager.set_output_file(request_id, output_file)
        
        # 3. 构建命令参数
        args = [
            sys.executable,
            "-u",  # 无缓冲输出
            str(self.feedback_ui_path),
            "--prompt", message,
            "--output-file", output_file,
            "--predefined-options", 
            "|||".join(predefined_options) if predefined_options else ""
        ]
        if window_title:
            args.extend(["--window-title", window_title])
        
        try:
            # 4. 非阻塞启动进程
            # Windows 特殊处理：使用 CREATE_NO_WINDOW 避免弹出控制台窗口
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=creation_flags
            )
            
            # 5. 保存进程引用
            self.manager.set_process(request_id, process)
            
            logger.info(f"UI 进程已启动，request_id={request_id}, pid={process.pid}")
            
            # 6. 创建后台监控任务
            task = asyncio.create_task(
                self._monitor_process(request_id, process, output_file)
            )
            self._monitor_tasks[request_id] = task
            
            return True
            
        except Exception as e:
            # 启动失败
            self.manager.update_status(request_id, RequestStatus.ERROR)
            if os.path.exists(output_file):
                os.unlink(output_file)
            logger.error(f"启动 UI 失败: {e}")
            return False
    
    async def _monitor_process(
        self, 
        request_id: str, 
        process: subprocess.Popen,
        output_file: str
    ) -> None:
        """
        后台监控进程状态
        
        在进程退出后读取结果并更新状态
        """
        try:
            logger.debug(f"开始监控进程 {request_id}, pid={process.pid}")
            
            # [P0] 使用优化后的轮询间隔
            while process.poll() is None:
                await asyncio.sleep(self.poll_interval)
            
            # 进程已结束
            exit_code = process.returncode
            logger.info(f"进程 {request_id} 已退出，exit_code={exit_code}")
            
            if exit_code == 0 and os.path.exists(output_file):
                # 正常退出，读取结果
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        result = json.load(f)
                    self.manager.update_status(
                        request_id, 
                        RequestStatus.COMPLETED, 
                        result
                    )
                    logger.info(f"请求 {request_id} 已完成，结果已读取")
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"读取结果失败: {e}")
                    self.manager.update_status(request_id, RequestStatus.ERROR)
            else:
                # 非正常退出（用户关闭窗口等）
                self.manager.update_status(request_id, RequestStatus.CANCELLED)
                logger.info(f"请求 {request_id} 已取消（用户关闭窗口或异常退出）")
                
        except asyncio.CancelledError:
            # 任务被取消
            logger.info(f"监控任务 {request_id} 被取消")
            self.manager.update_status(request_id, RequestStatus.CANCELLED)
            raise
            
        except Exception as e:
            logger.error(f"监控异常: {e}")
            self.manager.update_status(request_id, RequestStatus.ERROR)
            
        finally:
            # 清理临时文件
            if os.path.exists(output_file):
                try:
                    os.unlink(output_file)
                    logger.debug(f"已清理临时文件: {output_file}")
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {e}")
            
            # 移除任务引用
            if request_id in self._monitor_tasks:
                del self._monitor_tasks[request_id]
    
    async def cancel_feedback(self, request_id: str) -> bool:
        """
        取消反馈请求
        
        Args:
            request_id: 要取消的请求 ID
            
        Returns:
            是否成功取消
        """
        request = self.manager.get_request(request_id)
        if not request:
            logger.warning(f"取消失败：请求 {request_id} 不存在")
            return False
        
        logger.info(f"正在取消请求 {request_id}")
        
        # 1. 终止 UI 进程
        if request.process and request.process.poll() is None:
            try:
                request.process.terminate()
                logger.debug(f"已发送终止信号到进程 {request.process.pid}")
                # 等待进程退出
                try:
                    request.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 强制杀死
                    request.process.kill()
                    request.process.wait()
                    logger.warning(f"进程 {request.process.pid} 强制终止")
            except Exception as e:
                logger.error(f"终止进程失败: {e}")
        
        # 2. 取消监控任务
        if request_id in self._monitor_tasks:
            task = self._monitor_tasks[request_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # 3. 更新状态
        self.manager.update_status(request_id, RequestStatus.CANCELLED)
        
        # 4. 清理临时文件
        if request.output_file and os.path.exists(request.output_file):
            try:
                os.unlink(request.output_file)
                logger.debug(f"已清理临时文件: {request.output_file}")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")
        
        logger.info(f"请求 {request_id} 已取消")
        return True
    
    def get_active_count(self) -> int:
        """获取活跃的监控任务数量"""
        return len([t for t in self._monitor_tasks.values() if not t.done()])
    
    async def cancel_all(self) -> int:
        """
        取消所有待处理的请求
        
        Returns:
            取消的请求数量
        """
        pending = self.manager.get_pending_requests()
        cancelled_count = 0
        
        for req in pending:
            if await self.cancel_feedback(req.request_id):
                cancelled_count += 1
        
        logger.info(f"已取消 {cancelled_count} 个请求")
        return cancelled_count
    
    async def launch_and_wait(
        self,
        message: str,
        predefined_options: Optional[List[str]] = None,
        window_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        启动反馈 UI 并异步等待用户完成
        
        这个方法会阻塞当前协程直到用户完成反馈，但不会阻塞 Server 进程，
        允许其他 Agent 同时调用并各自等待自己的 UI。
        
        Args:
            message: 显示给用户的消息
            predefined_options: 预设选项
            
        Returns:
            用户反馈结果字典，包含 interactive_feedback 和 images 字段
            如果用户取消或出错，返回空字典
        """
        # 1. 创建唯一的临时输出文件
        try:
            fd, output_file = tempfile.mkstemp(
                suffix=".json",
                prefix="feedback_"
            )
            os.close(fd)
        except Exception as e:
            logger.error(f"创建临时文件失败: {e}")
            return {}
        
        # 2. 构建命令参数
        args = [
            sys.executable,
            "-u",
            str(self.feedback_ui_path),
            "--prompt", message,
            "--output-file", output_file,
            "--predefined-options", 
            "|||".join(predefined_options) if predefined_options else ""
        ]
        if window_title:
            args.extend(["--window-title", window_title])
        
        process = None
        try:
            # 3. 非阻塞启动进程
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=creation_flags
            )
            
            logger.info(f"UI 进程已启动，pid={process.pid}")
            
            # 4. 异步等待进程完成（不阻塞 Server）
            while process.poll() is None:
                await asyncio.sleep(self.poll_interval)
            
            # 5. 进程已结束，检查结果
            exit_code = process.returncode
            logger.info(f"UI 进程已退出，exit_code={exit_code}")
            
            if exit_code == 0 and os.path.exists(output_file):
                # 正常退出，读取结果
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        result = json.load(f)
                    logger.info("用户反馈已获取")
                    return result
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"读取结果失败: {e}")
                    return {}
            else:
                # 用户关闭窗口或异常退出
                logger.info("用户取消或窗口被关闭")
                return {}
                
        except asyncio.CancelledError:
            # 任务被取消，终止进程
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            logger.info("等待被取消")
            raise
            
        except Exception as e:
            logger.error(f"启动或等待 UI 失败: {e}")
            return {}
            
        finally:
            # 清理临时文件
            if os.path.exists(output_file):
                try:
                    os.unlink(output_file)
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {e}")

