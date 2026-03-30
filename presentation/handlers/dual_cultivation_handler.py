"""双修命令处理器"""
import re
from astrbot.api.event import AstrMessageEvent

from ...application.services.dual_cultivation_service import DualCultivationService


class DualCultivationHandler:
    """双修命令处理器"""
    
    def __init__(self, dual_service: DualCultivationService):
        self.dual_service = dual_service
    
    async def handle_dual_request(self, event: AstrMessageEvent, target: str = ""):
        """发起双修"""
        user_id = str(event.get_sender_id())
        
        # 提取目标ID
        target_id = self._extract_user_id(target, event)
        if not target_id:
            yield event.plain_result(
                "💕 双修系统\n"
                "━━━━━━━━━━━━━━━\n"
                "与他人双修，双方平分1小时闭关修为总和！\n"
                "冷却时间：24小时\n"
                "━━━━━━━━━━━━━━━\n"
                "💡 使用 /双修 @某人"
            )
            return
        
        success, msg = self.dual_service.send_request(user_id, target_id)
        yield event.plain_result(msg)
    
    async def handle_accept(self, event: AstrMessageEvent):
        """接受双修"""
        user_id = str(event.get_sender_id())
        success, msg = self.dual_service.accept_request(user_id)
        yield event.plain_result(msg)
    
    async def handle_reject(self, event: AstrMessageEvent):
        """拒绝双修"""
        user_id = str(event.get_sender_id())
        success, msg = self.dual_service.reject_request(user_id)
        yield event.plain_result(msg)
    
    def _extract_user_id(self, msg: str, event: AstrMessageEvent) -> str:
        """提取用户ID"""
        if not msg:
            return ""
        
        # 尝试从 @ 提及中提取
        at_match = re.search(r'\[CQ:at,qq=(\d+)\]', msg)
        if at_match:
            return at_match.group(1)
        
        # 尝试提取纯数字
        num_match = re.search(r'(\d{5,12})', msg)
        if num_match:
            return num_match.group(1)
        
        return ""
