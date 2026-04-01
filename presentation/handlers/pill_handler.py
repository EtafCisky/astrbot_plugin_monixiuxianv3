"""
丹药处理器

处理丹药相关的命令。
"""
from typing import AsyncGenerator
from astrbot.api.event import AstrMessageEvent

from ...application.services.pill_service import PillService
from ...core.exceptions import BusinessException
from ..decorators import require_player


class PillHandler:
    """丹药处理器"""
    
    def __init__(self, pill_service: PillService, player_service):
        """
        初始化丹药处理器
        
        Args:
            pill_service: 丹药服务
            player_service: 玩家服务
        """
        self.pill_service = pill_service
        self.player_service = player_service
    
    @require_player
    async def handle_show_pills(self, event: AstrMessageEvent, player) -> AsyncGenerator[str, None]:
        """
        显示丹药背包
        
        命令格式：丹药背包
        """
        try:
            user_id = event.get_sender_id()
            
            # 获取并格式化丹药背包
            message = self.pill_service.format_pill_inventory(user_id)
            
            yield event.plain_result(message)
            
        except BusinessException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"查看丹药背包失败：{str(e)}")
    
    @require_player
    async def handle_use_pill(self, event: AstrMessageEvent, player, pill_name: str = "", quantity: str = "") -> AsyncGenerator[str, None]:
        """
        服用丹药
        
        命令格式：服用丹药 <丹药名称> [数量]
        """
        try:
            user_id = event.get_sender_id()
            
            # 检查参数
            if not pill_name or pill_name.strip() == "":
                yield event.plain_result(
                    "❌ 请指定要服用的丹药名称\n"
                    "💡 格式：服用丹药 <丹药名称> [数量]\n"
                    "例如：服用丹药 一品气血丹\n"
                    "批量：服用丹药 一品气血丹 10"
                )
                return
            
            pill_name = pill_name.strip()
            
            # 解析数量
            use_quantity = 1
            if quantity:
                try:
                    use_quantity = int(quantity)
                    if use_quantity < 1:
                        yield event.plain_result("❌ 数量必须大于0")
                        return
                    if use_quantity > 99:
                        yield event.plain_result("❌ 单次服用数量不能超过99")
                        return
                except ValueError:
                    yield event.plain_result("❌ 数量必须是数字")
                    return
            
            # 使用丹药
            success, message = self.pill_service.use_pill(user_id, pill_name, use_quantity)
            
            yield event.plain_result(message)
            
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 服用丹药失败：{str(e)}")
    
    @require_player
    async def handle_search_pills(self, event: AstrMessageEvent, player, keyword: str = "") -> AsyncGenerator[str, None]:
        """
        搜索丹药
        
        命令格式：搜索丹药 <关键词>
        """
        try:
            user_id = event.get_sender_id()
            
            # 检查参数
            if not keyword or keyword.strip() == "":
                yield event.plain_result("❌ 请指定搜索关键词\n💡 格式：搜索丹药 <关键词>")
                return
            
            keyword = keyword.strip()
            
            # 搜索丹药
            results = self.pill_service.search_pills(user_id, keyword)
            
            if not results:
                yield event.plain_result(f"❌ 没有找到包含「{keyword}」的丹药")
                return
            
            # 格式化结果
            lines = [f"🔍 搜索结果（关键词：{keyword}）"]
            for pill_name, count in results:
                pill_config = self.pill_service.get_pill_config(pill_name)
                if pill_config:
                    rank = pill_config.get("rank", "未知")
                    lines.append(f"[{rank}] {pill_name} × {count}")
                else:
                    lines.append(f"{pill_name} × {count}")
            
            yield event.plain_result("\n".join(lines))
            
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 搜索丹药失败：{str(e)}")
