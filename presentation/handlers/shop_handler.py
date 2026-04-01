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
    async def handle_pill_pavilion(self, event: AstrMessageEvent, player) -> AsyncGenerator:
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
    async def handle_weapon_pavilion(self, event: AstrMessageEvent, player) -> AsyncGenerator:
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
    async def handle_treasure_pavilion(self, event: AstrMessageEvent, player) -> AsyncGenerator:
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
        player,
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
            
            # 尝试从最后一个参数解析数量
            quantity = 1
            item_name = args.strip()
            
            if len(parts) >= 2:
                # 检查最后一个参数是否为纯数字
                last_part = parts[-1]
                if last_part.isdigit():
                    quantity = int(last_part)
                    item_name = " ".join(parts[:-1])
            
            if not item_name:
                yield event.plain_result("❌ 请输入物品名称，例如：购买 一品凝气丹 10")
                return
            
            # 验证数量
            if quantity < 1:
                yield event.plain_result("❌ 购买数量必须大于0")
                return
            
            if quantity > 999:
                yield event.plain_result("❌ 单次购买数量不能超过999")
                return
            
            # 尝试从所有商店购买
            shop_ids = ["pill_pavilion", "weapon_pavilion", "general_shop"]
            
            for shop_id in shop_ids:
                try:
                    # 尝试从当前商店购买
                    success, message = self.shop_service.buy_item(
                        user_id=user_id,
                        shop_id=shop_id,
                        item_name=item_name,
                        quantity=quantity
                    )
                    
                    if success:
                        yield event.plain_result(f"✅ {message}")
                        return
                        
                except Exception:
                    # 如果在这个商店找不到，继续尝试下一个商店
                    continue
            
            # 所有商店都找不到
            yield event.plain_result(f"❌ 没有找到【{item_name}】，请检查物品名称或等待刷新")
                
        except XiuxianException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 购买失败：{str(e)}")
