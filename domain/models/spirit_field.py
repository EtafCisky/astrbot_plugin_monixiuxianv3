"""灵田系统领域模型"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class PlantedHerb:
    """已种植药草值对象"""
    herb_id: str  # 药草物品ID
    herb_name: str  # 药草名称
    herb_rank: str  # 药草品级
    plant_time: int  # 种植时间(Unix时间戳)
    mature_time: int  # 成熟时间(Unix时间戳)
    
    def is_mature(self, current_time: int) -> bool:
        """检查是否成熟"""
        return current_time >= self.mature_time
    
    def get_remaining_time(self, current_time: int) -> int:
        """获取剩余成熟时间(秒)"""
        if self.is_mature(current_time):
            return 0
        return self.mature_time - current_time
    
    def format_remaining_time(self, current_time: int) -> str:
        """格式化剩余时间显示"""
        remaining_seconds = self.get_remaining_time(current_time)
        
        if remaining_seconds <= 0:
            return "已成熟"
        
        if remaining_seconds < 60:
            return "即将成熟"
        
        days = remaining_seconds // 86400
        hours = (remaining_seconds % 86400) // 3600
        minutes = (remaining_seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}天")
        if hours > 0:
            parts.append(f"{hours}小时")
        if minutes > 0:
            parts.append(f"{minutes}分钟")
        
        return "".join(parts)


@dataclass
class Plot:
    """田地实体"""
    plot_id: int
    user_id: str
    planted_herb: Optional[PlantedHerb]  # 已种植的药草
    
    def is_empty(self) -> bool:
        """检查是否空闲"""
        return self.planted_herb is None
    
    def is_mature(self, current_time: int) -> bool:
        """检查是否成熟"""
        if self.is_empty():
            return False
        return self.planted_herb.is_mature(current_time)
    
    def plant(self, herb_id: str, herb_name: str, herb_rank: str, 
              plant_time: int, mature_time: int) -> None:
        """种植药草"""
        if not self.is_empty():
            raise ValueError("田地已被占用")
        
        self.planted_herb = PlantedHerb(
            herb_id=herb_id,
            herb_name=herb_name,
            herb_rank=herb_rank,
            plant_time=plant_time,
            mature_time=mature_time
        )
    
    def harvest(self) -> PlantedHerb:
        """收获药草"""
        if self.is_empty():
            raise ValueError("田地为空,无法收获")
        
        harvested = self.planted_herb
        self.planted_herb = None
        return harvested
    
    def get_remaining_time(self, current_time: int) -> int:
        """获取剩余成熟时间(秒)"""
        if self.is_empty():
            return 0
        return self.planted_herb.get_remaining_time(current_time)


@dataclass
class HerbSeed:
    """种子值对象"""
    seed_id: str  # 种子物品ID
    seed_name: str  # 种子名称
    herb_id: str  # 对应药草ID
    herb_name: str  # 对应药草名称
    herb_rank: str  # 药草品级
    herb_price: int  # 药草价格
    seed_price: int  # 种子价格
    grow_time: int  # 成熟时间(秒)
    is_unlocked: bool  # 是否已解锁
    purchase_count: int  # 购买次数
    
    @staticmethod
    def calculate_seed_price(herb_price: int) -> int:
        """计算种子价格 = 药草价格 × 1.5"""
        return int(herb_price * 1.5)
    
    def get_grow_time_display(self) -> str:
        """获取成熟时间显示"""
        seconds = self.grow_time
        
        if seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}分钟"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours}小时"
        else:
            days = seconds // 86400
            return f"{days}天"
    
    def get_unlock_progress(self) -> str:
        """获取解锁进度显示(如: 3/5)"""
        return f"{self.purchase_count}/5"


@dataclass
class SpiritField:
    """灵田聚合根"""
    user_id: str
    capacity: int  # 田地总容量
    plots: list[Plot]  # 田地列表
    unlocked_seeds: set[str]  # 已解锁的种子ID集合
    seed_purchase_count: dict[str, int]  # 种子购买次数 {seed_id: count}
    
    def get_available_plot(self) -> Optional[Plot]:
        """获取第一个空闲田地"""
        for plot in self.plots:
            if plot.is_empty():
                return plot
        return None
    
    def get_available_plots(self) -> list[Plot]:
        """获取所有空闲田地"""
        return [plot for plot in self.plots if plot.is_empty()]
    
    def get_occupied_plots(self) -> list[Plot]:
        """获取所有已占用的田地"""
        return [plot for plot in self.plots if not plot.is_empty()]
    
    def get_mature_plots(self, current_time: int) -> list[Plot]:
        """获取所有已成熟的田地"""
        return [plot for plot in self.plots if plot.is_mature(current_time)]
    
    def can_upgrade(self) -> bool:
        """检查是否可以升级"""
        max_capacity = 15
        return self.capacity < max_capacity
    
    def upgrade(self) -> None:
        """升级灵田(增加2个田地)"""
        if not self.can_upgrade():
            raise ValueError("灵田已达最大容量")
        
        # 增加容量
        old_capacity = self.capacity
        self.capacity += 2
        
        # 创建新的田地
        for i in range(2):
            new_plot_id = len(self.plots) + 1
            new_plot = Plot(
                plot_id=new_plot_id,
                user_id=self.user_id,
                planted_herb=None
            )
            self.plots.append(new_plot)
    
    def calculate_upgrade_cost(self) -> int:
        """计算升级费用"""
        return self.capacity * 10000
    
    def is_seed_unlocked(self, seed_id: str) -> bool:
        """检查种子是否已解锁"""
        return seed_id in self.unlocked_seeds
    
    def increment_seed_purchase(self, seed_id: str) -> None:
        """增加种子购买次数"""
        if seed_id not in self.seed_purchase_count:
            self.seed_purchase_count[seed_id] = 0
        self.seed_purchase_count[seed_id] += 1
    
    def check_and_unlock_seed(self, seed_id: str) -> bool:
        """检查并解锁种子(购买次数>=5时),返回是否新解锁"""
        unlock_threshold = 5
        purchase_count = self.seed_purchase_count.get(seed_id, 0)
        
        # 如果已经解锁,返回False
        if self.is_seed_unlocked(seed_id):
            return False
        
        # 如果购买次数达到阈值,解锁种子
        if purchase_count >= unlock_threshold:
            self.unlocked_seeds.add(seed_id)
            return True
        
        return False
