"""
炼丹命令处理器

处理炼丹相关的命令。
"""
from typing import AsyncGenerator

from astrbot.api.event import AstrMessageEvent

from ...application.services.alchemy_service import AlchemyService
from ...core.exceptions import BusinessException
from ..decorators import require_player


class AlchemyHandler:
    """炼丹命令处理器"""
    
    def __init__(self, alchemy_service: AlchemyService, player_service):
        """
        初始化炼丹命令处理器
        
        Args:
            alchemy_service: 炼丹服务
            player_service: 玩家服务
        """
        self.alchemy_service = alchemy_service
        self.player_service = player_service
    
    @require_player
    async def handle_show_recipes(
        self, 
        event: AstrMessageEvent,
        player
    ) -> AsyncGenerator[str, None]:
        """
        处理查看丹药配方命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        try:
            message = self.alchemy_service.format_new_recipes(user_id)
            yield event.plain_result(message)
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
    
    @require_player
    async def handle_craft_pill_by_name(
        self, 
        event: AstrMessageEvent,
        player,
        pill_name: str = "",
        quantity: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        处理通过丹药名称炼丹命令（支持批量）
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
            pill_name: 丹药名称
            quantity: 炼制数量
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        # 检查是否提供了丹药名称
        if not pill_name:
            yield event.plain_result(
                "❌ 请输入丹药名称\n"
                "💡 使用方法：炼丹 <丹药名称> [数量]\n"
                "📝 例如：炼丹 筑基丹 或 炼丹 筑基丹 10\n"
                "💡 使用 丹药配方 查看可用配方"
            )
            return
        
        # 解析数量
        craft_quantity = 1
        if quantity:
            try:
                craft_quantity = int(quantity)
                if craft_quantity < 1:
                    yield event.plain_result("❌ 数量必须大于0")
                    return
                if craft_quantity > 99:
                    yield event.plain_result("❌ 单次炼制数量不能超过99")
                    return
            except ValueError:
                yield event.plain_result("❌ 数量必须是数字")
                return
        
        try:
            success, message, result_data = self.alchemy_service.craft_pill_by_name(
                user_id, 
                pill_name,
                craft_quantity
            )
            yield event.plain_result(message)
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
    
    @require_player
    async def handle_query_recipe_by_id(
        self, 
        event: AstrMessageEvent,
        player,
        pill_id: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        处理通过丹药ID查询配方命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
            pill_id: 丹药ID
            
        Yields:
            响应消息
        """
        if not pill_id:
            yield event.plain_result("❌ 请输入丹药ID\n💡 例如：查询配方 1001")
            return
        
        try:
            recipe = self.alchemy_service.get_recipe_by_pill_id(pill_id)
            if not recipe:
                yield event.plain_result(f"❌ 未找到丹药ID为 {pill_id} 的配方")
                return
            
            materials_str = "\n".join([f"  · {k} × {v}" for k, v in recipe.materials.items()])
            
            message = f"""📜 配方详情
━━━━━━━━━━━━━━━

丹药：【{recipe.name}】
品质：{recipe.rank}
配方ID：{recipe.id}
丹药ID：{recipe.pill_id}

所需材料：
{materials_str}

炼丹等级：Lv.{recipe.level_required}
基础成功率：{recipe.success_rate}%
材料成本：{recipe.cost}灵石

💡 使用 炼丹 {recipe.name} 开始炼制"""
            
            yield event.plain_result(message)
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
    
    @require_player
    async def handle_query_recipe_by_name(
        self, 
        event: AstrMessageEvent,
        player,
        pill_name: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        处理通过丹药名称查询配方命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
            pill_name: 丹药名称
            
        Yields:
            响应消息
        """
        if not pill_name:
            yield event.plain_result("❌ 请输入丹药名称\n💡 例如：查询配方 筑基丹")
            return
        
        try:
            recipe = self.alchemy_service.get_recipe_by_name(pill_name)
            if not recipe:
                yield event.plain_result(f"❌ 未找到【{pill_name}】的配方")
                return
            
            materials_str = "\n".join([f"  · {k} × {v}" for k, v in recipe.materials.items()])
            
            message = f"""📜 配方详情
━━━━━━━━━━━━━━━

丹药：【{recipe.name}】
品质：{recipe.rank}
配方ID：{recipe.id}
丹药ID：{recipe.pill_id}

所需材料：
{materials_str}

炼丹等级：Lv.{recipe.level_required}
基础成功率：{recipe.success_rate}%
材料成本：{recipe.cost}灵石

💡 使用 炼丹 {recipe.name} 开始炼制"""
            
            yield event.plain_result(message)
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
    
    @require_player
    async def handle_query_recipes_by_rank(
        self, 
        event: AstrMessageEvent,
        player,
        rank: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        处理按品质查询配方命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
            rank: 品质等级
            
        Yields:
            响应消息
        """
        if not rank:
            yield event.plain_result("❌ 请输入品质等级\n💡 例如：查询品质配方 凡品\n可用品质：凡品、灵品、珍品、圣品、帝品、道品、仙品、神品")
            return
        
        try:
            if not self.alchemy_service.recipe_manager:
                yield event.plain_result("❌ 配方系统未初始化")
                return
            
            recipes = self.alchemy_service.recipe_manager.get_recipes_by_rank(rank)
            if not recipes:
                yield event.plain_result(f"❌ 未找到品质为【{rank}】的配方")
                return
            
            lines = [f"📜 {rank}配方列表", "━━━━━━━━━━━━━━━", ""]
            
            for recipe in recipes:
                materials_str = "、".join([f"{k}×{v}" for k, v in recipe.materials.items()])
                lines.append(f"【{recipe.name}】")
                lines.append(f"  等级：Lv.{recipe.level_required} | 成功率：{recipe.success_rate}%")
                lines.append(f"  材料：{materials_str}")
                lines.append("")
            
            lines.append(f"共 {len(recipes)} 个配方")
            lines.append("💡 使用 查询配方 <丹药名称> 查看详情")
            
            yield event.plain_result("\n".join(lines))
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
    
    @require_player
    async def handle_alchemy_info(
        self, 
        event: AstrMessageEvent,
        player
    ) -> AsyncGenerator[str, None]:
        """
        处理查看炼丹职业信息命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        try:
            message = self.alchemy_service.get_alchemy_info(user_id)
            yield event.plain_result(message)
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
