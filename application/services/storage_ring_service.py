"""储物戒业务服务"""
import json
from typing import Tuple, Dict, List, Optional
from pathlib import Path

from ...core.config import ConfigManager
from ...core.exceptions import XiuxianException
from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...domain.models.item import StorageRing


class StorageRingService:
    """储物戒业务服务"""
    
    # 物品分类定义 - 按类型关键词分类
    ITEM_CATEGORIES = {
        "丹药": {
            "keywords": ["丹"],
            "exclude_keywords": ["内丹"],  # 排除内丹（属于材料）
            "priority": 1
        },
        "材料": {
            "keywords": ["草", "铁", "石", "沙", "参", "芝", "果", "花", "根", "子", "髓", "核", "粉", "砂",
                        "皮", "血", "息", "齿轮", "碎片", "精华", "残页", "遗物", "种子", "内丹"],
            "priority": 2
        },
        "法器": {
            "keywords": ["剑", "刀", "枪", "弓", "幡", "甲", "袍", "铠", "阵"],
            "priority": 3
        },
        "功法": {
            "keywords": ["功", "诀", "经", "法"],
            "priority": 4
        },
        "储物戒": {
            "keywords": ["储物戒"],
            "priority": 5
        },
        "其他": {
            "keywords": [],
            "priority": 99
        }
    }
    
    def __init__(
        self,
        storage_ring_repo: StorageRingRepository,
        player_repo: PlayerRepository,
        config_manager: ConfigManager
    ):
        self.storage_ring_repo = storage_ring_repo
        self.player_repo = player_repo
        self.config_manager = config_manager
        
        # 加载储物戒配置
        self._load_storage_rings()
    
    def _load_storage_rings(self) -> None:
        """加载储物戒配置"""
        config_path = self.config_manager.config_dir / "storage_rings.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self.storage_rings = json.load(f)
        else:
            # 默认配置
            self.storage_rings = {
                "基础储物戒": {
                    "name": "基础储物戒",
                    "type": "storage_ring",
                    "rank": "凡品",
                    "description": "修士入门必备的储物法器，空间狭小但足够存放常用物品。",
                    "capacity": 20,
                    "required_level_index": 0,
                    "price": 0
                }
            }
    
    def get_storage_ring_config(self, ring_name: str) -> Optional[Dict]:
        """获取储物戒配置"""
        return self.storage_rings.get(ring_name)
    
    def get_ring_capacity(self, ring_name: str) -> int:
        """获取储物戒容量"""
        config = self.get_storage_ring_config(ring_name)
        return config.get("capacity", 20) if config else 20
    
    def get_used_slots(self, user_id: str) -> int:
        """获取已使用的格子数（每种物品占1格）"""
        items = self.storage_ring_repo.get_storage_ring_items(user_id)
        return len(items)
    
    def get_available_slots(self, user_id: str) -> int:
        """获取可用的格子数"""
        ring_name = self.storage_ring_repo.get_storage_ring_name(user_id)
        capacity = self.get_ring_capacity(ring_name)
        used = self.get_used_slots(user_id)
        return capacity - used
    
    def get_space_warning(self, user_id: str) -> Optional[str]:
        """获取储物戒空间警告"""
        available = self.get_available_slots(user_id)
        ring_name = self.storage_ring_repo.get_storage_ring_name(user_id)
        capacity = self.get_ring_capacity(ring_name)
        used = self.get_used_slots(user_id)
        
        if available == 0:
            return f"⚠️ 储物戒已满！({used}/{capacity}格)"
        elif available <= 2:
            return f"⚠️ 储物戒空间不足！仅剩{available}格({used}/{capacity}格)"
        return None
    
    def can_store_item(self, item_name: str) -> Tuple[bool, str]:
        """检查物品是否可以存入储物戒"""
        # 检查是否为储物戒（储物戒不能存入储物戒）
        if "储物戒" in item_name or item_name in self.storage_rings:
            return False, f"【{item_name}】是储物戒，不能存入另一个储物戒"
        
        return True, ""
    
    def _is_pill(self, item_name: str) -> bool:
        """检查是否为丹药（已废弃，现在丹药也可以存入储物戒）"""
        # 简单检查：包含"丹"字的物品
        return "丹" in item_name
    
    def store_item(
        self,
        user_id: str,
        item_name: str,
        count: int = 1,
        silent: bool = False
    ) -> Tuple[bool, str]:
        """存入物品到储物戒"""
        # 检查是否可以存入
        can_store, reason = self.can_store_item(item_name)
        if not can_store:
            return False, reason
        
        # 获取玩家
        player = self.player_repo.get_by_id(user_id)
        if not player:
            return False, "玩家不存在"
        
        # 检查是否需要新格子
        if item_name not in player.storage_ring_items:
            available = self.get_available_slots(user_id)
            if available <= 0:
                ring_name = player.storage_ring
                capacity = self.get_ring_capacity(ring_name)
                return False, f"储物戒已满！({capacity}/{capacity}格)"
        
        # 添加物品到player对象
        if item_name in player.storage_ring_items:
            player.storage_ring_items[item_name] += count
        else:
            player.storage_ring_items[item_name] = count
        
        # 保存玩家
        self.player_repo.save(player)
        
        if silent:
            return True, ""
        
        # 生成消息
        ring_name = player.storage_ring
        capacity = self.get_ring_capacity(ring_name)
        used = self.get_used_slots(user_id)
        
        msg = f"已将【{item_name}】x{count} 存入储物戒（{used}/{capacity}格）"
        
        warning = self.get_space_warning(user_id)
        if warning:
            msg += f"\n{warning}"
        
        return True, msg
    
    def discard_item(
        self,
        user_id: str,
        item_name: str,
        count: int = 1
    ) -> Tuple[bool, str]:
        """丢弃储物戒中的物品"""
        items = self.storage_ring_repo.get_storage_ring_items(user_id)
        
        if item_name not in items:
            return False, f"储物戒中没有【{item_name}】"
        
        current_count = items[item_name]
        if count > current_count:
            return False, f"储物戒中【{item_name}】数量不足（当前：{current_count}个）"
        
        # 减少数量
        if count >= current_count:
            del items[item_name]
            discard_count = current_count
        else:
            items[item_name] = current_count - count
            discard_count = count
        
        self.storage_ring_repo.set_storage_ring_items(user_id, items)
        
        ring_name = self.storage_ring_repo.get_storage_ring_name(user_id)
        capacity = self.get_ring_capacity(ring_name)
        used = self.get_used_slots(user_id)
        
        return True, f"已丢弃【{item_name}】x{discard_count}（{used}/{capacity}格）"
    
    def get_item_count(self, user_id: str, item_name: str) -> int:
        """获取物品数量"""
        items = self.storage_ring_repo.get_storage_ring_items(user_id)
        return items.get(item_name, 0)
    
    def has_item(self, user_id: str, item_name: str, count: int = 1) -> bool:
        """检查是否有足够数量的物品"""
        return self.get_item_count(user_id, item_name) >= count
    
    def get_storage_ring_info(self, user_id: str) -> Dict:
        """获取储物戒完整信息"""
        ring_name = self.storage_ring_repo.get_storage_ring_name(user_id)
        ring_config = self.get_storage_ring_config(ring_name) or {}
        items = self.storage_ring_repo.get_storage_ring_items(user_id)
        capacity = self.get_ring_capacity(ring_name)
        used = self.get_used_slots(user_id)
        
        return {
            "name": ring_name,
            "rank": ring_config.get("rank", "未知"),
            "description": ring_config.get("description", ""),
            "capacity": capacity,
            "used": used,
            "available": capacity - used,
            "items": items
        }
    
    def categorize_items(self, items: Dict[str, int]) -> Dict[str, List[Tuple[str, int]]]:
        """将物品按分类整理（优化版）"""
        result = {cat: [] for cat in self.ITEM_CATEGORIES.keys()}
        
        for item_name, count in items.items():
            categorized = False
            best_match = None
            best_priority = 999
            
            # 遍历所有分类，找到最佳匹配
            for category, config in self.ITEM_CATEGORIES.items():
                if category == "其他":
                    continue
                
                keywords = config["keywords"]
                exclude_keywords = config.get("exclude_keywords", [])
                priority = config["priority"]
                
                # 检查是否包含排除关键词
                is_excluded = False
                for exclude_keyword in exclude_keywords:
                    if exclude_keyword in item_name:
                        is_excluded = True
                        break
                
                if is_excluded:
                    continue
                
                # 检查物品名是否包含分类关键词
                for keyword in keywords:
                    if keyword in item_name:
                        # 找到优先级更高的分类（数字越小优先级越高）
                        if priority < best_priority:
                            best_match = category
                            best_priority = priority
                            categorized = True
                        break
            
            # 将物品添加到最佳匹配的分类
            if categorized and best_match:
                result[best_match].append((item_name, count))
            else:
                # 未分类的放入"其他"
                result["其他"].append((item_name, count))
        
        # 移除空分类，并按优先级排序
        sorted_result = {}
        for category in sorted(self.ITEM_CATEGORIES.keys(), 
                              key=lambda x: self.ITEM_CATEGORIES[x]["priority"]):
            if result[category]:
                sorted_result[category] = result[category]
        
        return sorted_result
    
    def upgrade_ring(
        self,
        user_id: str,
        new_ring_name: str
    ) -> Tuple[bool, str]:
        """升级储物戒"""
        # 检查储物戒是否存在
        ring_config = self.get_storage_ring_config(new_ring_name)
        if not ring_config:
            return False, f"未找到储物戒：{new_ring_name}"
        
        if ring_config.get("type") != "storage_ring":
            return False, f"【{new_ring_name}】不是储物戒类型的物品"
        
        # 获取玩家信息
        player = self.player_repo.get_by_id(user_id)
        if not player:
            return False, "玩家不存在"
        
        # 检查境界要求
        required_level = ring_config.get("required_level_index", 0)
        if player.level_index < required_level:
            level_name = self._format_required_level(required_level)
            return False, f"境界不足！【{new_ring_name}】（{ring_config.get('rank', '')}）需要达到【{level_name}】以上"
        
        # 检查是否为升级
        old_ring = self.storage_ring_repo.get_storage_ring_name(user_id)
        old_capacity = self.get_ring_capacity(old_ring)
        new_capacity = ring_config.get("capacity", 20)
        
        if new_capacity <= old_capacity:
            return False, f"【{new_ring_name}】容量（{new_capacity}格）不高于当前储物戒（{old_capacity}格），无法替换"
        
        # 检查价格
        price = ring_config.get("price", 0)
        if price > 0:
            if player.gold < price:
                return False, (
                    f"❌ 灵石不足！\n"
                    f"【{new_ring_name}】需要 {price:,} 灵石\n"
                    f"你当前拥有：{player.gold:,} 灵石"
                )
            player.gold -= price
            self.player_repo.save(player)
        
        # 升级储物戒
        self.storage_ring_repo.set_storage_ring_name(user_id, new_ring_name)
        
        cost_msg = f"\n消耗灵石：{price:,}" if price > 0 else ""
        return True, (
            f"储物戒升级成功！\n"
            f"【{old_ring}】({old_capacity}格) → 【{new_ring_name}】({new_capacity}格)\n"
            f"品级：{ring_config.get('rank', '未知')}{cost_msg}"
        )
    
    def _format_required_level(self, level_index: int) -> str:
        """格式化需求境界名称"""
        level_data = self.config_manager.get_level_data(level_index)
        if level_data:
            return level_data.get("level_name", f"境界{level_index}")
        return f"境界{level_index}"
    
    def get_all_storage_rings(self) -> List[Dict]:
        """获取所有可用的储物戒列表"""
        rings = []
        for name, config in self.storage_rings.items():
            rings.append({
                "name": name,
                "rank": config.get("rank", ""),
                "capacity": config.get("capacity", 20),
                "required_level_index": config.get("required_level_index", 0),
                "price": config.get("price", 0),
                "description": config.get("description", "")
            })
        rings.sort(key=lambda x: x["capacity"])
        return rings
    
    # ===== 赠予系统 =====
    
    def gift_item(
        self,
        sender_id: str,
        sender_name: str,
        receiver_id: str,
        item_name: str,
        count: int
    ) -> Tuple[bool, str]:
        """赠予物品（直接转移，无需接收确认）"""
        # 检查物品是否存在
        if not self.has_item(sender_id, item_name, count):
            current = self.get_item_count(sender_id, item_name)
            if current == 0:
                return False, f"储物戒中没有【{item_name}】"
            else:
                return False, f"储物戒中【{item_name}】数量不足（当前：{current}个）"
        
        # 检查接收者是否存在
        receiver = self.player_repo.get_by_id(receiver_id)
        if not receiver:
            return False, f"目标玩家（ID:{receiver_id}）尚未开始修仙"
        
        if sender_id == receiver_id:
            return False, "不能赠予物品给自己"
        
        # 检查接收者储物戒是否有空间（如果是新物品）
        if item_name not in receiver.storage_ring_items:
            available = self.get_available_slots(receiver_id)
            if available <= 0:
                ring_name = receiver.storage_ring
                capacity = self.get_ring_capacity(ring_name)
                return False, f"对方储物戒已满！({capacity}/{capacity}格)"
        
        # 从发送者储物戒中移除物品
        sender_items = self.storage_ring_repo.get_storage_ring_items(sender_id)
        current_count = sender_items[item_name]
        
        if count >= current_count:
            del sender_items[item_name]
        else:
            sender_items[item_name] = current_count - count
        
        self.storage_ring_repo.set_storage_ring_items(sender_id, sender_items)
        
        # 直接存入接收者的储物戒
        success, message = self.store_item(receiver_id, item_name, count, silent=True)
        
        if success:
            return True, (
                f"✅ 赠予成功！\n"
                f"【{item_name}】x{count} → {receiver.nickname}\n"
                f"物品已直接送达对方储物戒"
            )
        else:
            # 存入失败，物品返还给发送者
            self.store_item(sender_id, item_name, count, silent=True)
            return False, f"赠予失败：{message}\n物品已返还"

    def get_reference_price(self, item_name: str) -> Optional[int]:
        """
        获取物品参考价格
        
        Args:
            item_name: 物品名称
            
        Returns:
            参考价格，如果没有则返回None
        """
        # 从丹药配置获取
        pills_config = self._load_config("pills.json")
        if pills_config:
            for pill in pills_config:
                if pill.get("name") == item_name:
                    if "price" in pill:
                        return pill["price"]
                    if "gold_cost" in pill:
                        return pill["gold_cost"]
        
        # 从武器配置获取
        weapons_config = self._load_config("weapons.json")
        if weapons_config:
            for weapon in weapons_config:
                if weapon.get("name") == item_name:
                    if "price" in weapon:
                        return weapon["price"]
                    if "gold_cost" in weapon:
                        return weapon["gold_cost"]
        
        # 从通用物品配置获取
        items_config = self._load_config("items.json")
        if items_config:
            if isinstance(items_config, dict):
                for item_id, item_data in items_config.items():
                    if item_data.get("name") == item_name:
                        if "price" in item_data:
                            return item_data["price"]
                        if "gold_cost" in item_data:
                            return item_data["gold_cost"]
        
        return None
    
    def get_item_details(self, item_name: str) -> Optional[Dict]:
        """
        获取物品详细信息
        
        Args:
            item_name: 物品名称
            
        Returns:
            物品详细信息字典，包含name, type, rank, price, description, effects等
        """
        # 从丹药配置获取
        pills_config = self._load_config("pills.json")
        if pills_config:
            for pill in pills_config:
                if pill.get("name") == item_name:
                    return {
                        "name": pill.get("name"),
                        "type": "丹药",
                        "rank": pill.get("rank"),
                        "price": pill.get("price") or pill.get("gold_cost"),
                        "description": pill.get("description", ""),
                        "data": pill
                    }
        
        # 从武器配置获取
        weapons_config = self._load_config("weapons.json")
        if weapons_config:
            for weapon in weapons_config:
                if weapon.get("name") == item_name:
                    return {
                        "name": weapon.get("name"),
                        "type": weapon.get("type", "法器"),
                        "rank": weapon.get("rank"),
                        "price": weapon.get("price") or weapon.get("gold_cost"),
                        "description": weapon.get("description", ""),
                        "data": weapon
                    }
        
        # 从通用物品配置获取
        items_config = self._load_config("items.json")
        if items_config:
            if isinstance(items_config, dict):
                for item_id, item_data in items_config.items():
                    if item_data.get("name") == item_name:
                        return {
                            "name": item_data.get("name"),
                            "type": item_data.get("type", "其他"),
                            "rank": item_data.get("rank"),
                            "price": item_data.get("price") or item_data.get("gold_cost"),
                            "description": item_data.get("description", ""),
                            "data": item_data
                        }
        
        return None
    
    def format_item_effects(self, data: Dict) -> str:
        """
        格式化物品效果
        
        Args:
            data: 物品数据
            
        Returns:
            效果描述字符串
        """
        effects = []
        
        # 检查各种效果
        if data.get('effect'):
            effect_data = data['effect']
            if effect_data.get('add_hp'):
                effects.append(f"恢复气血+{effect_data['add_hp']}")
            if effect_data.get('add_experience'):
                effects.append(f"修为+{effect_data['add_experience']}")
            if effect_data.get('add_max_hp'):
                effects.append(f"气血上限+{effect_data['add_max_hp']}")
            if effect_data.get('add_spiritual_power'):
                effects.append(f"灵力+{effect_data['add_spiritual_power']}")
            if effect_data.get('breakthrough_rate'):
                effects.append(f"突破成功率+{effect_data['breakthrough_rate']}%")
        
        # 装备属性
        if data.get('magic_damage'):
            effects.append(f"法伤+{data['magic_damage']}")
        if data.get('physical_damage'):
            effects.append(f"物伤+{data['physical_damage']}")
        if data.get('magic_defense'):
            effects.append(f"法防+{data['magic_defense']}")
        if data.get('physical_defense'):
            effects.append(f"物防+{data['physical_defense']}")
        if data.get('mental_power'):
            effects.append(f"精神力+{data['mental_power']}")
        if data.get('max_hp') and not data.get('effect'):  # 避免重复显示
            effects.append(f"气血上限+{data['max_hp']}")
        if data.get('exp_multiplier'):
            effects.append(f"修炼倍率+{int(data['exp_multiplier']*100)}%")
        
        # 旧版装备效果
        if data.get('equip_effects'):
            equip_effects = data['equip_effects']
            if equip_effects.get('attack'):
                effects.append(f"攻击+{equip_effects['attack']}")
            if equip_effects.get('defense'):
                effects.append(f"防御+{equip_effects['defense']}")
        
        return "、".join(effects) if effects else "无"
    
    def _load_config(self, filename: str) -> Optional[any]:
        """
        加载配置文件
        
        Args:
            filename: 配置文件名
            
        Returns:
            配置数据，加载失败返回None
        """
        try:
            config_path = self.config_manager.config_dir / filename
            if not config_path.exists():
                return None
            
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
