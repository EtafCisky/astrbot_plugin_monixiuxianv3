"""秘境仓储"""
from typing import List, Optional, Dict, Any

from .base import BaseRepository
from ..storage import JSONStorage
from ...domain.models.rift import Rift


class RiftRepository(BaseRepository[Rift]):
    """秘境仓储"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化秘境仓储
        
        Args:
            storage: JSON存储管理器
        """
        super().__init__(storage, "rifts.json")
    
    def get_by_id(self, rift_id: str) -> Optional[Rift]:
        """根据ID获取秘境"""
        return self.get_rift_by_id(int(rift_id))
    
    def save(self, entity: Rift) -> None:
        """保存秘境"""
        rift_dict = self._to_dict(entity)
        self.storage.set(self.filename, str(entity.rift_id), rift_dict)
    
    def delete(self, rift_id: str) -> None:
        """删除秘境"""
        self.storage.delete(self.filename, rift_id)
    
    def exists(self, rift_id: str) -> bool:
        """检查秘境是否存在"""
        return self.storage.exists(self.filename, rift_id)
    
    def get_all_rifts(self) -> List[Rift]:
        """获取所有秘境"""
        results = self.storage.query(self.filename)
        return [self._to_domain(data) for data in results]
    
    def get_rift_by_id(self, rift_id: int) -> Optional[Rift]:
        """根据ID获取秘境"""
        data = self.storage.get(self.filename, str(rift_id))
        
        if not data:
            return None
        
        return self._to_domain(data)
    
    def get_rifts_by_level(self, rift_level: int) -> List[Rift]:
        """根据等级获取秘境"""
        results = self.storage.query(
            self.filename,
            filter_fn=lambda data: data.get("rift_level") == rift_level
        )
        
        return [self._to_domain(data) for data in results]
    
    def create_rift(self, rift: Rift) -> int:
        """创建秘境"""
        # 生成新的 rift_id
        all_data = self.storage.load(self.filename)
        if all_data:
            max_id = max(int(rid) for rid in all_data.keys())
            new_id = max_id + 1
        else:
            new_id = 1
        
        rift.rift_id = new_id
        
        rift_dict = self._to_dict(rift)
        self.storage.set(self.filename, str(new_id), rift_dict)
        
        return new_id
    
    def _to_domain(self, data: Dict[str, Any]) -> Rift:
        """转换为领域模型"""
        # 获取 required_level，如果缺失则默认为 0
        required_level = data.get("required_level", 0)
        
        # 获取 recommended_level
        # 如果缺失，根据秘境等级设置合理的默认推荐境界
        if "recommended_level" not in data:
            rift_level = data.get("rift_level", 1)
            # 低级秘境推荐筑基期(10)，中级推荐金丹期(13)，高级推荐元婴期(16)
            default_recommended = {1: 10, 2: 13, 3: 16}.get(rift_level, required_level + 7)
            recommended_level = default_recommended
        else:
            recommended_level = data["recommended_level"]
        
        return Rift(
            rift_id=data["rift_id"],
            rift_name=data["rift_name"],
            rift_level=data["rift_level"],
            required_level=required_level,
            recommended_level=recommended_level,
            exp_reward_min=int(data["exp_reward_min"]),
            exp_reward_max=int(data["exp_reward_max"]),
            gold_reward_min=int(data["gold_reward_min"]),
            gold_reward_max=int(data["gold_reward_max"]),
            description=data.get("description", ""),
            bounty_tag=data.get("bounty_tag", "")
        )
    
    def _to_dict(self, rift: Rift) -> Dict[str, Any]:
        """转换为字典数据"""
        return {
            "rift_id": rift.rift_id,
            "rift_name": rift.rift_name,
            "rift_level": rift.rift_level,
            "required_level": rift.required_level,
            "recommended_level": rift.recommended_level,
            "exp_reward_min": rift.exp_reward_min,
            "exp_reward_max": rift.exp_reward_max,
            "gold_reward_min": rift.gold_reward_min,
            "gold_reward_max": rift.gold_reward_max,
            "description": rift.description,
            "bounty_tag": rift.bounty_tag
        }
