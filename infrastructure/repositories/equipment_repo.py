"""
装备仓储层

负责装备数据的持久化和查询。
"""
import json
from typing import Optional, List, Dict, Any
from pathlib import Path

from .base import BaseRepository
from ..storage import JSONStorage
from ...domain.models.equipment import Equipment, EquippedItems
from ...domain.enums import ItemType, ItemRarity


class EquipmentRepository(BaseRepository[Equipment]):
    """装备仓储"""
    
    def __init__(self, storage: JSONStorage, config_dir: Path):
        """
        初始化装备仓储
        
        Args:
            storage: JSON存储管理器
            config_dir: 配置文件目录
        """
        super().__init__(storage, "equipped_items.json")
        self.config_dir = config_dir
        self._weapons_cache: Optional[Dict[str, Equipment]] = None
        self._items_cache: Optional[Dict[str, Equipment]] = None
    
    # 实现 BaseRepository 的抽象方法
    def get_by_id(self, id: str) -> Optional[Equipment]:
        """根据ID获取装备（实现抽象方法）"""
        return self.get_equipment_by_id(id)
    
    def save(self, entity: Equipment) -> None:
        """保存装备（装备数据从配置文件加载，不支持保存）"""
        raise NotImplementedError("装备数据从配置文件加载，不支持保存操作")
    
    def delete(self, id: str) -> None:
        """删除装备（装备数据从配置文件加载，不支持删除）"""
        raise NotImplementedError("装备数据从配置文件加载，不支持删除操作")
    
    def exists(self, id: str) -> bool:
        """检查装备是否存在"""
        return self.get_equipment_by_id(id) is not None
    
    def _to_domain(self, data: Dict[str, Any]) -> Equipment:
        """转换为领域模型（不使用）"""
        raise NotImplementedError("装备数据从配置文件加载")
    
    def _to_dict(self, entity: Equipment) -> Dict[str, Any]:
        """转换为字典数据（不使用）"""
        raise NotImplementedError("装备数据从配置文件加载")
    
    def _load_weapons(self) -> Dict[str, Equipment]:
        """加载武器配置"""
        if self._weapons_cache is not None:
            return self._weapons_cache
        
        weapons_file = self.config_dir / "weapons.json"
        if not weapons_file.exists():
            return {}
        
        with open(weapons_file, "r", encoding="utf-8") as f:
            weapons_data = json.load(f)
        
        self._weapons_cache = {}
        for weapon_data in weapons_data:
            # 构建属性字典
            equipment_dict = {
                "id": weapon_data.get("id", ""),
                "name": weapon_data.get("name", ""),
                "type": "weapon",
                "rank": weapon_data.get("rank", "凡品"),
                "description": weapon_data.get("description", ""),
                "required_level_index": weapon_data.get("required_level_index", 0),
                "price": weapon_data.get("price", 0),
                "weapon_category": weapon_data.get("weapon_category", ""),
                "magic_damage": weapon_data.get("magic_damage", 0),
                "physical_damage": weapon_data.get("physical_damage", 0),
                "magic_defense": weapon_data.get("magic_defense", 0),
                "physical_defense": weapon_data.get("physical_defense", 0),
                "mental_power": weapon_data.get("mental_power", 0),
                "spiritual_qi": weapon_data.get("spiritual_qi", 0),
                "exp_multiplier": weapon_data.get("exp_multiplier", 0.0),
            }
            
            equipment = Equipment.from_dict(equipment_dict)
            self._weapons_cache[equipment.id] = equipment
        
        return self._weapons_cache
    
    def _load_items(self) -> Dict[str, Equipment]:
        """加载物品配置（防具、功法等）"""
        if self._items_cache is not None:
            return self._items_cache
        
        items_file = self.config_dir / "items.json"
        if not items_file.exists():
            return {}
        
        with open(items_file, "r", encoding="utf-8") as f:
            items_data = json.load(f)
        
        self._items_cache = {}
        for item_id, item_data in items_data.items():
            # 只加载法器和功法
            item_type = item_data.get("type", "")
            if item_type not in ["法器", "功法"]:
                continue
            
            # 构建属性字典
            equipment_dict = {
                "id": item_id,
                "name": item_data.get("name", ""),
                "type": item_type,
                "rank": item_data.get("rank", "凡品"),
                "description": item_data.get("description", ""),
                "required_level_index": item_data.get("required_level_index", 0),
                "price": item_data.get("price", 0),
                "subtype": item_data.get("subtype", ""),
                "magic_damage": item_data.get("magic_damage", 0),
                "physical_damage": item_data.get("physical_damage", 0),
                "magic_defense": item_data.get("magic_defense", 0),
                "physical_defense": item_data.get("physical_defense", 0),
                "mental_power": item_data.get("mental_power", 0),
                "max_hp": item_data.get("max_hp", 0),
                "spiritual_qi": item_data.get("spiritual_qi", 0),
                "exp_multiplier": item_data.get("exp_multiplier", 0.0),
            }
            
            # 如果有旧的equip_effects，也保留用于兼容
            if "equip_effects" in item_data:
                equipment_dict["equip_effects"] = item_data["equip_effects"]
            
            equipment = Equipment.from_dict(equipment_dict)
            self._items_cache[item_id] = equipment
        
        return self._items_cache
    
    def get_equipment_by_id(self, equipment_id: str) -> Optional[Equipment]:
        """
        根据ID获取装备
        
        Args:
            equipment_id: 装备ID
            
        Returns:
            装备对象，如果不存在则返回None
        """
        # 先从武器中查找
        weapons = self._load_weapons()
        if equipment_id in weapons:
            return weapons[equipment_id]
        
        # 再从物品中查找
        items = self._load_items()
        if equipment_id in items:
            return items[equipment_id]
        
        return None
    
    def get_equipment_by_name(self, name: str) -> Optional[Equipment]:
        """
        根据名称获取装备
        
        Args:
            name: 装备名称
            
        Returns:
            装备对象，如果不存在则返回None
        """
        # 从武器中查找
        weapons = self._load_weapons()
        for equipment in weapons.values():
            if equipment.name == name:
                return equipment
        
        # 从物品中查找
        items = self._load_items()
        for equipment in items.values():
            if equipment.name == name:
                return equipment
        
        return None
    
    def get_all_weapons(self) -> List[Equipment]:
        """获取所有武器"""
        weapons = self._load_weapons()
        return list(weapons.values())
    
    def get_all_armors(self) -> List[Equipment]:
        """获取所有防具"""
        items = self._load_items()
        return [item for item in items.values() 
                if item.type == "法器" and item.subtype == "防具"]
    
    def get_all_techniques(self) -> List[Equipment]:
        """获取所有功法"""
        items = self._load_items()
        return [item for item in items.values() if item.type == "功法"]
    
    def get_equipped_items(self, user_id: str) -> Optional[EquippedItems]:
        """
        获取玩家已装备的物品
        
        Args:
            user_id: 用户ID
            
        Returns:
            已装备物品对象，如果玩家不存在则返回None
        """
        data = self.storage.get(self.filename, user_id)
        if not data:
            return None
        
        # 解析装备数据
        equipped_data = {
            "weapon": data.get("weapon"),
            "armor": data.get("armor"),
            "main_technique": data.get("main_technique"),
            "techniques": data.get("techniques", []),
        }
        
        return EquippedItems.from_dict(equipped_data)
    
    def save_equipped_items(self, user_id: str, equipped_items: EquippedItems) -> bool:
        """
        保存玩家已装备的物品
        
        Args:
            user_id: 用户ID
            equipped_items: 已装备物品对象
            
        Returns:
            是否保存成功
        """
        equipped_data = {
            "user_id": user_id,
            "weapon": equipped_items.weapon.to_dict() if equipped_items.weapon else None,
            "armor": equipped_items.armor.to_dict() if equipped_items.armor else None,
            "main_technique": equipped_items.main_technique.to_dict() if equipped_items.main_technique else None,
            "techniques": [t.to_dict() for t in equipped_items.techniques] if equipped_items.techniques else []
        }
        
        self.storage.set(self.filename, user_id, equipped_data)
        return True
    
    def equip_item(self, user_id: str, equipment: Equipment, slot: str) -> bool:
        """
        装备物品到指定槽位
        
        Args:
            user_id: 用户ID
            equipment: 装备对象
            slot: 槽位（weapon/armor/main_technique/technique）
            
        Returns:
            是否装备成功
        """
        equipped_items = self.get_equipped_items(user_id)
        if not equipped_items:
            return False
        
        if slot == "weapon":
            equipped_items.weapon = equipment
        elif slot == "armor":
            equipped_items.armor = equipment
        elif slot == "main_technique":
            equipped_items.main_technique = equipment
        elif slot == "technique":
            if len(equipped_items.techniques) < 3:
                equipped_items.techniques.append(equipment)
            else:
                return False  # 副功法已满
        else:
            return False  # 无效槽位
        
        return self.save_equipped_items(user_id, equipped_items)
    
    def unequip_item(self, user_id: str, slot: str, technique_index: Optional[int] = None) -> Optional[Equipment]:
        """
        卸下指定槽位的装备
        
        Args:
            user_id: 用户ID
            slot: 槽位（weapon/armor/main_technique/technique）
            technique_index: 副功法索引（仅当slot为technique时使用）
            
        Returns:
            被卸下的装备对象，如果失败则返回None
        """
        equipped_items = self.get_equipped_items(user_id)
        if not equipped_items:
            return None
        
        unequipped = None
        
        if slot == "weapon":
            unequipped = equipped_items.weapon
            equipped_items.weapon = None
        elif slot == "armor":
            unequipped = equipped_items.armor
            equipped_items.armor = None
        elif slot == "main_technique":
            unequipped = equipped_items.main_technique
            equipped_items.main_technique = None
        elif slot == "technique" and technique_index is not None:
            if 0 <= technique_index < len(equipped_items.techniques):
                unequipped = equipped_items.techniques.pop(technique_index)
        else:
            return None
        
        if unequipped:
            self.save_equipped_items(user_id, equipped_items)
        
        return unequipped
