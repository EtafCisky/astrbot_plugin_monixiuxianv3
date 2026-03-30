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
    
    def use_pill(self, user_id: str, pill_name: str) -> Tuple[bool, str]:
        """
        使用丹药
        
        Args:
            user_id: 用户ID
            pill_name: 丹药名称
            
        Returns:
            (是否成功, 消息)
            
        Raises:
            BusinessException: 各种业务异常
        """
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        # 检查储物戒是否有该丹药
        if not self.storage_ring_repo.has_item(user_id, pill_name, 1):
            raise BusinessException(f"你的储物戒中没有【{pill_name}】！")
        
        # 获取丹药配置
        pill_config = self.get_pill_config(pill_name)
        if not pill_config:
            raise BusinessException(f"丹药【{pill_name}】配置不存在！")
        
        # 检查境界需求
        required_level = pill_config.get("required_level_index", 0)
        if player.level_index < required_level:
            # 简单显示等级索引，避免依赖额外的服务
            raise BusinessException(
                f"境界不足！使用【{pill_name}】需要达到境界等级{required_level}（当前：境界等级{player.level_index}）"
            )
        
        # 根据丹药类型处理效果
        effect_type = pill_config.get("type", "丹药")
        
        # 应用丹药效果
        message = self._apply_pill_effects(player, pill_name, pill_config)
        
        # 从储物戒扣除丹药（直接修改player对象）
        if pill_name in player.storage_ring_items:
            if player.storage_ring_items[pill_name] <= 1:
                del player.storage_ring_items[pill_name]
            else:
                player.storage_ring_items[pill_name] -= 1
        
        # 保存玩家数据（包括储物戒的修改）
        self.player_repo.save(player)
        
        return True, message
    
    def _apply_pill_effects(self, player: Player, pill_name: str, pill_config: Dict) -> str:
        """
        应用丹药效果
        
        Args:
            player: 玩家对象
            pill_name: 丹药名称
            pill_config: 丹药配置
            
        Returns:
            效果描述消息
        """
        effects = pill_config.get("effect", {})
        message_parts = [f"✨ 服用【{pill_name}】成功！", "━━━━━━━━━━━━━━━"]
        
        # 恢复气血
        if "add_hp" in effects:
            hp_gain = effects["add_hp"]
            if hp_gain > 0:
                old_hp = player.spiritual_qi if hasattr(player, 'spiritual_qi') else 0
                # 根据修炼类型选择恢复的属性
                if player.cultivation_type.value == "灵修":
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
                # 负面效果
                if player.cultivation_type.value == "灵修":
                    player.spiritual_qi = max(0, player.spiritual_qi + hp_gain)
                    message_parts.append(f"⚠️ 损失灵气：{hp_gain}")
                else:
                    player.blood_qi = max(0, player.blood_qi + hp_gain)
                    message_parts.append(f"⚠️ 损失气血：{hp_gain}")
        
        # 增加修为
        if "add_experience" in effects:
            exp_gain = effects["add_experience"]
            player.experience += exp_gain
            message_parts.append(f"📈 获得修为：+{exp_gain}")
            message_parts.append(f"💫 当前修为：{player.experience}")
        
        # 增加气血上限
        if "add_max_hp" in effects:
            max_hp_gain = effects["add_max_hp"]
            if player.cultivation_type.value == "灵修":
                player.max_spiritual_qi += max_hp_gain
                message_parts.append(f"💪 灵气上限：+{max_hp_gain}")
            else:
                player.max_blood_qi += max_hp_gain
                message_parts.append(f"💪 气血上限：+{max_hp_gain}")
        
        # 增加灵力（灵修专属）
        if "add_spiritual_power" in effects:
            sp_gain = effects["add_spiritual_power"]
            if player.cultivation_type.value == "灵修":
                player.max_spiritual_qi += sp_gain
                message_parts.append(f"✨ 灵气上限：+{sp_gain}")
        
        # 增加精神力
        if "add_mental_power" in effects:
            mp_gain = effects["add_mental_power"]
            if mp_gain > 0:
                player.mental_power += mp_gain
                message_parts.append(f"🧠 精神力：+{mp_gain}")
            elif mp_gain < 0:
                player.mental_power = max(0, player.mental_power + mp_gain)
                message_parts.append(f"⚠️ 精神力：{mp_gain}")
        
        # 增加攻击力
        if "add_attack" in effects:
            atk_gain = effects["add_attack"]
            if atk_gain > 0:
                if player.cultivation_type.value == "灵修":
                    player.magic_damage += atk_gain
                    message_parts.append(f"⚔️ 法术攻击：+{atk_gain}")
                else:
                    player.physical_damage += atk_gain
                    message_parts.append(f"⚔️ 物理攻击：+{atk_gain}")
            elif atk_gain < 0:
                if player.cultivation_type.value == "灵修":
                    player.magic_damage = max(0, player.magic_damage + atk_gain)
                    message_parts.append(f"⚠️ 法术攻击：{atk_gain}")
                else:
                    player.physical_damage = max(0, player.physical_damage + atk_gain)
                    message_parts.append(f"⚠️ 物理攻击：{atk_gain}")
        
        # 增加防御力
        if "add_defense" in effects:
            def_gain = effects["add_defense"]
            if def_gain > 0:
                player.physical_defense += def_gain
                message_parts.append(f"🛡️ 防御力：+{def_gain}")
            elif def_gain < 0:
                player.physical_defense = max(0, player.physical_defense + def_gain)
                message_parts.append(f"⚠️ 防御力：{def_gain}")
        
        # 突破加成（临时效果，保存到玩家数据）
        if "add_breakthrough_bonus" in effects:
            bonus = effects["add_breakthrough_bonus"]
            # 保存到玩家的 level_up_rate 字段
            player.level_up_rate = int(bonus * 100)  # 转换为百分比整数
            message_parts.append(f"🎯 突破成功率：+{bonus * 100:.0f}%")
            message_parts.append(f"💡 当前突破加成：{player.level_up_rate}%")
        
        # 负面效果：消耗灵石
        if "add_gold" in effects and effects["add_gold"] < 0:
            gold_loss = abs(effects["add_gold"])
            player.gold = max(0, player.gold - gold_loss)
            message_parts.append(f"💰 消耗灵石：-{gold_loss}")
        
        message_parts.append("━━━━━━━━━━━━━━━")
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
                description = pill_config.get("description", "")
                if description:
                    lines.append(f"  {pill_name} × {count}")
                    lines.append(f"    {description}")
                else:
                    lines.append(f"  {pill_name} × {count}")
        
        lines.append(f"\n💡 使用 服用丹药 <丹药名> 来使用丹药")
        
        return "\n".join(lines)
    
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
