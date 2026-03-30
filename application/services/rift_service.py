"""秘境服务"""
import json
import random
import time
from typing import List, Tuple, Optional

from ...core.config import ConfigManager
from ...core.exceptions import GameException
from ...domain.models.rift import Rift, RiftEvent, RiftResult
from ...domain.enums import PlayerState
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.rift_repo import RiftRepository
from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository


class RiftService:
    """秘境服务"""
    
    # 默认探索时长（秒）
    DEFAULT_DURATION = 1800  # 30分钟
    
    # 秘境物品掉落表（按秘境等级分组）
    RIFT_DROP_TABLE = {
        1: [  # 低级秘境
            {"name": "灵草", "weight": 40, "min": 2, "max": 5},
            {"name": "精铁", "weight": 30, "min": 1, "max": 3},
            {"name": "灵石碎片", "weight": 20, "min": 3, "max": 8},
            {"name": "稀有掉落", "weight": 10, "min": 1, "max": 1},  # 这是类别，会触发二级掉落
        ],
        2: [  # 中级秘境
            {"name": "灵草", "weight": 30, "min": 3, "max": 7},
            {"name": "玄铁", "weight": 25, "min": 2, "max": 4},
            {"name": "灵兽毛皮", "weight": 20, "min": 1, "max": 3},
            {"name": "秘境精华", "weight": 10, "min": 1, "max": 2},
            {"name": "稀有掉落", "weight": 15, "min": 1, "max": 1},  # 这是类别，会触发二级掉落
        ],
        3: [  # 高级秘境
            {"name": "玄铁", "weight": 25, "min": 3, "max": 6},
            {"name": "星辰石", "weight": 20, "min": 2, "max": 4},
            {"name": "灵兽内丹", "weight": 20, "min": 1, "max": 2},
            {"name": "稀有掉落", "weight": 35, "min": 1, "max": 1},  # 这是类别，会触发二级掉落（增加权重）
        ],
    }
    
    # 稀有掉落子类别（按秘境等级分组）
    # 包含：天材地宝、炼器材料、法器、功法
    RARE_DROP_SUBTYPES = {
        1: {  # 低级秘境 - 凡品
            "天材地宝": [
                {"name": "百年灵芝", "weight": 35},
                {"name": "紫玉参", "weight": 30},
                {"name": "青莲子", "weight": 25},
                {"name": "赤血果", "weight": 10},
            ],
            "炼器材料": [
                {"name": "寒铁精", "weight": 40},
                {"name": "赤铜矿", "weight": 35},
                {"name": "灵木芯", "weight": 25},
            ],
            "法器": [
                {"name": "青锋剑", "weight": 50},
                {"name": "玄铁甲", "weight": 50},
            ],
            "功法": [
                {"name": "长春功残篇", "weight": 70},
                {"name": "御风诀残篇", "weight": 28},
                {"name": "长春功", "weight": 1},  # 完整功法，极低概率（5个残篇合成）
                {"name": "御风诀", "weight": 1},  # 完整功法，极低概率（5个残篇合成）
            ],
        },
        2: {  # 中级秘境 - 珍品
            "天材地宝": [
                {"name": "千年灵芝", "weight": 30},
                {"name": "九转仙草", "weight": 25},
                {"name": "龙血果", "weight": 20},
                {"name": "凤凰羽", "weight": 15},
                {"name": "玄冰莲", "weight": 10},
            ],
            "炼器材料": [
                {"name": "紫金沙", "weight": 35},
                {"name": "星辉晶砂", "weight": 30},
                {"name": "赤炎石", "weight": 25},
                {"name": "月光粉尘", "weight": 10},
            ],
            "法器": [
                {"name": "烈阳刀", "weight": 40},
                {"name": "月华袍", "weight": 40},
                {"name": "镇魂幡", "weight": 20},
            ],
            "功法": [
                {"name": "不动明王经残篇", "weight": 50},
                {"name": "北冥神功残篇", "weight": 30},
                {"name": "九阳神功残篇", "weight": 17},
                {"name": "不动明王经", "weight": 1},  # 完整功法（10个残篇合成）
                {"name": "北冥神功", "weight": 1},  # 完整功法（10个残篇合成）
                {"name": "九阳神功", "weight": 1},  # 完整功法（10个残篇合成）
            ],
        },
        3: {  # 高级秘境 - 圣品/帝品
            "天材地宝": [
                {"name": "万年灵芝王", "weight": 25},
                {"name": "九天息壤", "weight": 20},
                {"name": "太阳神果", "weight": 18},
                {"name": "太阴神花", "weight": 18},
                {"name": "混沌青莲", "weight": 12},
                {"name": "不死神药", "weight": 7},
            ],
            "炼器材料": [
                {"name": "玄冰之核", "weight": 30},
                {"name": "龙骨髓", "weight": 25},
                {"name": "凤凰真羽", "weight": 20},
                {"name": "星辰陨铁", "weight": 15},
                {"name": "混沌神石", "weight": 10},
            ],
            "法器": [
                {"name": "寒霜剑", "weight": 35},
                {"name": "泰坦之铠", "weight": 30},
                {"name": "妖精之弓", "weight": 25},
                {"name": "戮仙剑阵", "weight": 8},
                {"name": "弑神枪", "weight": 2},
            ],
            "功法": [
                {"name": "焚天诀残篇", "weight": 40},
                {"name": "道经残篇", "weight": 30},
                {"name": "吞天魔功残篇", "weight": 20},
                {"name": "他化自在大法残篇", "weight": 9},
                {"name": "焚天诀", "weight": 0.4},  # 完整功法（15个残篇合成）
                {"name": "道经", "weight": 0.3},  # 完整帝品功法（15个残篇合成）
                {"name": "吞天魔功", "weight": 0.2},  # 完整功法（15个残篇合成）
                {"name": "他化自在大法", "weight": 0.1},  # 完整功法（15个残篇合成）
            ],
        },
    }
    
    # 功法残篇合成配置
    TECHNIQUE_SYNTHESIS = {
        # 凡品功法 - 5个残篇合成
        "长春功": {"fragment": "长春功残篇", "required": 5, "tier": "凡品"},
        "御风诀": {"fragment": "御风诀残篇", "required": 5, "tier": "凡品"},
        # 珍品功法 - 10个残篇合成
        "不动明王经": {"fragment": "不动明王经残篇", "required": 10, "tier": "珍品"},
        "北冥神功": {"fragment": "北冥神功残篇", "required": 10, "tier": "珍品"},
        "九阳神功": {"fragment": "九阳神功残篇", "required": 10, "tier": "珍品"},
        # 圣品/帝品功法 - 15个残篇合成
        "焚天诀": {"fragment": "焚天诀残篇", "required": 15, "tier": "圣品"},
        "道经": {"fragment": "道经残篇", "required": 15, "tier": "帝品"},
        "吞天魔功": {"fragment": "吞天魔功残篇", "required": 15, "tier": "圣品"},
        "他化自在大法": {"fragment": "他化自在大法残篇", "required": 15, "tier": "圣品"},
    }
    
    # 稀有掉落类别权重（决定掉落哪个类别）
    RARE_DROP_CATEGORY_WEIGHTS = {
        1: {"天材地宝": 40, "炼器材料": 35, "法器": 20, "功法": 5},
        2: {"天材地宝": 35, "炼器材料": 30, "法器": 25, "功法": 10},
        3: {"天材地宝": 30, "炼器材料": 25, "法器": 30, "功法": 15},
    }
    
    # 秘境稀有丹药掉落表（按秘境等级分组）
    RIFT_PILL_DROP_TABLE = {
        1: [  # 低级秘境 - 3%概率掉落
            {"name": "三品凝神增益丹", "weight": 100, "min": 1, "max": 1},
        ],
        2: [  # 中级秘境 - 5%概率掉落
            {"name": "三品凝神增益丹", "weight": 50, "min": 1, "max": 1},
            {"name": "四品破境增益丹", "weight": 40, "min": 1, "max": 1},
            {"name": "五品渡劫增益丹", "weight": 10, "min": 1, "max": 1},
        ],
        3: [  # 高级秘境 - 10%概率掉落
            {"name": "四品破境增益丹", "weight": 40, "min": 1, "max": 1},
            {"name": "五品渡劫增益丹", "weight": 30, "min": 1, "max": 1},
            {"name": "六品破境增益丹", "weight": 20, "min": 1, "max": 1},
            {"name": "七品化神增益丹", "weight": 10, "min": 1, "max": 1},
        ],
    }
    
    # 秘境丹药掉落概率（百分比）
    RIFT_PILL_DROP_CHANCE = {
        1: 3,   # 低级秘境 3%
        2: 5,   # 中级秘境 5%
        3: 10,  # 高级秘境 10%
    }
    
    # 秘境事件列表
    RIFT_EVENTS = [
        {"desc": "你发现了一处灵泉，修为大增！", "item_chance": 70},
        {"desc": "你在秘境中击败了一只妖兽！", "item_chance": 80},
        {"desc": "你找到了一个隐藏的宝箱！", "item_chance": 100},
        {"desc": "你领悟了一些修炼心得。", "item_chance": 40},
        {"desc": "你在秘境中遇到了前辈留下的传承！", "item_chance": 90}
    ]
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        rift_repo: RiftRepository,
        storage_ring_repo: StorageRingRepository,
        config_manager: ConfigManager,
        bounty_repo=None  # 添加可选的悬赏仓储
    ):
        self.player_repo = player_repo
        self.rift_repo = rift_repo
        self.storage_ring_repo = storage_ring_repo
        self.config_manager = config_manager
        self.bounty_repo = bounty_repo  # 保存悬赏仓储引用
        self.explore_duration = self.DEFAULT_DURATION
    
    def get_all_rifts(self) -> List[Rift]:
        """获取所有秘境"""
        return self.rift_repo.get_all_rifts()
    
    def enter_rift(self, user_id: str, rift_id: int) -> str:
        """进入秘境"""
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 检查状态
        if player.state != PlayerState.IDLE:
            raise GameException("你当前无法探索秘境")
        
        # 获取秘境
        rift = self.rift_repo.get_rift_by_id(rift_id)
        if not rift:
            raise GameException("秘境不存在！使用【秘境列表】查看可用秘境")
        
        # 检查境界要求
        if player.level_index < rift.required_level:
            level_name = self._get_level_name(rift.required_level)
            raise GameException(f"探索【{rift.rift_name}】需要达到【{level_name}】！")
        
        # 设置探索状态
        start_time = int(time.time())
        end_time = start_time + self.explore_duration
        
        extra_data = {
            "rift_id": rift_id,
            "rift_level": rift.rift_level,
            "start_time": start_time,
            "end_time": end_time
        }
        
        self.player_repo.update_player_state(
            user_id,
            state=PlayerState.IN_RIFT.value,
            extra_data=json.dumps(extra_data)
        )
        
        return f"✨ 你进入了『{rift.rift_name}』！探索需要 {self.explore_duration//60} 分钟。\n使用【完成探索】领取奖励"
    
    def finish_exploration(self, user_id: str) -> RiftResult:
        """完成秘境探索"""
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        if player.state != PlayerState.IN_RIFT:
            raise GameException("你当前不在探索秘境")
        
        # 解析状态数据
        state_data = self.player_repo.get_player_state(user_id)
        if not state_data or not state_data.extra_data:
            raise GameException("秘境数据异常")
        
        extra_data = json.loads(state_data.extra_data)
        rift_id = extra_data.get("rift_id")
        rift_level = extra_data.get("rift_level", 1)
        end_time = extra_data.get("end_time", 0)
        
        # 检查是否完成
        current_time = int(time.time())
        if current_time < end_time:
            remaining = end_time - current_time
            minutes = remaining // 60
            raise GameException(f"探索尚未完成！还需要 {minutes} 分钟")
        
        # 获取秘境
        rift = self.rift_repo.get_rift_by_id(rift_id) if rift_id else None
        rift_name = rift.rift_name if rift else "未知秘境"
        
        # 计算死亡率
        death_occurred = False
        death_penalty = None
        
        if rift:
            death_rate = self._calculate_death_rate(player.level_index, rift)
            
            # 判断是否死亡
            if random.random() * 100 < death_rate:
                death_occurred = True
                
                # 死亡惩罚：直接删除角色（销号）
                self.player_repo.delete(user_id)
                
                death_penalty = {
                    "account_deleted": True
                }
                
                return RiftResult(
                    success=False,
                    rift_name=rift_name,
                    exp_gained=0,
                    gold_gained=0,
                    items_gained=[],
                    event_description=f"💀 你在『{rift_name}』中遭遇不测，道消身陨！（死亡率：{death_rate:.1f}%）\n你的修仙之路就此终结...",
                    death_occurred=True,
                    death_penalty=death_penalty
                )
        
        # 计算奖励
        if rift:
            exp_reward = random.randint(rift.exp_reward_min, rift.exp_reward_max)
            gold_reward = random.randint(rift.gold_reward_min, rift.gold_reward_max)
            rift_level = rift.rift_level
        else:
            # 兼容旧数据
            exp_reward = random.randint(1000, 5000)
            gold_reward = random.randint(500, 2000)
        
        # 随机事件
        event = random.choice(self.RIFT_EVENTS)
        
        # 物品掉落
        items_gained = self._roll_rift_drops(player, rift_level, event["item_chance"])
        
        # 重新加载玩家以获取最新数据
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        # 发放奖励
        player.add_gold(gold_reward)
        player.add_experience(exp_reward)
        
        # 发放物品
        synthesis_messages = []
        for item_name, count in items_gained:
            # 所有物品（包括丹药）都存入储物戒
            if item_name in player.storage_ring_items:
                player.storage_ring_items[item_name] += count
            else:
                player.storage_ring_items[item_name] = count
            
            # 检查是否触发功法残篇合成
            for technique_name, config in self.storage_ring_repo.TECHNIQUE_SYNTHESIS.items():
                fragment_name = config["fragment"]
                required_count = config["required"]
                
                if item_name == fragment_name:
                    current_count = player.storage_ring_items.get(fragment_name, 0)
                    
                    if current_count >= required_count:
                        # 消耗残篇
                        player.storage_ring_items[fragment_name] = current_count - required_count
                        if player.storage_ring_items[fragment_name] == 0:
                            del player.storage_ring_items[fragment_name]
                        
                        # 添加完整功法
                        player.storage_ring_items[technique_name] = player.storage_ring_items.get(technique_name, 0) + 1
                        
                        # 获取功法品质
                        tier = config.get("tier", "未知")
                        synthesis_messages.append(f"✨ 恭喜！你集齐了残篇，自动合成了【{tier}】功法《{technique_name}》！")
                        break
        
        # 保存玩家（包含所有更新）
        self.player_repo.save(player)
        
        # 重置状态
        self.player_repo.update_player_state(user_id, state=PlayerState.IDLE.value, extra_data=None)
        
        # 更新悬赏进度
        if self.bounty_repo and rift:
            try:
                self._update_bounty_progress(user_id, rift)
            except Exception as e:
                # 悬赏更新失败不影响秘境完成
                pass
        
        # 构建事件描述，包含合成信息
        event_desc = event["desc"]
        if synthesis_messages:
            event_desc += "\n\n" + "\n".join(synthesis_messages)
        
        return RiftResult(
            success=True,
            rift_name=rift_name,
            exp_gained=exp_reward,
            gold_gained=gold_reward,
            items_gained=items_gained,
            event_description=event_desc,
            death_occurred=False,
            death_penalty=None
        )
    
    def exit_rift(self, user_id: str) -> str:
        """退出秘境（放弃探索）"""
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        if player.state != PlayerState.IN_RIFT:
            raise GameException("你当前不在探索秘境")
        
        # 重置状态
        self.player_repo.update_player_state(user_id, state=PlayerState.IDLE.value, extra_data=None)
        
        return "✅ 你已退出秘境，本次探索未获得任何奖励。"
    
    def _roll_rift_drops(self, player, rift_level: int, item_chance: int) -> List[Tuple[str, int]]:
        """根据秘境等级随机掉落物品"""
        dropped_items = []
        
        # 检查是否触发物品掉落
        if random.randint(1, 100) > item_chance:
            return dropped_items
        
        # 获取对应等级的掉落表
        drop_table = self.RIFT_DROP_TABLE.get(rift_level, self.RIFT_DROP_TABLE[1])
        
        # 加权随机选择物品
        total_weight = sum(item["weight"] for item in drop_table)
        roll = random.randint(1, total_weight)
        
        current_weight = 0
        for item in drop_table:
            current_weight += item["weight"]
            if roll <= current_weight:
                count = random.randint(item["min"], item["max"])
                # 检查是否为类别物品（需要二级掉落）
                item_name = self._resolve_item_category(item["name"], rift_level)
                dropped_items.append((item_name, count))
                break
        
        # 高级秘境有50%概率额外掉落一件
        if rift_level >= 2 and random.randint(1, 100) <= 50:
            roll = random.randint(1, total_weight)
            current_weight = 0
            for item in drop_table:
                current_weight += item["weight"]
                if roll <= current_weight:
                    count = random.randint(item["min"], item["max"])
                    # 检查是否为类别物品（需要二级掉落）
                    item_name = self._resolve_item_category(item["name"], rift_level)
                    dropped_items.append((item_name, count))
                    break
        
        # 稀有丹药掉落检测
        pill_drops = self._roll_pill_drops(rift_level)
        if pill_drops:
            dropped_items.extend(pill_drops)
        
        return dropped_items
    
    def _roll_pill_drops(self, rift_level: int) -> List[Tuple[str, int]]:
        """根据秘境等级随机掉落稀有丹药"""
        dropped_pills = []
        
        # 获取丹药掉落概率
        pill_chance = self.RIFT_PILL_DROP_CHANCE.get(rift_level, 3)
        
        # 检查是否触发丹药掉落
        if random.randint(1, 100) > pill_chance:
            return dropped_pills
        
        # 获取对应等级的丹药掉落表
        pill_table = self.RIFT_PILL_DROP_TABLE.get(rift_level, self.RIFT_PILL_DROP_TABLE[1])
        
        # 加权随机选择丹药
        total_weight = sum(item["weight"] for item in pill_table)
        roll = random.randint(1, total_weight)
        
        current_weight = 0
        for item in pill_table:
            current_weight += item["weight"]
            if roll <= current_weight:
                count = random.randint(item["min"], item["max"])
                dropped_pills.append((item["name"], count))
                break
        
        return dropped_pills
    
    def _is_pill_item(self, item_name: str) -> bool:
        """检查物品是否为丹药"""
        # 简单判断：包含"丹"字的为丹药
        return "丹" in item_name
    
    def _resolve_item_category(self, item_name: str, rift_level: int) -> str:
        """
        解析物品类别，如果是类别物品则进行二级掉落
        
        Args:
            item_name: 物品名称（可能是类别）
            rift_level: 秘境等级
            
        Returns:
            具体的物品名称
        """
        # 检查是否为"稀有掉落"类别
        if item_name == "稀有掉落":
            return self._roll_rare_drop(rift_level)
        
        # 其他物品直接返回
        return item_name
    
    def _roll_rare_drop(self, rift_level: int) -> str:
        """
        从稀有掉落中随机选择一种物品（二级掉落）
        
        流程：
        1. 根据秘境等级选择类别（天材地宝、炼器材料、法器、功法）
        2. 从选中的类别中随机选择具体物品
        
        Args:
            rift_level: 秘境等级（决定掉落品质和类别权重）
            
        Returns:
            具体的物品名称
        """
        # 第一步：选择类别
        category_weights = self.RARE_DROP_CATEGORY_WEIGHTS.get(rift_level, self.RARE_DROP_CATEGORY_WEIGHTS[1])
        total_weight = sum(category_weights.values())
        roll = random.randint(1, total_weight)
        
        current_weight = 0
        selected_category = None
        for category, weight in category_weights.items():
            current_weight += weight
            if roll <= current_weight:
                selected_category = category
                break
        
        if not selected_category:
            selected_category = "天材地宝"  # 兜底
        
        # 第二步：从选中的类别中选择具体物品
        item_table = self.RARE_DROP_SUBTYPES.get(rift_level, {}).get(selected_category, [])
        if not item_table:
            # 兜底：返回默认物品
            return "灵草"
        
        # 加权随机选择
        total_weight = sum(item["weight"] for item in item_table)
        roll = random.randint(1, total_weight)
        
        current_weight = 0
        for item in item_table:
            current_weight += item["weight"]
            if roll <= current_weight:
                return item["name"]
        
        # 兜底：返回第一个
        return item_table[0]["name"]
    
    def _calculate_death_rate(self, player_level: int, rift: Rift) -> float:
        """
        计算秘境死亡率
        
        规则：
        - 达到推荐境界时死亡率为5%
        - 高于推荐境界2个境界时死亡率为0%
        - 低于推荐境界时死亡率快速增长
        
        举例：推荐金丹初期(index 13)
        - 金丹初期(13): 5%
        - 金丹中期(14): 2.5%
        - 金丹后期(15): 0%
        - 元婴期及以上(16+): 0%
        - 筑基后期(12): 15%
        - 筑基中期(11): 30%
        - 筑基初期(10): 50%
        
        Args:
            player_level: 玩家当前境界索引
            rift: 秘境对象
            
        Returns:
            死亡率（百分比，0-100）
        """
        level_diff = player_level - rift.recommended_level
        
        # 高于推荐境界2个境界或更高，死亡率为0
        if level_diff >= 2:
            return 0.0
        
        # 达到或高于推荐境界但未达到+2，线性递减
        if level_diff >= 0:
            # 推荐境界(0): 5%
            # 推荐+1(1): 2.5%
            # 推荐+2(2): 0%
            return max(0.0, 5.0 - (level_diff * 2.5))
        
        # 低于推荐境界，死亡率快速增长（指数增长）
        # 每低1个境界，死亡率增加基础值的倍数
        # 推荐-1: 5% + 10% = 15%
        # 推荐-2: 5% + 10% + 15% = 30%
        # 推荐-3: 5% + 10% + 15% + 20% = 50%
        # 推荐-4: 5% + 10% + 15% + 20% + 25% = 75%
        death_rate = 5.0
        for i in range(1, abs(level_diff) + 1):
            death_rate += 5.0 + (i * 5.0)
        
        # 最高死亡率不超过95%
        return min(95.0, death_rate)
    
    def _get_level_name(self, level_index: int) -> str:
        """获取境界名称"""
        # 从配置管理器获取境界名称
        level_data = self.config_manager.level_data
        if 0 <= level_index < len(level_data):
            return level_data[level_index].get("level_name", f"境界{level_index}")
        return f"境界{level_index}"

    def _update_bounty_progress(self, user_id: str, rift: Rift):
        """更新悬赏进度"""
        # 获取秘境的悬赏标签
        bounty_tag = rift.bounty_tag
        if not bounty_tag:
            return
        
        # 获取进行中的悬赏任务
        active_bounty = self.bounty_repo.get_active_bounty(user_id)
        if not active_bounty:
            return
        
        # 检查任务是否已过期
        if int(time.time()) > active_bounty.expire_time:
            return
        
        # 检查标签是否匹配（从配置加载悬赏模板）
        try:
            import json
            from pathlib import Path
            config_file = self.config_manager.config_dir / "bounty_templates.json"
            if not config_file.exists():
                return
            
            with open(config_file, 'r', encoding='utf-8') as f:
                bounty_config = json.load(f)
            
            templates = bounty_config.get("templates", [])
            template = next((t for t in templates if t["id"] == active_bounty.bounty_id), None)
            
            if not template:
                return
            
            progress_tags = template.get("progress_tags", [])
            if bounty_tag not in progress_tags:
                return
            
            # 秘境探索每次完成增加1点进度
            progress_to_add = 1
            
            # 更新进度
            new_progress = min(
                active_bounty.current_progress + progress_to_add,
                active_bounty.target_count
            )
            
            self.bounty_repo.update_progress(user_id, new_progress)
            
        except Exception:
            # 静默失败
            pass
