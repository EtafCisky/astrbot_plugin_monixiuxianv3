"""修炼命令处理器"""
from astrbot.api.event import AstrMessageEvent

from ...application.services.cultivation_service import CultivationService
from ...core.exceptions import InvalidStateException
from ..decorators import require_player


class CultivationHandler:
    """修炼命令处理器"""
    
    def __init__(self, cultivation_service: CultivationService, player_service):
        self.cultivation_service = cultivation_service
        self.player_service = player_service
    
    @require_player
    async def handle_start_cultivation(self, event: AstrMessageEvent, player):
        """
        处理闭关命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
        """
        try:
            # 开始闭关
            self.cultivation_service.start_cultivation(player)
            
            # 格式化输出
            message = (
                "🧘 道友已进入闭关状态\n"
                "━━━━━━━━━━━━━━━\n"
                "闭关期间，你将与世隔绝，潜心修炼。\n"
                "💡 发送「出关」结束闭关\n"
                "⏱️ 每分钟将获得修为，受灵根资质影响。"
            )
            
            yield event.plain_result(message)
            
        except InvalidStateException as e:
            if "修炼中" in e.current_state:
                yield event.plain_result("❌ 道友已在闭关中，请勿重复进入。")
            else:
                yield event.plain_result(f"❌ 当前状态「{e.current_state}」无法闭关修炼！")
        except Exception as e:
            yield event.plain_result(f"❌ 闭关失败：{str(e)}")
    
    @require_player
    async def handle_end_cultivation(self, event: AstrMessageEvent, player):
        """
        处理出关命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
        """
        try:
            # 结束闭关
            result = self.cultivation_service.end_cultivation(player)
            
            # 计算时长显示
            hours = result.duration_minutes // 60
            minutes = result.duration_minutes % 60
            time_str = ""
            if hours > 0:
                time_str += f"{hours}小时"
            if minutes > 0:
                time_str += f"{minutes}分钟"
            
            # 超时提示
            exceed_msg = ""
            if result.is_overtime:
                effective_hours = result.max_minutes // 60
                exceed_msg = f"\n⚠️ 闭关超过{effective_hours}小时，仅计算前{effective_hours}小时修为"
            
            # 格式化输出
            message = (
                "🌟 道友出关成功！\n"
                "━━━━━━━━━━━━━━━\n"
                f"⏱️ 闭关时长：{time_str}\n"
                f"📈 获得修为：{result.gained_exp:,}{exceed_msg}\n"
                f"💫 当前修为：{player.experience:,}\n"
                "━━━━━━━━━━━━━━━\n"
                "道友已回归红尘，可继续修行。"
            )
            
            yield event.plain_result(message)
            
        except InvalidStateException:
            yield event.plain_result("❌ 道友当前并未闭关，无需出关。")
        except ValueError as e:
            error_msg = str(e)
            # 如果是数据异常，状态已被重置，提示用户可以重新闭关
            if "数据异常" in error_msg:
                yield event.plain_result(f"❌ {error_msg}\n💡 你现在可以重新发送「闭关」命令开始修炼。")
            else:
                yield event.plain_result(f"❌ {error_msg}")
        except Exception as e:
            yield event.plain_result(f"❌ 出关失败：{str(e)}")
