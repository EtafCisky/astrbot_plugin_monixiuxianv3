"""
市场命令处理器

处理玩家交易市场相关的命令。
"""
from typing import AsyncGenerator

from astrbot.api.event import AstrMessageEvent

from ...application.services.market_service import MarketService
from ...core.exceptions import BusinessException
from ..decorators import require_player


class MarketHandler:
    """市场命令处理器"""
    
    def __init__(self, market_service: MarketService, player_service):
        """
        初始化市场命令处理器
        
        Args:
            market_service: 市场服务
            player_service: 玩家服务
        """
        self.market_service = market_service
        self.player_service = player_service
    
    @require_player
    async def handle_list_item(
        self,
        event: AstrMessageEvent,
        player,
        item_name: str = "",
        price: str = "",
        quantity: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        处理上架物品命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
            item_name: 物品名称
            price: 出售价格
            quantity: 上架数量（可选，默认为1）
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        # 验证参数
        if not item_name or not price:
            yield event.plain_result(
                "❌ 参数不完整\n"
                "💡 使用方法：市场上架 <物品名称> <价格> [数量]\n"
                "📝 例如：市场上架 筑基丹 1000\n"
                "📝 批量：市场上架 筑基丹 1000 5"
            )
            return
        
        # 验证价格格式
        try:
            price_int = int(price)
        except ValueError:
            yield event.plain_result("❌ 价格必须是数字")
            return
        
        # 验证数量格式
        quantity_int = 1
        if quantity:
            try:
                quantity_int = int(quantity)
                if quantity_int < 1:
                    yield event.plain_result("❌ 数量必须大于0")
                    return
                if quantity_int > 99:
                    yield event.plain_result("❌ 单次上架数量不能超过99")
                    return
            except ValueError:
                yield event.plain_result("❌ 数量必须是数字")
                return
        
        try:
            # 单次上架，包含指定数量的物品
            success, message, listing = self.market_service.list_item(
                user_id,
                item_name,
                price_int,
                quantity_int
            )
            
            if success and listing:
                qty_display = f" x{listing.quantity}" if listing.quantity > 1 else ""
                total_price = listing.get_total_price()
                total_info = f"\n💵 总价：{total_price}灵石" if listing.quantity > 1 else ""
                
                response = f"""✅ 上架成功！

📋 上架信息：
━━━━━━━━━━━━━━━
🆔 上架ID：{listing.listing_id[:8]}...
📦 物品：{listing.item_name}{qty_display}
💰 单价：{listing.price}灵石{total_info}
{f"💡 参考价：{listing.reference_price}灵石" if listing.reference_price else "💡 参考价：无"}

💡 使用 市场下架 {listing.listing_id[:8]} 可以取消上架"""
                yield event.plain_result(response)
            else:
                yield event.plain_result(message)
                
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
    
    async def handle_view_market(
        self,
        event: AstrMessageEvent
    ) -> AsyncGenerator[str, None]:
        """
        处理查看市场命令
        
        Args:
            event: 消息事件
            
        Yields:
            响应消息
        """
        try:
            listings = self.market_service.view_market()
            
            if not listings:
                yield event.plain_result(
                    "🏪 市场空空如也\n\n"
                    "💡 使用 市场上架 <物品名称> <价格> 来出售物品"
                )
                return
            
            # 构建市场列表
            lines = ["🏪 玩家交易市场", "━━━━━━━━━━━━━━━", ""]
            
            for idx, listing in enumerate(listings, 1):
                ref_price_info = f" (参考价:{listing.reference_price})" if listing.reference_price else ""
                qty_display = f" x{listing.quantity}" if listing.quantity > 1 else ""
                total_price = listing.get_total_price()
                total_info = f" (总价:{total_price})" if listing.quantity > 1 else ""
                
                lines.append(
                    f"{idx}. 【{listing.item_name}{qty_display}】\n"
                    f"   💰 单价:{listing.price}灵石{total_info}{ref_price_info}\n"
                    f"   👤 卖家：{listing.seller_name}\n"
                    f"   🆔 ID：{listing.listing_id[:8]}...\n"
                )
            
            lines.append("━━━━━━━━━━━━━━━")
            lines.append("💡 使用 购买 <上架ID前8位> [数量] 来购买物品")
            lines.append("📝 例如：购买 a1b2c3d4 或 购买 a1b2c3d4 5")
            
            yield event.plain_result("\n".join(lines))
            
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")

    @require_player
    async def handle_buy_item(
        self,
        event: AstrMessageEvent,
        player,
        listing_id_prefix: str = "",
        quantity: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        处理购买物品命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
            listing_id_prefix: 上架ID（可以是前缀）
            quantity: 购买数量（可选）
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        # 验证参数
        if not listing_id_prefix:
            yield event.plain_result(
                "❌ 请提供上架ID\n"
                "💡 使用方法：购买 <上架ID> [数量]\n"
                "📝 例如：购买 a1b2c3d4\n"
                "📝 批量：购买 a1b2c3d4 5"
            )
            return
        
        # 解析购买数量
        buy_qty = None
        if quantity:
            try:
                buy_qty = int(quantity)
                if buy_qty < 1:
                    yield event.plain_result("❌ 购买数量必须大于0")
                    return
            except ValueError:
                yield event.plain_result("❌ 数量必须是数字")
                return
        
        try:
            # 查找匹配的上架记录
            all_listings = self.market_service.view_market()
            matching_listing = None
            
            for listing in all_listings:
                if listing.listing_id.startswith(listing_id_prefix):
                    matching_listing = listing
                    break
            
            if not matching_listing:
                yield event.plain_result(f"❌ 未找到上架ID为 {listing_id_prefix} 的物品")
                return
            
            # 执行购买
            success, message, details = self.market_service.buy_item(
                user_id,
                matching_listing.listing_id,
                buy_qty
            )
            
            if success:
                qty_display = f" x{details['quantity']}" if details['quantity'] > 1 else ""
                response = f"""✅ {message}

💳 交易详情：
━━━━━━━━━━━━━━━
📦 物品：{details['item_name']}{qty_display}
💰 单价：{details['unit_price']}灵石
💵 总价：{details['total_price']}灵石
📊 交易税：{details['tax']}灵石 (5%)
👤 卖家收入：{details['seller_revenue']}灵石 (95%)
🤝 卖家：{details['seller_name']}"""
                yield event.plain_result(response)
            else:
                yield event.plain_result(message)
                
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
    
    @require_player
    async def handle_unlist_item(
        self,
        event: AstrMessageEvent,
        player,
        listing_id_prefix: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        处理下架物品命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
            listing_id_prefix: 上架ID（可以是前缀）
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        # 验证参数
        if not listing_id_prefix:
            yield event.plain_result(
                "❌ 请提供上架ID\n"
                "💡 使用方法：市场下架 <上架ID>\n"
                "📝 例如：市场下架 a1b2c3d4"
            )
            return
        
        try:
            # 查找匹配的上架记录
            all_listings = self.market_service.view_market()
            matching_listing = None
            
            for listing in all_listings:
                if listing.listing_id.startswith(listing_id_prefix):
                    matching_listing = listing
                    break
            
            if not matching_listing:
                yield event.plain_result(f"❌ 未找到上架ID为 {listing_id_prefix} 的物品")
                return
            
            # 执行下架
            success, message = self.market_service.unlist_item(
                user_id,
                matching_listing.listing_id
            )
            
            if success:
                response = f"""✅ {message}

📦 物品已返回储物戒"""
                yield event.plain_result(response)
            else:
                yield event.plain_result(message)
                
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
