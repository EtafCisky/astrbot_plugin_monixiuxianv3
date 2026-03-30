"""Boss服务"""
import random
import time
from typing import List, Tuple, Optional

from ...core.config import ConfigManager
from ...core.exceptions import GameException
from ...domain.models.boss import Boss, BossLevelConfig, BossBattleResult
from ...domain.enums import PlayerState
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.boss_repo import BossRepository
from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository


class BossService:
    """Boss服务"""
    
    # Boss境界配置
    BOSS_LEVELS = [
        {"name": "练气", "level_index": 0, "hp_mult": 1.0, "atk_mult": 1.0, "reward_mult": 1.0},
        {"name": "筑基", "level_index": 3, "hp_mult": 1.5, "atk_mult": 1.2, "reward_mult": 1.5},
        {"name": "金丹", "level_index": 6, "hp_mult": 2.0, "atk_mult": 1.5, "reward_mult": 2.0},
        {"name": "元婴", "level_index": 9, "hp_mult": 2.5, "atk_mult": 1.8, "reward_mult": 2.5},
        {"name": "化神", "level_index": 12, "hp_mult": 3.0, "atk_mult": 2.0, "reward_mult": 3.0},
        {"name": "炼虚", "level_index": 15, "hp_mult": 4.0, "atk_mult": 2.5, "reward_mult": 4.0},
        {"name": "合体", "level_index": 18, "hp_mult": 5.0, "atk_mult": 3.0, "reward_mult": 5.0},
        {"name": "大乘", "level_index": 21, "hp_mult": 6.0, "atk_mult": 3.5, "reward_mult": 6.0},
    ]
    
    # Boss名称池
    BOSS_NAMES = [
        "血魔", "邪修", "魔头", "妖王", "魔君",
        "异兽", "凶兽", "妖尊", "魔尊", "邪帝",
        "天魔", "地魔", "魔神", "妖神", "邪神"
    ]
    
    # Boss物品掉落表
    BOSS_DROP_TABLE = {
        "low": [  # 低级Boss (练气-金丹)
            {"name": "灵兽内丹", "weight": 40, "min": 1, "max": 2},
            {"name": "妖兽精血", "weight": 30, "min": 1, "max": 3},
            {"name": "玄铁", "weight": 30, "min": 3, "max": 6},
        ],
        "mid": [  # 中级Boss (元婴-化神)
            {"name": "灵兽内丹", "weight": 30, "min": 2, "max": 4},
            {"name": "星辰石", "weight": 25, "min": 2, "max": 4},
            {"name": "天材地宝", "weight": 45, "min": 1, "max": 2},
        ],
        "high": [  # 高级Boss (炼虚及以上)
            {"name": "天材地宝", "weight": 30, "min": 2, "max": 4},
            {"name": "混沌精华", "weight": 25, "min": 1, "max": 2},
            {"name": "神兽之骨", "weight": 20, "min": 1, "max": 1},
            {"name": "远古秘籍", "weight": 15, "min": 1, "max": 1},
            {"name": "仙器碎片", "weight": 10, "min": 1, "max": 1},
        ],
    }
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        boss_repo: BossRepository,
        storage_ring_repo: StorageRingRepository,
        config_manager: ConfigManager
    ):
        self.player_repo = player_repo
        self.boss_repo = boss_repo
        self.storage_ring_repo = storage_ring_repo
        self.config_manager = config_manager
    
    def get_active_boss(self) -> Optional[Boss]:
        """获取当前存活的Boss"""
        return self.boss_repo.get_active_boss()
    
    def spawn_boss(
        self,
        base_exp: int = 100000,
        level_config: Optional[dict] = None
    ) -> Boss:
        """
        生成Boss
        
        Args:
            base_exp: 基础修为（用于计算属性）
            level_config: Boss等级配置，如果为None则随机选择
            
        Returns:
            Boss对象
        """
        # 检查是否已有存活的Boss
        existing_boss = self.boss_repo.get_active_boss()
        if existing_boss:
            raise GameException(f"当前已有Boss『{existing_boss.boss_name}』存在！")
        
        # 选择Boss等级
        if not level_config:
            level_config = random.choice(self.BOSS_LEVELS)
        
        # 生成Boss名称
        boss_name = random.choice(self.BOSS_NAMES) + f"·{level_config['name']}境"
        
        # 计算Boss属性
        hp_mult = level_config["hp_mult"]
        atk_mult = level_config["atk_mult"]
        reward_mult = level_config["reward_mult"]
        
        # Boss的HP和ATK基于修为计算
        max_hp = int(base_exp * hp_mult // 2)
        atk = int(base_exp * atk_mult // 10)
        
        # 灵石奖励
        stone_reward = int(base_exp * reward_mult // 10)
        
        # Boss防御力（高境界Boss有减伤）
        defense = 0
        if level_config["level_index"] >= 15:  # 炼虚及以上
            defense = random.randint(40, 90)  # 40%-90%减伤
        
        # 创建Boss
        boss = Boss(
            boss_id=0,  # 自动生成
            boss_name=boss_name,
            boss_level=level_config["name"],
            hp=max_hp,
            max_hp=max_hp,
            atk=atk,
            defense=defense,
            stone_reward=stone_reward,
            create_time=int(time.time()),
            status=1  # 1=存活
        )
        
        boss_id = self.boss_repo.create_boss(boss)
        boss.boss_id = boss_id
        
        return boss
    
    def challenge_boss(self, user_id: str) -> BossBattleResult:
        """
        挑战Boss
        
        Args:
            user_id: 挑战者ID
            
        Returns:
            战斗结果
        """
        # 1. 检查玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 2. 检查Boss是否存在
        boss = self.boss_repo.get_active_boss()
        if not boss:
            raise GameException("当前没有Boss")
        
        # 3. 检查玩家状态
        if player.state != PlayerState.IDLE:
            raise GameException("你当前正忙，无法挑战Boss")
        
        # 4. 计算玩家战斗属性
        player_hp = player.hp if player.hp > 0 else int(player.experience // 2)
        player_mp = player.mp if player.mp > 0 else int(player.experience)
        player_atk = player.atk if player.atk > 0 else int(player.experience // 10)
        
        # 5. 开始战斗
        combat_log = []
        rounds = 0
        max_rounds = 50
        
        boss_hp = boss.hp
        boss_atk = boss.atk
        boss_defense = boss.defense
        
        while rounds < max_rounds and player_hp > 0 and boss_hp > 0:
            rounds += 1
            
            # 玩家攻击
            player_damage = player_atk
            # 暴击判断
            if random.randint(1, 100) <= 20:  # 20%暴击率
                player_damage = int(player_damage * 1.5)
                combat_log.append(f"第{rounds}回合：你发动暴击，造成 {player_damage} 点伤害！")
            else:
                combat_log.append(f"第{rounds}回合：你攻击Boss，造成 {player_damage} 点伤害")
            
            # Boss减伤
            if boss_defense > 0:
                actual_damage = int(player_damage * (100 - boss_defense) / 100)
                combat_log.append(f"  Boss防御减免 {boss_defense}%，实际伤害 {actual_damage}")
                boss_hp -= actual_damage
            else:
                boss_hp -= player_damage
            
            if boss_hp <= 0:
                combat_log.append(f"  Boss被击败！")
                break
            
            # Boss攻击
            boss_damage = boss_atk
            # Boss暴击判断
            if random.randint(1, 100) <= 30:  # Boss 30%暴击率
                boss_damage = int(boss_damage * 1.5)
                combat_log.append(f"  Boss发动暴击，对你造成 {boss_damage} 点伤害！")
            else:
                combat_log.append(f"  Boss攻击你，造成 {boss_damage} 点伤害")
            
            player_hp -= boss_damage
            
            if player_hp <= 0:
                combat_log.append(f"  你被击败了...")
                break
        
        # 6. 处理战斗结果
        player_hp = max(0, player_hp)
        boss_hp = max(0, boss_hp)
        
        winner_id = user_id if boss_hp <= 0 else str(boss.boss_id)
        boss_defeated = boss_hp <= 0
        
        # 计算奖励
        if boss_defeated:
            # 玩家胜利，获得全额奖励
            stone_reward = boss.stone_reward
            # 更新Boss状态
            self.boss_repo.defeat_boss(boss.boss_id)
            # 物品掉落
            items_gained = self._roll_boss_drops(boss)
        else:
            # 玩家失败，获得安慰奖
            stone_reward = boss.stone_reward // 10
            # 更新Boss HP
            boss.hp = boss_hp
            self.boss_repo.update_boss(boss)
            items_gained = []
        
        # 发放灵石奖励
        self.player_repo.add_gold(user_id, stone_reward)
        
        # 发放物品奖励
        for item_name, count in items_gained:
            self.storage_ring_repo.add_item(user_id, item_name, count)
        
        # 更新玩家HP/MP（注意：这里简化处理，实际应该更新玩家对象）
        # 由于 PlayerRepository 没有 update_player_combat_stats 方法
        # 我们需要获取玩家对象，更新属性，然后保存
        player.hp = player_hp
        player.mp = player_mp
        self.player_repo.save(player)
        
        return BossBattleResult(
            success=boss_defeated,
            winner_id=winner_id,
            rounds=rounds,
            player_final_hp=player_hp,
            player_final_mp=player_mp,
            boss_final_hp=boss_hp,
            stone_reward=stone_reward,
            items_gained=items_gained,
            combat_log=combat_log,
            boss_defeated=boss_defeated
        )
    
    def auto_spawn_boss(self) -> Boss:
        """
        自动生成Boss（定时任务使用）
        根据服务器玩家数量和平均等级自动调整Boss难度
        
        Returns:
            Boss对象
        """
        # 检查是否已有Boss
        existing_boss = self.boss_repo.get_active_boss()
        if existing_boss:
            raise GameException("当前已有Boss存在")
        
        # 获取所有玩家的平均等级
        # 这里简化处理，使用固定值
        # 实际应该查询所有玩家的平均修为
        base_exp = 100000
        level_config = random.choice(self.BOSS_LEVELS)
        
        return self.spawn_boss(base_exp, level_config)
    
    def _roll_boss_drops(self, boss: Boss) -> List[Tuple[str, int]]:
        """
        根据Boss等级随机掉落物品
        
        Args:
            boss: Boss对象
            
        Returns:
            掉落物品列表 [(物品名, 数量), ...]
        """
        dropped_items = []
        
        # 根据Boss等级确定掉落表
        boss_level_index = 0
        for level in self.BOSS_LEVELS:
            if level["name"] == boss.boss_level:
                boss_level_index = level["level_index"]
                break
        
        if boss_level_index <= 6:  # 练气-金丹
            drop_table = self.BOSS_DROP_TABLE["low"]
        elif boss_level_index <= 12:  # 元婴-化神
            drop_table = self.BOSS_DROP_TABLE["mid"]
        else:  # 炼虚及以上
            drop_table = self.BOSS_DROP_TABLE["high"]
        
        # Boss击杀100%掉落至少1件物品
        total_weight = sum(item["weight"] for item in drop_table)
        roll = random.randint(1, total_weight)
        
        current_weight = 0
        for item in drop_table:
            current_weight += item["weight"]
            if roll <= current_weight:
                count = random.randint(item["min"], item["max"])
                dropped_items.append((item["name"], count))
                break
        
        # 高级Boss有70%概率额外掉落
        if boss_level_index >= 9:  # 元婴及以上
            extra_chance = 50 if boss_level_index < 15 else 70
            if random.randint(1, 100) <= extra_chance:
                roll = random.randint(1, total_weight)
                current_weight = 0
                for item in drop_table:
                    current_weight += item["weight"]
                    if roll <= current_weight:
                        count = random.randint(item["min"], item["max"])
                        dropped_items.append((item["name"], count))
                        break
        
        return dropped_items

