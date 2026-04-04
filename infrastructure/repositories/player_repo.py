"""玩家仓储"""
import json
import time
from typing import Optional, List, Dict, Any

from ...domain.models.player import Player
from ...domain.enums import CultivationType, PlayerState
from ..storage import JSONStorage, TimestampConverter
from .base import BaseRepository


class PlayerRepository(BaseRepository[Player]):
    """玩家仓储实现"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化玩家仓储
        
        Args:
            storage: JSON 存储管理器
        """
        super().__init__(storage, "players.json")
    
    def get_by_id(self, user_id: str) -> Optional[Player]:
        """
        根据用户ID获取玩家
        
        Args:
            user_id: 用户ID
            
        Returns:
            玩家对象，不存在则返回None
        """
        data = self.storage.get(self.filename, user_id)
        if data is None:
            return None
        return self._to_domain(data)
    
    def get_by_nickname(self, nickname: str) -> Optional[Player]:
        """
        根据道号获取玩家
        
        Args:
            nickname: 道号
            
        Returns:
            玩家对象，不存在则返回None
        """
        # 查询所有玩家，找到匹配的道号
        results = self.storage.query(
            self.filename,
            filter_fn=lambda x: x.get('nickname') == nickname,
            limit=1
        )
        
        if not results:
            return None
        
        return self._to_domain(results[0])
    
    def save(self, player: Player) -> None:
        """
        保存玩家（创建或更新）
        
        注意：为了避免覆盖玩家的探索状态（如秘境、历练等），
        在保存前会先读取当前存储的状态并保留它。
        
        Args:
            player: 玩家对象
        """
        # 先读取当前存储的状态（如果存在）
        existing_data = self.storage.get(self.filename, player.user_id)
        current_state = None
        if existing_data:
            current_state = existing_data.get('state')
        
        # 转换为字典
        data = self._to_dict(player)
        
        # 如果存在旧状态且不是 IDLE，保留旧状态
        # 这样可以避免在购买、签到等操作时意外清除探索状态
        if current_state and current_state != PlayerState.IDLE.value:
            # 只有当新状态也是 IDLE 时才保留旧状态
            if data['state'] == PlayerState.IDLE.value:
                data['state'] = current_state
        
        self.storage.set(self.filename, player.user_id, data)
    
    def delete(self, user_id: str) -> None:
        """
        删除玩家
        
        Args:
            user_id: 用户ID
        """
        self.storage.delete(self.filename, user_id)
    
    def exists(self, user_id: str) -> bool:
        """
        检查玩家是否存在
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否存在
        """
        return self.storage.exists(self.filename, user_id)
    
    def get_top_by_level(self, limit: int = 10) -> List[Player]:
        """
        获取境界排行榜
        
        Args:
            limit: 返回数量
            
        Returns:
            玩家列表
        """
        results = self.storage.query(
            self.filename,
            sort_key=lambda x: (x['level_index'], x['experience']),
            reverse=True,
            limit=limit
        )
        return [self._to_domain(data) for data in results]
    
    def get_top_by_gold(self, limit: int = 10) -> List[Player]:
        """
        获取灵石排行榜
        
        Args:
            limit: 返回数量
            
        Returns:
            玩家列表
        """
        results = self.storage.query(
            self.filename,
            sort_key=lambda x: x['gold'],
            reverse=True,
            limit=limit
        )
        return [self._to_domain(data) for data in results]
    
    def get_player(self, user_id: str) -> Optional[Player]:
        """
        获取玩家（get_by_id 的别名，用于兼容性）
        
        Args:
            user_id: 用户ID
            
        Returns:
            玩家对象，不存在则返回None
        """
        return self.get_by_id(user_id)
    
    def add_gold(self, user_id: str, amount: int) -> None:
        """
        增加/减少玩家灵石（便捷方法）
        
        Args:
            user_id: 用户ID
            amount: 灵石数量（正数为增加，负数为减少）
        """
        player = self.get_by_id(user_id)
        if not player:
            raise ValueError(f"玩家不存在: {user_id}")
        
        if amount > 0:
            player.add_gold(amount)
        else:
            player.consume_gold(-amount)
        
        self.save(player)
    
    def add_experience(self, user_id: str, exp: int) -> None:
        """
        增加玩家修为（便捷方法）
        
        Args:
            user_id: 用户ID
            exp: 修为数量
        """
        player = self.get_by_id(user_id)
        if not player:
            raise ValueError(f"玩家不存在: {user_id}")
        
        player.add_experience(exp)
        self.save(player)
    
    def add_pill(self, user_id: str, pill_name: str, count: int) -> None:
        """
        增加玩家丹药（已废弃，现在添加到储物戒）
        
        Args:
            user_id: 用户ID
            pill_name: 丹药名称
            count: 数量
        """
        player = self.get_by_id(user_id)
        if not player:
            raise ValueError(f"玩家不存在: {user_id}")
        
        # 添加到储物戒而不是丹药背包
        if pill_name in player.storage_ring_items:
            player.storage_ring_items[pill_name] += count
        else:
            player.storage_ring_items[pill_name] = count
        
        player.updated_at = int(time.time())
        self.save(player)
    
    def get_player_state(self, user_id: str):
        """
        获取玩家状态（便捷方法，用于兼容性）
        
        Args:
            user_id: 用户ID
            
        Returns:
            玩家状态对象（包含 extra_data 字段）
        """
        # 从 player_states.json 获取状态数据
        state_data = self.storage.get("player_states.json", user_id)
        if not state_data:
            return None
        
        # 返回一个简单的对象，包含 extra_data
        class PlayerStateData:
            def __init__(self, extra_data):
                self.extra_data = extra_data
        
        return PlayerStateData(state_data.get('extra_data'))
    
    def update_player_state(
        self,
        user_id: str,
        state: str,
        extra_data: Optional[str] = None
    ) -> None:
        """
        更新玩家状态
        
        Args:
            user_id: 用户ID
            state: 状态值（字符串或 PlayerState 枚举）
            extra_data: 额外数据（JSON 字符串）
        """
        # 直接从存储中获取玩家数据（不通过领域模型）
        player_data = self.storage.get(self.filename, user_id)
        if not player_data:
            raise ValueError(f"玩家不存在: {user_id}")
        
        # 更新状态字段
        if isinstance(state, PlayerState):
            player_data['state'] = state.value
        else:
            # 如果是字符串，直接使用
            player_data['state'] = state
        
        # 保存更新后的数据
        self.storage.set(self.filename, user_id, player_data)
        
        # 保存额外数据到 player_states.json
        if extra_data is not None:
            state_data = {
                'user_id': user_id,
                'state': player_data['state'],
                'extra_data': extra_data,
                'updated_at': TimestampConverter.to_iso8601(int(time.time()))
            }
            self.storage.set("player_states.json", user_id, state_data)
        else:
            # 如果 extra_data 为 None，删除状态数据
            if self.storage.exists("player_states.json", user_id):
                self.storage.delete("player_states.json", user_id)
    
    def get_all_players(self) -> List[Player]:
        """
        获取所有玩家
        
        Returns:
            玩家列表
        """
        results = self.storage.query(self.filename)
        return [self._to_domain(data) for data in results]
    
    def _to_domain(self, data: Dict[str, Any]) -> Player:
        """
        将字典数据转换为领域对象
        
        Args:
            data: 字典数据
            
        Returns:
            Player 对象
        """
        # 转换时间戳
        created_at = TimestampConverter.from_iso8601(data.get('created_at'))
        updated_at = TimestampConverter.from_iso8601(data.get('updated_at'))
        cultivation_start_time = TimestampConverter.from_iso8601(data.get('cultivation_start_time'))
        
        # 如果时间戳为 None，使用默认值
        if created_at is None:
            created_at = 0
        if updated_at is None:
            updated_at = 0
        if cultivation_start_time is None:
            cultivation_start_time = 0
        
        # 解析丹药背包
        pills_inventory = data.get('pills_inventory', {})
        if isinstance(pills_inventory, str):
            try:
                pills_inventory = json.loads(pills_inventory)
            except:
                pills_inventory = {}
        
        # 解析储物戒物品
        storage_ring_items = data.get('storage_ring_items', {})
        if isinstance(storage_ring_items, str):
            try:
                storage_ring_items = json.loads(storage_ring_items)
            except:
                storage_ring_items = {}
        
        return Player(
            user_id=data['user_id'],
            nickname=data['nickname'],
            cultivation_type=CultivationType(data['cultivation_type']),
            spiritual_root=data['spiritual_root'],
            level_index=data.get('level_index', 0),
            experience=data.get('experience', 0),
            gold=data.get('gold', 0),
            state=PlayerState.from_string(data.get('state', 'idle')),
            spiritual_qi=data.get('spiritual_qi', 0),
            max_spiritual_qi=data.get('max_spiritual_qi', 0),
            blood_qi=data.get('blood_qi', 0),
            max_blood_qi=data.get('max_blood_qi', 0),
            lifespan=data.get('lifespan', 100),
            mental_power=data.get('mental_power', 100),
            physical_damage=data.get('physical_damage', 5),
            magic_damage=data.get('magic_damage', 5),
            physical_defense=data.get('physical_defense', 5),
            magic_defense=data.get('magic_defense', 0),
            weapon=data.get('weapon'),
            armor=data.get('armor'),
            main_technique=data.get('main_technique'),
            pills_inventory=pills_inventory,
            storage_ring=data.get('storage_ring', '基础储物戒'),
            storage_ring_items=storage_ring_items,
            sect_id=data.get('sect_id'),
            sect_position=data.get('sect_position'),
            level_up_rate=data.get('level_up_rate', 0),
            alchemy_level=data.get('alchemy_level', 0),
            alchemy_exp=data.get('alchemy_exp', 0),
            created_at=created_at,
            updated_at=updated_at,
            last_check_in_date=data.get('last_check_in_date'),
            cultivation_start_time=cultivation_start_time,
            user_name=data.get('user_name')
        )
    
    def _to_dict(self, player: Player) -> Dict[str, Any]:
        """
        将领域对象转换为字典数据
        
        Args:
            player: Player 对象
            
        Returns:
            字典数据
        """
        return {
            'user_id': player.user_id,
            'nickname': player.nickname,
            'cultivation_type': player.cultivation_type.value,
            'spiritual_root': player.spiritual_root,
            'level_index': player.level_index,
            'experience': player.experience,
            'gold': player.gold,
            'state': player.state.value,
            'spiritual_qi': player.spiritual_qi,
            'max_spiritual_qi': player.max_spiritual_qi,
            'blood_qi': player.blood_qi,
            'max_blood_qi': player.max_blood_qi,
            'lifespan': player.lifespan,
            'mental_power': player.mental_power,
            'physical_damage': player.physical_damage,
            'magic_damage': player.magic_damage,
            'physical_defense': player.physical_defense,
            'magic_defense': player.magic_defense,
            'weapon': player.weapon,
            'armor': player.armor,
            'main_technique': player.main_technique,
            'pills_inventory': player.pills_inventory,
            'storage_ring': player.storage_ring,
            'storage_ring_items': player.storage_ring_items,
            'sect_id': player.sect_id,
            'sect_position': player.sect_position,
            'level_up_rate': player.level_up_rate,
            'alchemy_level': player.alchemy_level,
            'alchemy_exp': player.alchemy_exp,
            'created_at': TimestampConverter.to_iso8601(player.created_at),
            'updated_at': TimestampConverter.to_iso8601(player.updated_at),
            'last_check_in_date': player.last_check_in_date,
            'cultivation_start_time': TimestampConverter.to_iso8601(player.cultivation_start_time),
            'user_name': player.user_name
        }
