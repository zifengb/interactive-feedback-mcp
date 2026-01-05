"""
server_async.py - 异步版 MCP Server
支持多 Agent 并发的非阻塞反馈

支持功能：
- 新增异步工具集：start_feedback, check_feedback, get_feedback, cancel_feedback, list_pending_feedbacks
- 兼容原有阻塞式 interactive_feedback 工具
- [P1] 自动过期清理后台任务
- [P1] 启动时清理残留临时文件
- [P1] 统一日志配置
"""
import os
import sys
import glob
import asyncio
import base64
import logging
import tempfile
from typing import Optional, List, Tuple, Union

from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from pydantic import Field

from request_manager import RequestManager, RequestStatus
from async_launcher import AsyncUILauncher

# ============================================================
# [P1] 日志配置
# ============================================================

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 创建 MCP 实例
# log_level="ERROR" 是 FastMCP 需要的，用于 Cline 兼容
mcp = FastMCP("Interactive Feedback MCP (Async)", log_level="ERROR")

# 全局单例
manager = RequestManager()
launcher = AsyncUILauncher()

# 后台清理任务引用
_cleanup_task: Optional[asyncio.Task] = None


# ============================================================
# [P1] 启动时清理残留临时文件
# ============================================================

def cleanup_temp_files() -> int:
    """
    清理残留的临时反馈文件
    
    Returns:
        清理的文件数量
    """
    temp_dir = tempfile.gettempdir()
    pattern = os.path.join(temp_dir, "feedback_*.json")
    files = glob.glob(pattern)
    
    cleaned = 0
    for f in files:
        try:
            os.unlink(f)
            cleaned += 1
            logger.debug(f"清理残留文件: {f}")
        except Exception as e:
            logger.warning(f"清理文件失败 {f}: {e}")
    
    if cleaned > 0:
        logger.info(f"启动时清理了 {cleaned} 个残留临时文件")
    
    return cleaned


# ============================================================
# [P1] 自动过期清理后台任务
# ============================================================

async def auto_cleanup_task(interval_seconds: int = 300) -> None:
    """
    后台自动清理任务
    
    Args:
        interval_seconds: 清理间隔（秒），默认 5 分钟
    """
    logger.info(f"启动自动清理任务，间隔: {interval_seconds}秒")
    
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            
            # 清理过期的待处理请求（超过1小时）
            expired_count = manager.cleanup_expired(max_age_seconds=3600)
            
            # 清理已完成但未被获取的请求（超过5分钟）
            completed_count = manager.cleanup_completed(max_age_seconds=300)
            
            if expired_count > 0 or completed_count > 0:
                stats = manager.get_stats()
                logger.info(
                    f"自动清理完成: 过期={expired_count}, 已完成={completed_count}, "
                    f"当前状态: {stats}"
                )
                
        except asyncio.CancelledError:
            logger.info("自动清理任务已停止")
            break
        except Exception as e:
            logger.error(f"自动清理任务异常: {e}")


def start_cleanup_task() -> None:
    """启动后台清理任务"""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(auto_cleanup_task())
        logger.info("后台清理任务已启动")


def stop_cleanup_task() -> None:
    """停止后台清理任务"""
    global _cleanup_task
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        logger.info("后台清理任务已停止")


# ============================================================
# 新增异步工具
# ============================================================

@mcp.tool()
async def start_feedback(
    message: str = Field(description="显示给用户的问题或提示"),
    predefined_options: Optional[List[str]] = Field(
        default=None, 
        description="预设选项列表，方便用户快速选择（可选）"
    ),
) -> str:
    """
    启动交互式反馈 UI（非阻塞）
    
    此工具会立即返回一个 request_id，不会等待用户完成输入。
    请使用 check_feedback 检查状态，使用 get_feedback 获取结果。
    
    Returns:
        - feedback_started:{request_id} - 成功启动
        - feedback_error:{message} - 启动失败
    """
    # 确保清理任务在运行
    start_cleanup_task()
    
    # 创建请求
    request_id = manager.create_request(message, predefined_options)
    
    if request_id is None:
        # 超过并发限制
        return f"feedback_error:已达到最大并发请求数限制 ({manager.MAX_CONCURRENT_REQUESTS})"
    
    # 异步启动 UI
    success = await launcher.start_feedback_ui(
        request_id, 
        message, 
        predefined_options
    )
    
    if success:
        logger.info(f"反馈请求已启动: {request_id}")
        return f"feedback_started:{request_id}"
    else:
        manager.remove_request(request_id)
        return "feedback_error:启动 UI 失败，请检查系统环境"


@mcp.tool()
def check_feedback(
    request_id: str = Field(description="反馈请求的 ID（由 start_feedback 返回）"),
) -> str:
    """
    检查反馈请求的状态
    
    Returns:
        - status:pending - 等待用户输入
        - status:completed - 用户已完成，可调用 get_feedback 获取结果
        - status:cancelled - 用户取消或窗口被关闭
        - status:expired - 请求已过期
        - status:error - 发生错误
        - error:请求不存在 - request_id 无效
    """
    request = manager.get_request(request_id)
    if not request:
        return "error:请求不存在"
    
    return f"status:{request.status.value}"


@mcp.tool()
def get_feedback(
    request_id: str = Field(description="反馈请求的 ID"),
) -> Union[Tuple[Union[str, Image], ...], str]:
    """
    获取已完成的反馈结果
    
    注意：必须在 check_feedback 返回 status:completed 后调用。
    调用后请求会被自动清理。
    
    Returns:
        - 成功：返回用户反馈文本和/或图片
        - 失败：返回 error:{message}
    """
    request = manager.get_request(request_id)
    if not request:
        return "error:请求不存在"
    
    if request.status != RequestStatus.COMPLETED:
        return f"error:请求尚未完成，当前状态: {request.status.value}"
    
    # 解析结果
    result = request.result or {}
    txt = result.get("interactive_feedback", "").strip()
    img_b64_list = result.get("images", [])
    
    # 转换图片
    images: List[Image] = []
    for b64 in img_b64_list:
        try:
            img_bytes = base64.b64decode(b64)
            images.append(Image(data=img_bytes, format="png"))
        except Exception:
            txt += "\n\n[warning] 有一张图片解码失败。"
    
    # 清理请求（防止内存泄漏）
    manager.remove_request(request_id)
    logger.info(f"已获取并清理请求: {request_id}")
    
    # 组装返回值
    if txt and images:
        return (txt, *images)
    elif txt:
        return txt
    elif images:
        return tuple(images) if len(images) > 1 else (images[0],)
    else:
        return ""


@mcp.tool()
async def cancel_feedback(
    request_id: str = Field(description="要取消的反馈请求 ID"),
) -> str:
    """
    取消正在进行的反馈请求
    
    会关闭对应的 UI 窗口并清理资源。
    
    Returns:
        - cancelled:{request_id} - 取消成功
        - error:{message} - 取消失败
    """
    request = manager.get_request(request_id)
    if not request:
        return "error:请求不存在"
    
    if request.status != RequestStatus.PENDING:
        return f"error:请求已结束，状态: {request.status.value}"
    
    success = await launcher.cancel_feedback(request_id)
    if success:
        logger.info(f"请求已取消: {request_id}")
        return f"cancelled:{request_id}"
    else:
        return "error:取消失败"


@mcp.tool()
def list_pending_feedbacks() -> str:
    """
    列出所有待处理的反馈请求
    
    用于查看当前有哪些反馈正在等待用户输入。
    
    Returns:
        - no_pending_requests - 没有待处理的请求
        - 每行一个：{request_id}:{message前50字符}...
    """
    pending = manager.get_pending_requests()
    if not pending:
        return "no_pending_requests"
    
    lines = []
    for req in pending:
        msg_preview = req.message[:50] + "..." if len(req.message) > 50 else req.message
        # 移除换行符以保持输出整洁
        msg_preview = msg_preview.replace('\n', ' ').replace('\r', '')
        lines.append(f"{req.request_id}:{msg_preview}")
    
    return "\n".join(lines)


# ============================================================
# 兼容工具（保留原有阻塞模式）
# ============================================================

@mcp.tool()
def interactive_feedback(
    message: str = Field(description="显示给用户的问题或提示"),
    predefined_options: Optional[List[str]] = Field(
        default=None,
        description="预设选项列表（可选）"
    ),
) -> Union[Tuple[Union[str, Image], ...], str]:
    """
    [兼容模式] 阻塞式交互反馈
    
    ⚠️ 注意：此工具会阻塞直到用户完成反馈，不支持多 Agent 并发。
    建议使用 start_feedback + check_feedback + get_feedback 组合。
    """
    # 导入原有实现
    script_dir = os.path.dirname(__file__)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    
    from server import launch_feedback_ui
    
    predefined_options_list = predefined_options if isinstance(predefined_options, list) else None
    result_dict = launch_feedback_ui(message, predefined_options_list)
    
    txt: str = result_dict.get("interactive_feedback", "").strip()
    img_b64_list: List[str] = result_dict.get("images", [])
    
    images: List[Image] = []
    for b64 in img_b64_list:
        try:
            img_bytes = base64.b64decode(b64)
            images.append(Image(data=img_bytes, format="png"))
        except Exception:
            txt += "\n\n[warning] 有一张图片解码失败。"
    
    if txt and images:
        return (txt, *images)
    elif txt:
        return txt
    elif images:
        return tuple(images) if len(images) == 1 else tuple(images)
    else:
        return ""


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    # [P1] 启动时清理残留临时文件
    cleanup_temp_files()
    
    logger.info("Interactive Feedback MCP (Async) 服务器启动")
    logger.info(f"最大并发请求数: {manager.MAX_CONCURRENT_REQUESTS}")
    logger.info(f"轮询间隔: {launcher.poll_interval}s")
    
    mcp.run(transport="stdio")

