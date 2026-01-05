"""
request_manager.py - 请求管理器
职责：管理所有反馈请求的生命周期

支持功能：
- 创建和存储请求
- 状态更新
- 过期清理
- [P0] 最大并发限制
"""
import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from enum import Enum
from datetime import datetime
import subprocess

# 配置日志
logger = logging.getLogger(__name__)


class RequestStatus(Enum):
    """请求状态枚举"""
    PENDING = "pending"       # 等待用户反馈
    COMPLETED = "completed"   # 用户已完成反馈
    CANCELLED = "cancelled"   # 请求已取消
    EXPIRED = "expired"       # 请求已过期
    ERROR = "error"           # 发生错误


@dataclass
class FeedbackRequest:
    """
    反馈请求数据类
    存储单个反馈请求的所有相关信息
    """
    request_id: str                                    # 唯一标识
    message: str                                       # 显示给用户的消息
    predefined_options: Optional[List[str]] = None    # 预设选项
    status: RequestStatus = RequestStatus.PENDING      # 当前状态
    result: Optional[Dict[str, Any]] = None           # 反馈结果
    output_file: str = ""                              # 输出文件路径
    process: Optional[subprocess.Popen] = None         # UI 进程引用
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    completed_at: Optional[datetime] = None            # 完成时间


class RequestManager:
    """
    请求管理器（单例模式）
    负责：
    - 创建和存储请求
    - 状态更新
    - 过期清理
    - [P0] 最大并发限制
    """
    _instance: Optional['RequestManager'] = None
    
    # [P0] 最大并发请求数限制
    MAX_CONCURRENT_REQUESTS = 10
    
    def __new__(cls) -> 'RequestManager':
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._requests: Dict[str, FeedbackRequest] = {}
            cls._instance._initialized = True
            logger.info("RequestManager 单例已创建")
        return cls._instance
    
    def create_request(
        self, 
        message: str, 
        predefined_options: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        创建新的反馈请求
        
        Args:
            message: 显示给用户的问题/提示
            predefined_options: 预设选项列表
            
        Returns:
            request_id: 8位唯一标识符，如果超过并发限制则返回 None
        """
        # [P0] 检查并发限制
        pending_count = len(self.get_pending_requests())
        if pending_count >= self.MAX_CONCURRENT_REQUESTS:
            logger.warning(
                f"已达到最大并发请求数限制 ({self.MAX_CONCURRENT_REQUESTS})，"
                f"当前待处理请求数: {pending_count}"
            )
            return None
        
        request_id = str(uuid.uuid4())[:8]
        
        # 确保 ID 唯一（极小概率冲突）
        while request_id in self._requests:
            request_id = str(uuid.uuid4())[:8]
        
        request = FeedbackRequest(
            request_id=request_id,
            message=message,
            predefined_options=predefined_options
        )
        self._requests[request_id] = request
        
        logger.info(f"创建请求 {request_id}，当前总请求数: {len(self._requests)}")
        return request_id
    
    def get_request(self, request_id: str) -> Optional[FeedbackRequest]:
        """获取请求对象"""
        return self._requests.get(request_id)
    
    def update_status(
        self, 
        request_id: str, 
        status: RequestStatus, 
        result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新请求状态
        
        Args:
            request_id: 请求 ID
            status: 新状态
            result: 反馈结果（可选）
            
        Returns:
            是否更新成功
        """
        if request_id not in self._requests:
            logger.warning(f"尝试更新不存在的请求: {request_id}")
            return False
            
        request = self._requests[request_id]
        old_status = request.status
        request.status = status
        
        if result is not None:
            request.result = result
            
        if status == RequestStatus.COMPLETED:
            request.completed_at = datetime.now()
        
        logger.info(f"请求 {request_id} 状态更新: {old_status.value} -> {status.value}")
        return True
    
    def set_output_file(self, request_id: str, output_file: str) -> bool:
        """设置请求的输出文件路径"""
        if request_id not in self._requests:
            return False
        self._requests[request_id].output_file = output_file
        return True
    
    def set_process(self, request_id: str, process: subprocess.Popen) -> bool:
        """设置请求的进程引用"""
        if request_id not in self._requests:
            return False
        self._requests[request_id].process = process
        return True
    
    def remove_request(self, request_id: str) -> bool:
        """移除请求（获取结果后调用）"""
        if request_id in self._requests:
            del self._requests[request_id]
            logger.info(f"移除请求 {request_id}，剩余请求数: {len(self._requests)}")
            return True
        return False
    
    def get_pending_requests(self) -> List[FeedbackRequest]:
        """获取所有待处理的请求"""
        return [
            r for r in self._requests.values() 
            if r.status == RequestStatus.PENDING
        ]
    
    def get_all_requests(self) -> Dict[str, FeedbackRequest]:
        """获取所有请求（调试用）"""
        return self._requests.copy()
    
    def cleanup_expired(self, max_age_seconds: int = 3600) -> int:
        """
        清理过期请求
        
        Args:
            max_age_seconds: 最大存活时间（秒），默认1小时
            
        Returns:
            清理的请求数量
        """
        now = datetime.now()
        expired_ids = []
        
        for rid, req in self._requests.items():
            age = (now - req.created_at).total_seconds()
            if age > max_age_seconds and req.status == RequestStatus.PENDING:
                expired_ids.append(rid)
        
        for rid in expired_ids:
            self.update_status(rid, RequestStatus.EXPIRED)
            logger.info(f"请求 {rid} 已过期（存活时间超过 {max_age_seconds} 秒）")
            
        if expired_ids:
            logger.info(f"清理了 {len(expired_ids)} 个过期请求")
            
        return len(expired_ids)
    
    def cleanup_completed(self, max_age_seconds: int = 300) -> int:
        """
        清理已完成但未被获取的请求
        
        Args:
            max_age_seconds: 完成后最大保留时间（秒），默认5分钟
            
        Returns:
            清理的请求数量
        """
        now = datetime.now()
        cleanup_ids = []
        
        for rid, req in self._requests.items():
            if req.status in (RequestStatus.COMPLETED, RequestStatus.CANCELLED, 
                              RequestStatus.EXPIRED, RequestStatus.ERROR):
                if req.completed_at:
                    age = (now - req.completed_at).total_seconds()
                else:
                    age = (now - req.created_at).total_seconds()
                    
                if age > max_age_seconds:
                    cleanup_ids.append(rid)
        
        for rid in cleanup_ids:
            self.remove_request(rid)
            
        if cleanup_ids:
            logger.info(f"清理了 {len(cleanup_ids)} 个已完成的请求")
            
        return len(cleanup_ids)
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        stats = {
            "total": len(self._requests),
            "pending": 0,
            "completed": 0,
            "cancelled": 0,
            "expired": 0,
            "error": 0
        }
        for req in self._requests.values():
            stats[req.status.value] += 1
        return stats
    
    def reset(self) -> None:
        """重置管理器（主要用于测试）"""
        self._requests.clear()
        logger.info("RequestManager 已重置")

