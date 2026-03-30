"""突破业务服务"""
import random
from typing import Tuple, Optional
from astrbot.api import logger

from ...core.config import ConfigManager
from ...core.exceptions import InvalidStateException
from ...domain.models.player import Player
from ...domain.enums import PlayerState, CultivationType
from ...domain.value_objects import BreakthroughResult
from ...infrastructure.repositories.player_repo import PlayerRepository


class BreakthroughService:
    """突破业务服务"""
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        config_manager: ConfigManager
    ):
        self.player_repo = player_repo
        self.config_manager = config_manager
    
    def check_breakthrough_requirements(self, player: Player) -> Tuple[bool, str]:
        """
        检查玩家是否满足突破条件
        
        Args:
            player: 玩家对象
            
        Returns:
            (是否满足, 错误消息)
        """
        # 获取境界配置
        level_data = self._get_level_data(player)
        
        # 检查是否已经是最高境界
        if player.level_index >= len(level_data) - 1:
            return False, "你已经达到了最高境界，无法继续突破！"
        
        # 获取下一境界所需修为
        next_level_index = player.level_index + 1
        next_level_data = level_data[next_level_index]
        required_exp = next_level_data.get("required_exp", next_level_data.get("exp_needed", 0))
        
        # 检查修为是否满足
        if player.experience < required_exp:
            current_level = level_data[player.level_index].get("name", level_data[player.level_index].get("level_name", "未知"))
            next_level = next_level_data.get("name", next_level_data.get("level_name", "未知"))
            return False, (
                f"修为不足！\n"
                f"当前境界：{current_level}\n"
                f"当前修为：{player.experience:,}\n"
                f"突破至【{next_level}】需要修为：{required_exp:,}"
            )
        
        return True, ""
    
    def get_breakthrough_info(self, player: Player) -> dict:
        """
        获取突破信息
        
        Args:
            player: 玩家对象
            
        Returns:
            突破信息字典
        """
        level_data = self._get_level_data(player)
        
        # 检查是否已经是最高境界
        if player.level_index >= len(level_data) - 1:
            return {
                "can_breakthrough": False,
                "message": "你已经达到了最高境界，无法继续突破！"
            }
        
        # 获取当前和下一境界信息
        current_level_data = level_data[player.level_index]
        next_level_data = level_data[player.level_index + 1]
        
        current_level_name = current_level_data.get("name", current_level_data.get("level_name", "未知"))
        next_level_name = next_level_data.get("name", next_level_data.get("level_name", "未知"))
        required_exp = next_level_data.get("required_exp", next_level_data.get("exp_needed", 0))
        base_success_rate = next_level_data.get("success_rate", 0.5)
        
        # 检查修为是否满足
        exp_satisfied = player.experience >= required_exp
        
        return {
            "can_breakthrough": exp_satisfied,
            "current_level": current_level_name,
            "next_level": next_level_name,
            "required_exp": required_exp,
            "current_exp": player.experience,
            "exp_satisfied": exp_satisfied,
            "base_success_rate": base_success_rate,
            "cultivation_type": player.cultivation_type
        }
    
    def execute_breakthrough(
        self,
        player: Player,
        pill_name: Optional[str] = None
    ) -> BreakthroughResult:
        """
        执行突破
        
        Args:
            player: 玩家对象
            pill_name: 使用的破境丹名称（可选）
            
        Returns:
            突破结果
            
        Raises:
            InvalidStateException: 当前状态无法突破
            ValueError: 不满足突破条件
        """
        # 检查状态
        if player.state != PlayerState.IDLE:
            raise InvalidStateException(
                player.state.value,
                PlayerState.IDLE.value
            )
        
        # 检查突破条件
        can_breakthrough, error_msg = self.check_breakthrough_requirements(player)
        if not can_breakthrough:
            raise ValueError(error_msg)
        
        # 如果使用了破境丹，先检查并扣除
        if pill_name:
            # 检查储物戒中是否有该丹药
            if pill_name not in player.storage_ring_items or player.storage_ring_items[pill_name] < 1:
                raise ValueError(f"储物戒中没有【{pill_name}】！")
            
            # 扣除丹药
            if player.storage_ring_items[pill_name] <= 1:
                del player.storage_ring_items[pill_name]
            else:
                player.storage_ring_items[pill_name] -= 1
        
        # 获取境界配置
        level_data = self._get_level_data(player)
        
        # 计算成功率
        success_rate, rate_info = self._calculate_success_rate(
            player, level_data, pill_name
        )
        
        # 判定突破结果
        random_value = random.random()
        breakthrough_success = random_value < success_rate
        
        current_level_name = level_data[player.level_index].get("name", level_data[player.level_index].get("level_name", "未知"))
        next_level_index = player.level_index + 1
        next_level_data = level_data[next_level_index]
        next_level_name = next_level_data.get("name", next_level_data.get("level_name", "未知"))
        
        if breakthrough_success:
            # 突破成功 - 提升境界并更新属性
            attribute_gains = self._apply_breakthrough_success(player, next_level_data)
            
            # 清除突破加成（一次性效果）
            player.level_up_rate = 0
            
            # 保存
            self.player_repo.save(player)
            
            # 记录日志
            logger.info(
                f"玩家 {player.user_id} 突破成功：{current_level_name} -> {next_level_name}"
            )
            
            return BreakthroughResult(
                success=True,
                died=False,
                current_level=current_level_name,
                next_level=next_level_name,
                rate_info=rate_info,
                attribute_gains=attribute_gains,
                exp_loss=0
            )
        else:
            # 突破失败 - 判断是否死亡
            death_rate = self._calculate_death_rate()
            died = random.random() < death_rate
            
            if died:
                # 玩家死亡 - 删除玩家数据
                self.player_repo.delete(player.user_id)
                
                # 记录日志
                logger.info(
                    f"玩家 {player.user_id} 突破失败并死亡：{current_level_name} -> {next_level_name}，"
                    f"死亡概率 {death_rate:.2%}"
                )
                
                return BreakthroughResult(
                    success=False,
                    died=True,
                    current_level=current_level_name,
                    next_level=next_level_name,
                    rate_info=rate_info,
                    attribute_gains={},
                    exp_loss=0
                )
            else:
                # 突破失败但未死亡 - 扣除部分修为
                exp_penalty = int(player.experience * 0.1)  # 扣除10%修为
                player.experience = max(0, player.experience - exp_penalty)
                
                # 清除突破加成（一次性效果）
                player.level_up_rate = 0
                
                # 保存
                self.player_repo.save(player)
                
                # 记录日志
                logger.info(
                    f"玩家 {player.user_id} 突破失败：{current_level_name} -> {next_level_name}，"
                    f"损失修为 {exp_penalty}"
                )
                
                return BreakthroughResult(
                    success=False,
                    died=False,
                    current_level=current_level_name,
                    next_level=next_level_name,
                    rate_info=rate_info,
                    attribute_gains={},
                    exp_loss=exp_penalty
                )
    
    def _get_level_data(self, player: Player) -> list:
        """获取境界配置数据"""
        if player.cultivation_type == CultivationType.PHYSICAL.value:
            return self.config_manager.body_level_data
        else:
            return self.config_manager.level_data
    
    def _calculate_success_rate(
        self,
        player: Player,
        level_data: list,
        pill_name: Optional[str] = None
    ) -> Tuple[float, str]:
        """
        计算突破成功率
        
        Args:
            player: 玩家对象
            level_data: 境界配置数据
            pill_name: 使用的破境丹名称（可选）
            
        Returns:
            (成功率, 说明信息)
        """
        # 获取基础成功率
        next_level_index = player.level_index + 1
        next_level_data = level_data[next_level_index]
        base_success_rate = next_level_data.get("success_rate", 0.5)
        
        info_lines = [f"基础成功率：{base_success_rate:.1%}"]
        
        final_rate = base_success_rate
        max_rate = 1.0  # 默认最大100%
        
        # 添加玩家已有的突破加成（来自之前服用的破境丹）
        if player.level_up_rate > 0:
            bonus_rate = player.level_up_rate / 100.0  # 转换为小数
            final_rate += bonus_rate
            info_lines.append(f"破境丹加成：+{player.level_up_rate}%")
        
        # 如果使用了破境丹，添加丹药加成
        if pill_name:
            pills_config = self.config_manager.get_config("pills")
            pill_found = False
            
            # pills_config 可能是字典或列表
            if pills_config:
                if isinstance(pills_config, dict):
                    # 如果是字典，遍历所有值
                    for pill_data in pills_config.values():
                        if isinstance(pill_data, dict) and pill_data.get("name") == pill_name and pill_data.get("subtype") == "breakthrough":
                            pill_bonus = pill_data.get("breakthrough_bonus", 0)
                            pill_max_rate = pill_data.get("max_success_rate", 1.0)
                            
                            if pill_bonus > 0:
                                final_rate += pill_bonus
                                info_lines.append(f"使用【{pill_name}】：+{pill_bonus:.1%}")
                            
                            # 更新最大成功率限制
                            max_rate = pill_max_rate
                            info_lines.append(f"最大成功率：{max_rate:.1%}")
                            pill_found = True
                            break
                elif isinstance(pills_config, list):
                    # 如果是列表，直接遍历
                    for pill_data in pills_config:
                        if pill_data.get("name") == pill_name and pill_data.get("subtype") == "breakthrough":
                            pill_bonus = pill_data.get("breakthrough_bonus", 0)
                            pill_max_rate = pill_data.get("max_success_rate", 1.0)
                            
                            if pill_bonus > 0:
                                final_rate += pill_bonus
                                info_lines.append(f"使用【{pill_name}】：+{pill_bonus:.1%}")
                            
                            # 更新最大成功率限制
                            max_rate = pill_max_rate
                            info_lines.append(f"最大成功率：{max_rate:.1%}")
                            pill_found = True
                            break
        
        final_rate = max(0.0, min(final_rate, max_rate))
        info_lines.append(f"最终成功率：{final_rate:.1%}")
        info = "\n".join(info_lines)
        
        return final_rate, info
    
    def _calculate_death_rate(self) -> float:
        """
        计算突破失败的死亡概率
        
        Returns:
            死亡概率
        """
        # 从配置中获取死亡概率范围
        death_probability_range = self.config_manager.settings.values.breakthrough_death_probability
        
        # 随机一个死亡概率
        death_rate = random.uniform(
            death_probability_range[0],
            death_probability_range[1]
        )
        
        return max(0.0, min(1.0, death_rate))
    
    def _apply_breakthrough_success(
        self,
        player: Player,
        next_level_data: dict
    ) -> dict:
        """
        应用突破成功的属性增长
        
        Args:
            player: 玩家对象
            next_level_data: 下一境界配置数据
            
        Returns:
            属性增长字典
        """
        # 提升境界
        player.level_index += 1
        
        # 获取属性增长
        lifespan_gain = next_level_data.get("breakthrough_lifespan_gain", 0)
        mental_power_gain = next_level_data.get("breakthrough_mental_power_gain", 0)
        physical_damage_gain = next_level_data.get("breakthrough_physical_damage_gain", 0)
        magic_damage_gain = next_level_data.get("breakthrough_magic_damage_gain", 0)
        physical_defense_gain = next_level_data.get("breakthrough_physical_defense_gain", 0)
        magic_defense_gain = next_level_data.get("breakthrough_magic_defense_gain", 0)
        
        # 根据修炼类型处理灵气/气血增长
        if player.cultivation_type == CultivationType.PHYSICAL.value:
            # 体修使用气血
            blood_qi_gain = next_level_data.get("breakthrough_blood_qi_gain", 0)
            player.max_blood_qi += blood_qi_gain
            player.blood_qi = player.max_blood_qi  # 恢复满气血
            energy_name = "气血"
            energy_gain = blood_qi_gain
        else:
            # 灵修使用灵气
            spiritual_qi_gain = next_level_data.get("breakthrough_spiritual_qi_gain", 0)
            player.max_spiritual_qi += spiritual_qi_gain
            player.spiritual_qi = player.max_spiritual_qi  # 恢复满灵气
            energy_name = "灵气"
            energy_gain = spiritual_qi_gain
        
        # 应用属性增长
        player.lifespan += lifespan_gain
        player.physical_damage += physical_damage_gain
        player.magic_damage += magic_damage_gain
        player.physical_defense += physical_defense_gain
        player.magic_defense += magic_defense_gain
        player.mental_power += mental_power_gain
        
        # 返回属性增长信息
        return {
            "lifespan": lifespan_gain,
            "energy_name": energy_name,
            "energy": energy_gain,
            "physical_damage": physical_damage_gain,
            "magic_damage": magic_damage_gain,
            "physical_defense": physical_defense_gain,
            "magic_defense": magic_defense_gain,
            "mental_power": mental_power_gain
        }
