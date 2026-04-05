"""玩家领域模型"""
from dataclasses import dataclass, field
from typing import Optional
import time

from ..enums import CultivationType, PlayerState


@dataclass
class Player:
    """玩家领域模型"""
    # 基础信息
    user_id: str
    nickname: str
    cultivation_type: CultivationType
    spiritual_root: str
    
    # 境界和修为
    level_index: int = 0
    experience: int = 0
    
    # 资源
    gold: int = 0
    
    # 状态
    state: PlayerState = PlayerState.IDLE
    
    # 属性（灵修）- 灵修使用灵气
    spiritual_qi: int = 0
    max_spiritual_qi: int = 0
    
    # 属性（体修）- 体修使用气血
    blood_qi: int = 0
    max_blood_qi: int = 0
    
    # 通用属性
    lifespan: int = 100
    mental_power: int = 100
    
    # 战斗属性
    # 灵修：法伤5-100，物伤5，法防0，物防5
    # 体修：法伤0，物伤100-500，法防38-150，物防100-500
    physical_damage: int = 5
    magic_damage: int = 5
    physical_defense: int = 5
    magic_defense: int = 0
    
    # 装备
    weapon: Optional[str] = None
    armor: Optional[str] = None
    main_technique: Optional[str] = None
    
    # 丹药背包（已废弃，保留用于兼容性）
    pills_inventory: dict = field(default_factory=dict)  # {丹药名称: 数量}
    
    # 储物戒系统
    storage_ring: str = "基础储物戒"  # 当前装备的储物戒名称
    storage_ring_items: dict = field(default_factory=dict)  # {物品名称: 数量}
    
    # 宗门
    sect_id: Optional[int] = None
    sect_position: Optional[int] = None
    
    # 突破相关
    level_up_rate: int = 0  # 突破成功率加成
    
    # 炼丹职业
    alchemy_level: int = 0  # 炼丹等级（0-100）
    alchemy_exp: int = 0  # 炼丹经验
    
    # 时间戳
    created_at: int = field(default_factory=lambda: int(time.time()))
    updated_at: int = field(default_factory=lambda: int(time.time()))
    last_check_in_date: Optional[str] = None
    cultivation_start_time: int = 0
    
    # 用户自定义道号
    user_name: Optional[str] = None
    
    def can_cultivate(self) -> bool:
        """检查是否可以闭关"""
        return self.state == PlayerState.IDLE
    
    def start_cultivation(self) -> None:
        """开始闭关"""
        if not self.can_cultivate():
            raise ValueError(f"当前状态「{self.state.value}」无法闭关")
        self.state = PlayerState.CULTIVATING
        self.cultivation_start_time = int(time.time())
    
    def end_cultivation(self) -> int:
        """
        结束闭关
        
        Returns:
            闭关时长（分钟）
        """
        if self.state != PlayerState.CULTIVATING:
            raise ValueError("当前并未闭关")
        
        if self.cultivation_start_time == 0:
            # 数据异常：闭关时间丢失，重置状态让玩家可以继续游戏
            self.state = PlayerState.IDLE
            raise ValueError("数据异常：闭关时间丢失，已自动重置状态。抱歉给您带来不便")
        
        duration_seconds = int(time.time()) - self.cultivation_start_time
        duration_minutes = duration_seconds // 60
        
        self.state = PlayerState.IDLE
        self.cultivation_start_time = 0
        
        return duration_minutes
    
    def calculate_power(self) -> int:
        """
        计算战力
        
        Returns:
            综合战力值
        """
        return (
            self.physical_damage +
            self.magic_damage +
            self.physical_defense +
            self.magic_defense +
            self.mental_power // 10
        )
    
    def add_experience(self, exp: int) -> None:
        """增加修为"""
        self.experience += exp
        self.updated_at = int(time.time())
    
    def add_gold(self, amount: int) -> None:
        """增加灵石"""
        self.gold += amount
        self.updated_at = int(time.time())
    
    def consume_gold(self, amount: int) -> bool:
        """
        消耗灵石
        
        Returns:
            是否成功
        """
        if self.gold < amount:
            return False
        self.gold -= amount
        self.updated_at = int(time.time())
        return True
    
    def is_alive(self) -> bool:
        """检查是否存活"""
        if self.cultivation_type == CultivationType.SPIRITUAL:
            return self.spiritual_qi > 0
        else:
            return self.blood_qi > 0
    
    def restore_health(self) -> None:
        """恢复生命值"""
        if self.cultivation_type == CultivationType.SPIRITUAL:
            self.spiritual_qi = self.max_spiritual_qi
        else:
            self.blood_qi = self.max_blood_qi
        self.updated_at = int(time.time())
    
    def get_health_percentage(self) -> float:
        """获取生命值百分比"""
        if self.cultivation_type == CultivationType.SPIRITUAL:
            return self.spiritual_qi / self.max_spiritual_qi if self.max_spiritual_qi > 0 else 0
        else:
            return self.blood_qi / self.max_blood_qi if self.max_blood_qi > 0 else 0

    def get_alchemy_title(self) -> str:
        """
        获取炼丹师称号
        
        Returns:
            炼丹师称号
        """
        level = self.alchemy_level
        if level < 10:
            return "见习炼丹师"
        elif level < 20:
            return "初级炼丹师"
        elif level < 30:
            return "中级炼丹师"
        elif level < 40:
            return "高级炼丹师"
        elif level < 50:
            return "炼丹大师"
        elif level < 60:
            return "炼丹宗师"
        elif level < 70:
            return "炼丹圣手"
        elif level < 80:
            return "丹道真人"
        elif level < 90:
            return "丹圣"
        elif level < 100:
            return "丹帝"
        else:
            return "丹神"
    
    def add_alchemy_exp(self, exp: int) -> bool:
        """
        增加炼丹经验
        
        Args:
            exp: 经验值
            
        Returns:
            是否升级
        """
        self.alchemy_exp += exp
        
        # 检查是否升级
        required_exp = self.get_required_alchemy_exp()
        if self.alchemy_exp >= required_exp and self.alchemy_level < 100:
            self.alchemy_level += 1
            self.alchemy_exp -= required_exp
            self.updated_at = int(time.time())
            return True
        
        self.updated_at = int(time.time())
        return False
    
    def get_required_alchemy_exp(self) -> int:
        """
        获取升级所需炼丹经验
        
        Returns:
            所需经验值
        """
        # 每级所需经验递增
        return 100 + self.alchemy_level * 50
    
    def get_alchemy_success_bonus(self) -> int:
        """
        获取炼丹成功率加成
        
        Returns:
            成功率加成（百分比）
        """
        # 每级增加0.5%成功率
        return int(self.alchemy_level * 0.5)
