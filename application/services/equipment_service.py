"""
装备服务层

处理装备相关的业务逻辑。
"""
from typing import Optional, Tuple
from pathlib import Path

from ...domain.models.equipment import Equipment, EquippedItems, EquipmentStats
from ...domain.models.player import Player
from ...infrastructure.repositories.equipment_repo import EquipmentRepository
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository
from ...core.exceptions import BusinessException


class EquipmentService:
    """装备服务"""
    
    def __init__(
        self,
        equipment_repo: EquipmentRepository,
        player_repo: PlayerRepository,
        storage_ring_repo: StorageRingRepository,
    ):
        """
        初始化装备服务
        
        Args:
            equipment_repo: 装备仓储
            player_repo: 玩家仓储
            storage_ring_repo: 储物戒仓储
        """
        self.equipment_repo = equipment_repo
        self.player_repo = player_repo
        self.storage_ring_repo = storage_ring_repo
    
    def get_equipped_items(self, user_id: str) -> EquippedItems:
        """
        获取玩家已装备的物品
        
        Args:
            user_id: 用户ID
            
        Returns:
            已装备物品对象
            
        Raises:
            BusinessException: 玩家不存在
        """
        # 先检查玩家是否存在
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        # 获取装备信息，如果没有则返回空装备
        equipped_items = self.equipment_repo.get_equipped_items(user_id)
        if equipped_items is None:
            # 返回空装备对象
            equipped_items = EquippedItems()
        
        return equipped_items
    
    def equip_item(self, user_id: str, item_name: str) -> Tuple[Equipment, Optional[Equipment]]:
        """
        装备物品
        
        Args:
            user_id: 用户ID
            item_name: 物品名称
            
        Returns:
            (装备的物品, 被替换的旧装备)
            
        Raises:
            BusinessException: 各种业务异常
        """
        # 获取玩家信息
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        # 检查物品是否在储物戒中
        if not self.storage_ring_repo.has_item(user_id, item_name):
            raise BusinessException(f"储物戒中没有{item_name}")
        
        # 获取装备信息
        equipment = self.equipment_repo.get_equipment_by_name(item_name)
        if not equipment:
            raise BusinessException(f"{item_name}不是有效的装备")
        
        # 检查等级要求
        if player.level_index < equipment.required_level_index:
            # 简单显示等级索引，避免依赖配置管理器
            raise BusinessException(f"你的境界不足，需要达到境界等级{equipment.required_level_index}才能装备{item_name}（当前：境界等级{player.level_index}）")
        
        # 确定装备槽位
        slot = self._determine_slot(equipment)
        if not slot:
            raise BusinessException(f"{item_name}无法装备")
        
        # 获取当前装备
        equipped_items = self.get_equipped_items(user_id)
        old_equipment = None
        
        # 根据槽位处理装备
        if slot == "weapon":
            old_equipment = equipped_items.weapon
            equipped_items.weapon = equipment
        elif slot == "armor":
            old_equipment = equipped_items.armor
            equipped_items.armor = equipment
        elif slot == "main_technique":
            old_equipment = equipped_items.main_technique
            equipped_items.main_technique = equipment
        elif slot == "technique":
            if len(equipped_items.techniques) >= 3:
                raise BusinessException("副功法已满，请先卸下一个副功法")
            equipped_items.techniques.append(equipment)
        
        # 从储物戒中移除新装备
        self.storage_ring_repo.remove_item(user_id, item_name, 1)
        
        # 如果有旧装备，放入储物戒
        if old_equipment:
            self.storage_ring_repo.add_item(user_id, old_equipment.name, 1)
        
        # 保存装备信息
        self.equipment_repo.save_equipped_items(user_id, equipped_items)
        
        return equipment, old_equipment
    
    def unequip_item(self, user_id: str, item_name: Optional[str] = None, slot: Optional[str] = None) -> Equipment:
        """
        卸下装备
        
        Args:
            user_id: 用户ID
            item_name: 物品名称（可选）
            slot: 槽位（可选，weapon/armor/main_technique/technique）
            
        Returns:
            被卸下的装备
            
        Raises:
            BusinessException: 各种业务异常
        """
        # 获取当前装备
        equipped_items = self.get_equipped_items(user_id)
        
        # 确定要卸下的装备
        unequipped = None
        
        if item_name:
            # 根据名称查找装备
            if equipped_items.weapon and equipped_items.weapon.name == item_name:
                unequipped = equipped_items.weapon
                equipped_items.weapon = None
            elif equipped_items.armor and equipped_items.armor.name == item_name:
                unequipped = equipped_items.armor
                equipped_items.armor = None
            elif equipped_items.main_technique and equipped_items.main_technique.name == item_name:
                unequipped = equipped_items.main_technique
                equipped_items.main_technique = None
            else:
                # 在副功法中查找
                for i, technique in enumerate(equipped_items.techniques):
                    if technique.name == item_name:
                        unequipped = equipped_items.techniques.pop(i)
                        break
        elif slot:
            # 根据槽位卸下装备
            if slot == "weapon":
                unequipped = equipped_items.weapon
                equipped_items.weapon = None
            elif slot == "armor":
                unequipped = equipped_items.armor
                equipped_items.armor = None
            elif slot == "main_technique":
                unequipped = equipped_items.main_technique
                equipped_items.main_technique = None
            elif slot == "technique" and equipped_items.techniques:
                unequipped = equipped_items.techniques.pop(0)
        
        if not unequipped:
            raise BusinessException("没有找到要卸下的装备")
        
        # 放入储物戒
        self.storage_ring_repo.add_item(user_id, unequipped.name, 1)
        
        # 保存装备信息
        self.equipment_repo.save_equipped_items(user_id, equipped_items)
        
        return unequipped
    
    def get_equipment_bonuses(self, user_id: str) -> EquipmentStats:
        """
        获取装备属性加成
        
        Args:
            user_id: 用户ID
            
        Returns:
            装备属性加成
        """
        equipped_items = self.get_equipped_items(user_id)
        return equipped_items.get_total_stats()
    
    def _determine_slot(self, equipment: Equipment) -> Optional[str]:
        """
        确定装备槽位
        
        Args:
            equipment: 装备对象
            
        Returns:
            槽位名称，如果无法确定则返回None
        """
        # 武器类型
        if equipment.type == "weapon" or (equipment.type == "法器" and equipment.subtype == "武器"):
            return "weapon"
        
        # 防具类型
        if equipment.type == "法器" and equipment.subtype == "防具":
            return "armor"
        
        # 功法类型
        if equipment.type == "功法":
            # 默认装备为主功法，如果主功法已装备则装备为副功法
            return "main_technique"
        
        return None
    
    def format_equipped_items(self, equipped_items: EquippedItems) -> str:
        """
        格式化已装备物品信息
        
        Args:
            equipped_items: 已装备物品对象
            
        Returns:
            格式化后的字符串
        """
        lines = ["【装备信息】"]
        
        # 武器
        if equipped_items.weapon:
            weapon = equipped_items.weapon
            lines.append(f"\n武器：{weapon.name}（{weapon.rank.value if hasattr(weapon.rank, 'value') else weapon.rank}）")
            stats = self._format_stats(weapon.stats)
            if stats:
                lines.append(f"  效果：{stats}")
            if weapon.description:
                desc_short = weapon.description[:40] + "..." if len(weapon.description) > 40 else weapon.description
                lines.append(f"  介绍：{desc_short}")
        else:
            lines.append("\n武器：无")
        
        # 防具
        if equipped_items.armor:
            armor = equipped_items.armor
            lines.append(f"\n防具：{armor.name}（{armor.rank.value if hasattr(armor.rank, 'value') else armor.rank}）")
            stats = self._format_stats(armor.stats)
            if stats:
                lines.append(f"  效果：{stats}")
            if armor.description:
                desc_short = armor.description[:40] + "..." if len(armor.description) > 40 else armor.description
                lines.append(f"  介绍：{desc_short}")
        else:
            lines.append("\n防具：无")
        
        # 主功法
        if equipped_items.main_technique:
            technique = equipped_items.main_technique
            lines.append(f"\n主功法：{technique.name}（{technique.rank.value if hasattr(technique.rank, 'value') else technique.rank}）")
            stats = self._format_stats(technique.stats)
            if stats:
                lines.append(f"  效果：{stats}")
            if technique.description:
                desc_short = technique.description[:40] + "..." if len(technique.description) > 40 else technique.description
                lines.append(f"  介绍：{desc_short}")
        else:
            lines.append("\n主功法：无")
        
        # 副功法
        if equipped_items.techniques:
            lines.append(f"\n副功法（{len(equipped_items.techniques)}/3）：")
            for i, technique in enumerate(equipped_items.techniques, 1):
                lines.append(f"  {i}. {technique.name}（{technique.rank.value if hasattr(technique.rank, 'value') else technique.rank}）")
                stats = self._format_stats(technique.stats)
                if stats:
                    lines.append(f"     效果：{stats}")
        else:
            lines.append("\n副功法：无")
        
        # 总属性加成
        total_stats = equipped_items.get_total_stats()
        total_stats_str = self._format_stats(total_stats)
        if total_stats_str:
            lines.append(f"\n总属性加成：{total_stats_str}")
        
        return "\n".join(lines)
    
    def _format_stats(self, stats: EquipmentStats) -> str:
        """
        格式化属性加成
        
        Args:
            stats: 属性加成对象
            
        Returns:
            格式化后的字符串
        """
        parts = []
        
        if stats.magic_damage > 0:
            parts.append(f"法攻+{stats.magic_damage}")
        if stats.physical_damage > 0:
            parts.append(f"物攻+{stats.physical_damage}")
        if stats.magic_defense > 0:
            parts.append(f"法防+{stats.magic_defense}")
        if stats.physical_defense > 0:
            parts.append(f"物防+{stats.physical_defense}")
        if stats.mental_power > 0:
            parts.append(f"神念+{stats.mental_power}")
        if stats.max_hp > 0:
            parts.append(f"气血+{stats.max_hp}")
        if stats.spiritual_qi > 0:
            parts.append(f"灵气+{stats.spiritual_qi}")
        if stats.exp_multiplier > 0:
            parts.append(f"修炼+{stats.exp_multiplier * 100:.0f}%")
        
        # 旧版属性
        if stats.attack > 0:
            parts.append(f"攻击+{stats.attack}")
        if stats.defense > 0:
            parts.append(f"防御+{stats.defense}")
        
        return "、".join(parts)
