"""
server_async.py - 异步版 MCP Server
支持多 Agent 并发的反馈请求（每个 Agent 各自阻塞等待自己的 UI，不阻塞 Server）

支持功能：
- start_feedback: 启动反馈 UI 并阻塞等待结果（支持多 Agent 并发）
- interactive_feedback: 兼容模式
- [P1] 启动时清理残留临时文件
- [P1] 统一日志配置
"""
import os
import sys
import glob
import base64
import logging
import tempfile
from typing import Optional, List, Tuple, Union

from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from pydantic import Field

from async_launcher import AsyncUILauncher

# ============================================================
# [P1] 日志配置
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 创建 MCP 实例
mcp = FastMCP("Interactive Feedback MCP (Async)", log_level="ERROR")

# 全局启动器
launcher = AsyncUILauncher()


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
# 辅助函数
# ============================================================

def _parse_feedback_result(result_dict: dict) -> Union[Tuple[Union[str, Image], ...], str]:
    """
    解析反馈结果，转换为 MCP 返回格式
    
    Args:
        result_dict: 包含 interactive_feedback 和 images 的字典
        
    Returns:
        文本、图片或它们的组合
    """
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
        return tuple(images) if len(images) > 1 else (images[0],)
    else:
        return ""


# ============================================================
# MCP 工具
# ============================================================

@mcp.tool()
async def start_feedback(
    message: str = Field(description="显示给用户的问题或提示"),
    predefined_options: Optional[List[str]] = Field(
        default=None, 
        description="预设选项列表，方便用户快速选择（可选）"
    ),
    window_title: Optional[str] = Field(
        default=None,
        description="反馈窗口标题，建议传入当前会话的主题摘要，"
                    "用于在反馈窗口标题栏显示。"
                    "请保持简洁，建议不超过 30 个字符。"
    ),
) -> Union[Tuple[Union[str, Image], ...], str]:
    """
    启动交互式反馈 UI 并等待用户完成
    
    此工具会弹出一个反馈窗口，等待用户输入后返回结果。
    支持多个 Agent 同时调用，每个 Agent 各自等待自己的 UI 窗口。
    
    Returns:
        用户的反馈文本和/或图片，如果用户取消则返回空字符串
    """
    logger.info(f"收到反馈请求: {message[:50]}...")
    
    # 使用 launch_and_wait 异步等待用户反馈
    # 这会阻塞当前协程，但不会阻塞 Server 进程
    result_dict = await launcher.launch_and_wait(message, predefined_options, window_title)
    
    if not result_dict:
        logger.info("用户取消了反馈或发生错误")
        return ""
    
    logger.info("用户反馈已获取")
    return _parse_feedback_result(result_dict)


@mcp.tool()
def interactive_feedback(
    message: str = Field(description="显示给用户的问题或提示"),
    predefined_options: Optional[List[str]] = Field(
        default=None,
        description="预设选项列表（可选）"
    ),
    window_title: Optional[str] = Field(
        default=None,
        description="反馈窗口标题，建议传入当前会话的主题摘要，"
                    "用于在反馈窗口标题栏显示。"
                    "请保持简洁，建议不超过 30 个字符。"
    ),
) -> Union[Tuple[Union[str, Image], ...], str]:
    """
    [兼容模式] 阻塞式交互反馈
    
    与 start_feedback 功能相同，保留此工具是为了向后兼容。
    推荐使用 start_feedback。
    """
    # 导入原有实现
    script_dir = os.path.dirname(__file__)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    
    from server import launch_feedback_ui
    
    predefined_options_list = predefined_options if isinstance(predefined_options, list) else None
    result_dict = launch_feedback_ui(message, predefined_options_list, window_title)
    
    return _parse_feedback_result(result_dict)


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    # [P1] 启动时清理残留临时文件
    cleanup_temp_files()
    
    logger.info("Interactive Feedback MCP (Async) 服务器启动")
    logger.info(f"轮询间隔: {launcher.poll_interval}s")
    
    mcp.run(transport="stdio")
