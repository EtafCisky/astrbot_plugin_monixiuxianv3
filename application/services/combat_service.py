"""战斗业务服务"""
import random
import time
import json
from typing import Tuple, Optional

from ...domain.models.combat import CombatStats, CombatTurn, CombatResult, CombatCooldown
from ...domain.models.player import Player
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.combat_repo import CombatRepository
from ...core.config import ConfigManager


class CombatService:
    """战斗业务服务"""
    
    # 战斗冷却配置（秒）
    DUEL_COOLDOWN = 300  # 决斗冷却5分钟
    SPAR_COOLDOWN = 60   # 切磋冷却1分钟
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        combat_repo: CombatRepository,
        config_manager: ConfigManager
    ):
        self.player_repo = player_repo
        self.combat_repo = combat_repo
        self.config_manager = config_manager
    
    @staticmethod
    def calculate_hp_mp(experience: int, hp_buff: float = 0.0, mp_buff: float = 0.0) -> Tuple[int, int]:
        """
        根据修为计算HP和MP
        
        Args:
            experience: 修为
            hp_buff: HP加成百分比
            mp_buff: MP加成百分比
            
        Returns:
            (hp, mp) 元组
        """
        base_hp = experience // 2
        base_mp = experience
        
        hp = int(base_hp * (1 + hp_buff))
        mp = int(base_mp * (1 + mp_buff))
        
        return max(hp, 100), max(mp, 100)  # 最小值100
    
    @staticmethod
    def calculate_atk(experience: int, atkpractice: int = 0, atk_buff: float = 0.0) -> int:
        """
        根据修为和攻击修炼等级计算攻击力
        
        Args:
            experience: 修为
            atkpractice: 攻击修炼等级（每级提升4%攻击力）
            atk_buff: 额外攻击加成百分比
            
        Returns:
            攻击力
        """
        base_atk = experience // 10
        practice_bonus = atkpractice * 0.04  # 每级4%加成
        total_atk = int(base_atk * (1 + practice_bonus + atk_buff))
        
        return max(total_atk, 10)  # 至少为10
    
    @staticmethod
    def calculate_turn_attack(
        base_atk: int,
        crit_rate: int = 0,
        atk_buff: float = 0.0
    ) -> Tuple[bool, int]:
        """
        计算单回合攻击伤害
        
        Args:
            base_atk: 基础攻击力
            crit_rate: 会心率（百分比，0-100）
            atk_buff: 攻击加成（技能buff等）
            
        Returns:
            (是否暴击, 伤害值) 元组
        """
        # 攻击波动 95%-105%
        damage = int(round(random.uniform(0.95, 1.05), 2) * base_atk * (1 + atk_buff))
        
        # 会心判定
        is_crit = random.randint(0, 100) <= crit_rate
        if is_crit:
            damage = int(damage * 1.5)  # 会心伤害1.5倍
        
        return is_crit, max(damage, 1)
    
    @staticmethod
    def apply_damage_reduction(damage: int, defense: int = 0) -> int:
        """
        应用伤害减免（使用递减公式）
        
        Args:
            damage: 原始伤害
            defense: 防御力
            
        Returns:
            减免后的伤害
        """
        if defense <= 0:
            return damage
        reduction_rate = defense / (defense + 100)
        final_damage = int(damage * (1 - reduction_rate))
        return max(1, final_damage)
    
    def _calculate_equipment_bonus(self, player: Player) -> dict:
        """计算装备提供的属性加成"""
        bonus = {"atk": 0, "defense": 0}
        
        # 使用装备服务获取装备加成
        from .equipment_service import EquipmentService
        from ...infrastructure.repositories.equipment_repo import EquipmentRepository
        from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository
        
        equipment_repo = EquipmentRepository(self.player_repo.storage, self.config_manager.config_dir)
        storage_ring_repo = StorageRingRepository(self.player_repo.storage)
        
        equipment_service = EquipmentService(
            equipment_repo,
            self.player_repo,
            storage_ring_repo
        )
        equipment_bonuses = equipment_service.get_equipment_bonuses(player.user_id)
        
        # 攻击力 = 物理攻击 + 法术攻击
        bonus["atk"] = equipment_bonuses.physical_damage + equipment_bonuses.magic_damage
        
        # 防御力 = 物理防御 + 法术防御
        bonus["defense"] = equipment_bonuses.physical_defense + equipment_bonuses.magic_defense
        
        return bonus
    
    async def prepare_combat_stats(self, user_id: str) -> Optional[CombatStats]:
        """
        准备战斗属性
        
        Args:
            user_id: 用户ID
            
        Returns:
            战斗属性，如果玩家不存在返回None
        """
        player = self.player_repo.get_by_id(user_id)
        if not player:
            return None
        
        # 计算基础属性
        # TODO: 获取传承加成（需要传承系统）
        hp_buff = 0.0
        mp_buff = 0.0
        atk_buff = 0.0
        
        hp, mp = self.calculate_hp_mp(player.experience, hp_buff, mp_buff)
        base_atk = self.calculate_atk(player.experience, 0, atk_buff)  # TODO: atkpractice
        
        # 加上装备加成
        equip_bonus = self._calculate_equipment_bonus(player)
        final_atk = base_atk + equip_bonus["atk"]
        
        return CombatStats(
            user_id=user_id,
            name=player.nickname if player.nickname else f"道友{user_id[:6]}",
            hp=hp,
            max_hp=hp,
            mp=mp,
            max_mp=mp,
            atk=final_atk,
            defense=equip_bonus["defense"],
            crit_rate=0,  # TODO: 从装备/技能获取
            exp=player.experience
        )
    
    async def check_combat_cooldown(
        self,
        user_id: str,
        combat_type: str
    ) -> Tuple[bool, int]:
        """
        检查战斗冷却
        
        Args:
            user_id: 用户ID
            combat_type: 战斗类型（duel/spar）
            
        Returns:
            (是否可以战斗, 剩余冷却时间) 元组
        """
        cooldown = self.combat_repo.get_combat_cooldown(user_id)
        if not cooldown:
            return True, 0
        
        current_time = int(time.time())
        
        if combat_type == "duel":
            can_fight = cooldown.can_duel(current_time, self.DUEL_COOLDOWN)
            remaining = cooldown.get_duel_remaining(current_time, self.DUEL_COOLDOWN)
        else:  # spar
            can_fight = cooldown.can_spar(current_time, self.SPAR_COOLDOWN)
            remaining = cooldown.get_spar_remaining(current_time, self.SPAR_COOLDOWN)
        
        return can_fight, remaining
    
    async def update_combat_cooldown(self, user_id: str, combat_type: str):
        """
        更新战斗冷却
        
        Args:
            user_id: 用户ID
            combat_type: 战斗类型（duel/spar）
        """
        current_time = int(time.time())
        
        if combat_type == "duel":
            self.combat_repo.update_duel_cooldown(user_id, current_time)
        else:  # spar
            self.combat_repo.update_spar_cooldown(user_id, current_time)
    
    def player_vs_player(
        self,
        player1: CombatStats,
        player2: CombatStats,
        combat_type: str = "spar"
    ) -> CombatResult:
        """
        玩家vs玩家战斗
        
        Args:
            player1: 玩家1战斗属性
            player2: 玩家2战斗属性
            combat_type: 战斗类型（spar=切磋不消耗HP/MP，duel=决斗消耗HP/MP）
            
        Returns:
            战斗结果
        """
        combat_log = []
        combat_log.append(f"☆━━━━ 战斗开始 ━━━━☆")
        combat_log.append(f"{player1.name} VS {player2.name}")
        combat_log.append(f"{player1.name}：HP {player1.hp}/{player1.max_hp}，ATK {player1.atk}")
        combat_log.append(f"{player2.name}：HP {player2.hp}/{player2.max_hp}，ATK {player2.atk}")
        combat_log.append("")
        
        round_num = 0
        max_rounds = 100  # 最大回合数，防止无限循环
        
        while player1.is_alive() and player2.is_alive() and round_num < max_rounds:
            round_num += 1
            combat_log.append(f"-- 第 {round_num} 回合 --")
            
            # 玩家1攻击
            is_crit1, damage1 = self.calculate_turn_attack(player1.atk, player1.crit_rate)
            damage1 = self.apply_damage_reduction(damage1, player2.defense)
            player2.take_damage(damage1)
            
            turn1 = CombatTurn(
                round_num=round_num,
                attacker_name=player1.name,
                defender_name=player2.name,
                damage=damage1,
                is_crit=is_crit1,
                defender_hp_remaining=player2.hp
            )
            combat_log.append(turn1.to_log_message())
            combat_log.append(f"{player2.name} 剩余 HP: {player2.hp}")
            
            if not player2.is_alive():
                break
            
            # 玩家2攻击
            is_crit2, damage2 = self.calculate_turn_attack(player2.atk, player2.crit_rate)
            damage2 = self.apply_damage_reduction(damage2, player1.defense)
            player1.take_damage(damage2)
            
            turn2 = CombatTurn(
                round_num=round_num,
                attacker_name=player2.name,
                defender_name=player1.name,
                damage=damage2,
                is_crit=is_crit2,
                defender_hp_remaining=player1.hp
            )
            combat_log.append(turn2.to_log_message())
            combat_log.append(f"{player1.name} 剩余 HP: {player1.hp}")
            combat_log.append("")
        
        # 判断胜负
        if player1.is_alive() and not player2.is_alive():
            winner_id = player1.user_id
            winner_name = player1.name
            combat_log.append(f"☆━━━━ {player1.name} 胜利！━━━━☆")
        elif player2.is_alive() and not player1.is_alive():
            winner_id = player2.user_id
            winner_name = player2.name
            combat_log.append(f"☆━━━━ {player2.name} 胜利！━━━━☆")
        else:
            winner_id = None
            winner_name = "平局"
            combat_log.append(f"☆━━━━ 平局！━━━━☆")
        
        # 如果是切磋，不消耗HP/MP
        if combat_type == "spar":
            player1_final_hp = player1.max_hp
            player1_final_mp = player1.max_mp
            player2_final_hp = player2.max_hp
            player2_final_mp = player2.max_mp
        else:  # duel
            # 决斗消耗HP/MP，战败者HP降为1
            player1_final_hp = max(1, player1.hp)
            player1_final_mp = player1.mp
            player2_final_hp = max(1, player2.hp)
            player2_final_mp = player2.mp
        
        return CombatResult(
            winner_id=winner_id,
            winner_name=winner_name,
            combat_log=combat_log,
            rounds=round_num,
            player1_final_hp=player1_final_hp,
            player1_final_mp=player1_final_mp,
            player2_final_hp=player2_final_hp,
            player2_final_mp=player2_final_mp
        )
    
    async def execute_spar(
        self,
        attacker_id: str,
        defender_id: str
    ) -> CombatResult:
        """
        执行切磋（不消耗HP/MP）
        
        Args:
            attacker_id: 攻击者ID
            defender_id: 防御者ID
            
        Returns:
            战斗结果
        """
        # 准备战斗属性
        attacker_stats = await self.prepare_combat_stats(attacker_id)
        defender_stats = await self.prepare_combat_stats(defender_id)
        
        if not attacker_stats or not defender_stats:
            raise ValueError("玩家不存在")
        
        # 执行战斗
        result = self.player_vs_player(attacker_stats, defender_stats, "spar")
        
        # 保存战斗日志
        self.combat_repo.save_combat_log(
            attacker_id=attacker_id,
            defender_id=defender_id,
            combat_type="spar",
            winner_id=result.winner_id,
            combat_log=json.dumps(result.combat_log, ensure_ascii=False)
        )
        
        # 更新冷却
        await self.update_combat_cooldown(attacker_id, "spar")
        
        return result
    
    async def execute_duel(
        self,
        attacker_id: str,
        defender_id: str
    ) -> CombatResult:
        """
        执行决斗（消耗HP/MP）
        
        Args:
            attacker_id: 攻击者ID
            defender_id: 防御者ID
            
        Returns:
            战斗结果
        """
        # 准备战斗属性
        attacker_stats = await self.prepare_combat_stats(attacker_id)
        defender_stats = await self.prepare_combat_stats(defender_id)
        
        if not attacker_stats or not defender_stats:
            raise ValueError("玩家不存在")
        
        # 执行战斗
        result = self.player_vs_player(attacker_stats, defender_stats, "duel")
        
        # 更新玩家HP/MP
        attacker = self.player_repo.get_by_id(attacker_id)
        defender = self.player_repo.get_by_id(defender_id)
        
        attacker.hp = result.player1_final_hp
        attacker.mp = result.player1_final_mp
        defender.hp = result.player2_final_hp
        defender.mp = result.player2_final_mp
        
        self.player_repo.save(attacker)
        self.player_repo.save(defender)
        
        # 保存战斗日志
        self.combat_repo.save_combat_log(
            attacker_id=attacker_id,
            defender_id=defender_id,
            combat_type="duel",
            winner_id=result.winner_id,
            combat_log=json.dumps(result.combat_log, ensure_ascii=False)
        )
        
        # 更新冷却
        await self.update_combat_cooldown(attacker_id, "duel")
        
        return result
