"""
丹药服务层

处理丹药相关的业务逻辑，包括从储物戒获取丹药、使用丹药等。
"""
import time
from typing import Optional, Tuple, Dict, List
from pathlib import Path

from ...domain.models.player import Player
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository
from ...core.config import ConfigManager
from ...core.exceptions import BusinessException


class PillService:
    """丹药服务"""
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        storage_ring_repo: StorageRingRepository,
        config_manager: ConfigManager,
    ):
        """
        初始化丹药服务
        
        Args:
            player_repo: 玩家仓储
            storage_ring_repo: 储物戒仓储
            config_manager: 配置管理器
        """
        self.player_repo = player_repo
        self.storage_ring_repo = storage_ring_repo
        self.config_manager = config_manager
    
    def get_pill_inventory(self, user_id: str) -> Dict[str, int]:
        """
        获取玩家的丹药（从储物戒中筛选）
        
        Args:
            user_id: 用户ID
            
        Returns:
            丹药字典 {丹药名称: 数量}
            
        Raises:
            BusinessException: 玩家不存在
        """
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        # 从储物戒获取所有物品
        all_items = self.storage_ring_repo.get_storage_ring_items(user_id)
        
        # 筛选出丹药（包含"丹"字的物品）
        pills = {name: count for name, count in all_items.items() if "丹" in name}
        
        return pills
    
    def add_pill(self, user_id: str, pill_name: str, count: int = 1) -> bool:
        """
        添加丹药到储物戒
        
        Args:
            user_id: 用户ID
            pill_name: 丹药名称
            count: 数量
            
        Returns:
            是否成功
            
        Raises:
            BusinessException: 玩家不存在
        """
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        # 添加到储物戒
        if pill_name in player.storage_ring_items:
            player.storage_ring_items[pill_name] += count
        else:
            player.storage_ring_items[pill_name] = count
        
        self.player_repo.save(player)
        return True
    
    def remove_pill(self, user_id: str, pill_name: str, count: int = 1) -> bool:
        """
        从储物戒移除丹药
        
        Args:
            user_id: 用户ID
            pill_name: 丹药名称
            count: 数量
            
        Returns:
            是否成功
            
        Raises:
            BusinessException: 玩家不存在或丹药不足
        """
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        # 检查储物戒中是否有足够的丹药
        if not self.storage_ring_repo.has_item(user_id, pill_name, count):
            raise BusinessException(f"储物戒中没有足够的{pill_name}")
        
        # 从储物戒移除
        self.storage_ring_repo.remove_item(user_id, pill_name, count)
        return True
    
    def get_pill_config(self, pill_name: str) -> Optional[Dict]:
        """
        获取丹药配置
        
        Args:
            pill_name: 丹药名称
            
        Returns:
            丹药配置字典，如果不存在则返回None
        """
        # 先从 pills.json（突破丹药）中查找
        pills_config = self.config_manager.get_config("pills")
        if pills_config:
            # 遍历所有突破丹药配置
            for pill_id, pill_data in pills_config.items():
                if pill_data.get("name") == pill_name:
                    return pill_data
        
        # 再从 items.json（通用物品，包含各种丹药）中查找
        items_config = self.config_manager.get_config("items")
        if items_config:
            # 遍历所有物品配置
            for item_id, item_data in items_config.items():
                # 只查找类型为"丹药"的物品
                if item_data.get("type") == "丹药" and item_data.get("name") == pill_name:
                    return item_data
        
        return None
    
    def use_pill(self, user_id: str, pill_name: str, quantity: int = 1) -> Tuple[bool, str]:
        """
        使用丹药（支持批量）
        
        Args:
            user_id: 用户ID
            pill_name: 丹药名称
            quantity: 使用数量
            
        Returns:
            (是否成功, 消息)
            
        Raises:
            BusinessException: 各种业务异常
        """
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        # 检查储物戒是否有足够的丹药
        if not self.storage_ring_repo.has_item(user_id, pill_name, quantity):
            current_count = self.storage_ring_repo.get_item_count(user_id, pill_name)
            if current_count == 0:
                raise BusinessException(f"你的储物戒中没有【{pill_name}】！")
            else:
                raise BusinessException(f"你的储物戒中【{pill_name}】数量不足！（当前：{current_count}个，需要：{quantity}个）")
        
        # 获取丹药配置
        pill_config = self.get_pill_config(pill_name)
        if not pill_config:
            raise BusinessException(f"丹药【{pill_name}】配置不存在！")
        
        # 检查境界需求
        required_level = pill_config.get("required_level_index", 0)
        if player.level_index < required_level:
            raise BusinessException(
                f"境界不足！使用【{pill_name}】需要达到境界等级{required_level}（当前：境界等级{player.level_index}）"
            )
        
        # 批量应用丹药效果
        total_effects = {}
        for i in range(quantity):
            effects = self._calculate_pill_effects(player, pill_config)
            # 累加效果
            for key, value in effects.items():
                total_effects[key] = total_effects.get(key, 0) + value
        
        # 应用累计效果
        message = self._apply_accumulated_effects(player, pill_name, pill_config, total_effects, quantity)
        
        # 从储物戒扣除丹药
        if pill_name in player.storage_ring_items:
            if player.storage_ring_items[pill_name] <= quantity:
                del player.storage_ring_items[pill_name]
            else:
                player.storage_ring_items[pill_name] -= quantity
        
        # 保存玩家数据
        self.player_repo.save(player)
        
        return True, message
    
    def _calculate_pill_effects(self, player: Player, pill_config: Dict) -> Dict:
        """
        计算单个丹药的效果（不应用）
        
        Args:
            player: 玩家对象
            pill_config: 丹药配置
            
        Returns:
            效果字典
        """
        effects = pill_config.get("effect", {})
        calculated = {}
        
        # 恢复气血
        if "add_hp" in effects:
            calculated["add_hp"] = effects["add_hp"]
        
        # 增加修为
        if "add_experience" in effects:
            calculated["add_experience"] = effects["add_experience"]
        
        # 增加气血上限
        if "add_max_hp" in effects:
            calculated["add_max_hp"] = effects["add_max_hp"]
        
        # 增加攻击力
        if "add_attack" in effects:
            calculated["add_attack"] = effects["add_attack"]
        
        # 增加/减少寿命
        if "add_lifespan" in effects:
            calculated["add_lifespan"] = effects["add_lifespan"]
        
        # 增加突破加成（累积效果）
        if "add_breakthrough_bonus" in effects:
            calculated["add_breakthrough_bonus"] = effects["add_breakthrough_bonus"]
        
        # 增加灵力（临时属性）
        if "add_spiritual_power" in effects:
            calculated["add_spiritual_power"] = effects["add_spiritual_power"]
        
        # 增加精神力（临时属性）
        if "add_mental_power" in effects:
            calculated["add_mental_power"] = effects["add_mental_power"]
        
        # 增加防御力
        if "add_defense" in effects:
            calculated["add_defense"] = effects["add_defense"]
        
        return calculated
    
    def _apply_accumulated_effects(
        self, 
        player: Player, 
        pill_name: str, 
        pill_config: Dict, 
        total_effects: Dict,
        quantity: int
    ) -> str:
        """
        应用累计的丹药效果
        
        Args:
            player: 玩家对象
            pill_name: 丹药名称
            pill_config: 丹药配置
            total_effects: 累计效果
            quantity: 服用数量
            
        Returns:
            效果描述消息
        """
        qty_display = f" x{quantity}" if quantity > 1 else ""
        message_parts = [f"✨ 服用【{pill_name}{qty_display}】成功！", "━━━━━━━━━━━━━━━"]
        
        # 恢复气血
        if "add_hp" in total_effects:
            hp_gain = total_effects["add_hp"]
            if hp_gain > 0:
                if player.cultivation_type.value == "灵修":
                    old_hp = player.spiritual_qi
                    player.spiritual_qi = min(player.spiritual_qi + hp_gain, player.max_spiritual_qi)
                    actual_gain = player.spiritual_qi - old_hp
                    if actual_gain > 0:
                        message_parts.append(f"🌟 恢复灵气：+{actual_gain}")
                        message_parts.append(f"💖 当前灵气：{player.spiritual_qi}/{player.max_spiritual_qi}")
                else:  # 体修
                    old_hp = player.blood_qi
                    player.blood_qi = min(player.blood_qi + hp_gain, player.max_blood_qi)
                    actual_gain = player.blood_qi - old_hp
                    if actual_gain > 0:
                        message_parts.append(f"🌟 恢复气血：+{actual_gain}")
                        message_parts.append(f"💖 当前气血：{player.blood_qi}/{player.max_blood_qi}")
            elif hp_gain < 0:
                if player.cultivation_type.value == "灵修":
                    player.spiritual_qi = max(0, player.spiritual_qi + hp_gain)
                    message_parts.append(f"⚠️ 损失灵气：{hp_gain}")
                else:
                    player.blood_qi = max(0, player.blood_qi + hp_gain)
                    message_parts.append(f"⚠️ 损失气血：{hp_gain}")
        
        # 增加修为
        if "add_experience" in total_effects:
            exp_gain = total_effects["add_experience"]
            player.experience += exp_gain
            message_parts.append(f"📈 获得修为：+{exp_gain:,}")
            message_parts.append(f"💫 当前修为：{player.experience:,}")
        
        # 增加气血上限
        if "add_max_hp" in total_effects:
            max_hp_gain = total_effects["add_max_hp"]
            if player.cultivation_type.value == "灵修":
                player.max_spiritual_qi += max_hp_gain
                message_parts.append(f"💪 灵气上限：+{max_hp_gain}")
            else:
                player.max_blood_qi += max_hp_gain
                message_parts.append(f"💪 气血上限：+{max_hp_gain}")
        
        # 增加攻击力
        if "add_attack" in total_effects:
            attack_gain = total_effects["add_attack"]
            # 根据修炼类型增加对应的伤害属性
            if player.cultivation_type.value == "灵修":
                player.magic_damage += attack_gain
                message_parts.append(f"⚔️ 法术伤害：+{attack_gain}")
            else:  # 体修
                player.physical_damage += attack_gain
                message_parts.append(f"⚔️ 物理伤害：+{attack_gain}")
        
        # 增加/减少寿命
        if "add_lifespan" in total_effects:
            lifespan_change = total_effects["add_lifespan"]
            player.lifespan += lifespan_change
            if lifespan_change > 0:
                message_parts.append(f"🕰️ 寿命增加：+{lifespan_change}年")
            else:
                message_parts.append(f"💀 寿命减少：{lifespan_change}年")
            message_parts.append(f"⏳ 当前寿命：{player.lifespan}年")
        
        # 增加突破加成（累积到level_up_rate）
        if "add_breakthrough_bonus" in total_effects:
            breakthrough_bonus = total_effects["add_breakthrough_bonus"]
            # 转换为百分比整数（0.1 -> 10）
            bonus_percent = int(breakthrough_bonus * 100)
            player.level_up_rate += bonus_percent
            message_parts.append(f"✨ 突破加成：+{bonus_percent}%")
            message_parts.append(f"🎯 累计突破加成：{player.level_up_rate}%")
        
        # 增加灵力（临时属性，可能需要其他处理）
        if "add_spiritual_power" in total_effects:
            spiritual_power_gain = total_effects["add_spiritual_power"]
            message_parts.append(f"💫 灵力提升：+{spiritual_power_gain}")
        
        # 增加精神力（临时属性，可能需要其他处理）
        if "add_mental_power" in total_effects:
            mental_power_gain = total_effects["add_mental_power"]
            message_parts.append(f"🧠 精神力提升：+{mental_power_gain}")
        
        # 增加防御力
        if "add_defense" in total_effects:
            defense_gain = total_effects["add_defense"]
            # 根据修炼类型增加对应的防御属性
            if player.cultivation_type.value == "灵修":
                player.magic_defense += defense_gain
                message_parts.append(f"🛡️ 法术防御：+{defense_gain}")
            else:  # 体修
                player.physical_defense += defense_gain
                message_parts.append(f"🛡️ 物理防御：+{defense_gain}")
        
        return "\n".join(message_parts)
    
    def format_pill_inventory(self, user_id: str) -> str:
        """
        格式化丹药显示（从储物戒）
        
        Args:
            user_id: 用户ID
            
        Returns:
            格式化后的字符串
            
        Raises:
            BusinessException: 玩家不存在
        """
        inventory = self.get_pill_inventory(user_id)
        
        if not inventory:
            return "你的储物戒中没有丹药！"
        
        lines = ["【储物戒 - 丹药】"]
        
        # 按品阶分组
        pills_by_rank = {}
        for pill_name, count in inventory.items():
            pill_config = self.get_pill_config(pill_name)
            if pill_config:
                rank = pill_config.get("rank", "未知")
                if rank not in pills_by_rank:
                    pills_by_rank[rank] = []
                pills_by_rank[rank].append((pill_name, count, pill_config))
            else:
                if "未知" not in pills_by_rank:
                    pills_by_rank["未知"] = []
                pills_by_rank["未知"].append((pill_name, count, {}))
        
        # 品阶排序
        rank_order = ["神品", "帝品", "圣品", "珍品", "凡品", "未知"]
        for rank in rank_order:
            if rank not in pills_by_rank:
                continue
            
            lines.append(f"\n【{rank}】")
            for pill_name, count, pill_config in pills_by_rank[rank]:
                lines.append(f"  {pill_name} × {count}")
                
                # 显示效果
                effects = self._format_pill_effects(pill_config)
                if effects:
                    lines.append(f"    效果: {effects}")
                
                # 显示介绍
                description = pill_config.get("description", "")
                if description:
                    # 限制长度
                    desc_short = description[:40] + "..." if len(description) > 40 else description
                    lines.append(f"    介绍: {desc_short}")
        
        lines.append(f"\n💡 使用 服用丹药 <丹药名> 来使用丹药")
        
        return "\n".join(lines)
    
    def _format_pill_effects(self, pill_config: Dict) -> str:
        """
        格式化丹药效果
        
        Args:
            pill_config: 丹药配置
            
        Returns:
            效果描述字符串
        """
        effects = []
        
        if pill_config.get('effect'):
            effect_data = pill_config['effect']
            if effect_data.get('add_hp'):
                hp_value = effect_data['add_hp']
                if hp_value > 0:
                    effects.append(f"恢复气血+{hp_value}")
                else:
                    effects.append(f"损失气血{hp_value}")
            if effect_data.get('add_experience'):
                effects.append(f"修为+{effect_data['add_experience']}")
            if effect_data.get('add_max_hp'):
                effects.append(f"气血上限+{effect_data['add_max_hp']}")
            if effect_data.get('add_spiritual_power'):
                effects.append(f"灵力+{effect_data['add_spiritual_power']}")
            if effect_data.get('add_mental_power'):
                effects.append(f"精神力+{effect_data['add_mental_power']}")
            if effect_data.get('add_attack'):
                effects.append(f"攻击力+{effect_data['add_attack']}")
            if effect_data.get('add_defense'):
                effects.append(f"防御力+{effect_data['add_defense']}")
            if effect_data.get('breakthrough_rate'):
                effects.append(f"突破成功率+{effect_data['breakthrough_rate']}%")
            if effect_data.get('add_breakthrough_bonus'):
                bonus_percent = effect_data['add_breakthrough_bonus'] * 100
                effects.append(f"突破加成+{bonus_percent}%")
            if effect_data.get('add_lifespan'):
                lifespan_value = effect_data['add_lifespan']
                if lifespan_value > 0:
                    effects.append(f"寿命+{lifespan_value}年")
                else:
                    effects.append(f"寿命{lifespan_value}年")
        
        return "、".join(effects) if effects else ""
    
    def search_pills(self, user_id: str, keyword: str) -> List[Tuple[str, int]]:
        """
        搜索丹药
        
        Args:
            user_id: 用户ID
            keyword: 搜索关键词
            
        Returns:
            匹配的丹药列表 [(丹药名称, 数量)]
            
        Raises:
            BusinessException: 玩家不存在
        """
        inventory = self.get_pill_inventory(user_id)
        
        results = []
        for pill_name, count in inventory.items():
            if keyword.lower() in pill_name.lower():
                results.append((pill_name, count))
        
        return results
