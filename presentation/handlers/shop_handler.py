"""商店命令处理器"""
from typing import AsyncGenerator
from astrbot.api.event import AstrMessageEvent

from ...application.services.shop_service import ShopService
from ...application.services.player_service import PlayerService
from ...core.exceptions import XiuxianException
from ..decorators import require_player


class ShopHandler:
    """商店命令处理器"""
    
    def __init__(
        self,
        shop_service: ShopService,
        player_service: PlayerService
    ):
        self.shop_service = shop_service
        self.player_service = player_service
    
    @require_player
    async def handle_pill_pavilion(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理丹阁命令"""
        try:
            # 丹阁：只显示丹药
            def pill_filter(item):
                return item['type'] in ['pill', 'exp_pill', 'utility_pill']
            
            shop = self.shop_service.ensure_shop_refreshed(
                shop_id="pill_pavilion",
                shop_name="丹阁",
                item_filter=pill_filter,
                count=10,
                refresh_hours=6
            )
            
            display = self.shop_service.format_shop_display(shop)
            yield event.plain_result(display)
            
        except XiuxianException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 查看丹阁失败：{str(e)}")
    
    @require_player
    async def handle_weapon_pavilion(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理器阁命令"""
        try:
            # 器阁：只显示武器和防具
            def weapon_filter(item):
                return item['type'] in ['weapon', 'armor', 'accessory']
            
            shop = self.shop_service.ensure_shop_refreshed(
                shop_id="weapon_pavilion",
                shop_name="器阁",
                item_filter=weapon_filter,
                count=10,
                refresh_hours=6
            )
            
            display = self.shop_service.format_shop_display(shop)
            yield event.plain_result(display)
            
        except XiuxianException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 查看器阁失败：{str(e)}")
    
    @require_player
    async def handle_treasure_pavilion(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理百宝阁命令"""
        try:
            # 百宝阁：显示所有物品
            shop = self.shop_service.ensure_shop_refreshed(
                shop_id="general_shop",
                shop_name="百宝阁",
                item_filter=None,
                count=15,
                refresh_hours=6
            )
            
            display = self.shop_service.format_shop_display(shop)
            yield event.plain_result(display)
            
        except XiuxianException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 查看百宝阁失败：{str(e)}")
    
    @require_player
    async def handle_buy(
        self, 
        event: AstrMessageEvent,
        args: str = ""
    ) -> AsyncGenerator:
        """处理购买命令"""
        try:
            user_id = event.get_sender_id()
            
            if not args or args.strip() == "":
                yield event.plain_result("❌ 请输入物品名称，例如：购买 一品凝气丹 10")
                return
            
            # 解析参数：物品名 [数量]
            parts = args.strip().split()
            if len(parts) == 1:
                item_name = parts[0]
                quantity = 1
            elif len(parts) >= 2:
                # 最后一个参数可能是数量
                try:
                    quantity = int(parts[-1])
                    item_name = " ".join(parts[:-1])
                except ValueError:
                    # 如果最后一个参数不是数字，则全部作为物品名
                    item_name = " ".join(parts)
                    quantity = 1
            else:
                yield event.plain_result("❌ 请输入物品名称，例如：购买 一品凝气丹 10")
                return
            
            # 验证数量
            if quantity < 1:
                yield event.plain_result("❌ 购买数量必须大于0")
                return
            
            if quantity > 999:
                yield event.plain_result("❌ 单次购买数量不能超过999")
                return
            
            # 获取当前商店ID（从玩家最后访问的商店）
            player = self.player_service.get_player(user_id)
            if not player:
                yield event.plain_result("❌ 玩家不存在")
                return
            
            # 默认使用百宝阁
            shop_id = "general_shop"
            
            # 购买物品
            success, message = self.shop_service.buy_item(
                user_id=user_id,
                shop_id=shop_id,
                item_name=item_name,
                quantity=quantity
            )
            
            if success:
                yield event.plain_result(f"✅ {message}")
            else:
                yield event.plain_result(f"❌ {message}")
                
        except XiuxianException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 购买失败：{str(e)}")
