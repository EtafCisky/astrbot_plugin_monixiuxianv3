"""修炼业务服务"""
import time
from typing import Optional

from ...core.config import ConfigManager
from ...core.exceptions import InvalidStateException
from ...domain.models.player import Player
from ...domain.enums import PlayerState
from ...domain.value_objects import CultivationResult
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...utils.spirit_root_generator import SpiritRootGenerator


class CultivationService:
    """修炼业务服务"""
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        config_manager: ConfigManager,
        spirit_root_generator: SpiritRootGenerator
    ):
        self.player_repo = player_repo
        self.config_manager = config_manager
        self.spirit_root_generator = spirit_root_generator
    
    def start_cultivation(self, player: Player) -> None:
        """
        开始闭关
        
        Args:
            player: 玩家对象
            
        Raises:
            InvalidStateException: 当前状态无法闭关
        """
        # 检查状态
        if not player.can_cultivate():
            raise InvalidStateException(
                player.state.value,
                PlayerState.IDLE.value
            )
        
        # 开始闭关
        player.start_cultivation()
        
        # 保存玩家状态（强制保存状态，因为这是明确的状态变更）
        self.player_repo.save(player, force_state=True)
    
    def end_cultivation(self, player: Player) -> CultivationResult:
        """
        结束闭关
        
        Args:
            player: 玩家对象
            
        Returns:
            闭关结果
            
        Raises:
            InvalidStateException: 当前未闭关
            ValueError: 闭关时间异常
        """
        # 检查状态
        if player.state != PlayerState.CULTIVATING:
            raise InvalidStateException(
                player.state.value,
                PlayerState.CULTIVATING.value
            )
        
        try:
            # 结束闭关，获取时长
            duration_minutes = player.end_cultivation()
        except ValueError as e:
            # 如果是数据异常（闭关时间丢失），强制保存重置后的状态
            if "数据异常" in str(e):
                self.player_repo.save(player, force_state=True)
            # 重新抛出异常让上层处理
            raise
        
        # 检查最小时长
        if duration_minutes < 1:
            raise ValueError("闭关时间不足1分钟")
        
        # 计算时长上限
        max_minutes = self._get_max_cultivation_minutes(player.level_index)
        effective_minutes = min(duration_minutes, max_minutes)
        is_overtime = duration_minutes > max_minutes
        
        # 计算获得的修为
        gained_exp = self._calculate_cultivation_exp(player, effective_minutes)
        
        # 更新玩家修为
        player.add_experience(gained_exp)
        
        # 保存玩家状态（强制保存状态，因为这是明确的状态变更）
        self.player_repo.save(player, force_state=True)
        
        return CultivationResult(
            duration_minutes=duration_minutes,
            gained_exp=gained_exp,
            is_overtime=is_overtime,
            max_minutes=max_minutes
        )
    
    def _get_max_cultivation_minutes(self, level_index: int) -> int:
        """
        获取闭关时长上限
        
        基础24小时，每提升一个大境界增加6小时
        level_index: 0-8练气, 9-17筑基, 18-26金丹, 27-35元婴, 
                    36-44化神, 45-53炼虚, 54-62合体, 63-71大乘, 72+渡劫
        
        Args:
            level_index: 境界索引
            
        Returns:
            最大闭关时长（分钟）
        """
        base_minutes = 1440  # 24小时
        realm_bonus = (level_index // 9) * 360  # 每个大境界增加6小时
        return base_minutes + realm_bonus
    
    def _calculate_cultivation_exp(
        self,
        player: Player,
        minutes: int,
        technique_bonus: float = 0.0,
        pill_multiplier: float = 1.0
    ) -> int:
        """
        计算修炼获得的修为
        
        Args:
            player: 玩家对象
            minutes: 闭关时长（分钟）
            technique_bonus: 心法加成（来自主修心法）
            pill_multiplier: 丹药倍率
            
        Returns:
            获得的修为值
        """
        # 获取基础修为配置
        settings = self.config_manager.settings.values
        base_exp = settings.base_exp_per_minute
        
        # 获取灵根速度倍率
        root_name = player.spiritual_root.replace("灵根", "")
        root_speed = self.spirit_root_generator.get_root_speed_by_name(root_name)
        
        # 计算总修为倍率：灵根倍率 * (1 + 心法倍率) * 丹药倍率
        total_multiplier = root_speed * (1.0 + technique_bonus) * pill_multiplier
        
        # 计算总修为：基础修为 * 时长 * 总倍率
        total_exp = int(base_exp * minutes * total_multiplier)
        
        return total_exp
