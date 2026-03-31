"""灵田仓储"""
import json
import time
from typing import Optional, Dict, Any

from ...domain.models.spirit_field import SpiritField, Plot, PlantedHerb
from ..storage import JSONStorage, TimestampConverter
from .base import BaseRepository


class SpiritFieldRepository(BaseRepository[SpiritField]):
    """灵田仓储实现"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化灵田仓储
        
        Args:
            storage: JSON 存储管理器
        """
        super().__init__(storage, "spirit_fields.json")
    
    def get_by_id(self, user_id: str) -> Optional[SpiritField]:
        """
        根据用户ID获取灵田
        
        Args:
            user_id: 用户ID
            
        Returns:
            灵田对象，不存在则返回None
        """
        return self.get_by_user_id(user_id)
    
    def get_by_user_id(self, user_id: str) -> Optional[SpiritField]:
        """
        根据用户ID获取灵田
        
        Args:
            user_id: 用户ID
            
        Returns:
            灵田对象，不存在则返回None
        """
        data = self.storage.get(self.filename, user_id)
        if data is None:
            return None
        return self._to_domain(data)
    
    def create(self, user_id: str, capacity: int = 3) -> SpiritField:
        """
        创建新的灵田
        
        Args:
            user_id: 用户ID
            capacity: 初始容量（默认3）
            
        Returns:
            创建的灵田对象
        """
        # 创建空的田地列表
        plots = []
        for i in range(capacity):
            plot = Plot(
                plot_id=i + 1,
                user_id=user_id,
                planted_herb=None
            )
            plots.append(plot)
        
        # 创建灵田对象
        spirit_field = SpiritField(
            user_id=user_id,
            capacity=capacity,
            plots=plots,
            unlocked_seeds=set(),
            seed_purchase_count={}
        )
        
        # 保存到存储
        self.save(spirit_field)
        
        return spirit_field
    
    def update(self, spirit_field: SpiritField) -> None:
        """
        更新灵田
        
        Args:
            spirit_field: 灵田对象
        """
        self.save(spirit_field)
    
    def save(self, spirit_field: SpiritField) -> None:
        """
        保存灵田（创建或更新）
        
        Args:
            spirit_field: 灵田对象
        """
        data = self._to_dict(spirit_field)
        self.storage.set(self.filename, spirit_field.user_id, data)
    
    def delete(self, user_id: str) -> None:
        """
        删除灵田
        
        Args:
            user_id: 用户ID
        """
        self.storage.delete(self.filename, user_id)
    
    def exists(self, user_id: str) -> bool:
        """
        检查灵田是否存在
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否存在
        """
        return self.storage.exists(self.filename, user_id)
    
    def _to_domain(self, data: Dict[str, Any]) -> SpiritField:
        """
        将字典数据转换为领域对象
        
        Args:
            data: 字典数据
            
        Returns:
            SpiritField 对象
        """
        user_id = data['user_id']
        capacity = data.get('capacity', 3)
        
        # 解析已解锁的种子列表
        unlocked_seeds_data = data.get('unlocked_seeds', '[]')
        if isinstance(unlocked_seeds_data, str):
            try:
                unlocked_seeds = set(json.loads(unlocked_seeds_data))
            except:
                unlocked_seeds = set()
        elif isinstance(unlocked_seeds_data, list):
            unlocked_seeds = set(unlocked_seeds_data)
        else:
            unlocked_seeds = set()
        
        # 解析种子购买次数
        seed_purchase_count_data = data.get('seed_purchase_count', '{}')
        if isinstance(seed_purchase_count_data, str):
            try:
                seed_purchase_count = json.loads(seed_purchase_count_data)
            except:
                seed_purchase_count = {}
        elif isinstance(seed_purchase_count_data, dict):
            seed_purchase_count = seed_purchase_count_data
        else:
            seed_purchase_count = {}
        
        # 解析田地列表
        plots_data = data.get('plots', [])
        plots = []
        for plot_data in plots_data:
            planted_herb = None
            if plot_data.get('herb_id'):
                planted_herb = PlantedHerb(
                    herb_id=plot_data['herb_id'],
                    herb_name=plot_data['herb_name'],
                    herb_rank=plot_data['herb_rank'],
                    plant_time=plot_data['plant_time'],
                    mature_time=plot_data['mature_time']
                )
            
            plot = Plot(
                plot_id=plot_data['plot_id'],
                user_id=user_id,
                planted_herb=planted_herb
            )
            plots.append(plot)
        
        return SpiritField(
            user_id=user_id,
            capacity=capacity,
            plots=plots,
            unlocked_seeds=unlocked_seeds,
            seed_purchase_count=seed_purchase_count
        )
    
    def _to_dict(self, spirit_field: SpiritField) -> Dict[str, Any]:
        """
        将领域对象转换为字典数据
        
        Args:
            spirit_field: SpiritField 对象
            
        Returns:
            字典数据
        """
        # 序列化田地列表
        plots_data = []
        for plot in spirit_field.plots:
            plot_data = {
                'plot_id': plot.plot_id,
                'user_id': plot.user_id,
                'herb_id': None,
                'herb_name': None,
                'herb_rank': None,
                'plant_time': None,
                'mature_time': None
            }
            
            if plot.planted_herb:
                plot_data.update({
                    'herb_id': plot.planted_herb.herb_id,
                    'herb_name': plot.planted_herb.herb_name,
                    'herb_rank': plot.planted_herb.herb_rank,
                    'plant_time': plot.planted_herb.plant_time,
                    'mature_time': plot.planted_herb.mature_time
                })
            
            plots_data.append(plot_data)
        
        # 序列化已解锁种子列表为JSON字符串
        unlocked_seeds_json = json.dumps(list(spirit_field.unlocked_seeds))
        
        # 序列化种子购买次数为JSON字符串
        seed_purchase_count_json = json.dumps(spirit_field.seed_purchase_count)
        
        current_time = int(time.time())
        
        return {
            'user_id': spirit_field.user_id,
            'capacity': spirit_field.capacity,
            'plots': plots_data,
            'unlocked_seeds': unlocked_seeds_json,
            'seed_purchase_count': seed_purchase_count_json,
            'created_at': TimestampConverter.to_iso8601(current_time),
            'updated_at': TimestampConverter.to_iso8601(current_time)
        }
