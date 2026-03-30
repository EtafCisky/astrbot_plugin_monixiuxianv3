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
        price: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        处理上架物品命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
            item_name: 物品名称
            price: 出售价格
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        # 验证参数
        if not item_name or not price:
            yield event.plain_result(
                "❌ 参数不完整\n"
                "💡 使用方法：市场上架 <物品名称> <价格>\n"
                "📝 例如：市场上架 筑基丹 1000"
            )
            return
        
        # 验证价格格式
        try:
            price_int = int(price)
        except ValueError:
            yield event.plain_result("❌ 价格必须是数字")
            return
        
        try:
            success, message, listing = self.market_service.list_item(
                user_id,
                item_name,
                price_int
            )
            
            if success and listing:
                response = f"""✅ {message}

📋 上架信息：
━━━━━━━━━━━━━━━
🆔 上架ID：{listing.listing_id[:8]}...
📦 物品：{listing.item_name}
💰 售价：{listing.price}灵石
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
                lines.append(
                    f"{idx}. 【{listing.item_name}】\n"
                    f"   💰 {listing.price}灵石{ref_price_info}\n"
                    f"   👤 卖家：{listing.seller_name}\n"
                    f"   🆔 ID：{listing.listing_id[:8]}...\n"
                )
            
            lines.append("━━━━━━━━━━━━━━━")
            lines.append("💡 使用 购买 <上架ID前8位> 来购买物品")
            
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
        listing_id_prefix: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        处理购买物品命令
        
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
                "💡 使用方法：购买 <上架ID>\n"
                "📝 例如：购买 a1b2c3d4"
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
            
            # 执行购买
            success, message, details = self.market_service.buy_item(
                user_id,
                matching_listing.listing_id
            )
            
            if success:
                response = f"""✅ {message}

💳 交易详情：
━━━━━━━━━━━━━━━
📦 物品：{details['item_name']}
💰 支付：{details['price']}灵石
📊 交易税：{details['tax']}灵石 (15%)
👤 卖家收入：{details['seller_revenue']}灵石 (85%)
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
