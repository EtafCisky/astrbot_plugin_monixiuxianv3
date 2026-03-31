"""种子商店命令处理器"""
from astrbot.api.event import AstrMessageEvent

from ...application.services.seed_shop_service import SeedShopService


class SeedShopHandler:
    """种子商店命令处理器"""
    
    def __init__(self, seed_shop_service: SeedShopService):
        self.seed_shop_service = seed_shop_service
    
    async def handle_shop(self, event: AstrMessageEvent):
        """处理 /种子商店 命令 - 显示种子列表"""
        user_id = str(event.get_sender_id())
        
        try:
            # 获取种子列表
            seed_list = self.seed_shop_service.get_seed_list(user_id)
            
            if not seed_list:
                yield event.plain_result("❌ 种子商店暂无可用种子")
                return
            
            # 格式化显示
            msg = self._format_seed_list(seed_list)
            yield event.plain_result(msg)
            
        except Exception as e:
            yield event.plain_result(str(e))
    
    async def handle_buy(self, event: AstrMessageEvent, seed_name: str = "", quantity: str = "1"):
        """处理 /购买种子 [种子名称] [数量] 命令 - 购买种子"""
        user_id = str(event.get_sender_id())
        
        if not seed_name:
            yield event.plain_result(
                "🌱 购买种子\n"
                "━━━━━━━━━━━━━━━\n"
                "购买药草种子用于种植！\n"
                "━━━━━━━━━━━━━━━\n"
                "💡 使用方法：\n"
                "  /购买种子 灵草\n"
                "  /购买种子 血莲子 5\n"
                "━━━━━━━━━━━━━━━\n"
                "📝 提示：\n"
                "• 购买同一种子5次后永久解锁\n"
                "• 已解锁种子可免费获取\n"
                "• 使用 /种子商店 查看所有种子"
            )
            return
        
        try:
            # 解析数量
            try:
                qty = int(quantity)
            except ValueError:
                yield event.plain_result("❌ 数量必须是正整数")
                return
            
            # 购买种子
            result = self.seed_shop_service.buy_seed(user_id, seed_name, qty)
            yield event.plain_result(result)
            
        except Exception as e:
            yield event.plain_result(str(e))
    
    def _format_seed_list(self, seed_list) -> str:
        """格式化种子商店列表"""
        msg = "🏪 种子商店\n"
        msg += "━━━━━━━━━━━━━━━\n"
        
        # 按品级分组显示
        current_rank = None
        for seed in seed_list:
            # 品级分隔
            if seed.herb_rank != current_rank:
                if current_rank is not None:
                    msg += "\n"
                msg += f"【{seed.herb_rank}】\n"
                current_rank = seed.herb_rank
            
            # 种子信息
            seed_display_name = seed.herb_name  # 显示药草名称而非种子名称
            price_display = f"{seed.seed_price:,}灵石" if not seed.is_unlocked else "已解锁"
            grow_time_display = seed.get_grow_time_display()
            
            # 解锁状态或购买进度
            if seed.is_unlocked:
                status = "✅"
            else:
                progress = seed.get_unlock_progress()
                status = f"({progress})"
            
            msg += f"  • {seed_display_name} - {price_display} {status}\n"
            msg += f"    成熟: {grow_time_display}\n"
        
        msg += "━━━━━━━━━━━━━━━\n"
        msg += "💡 提示：\n"
        msg += "• /购买种子 [名称] [数量]\n"
        msg += "• 购买5次后永久解锁\n"
        msg += "• 已解锁种子免费获取"
        
        return msg
