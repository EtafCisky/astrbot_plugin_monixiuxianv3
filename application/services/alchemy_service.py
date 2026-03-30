"""
炼丹服务层

处理炼丹相关的业务逻辑。
"""
import random
from typing import Optional, Tuple, Dict
from pathlib import Path

from ...domain.models.player import Player
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository
from ...core.config import ConfigManager
from ...core.exceptions import BusinessException
from .recipe_manager import RecipeManager
from ...domain.models.recipe import Recipe


class AlchemyService:
    """炼丹服务"""
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        storage_ring_repo: StorageRingRepository,
        config_manager: ConfigManager,
    ):
        """
        初始化炼丹服务
        
        Args:
            player_repo: 玩家仓储
            storage_ring_repo: 储物戒仓储
            config_manager: 配置管理器
        """
        self.player_repo = player_repo
        self.storage_ring_repo = storage_ring_repo
        self.config_manager = config_manager
        
        # 初始化配方管理器
        try:
            self.recipe_manager = RecipeManager()
            self.recipe_manager.load_recipes()
        except Exception as e:
            print(f"警告：无法加载配方管理器: {e}")
            self.recipe_manager = None
    
    def get_recipe_by_pill_id(self, pill_id: str) -> Optional[Recipe]:
        """
        通过丹药ID获取配方
        
        Args:
            pill_id: 丹药ID
            
        Returns:
            配方对象，不存在则返回None
        """
        if not self.recipe_manager:
            return None
        return self.recipe_manager.get_recipe_by_pill_id(pill_id)
    
    def get_recipe_by_name(self, pill_name: str) -> Optional[Recipe]:
        """
        通过丹药名称获取配方
        
        Args:
            pill_name: 丹药名称
            
        Returns:
            配方对象，不存在则返回None
        """
        if not self.recipe_manager:
            return None
        return self.recipe_manager.get_recipe_by_name(pill_name)
    
    def craft_pill_by_name(self, user_id: str, pill_name: str) -> Tuple[bool, str, Dict]:
        """
        通过丹药名称炼制丹药
        
        Args:
            user_id: 用户ID
            pill_name: 丹药名称
            
        Returns:
            (是否成功, 消息, 结果数据)
            
        Raises:
            BusinessException: 各种业务异常
        """
        # 获取玩家
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        # 检查玩家状态
        if not player.can_cultivate():
            raise BusinessException(f"当前状态「{player.state.value}」无法炼丹")
        
        # 获取配方
        if not self.recipe_manager:
            raise BusinessException("配方系统未初始化")
        
        recipe = self.recipe_manager.get_recipe_by_name(pill_name)
        if not recipe:
            raise BusinessException(f"未找到【{pill_name}】的配方")
        
        # 检查炼丹等级要求
        if player.alchemy_level < recipe.level_required:
            raise BusinessException(
                f"炼制【{recipe.name}】需要炼丹等级 Lv.{recipe.level_required}（当前：Lv.{player.alchemy_level} {player.get_alchemy_title()}）"
            )
        
        # 检查材料
        missing_materials = []
        
        for material_name, required_count in recipe.materials.items():
            # 检查储物戒中的材料
            current_count = self.storage_ring_repo.get_item_count(user_id, material_name)
            if current_count < required_count:
                missing_materials.append(
                    f"{material_name}（需要{required_count}，拥有{current_count}）"
                )
        
        if missing_materials:
            raise BusinessException(
                f"材料不足：\n" + "\n".join(missing_materials)
            )
        
        # 计算成功率
        base_success_rate = recipe.success_rate
        alchemy_bonus = player.get_alchemy_success_bonus()  # 炼丹等级加成
        final_success_rate = min(base_success_rate + alchemy_bonus, 100)
        
        # 判断是否成功
        is_success = random.random() * 100 < final_success_rate
        
        # 消耗材料
        for material_name, required_count in recipe.materials.items():
            self.storage_ring_repo.remove_item(user_id, material_name, required_count)
        
        # 计算炼丹经验
        base_exp = self._calculate_alchemy_exp(recipe.rank)
        gained_exp = base_exp if is_success else base_exp // 3
        
        # 增加炼丹经验
        level_up = player.add_alchemy_exp(gained_exp)
        
        result_data = {
            "pill_name": recipe.name,
            "success": is_success,
            "success_rate": final_success_rate,
            "alchemy_exp": gained_exp,
            "level_up": level_up
        }
        
        if is_success:
            # 炼丹成功，添加丹药到储物戒
            self.storage_ring_repo.add_item(user_id, recipe.name, 1)
            
            level_up_msg = ""
            if level_up:
                level_up_msg = f"\n\n🎊 炼丹等级提升！\n当前等级：Lv.{player.alchemy_level} {player.get_alchemy_title()}"
            
            message = f"""🎉 炼丹成功！

获得：【{recipe.name}】× 1
成功率：{final_success_rate}%
炼丹经验：+{gained_exp}{level_up_msg}"""
        else:
            # 炼丹失败
            level_up_msg = ""
            if level_up:
                level_up_msg = f"\n\n🎊 炼丹等级提升！\n当前等级：Lv.{player.alchemy_level} {player.get_alchemy_title()}"
            
            message = f"""💔 炼丹失败

丹药：【{recipe.name}】
成功率：{final_success_rate}%
炼丹经验：+{gained_exp}（失败获得1/3经验）{level_up_msg}

💡 提升炼丹等级可以增加成功率！"""
        
        # 保存玩家数据
        self.player_repo.save(player)
        
        return is_success, message, result_data
    
    def format_new_recipes(self, user_id: str) -> str:
        """
        格式化配方列表显示
        
        Args:
            user_id: 用户ID
            
        Returns:
            格式化后的字符串
            
        Raises:
            BusinessException: 玩家不存在或配方系统未初始化
        """
        # 获取玩家
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        if not self.recipe_manager:
            raise BusinessException("配方系统未初始化")
        
        # 获取所有配方
        all_recipes = self.recipe_manager.get_all_recipes()
        
        # 筛选玩家可用的配方
        available_recipes = [
            recipe for recipe in all_recipes
            if player.alchemy_level >= recipe.level_required
        ]
        
        if not available_recipes:
            return f"❌ 你当前炼丹等级（Lv.{player.alchemy_level}）无法炼制任何丹药！\n💡 通过炼丹获得经验提升炼丹等级"
        
        # 按品质和等级排序
        rank_order = {"凡品": 0, "灵品": 1, "珍品": 2, "圣品": 3, "帝品": 4, "道品": 5, "仙品": 6, "神品": 7}
        available_recipes.sort(key=lambda r: (rank_order.get(r.rank, 99), r.level_required))
        
        # 获取炼丹职业信息
        alchemy_title = player.get_alchemy_title()
        alchemy_level = player.alchemy_level
        success_bonus = player.get_alchemy_success_bonus()
        
        lines = [
            "🔥 丹药配方",
            "━━━━━━━━━━━━━━━",
            f"炼丹职业：Lv.{alchemy_level} {alchemy_title}",
            f"成功率加成：+{success_bonus}%",
            ""
        ]
        
        for recipe in available_recipes:
            materials_str = "、".join([f"{k}×{v}" for k, v in recipe.materials.items()])
            
            lines.append(f"【{recipe.name}】({recipe.rank})")
            lines.append(f"  炼丹等级：Lv.{recipe.level_required}")
            lines.append(f"  材料：{materials_str}")
            lines.append(f"  成功率：{recipe.success_rate}%")
            
            # 获取丹药效果描述
            desc = self._get_pill_description(recipe.name)
            if desc:
                lines.append(f"  效果：{desc}")
            
            lines.append("")
        
        lines.append(f"共 {len(available_recipes)} 个可用配方")
        lines.append("💡 使用 炼丹 <丹药名称> 开始炼制")
        lines.append("💡 使用 查询配方 <丹药名称> 查看详情")
        
        return "\n".join(lines)

    def _get_pill_description(self, pill_name: str) -> str:
        """
        获取丹药效果描述
        
        Args:
            pill_name: 丹药名称
            
        Returns:
            丹药效果描述
        """
        # 从配置中获取丹药信息
        pills_config = self.config_manager.get_config("pills")
        items_config = self.config_manager.get_config("items")
        
        pill_data = None
        
        # 先从 pills.json 查找（突破丹药）
        if pills_config:
            # pills_config 可能是字典或列表
            if isinstance(pills_config, dict):
                # 如果是字典，直接通过名称查找
                pill_data = pills_config.get(pill_name)
            elif isinstance(pills_config, list):
                # 如果是列表，遍历查找
                for pill in pills_config:
                    if pill.get("name") == pill_name:
                        pill_data = pill
                        break
        
        # 如果没找到，从 items.json 查找（通用丹药）
        if not pill_data and items_config:
            # items_config 可能是字典或列表
            if isinstance(items_config, dict):
                # 如果是字典，遍历所有值查找
                for item in items_config.values():
                    if isinstance(item, dict) and item.get("name") == pill_name and item.get("type") == "丹药":
                        pill_data = item
                        break
            elif isinstance(items_config, list):
                # 如果是列表，遍历查找
                for item in items_config:
                    if item.get("name") == pill_name and item.get("type") == "丹药":
                        pill_data = item
                        break
        
        if not pill_data:
            return ""
        
        # 构建效果描述
        effects = []
        
        # 修为加成
        if pill_data.get("experience_bonus"):
            effects.append(f"增加{pill_data['experience_bonus']}修为")
        
        # 突破率加成
        if pill_data.get("success_rate_bonus"):
            effects.append(f"提升{pill_data['success_rate_bonus']}%突破率")
        
        # 其他效果（不显示具体数值）
        if pill_data.get("hp_bonus"):
            if pill_data["hp_bonus"] > 0:
                effects.append("恢复气血")
            else:
                effects.append("损失气血")
        
        if pill_data.get("max_hp_bonus"):
            if pill_data["max_hp_bonus"] > 0:
                effects.append("提升气血上限")
            else:
                effects.append("降低气血上限")
        
        if pill_data.get("mp_bonus"):
            if pill_data["mp_bonus"] > 0:
                effects.append("提升精神力")
            else:
                effects.append("损失精神力")
        
        if pill_data.get("attack_bonus"):
            if pill_data["attack_bonus"] > 0:
                effects.append("提升攻击")
            else:
                effects.append("降低攻击")
        
        if pill_data.get("defense_bonus"):
            if pill_data["defense_bonus"] > 0:
                effects.append("提升防御")
            else:
                effects.append("降低防御")
        
        if pill_data.get("spiritual_qi_bonus"):
            if pill_data["spiritual_qi_bonus"] > 0:
                effects.append("提升灵力")
            else:
                effects.append("损失灵力")
        
        if pill_data.get("gold_cost"):
            effects.append("消耗灵石")
        
        return "、".join(effects) if effects else "丹药效果"

    def _calculate_alchemy_exp(self, pill_rank: str) -> int:
        """
        根据丹药品质计算炼丹经验
        
        Args:
            pill_rank: 丹药品质
            
        Returns:
            经验值
        """
        exp_map = {
            "凡品": 10,
            "灵品": 20,
            "珍品": 30,
            "圣品": 50,
            "帝品": 80,
            "道品": 120,
            "仙品": 180,
            "神品": 250
        }
        return exp_map.get(pill_rank, 10)
    
    def get_alchemy_info(self, user_id: str) -> str:
        """
        获取玩家炼丹职业信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            格式化的炼丹信息
            
        Raises:
            BusinessException: 玩家不存在
        """
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        title = player.get_alchemy_title()
        level = player.alchemy_level
        exp = player.alchemy_exp
        required_exp = player.get_required_alchemy_exp()
        success_bonus = player.get_alchemy_success_bonus()
        
        # 计算下一级称号
        next_title = ""
        if level < 10:
            next_title = "初级炼丹师"
        elif level < 20:
            next_title = "中级炼丹师"
        elif level < 30:
            next_title = "高级炼丹师"
        elif level < 40:
            next_title = "炼丹大师"
        elif level < 50:
            next_title = "炼丹宗师"
        elif level < 60:
            next_title = "炼丹圣手"
        elif level < 70:
            next_title = "丹道真人"
        elif level < 80:
            next_title = "丹圣"
        elif level < 90:
            next_title = "丹帝"
        elif level < 100:
            next_title = "丹神"
        
        lines = [
            "🔥 炼丹职业信息",
            "━━━━━━━━━━━━━━━",
            f"当前称号：{title}",
            f"炼丹等级：Lv.{level}",
            f"炼丹经验：{exp}/{required_exp}",
            f"成功率加成：+{success_bonus}%",
            ""
        ]
        
        if next_title:
            next_level = (level // 10 + 1) * 10
            lines.append(f"下一称号：{next_title}（Lv.{next_level}）")
        else:
            lines.append("🎉 已达到最高称号！")
        
        lines.append("")
        lines.append("💡 通过炼丹获得经验提升等级")
        lines.append("💡 每级增加0.5%成功率加成")
        
        return "\n".join(lines)
