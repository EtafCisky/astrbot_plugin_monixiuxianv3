"""种子商店业务服务"""
import json
from typing import List, Dict, Optional

from ...core.config import ConfigManager
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository
from ...infrastructure.repositories.spirit_field_repo import SpiritFieldRepository
from ...domain.models.spirit_field import HerbSeed


class SeedShopService:
    """种子商店服务"""
    
    # 成熟时间配置(秒)
    GROW_TIME_CONFIG = {
        "凡品": {"min": 3600, "max": 7200},      # 1-2小时
        "珍品": {"min": 21600, "max": 43200},    # 6-12小时
        "圣品": {"min": 86400, "max": 259200},   # 1-3天
        "帝品": {"min": 432000, "max": 604800},  # 5-7天
        "道品": {"min": 864000, "max": 864000},  # 10天
        "仙品": {"min": 1296000, "max": 1296000},  # 15天
        "神品": {"min": 1728000, "max": 1728000}   # 20天
    }
    
    # 种子解锁配置
    UNLOCK_THRESHOLD = 5  # 解锁所需购买次数
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        storage_ring_repo: StorageRingRepository,
        spirit_field_repo: SpiritFieldRepository,
        config_manager: ConfigManager
    ):
        self.player_repo = player_repo
        self.storage_ring_repo = storage_ring_repo
        self.spirit_field_repo = spirit_field_repo
        self.config_manager = config_manager
        
        # 缓存可种植药草列表
        self._plantable_herbs_cache: Optional[List[Dict]] = None
    
    def _load_plantable_herbs(self) -> List[Dict]:
        """从items.json加载可种植药草"""
        if self._plantable_herbs_cache is not None:
            return self._plantable_herbs_cache
        
        # 加载items.json
        items_path = self.config_manager.config_dir / "items.json"
        if not items_path.exists():
            return []
        
        with open(items_path, 'r', encoding='utf-8') as f:
            items_data = json.load(f)
        
        # 筛选可种植的药草材料
        plantable_herbs = []
        for item_id, item_data in items_data.items():
            # 必须是材料类型
            if item_data.get("type") != "材料":
                continue
            
            # 排除非药草材料(矿石、兽类材料、机械部件等)
            name = item_data.get("name", "")
            
            # 排除明显的非药草材料
            non_herb_keywords = [
                "铁", "石", "沙", "砂", "皮", "毛", "血", "息", "齿轮", 
                "碎片", "精华", "残页", "遗物", "种子", "蛋", "符", "水",
                "核心", "内丹", "精血", "地宝", "秘境", "阵法", "封印",
                "古代法器", "邪修遗物"
            ]
            
            # 检查是否包含非药草关键词
            is_non_herb = False
            for keyword in non_herb_keywords:
                if keyword in name:
                    is_non_herb = True
                    break
            
            if is_non_herb:
                continue
            
            # 包含药草关键词的才是可种植的
            herb_keywords = [
                "草", "参", "芝", "果", "花", "根", "子", "藤", "莲", "叶",
                "药", "丹", "精", "黄", "当归", "茯苓", "甘草", "薄荷",
                "菊花", "枸杞", "山楂", "陈皮", "桔梗", "白芍", "川芎",
                "防风", "荆芥", "连翘", "金银花", "板蓝根", "蒲公英",
                "车前", "夏枯", "半夏", "苍术", "白术", "党参", "黄芪"
            ]
            
            is_herb = False
            for keyword in herb_keywords:
                if keyword in name:
                    is_herb = True
                    break
            
            if not is_herb:
                continue
            
            # 添加到可种植列表
            plantable_herbs.append({
                "id": item_id,
                "name": name,
                "rank": item_data.get("rank", "凡品"),
                "price": item_data.get("price", 100)
            })
        
        # 缓存结果
        self._plantable_herbs_cache = plantable_herbs
        return plantable_herbs
    
    def _create_seed_from_herb(
        self, 
        herb: Dict, 
        is_unlocked: bool, 
        purchase_count: int
    ) -> HerbSeed:
        """从药草创建种子(包含解锁状态)"""
        herb_id = herb["id"]
        herb_name = herb["name"]
        herb_rank = herb["rank"]
        herb_price = herb["price"]
        
        # 计算种子价格
        seed_price = HerbSeed.calculate_seed_price(herb_price)
        
        # 计算成熟时间(使用配置的中间值)
        grow_config = self.GROW_TIME_CONFIG.get(herb_rank, {"min": 3600, "max": 7200})
        grow_time = (grow_config["min"] + grow_config["max"]) // 2
        
        return HerbSeed(
            seed_id=herb_id,
            seed_name=f"{herb_name}种子",
            herb_id=herb_id,
            herb_name=herb_name,
            herb_rank=herb_rank,
            herb_price=herb_price,
            seed_price=seed_price,
            grow_time=grow_time,
            is_unlocked=is_unlocked,
            purchase_count=purchase_count
        )
    
    def get_seed_list(self, user_id: str) -> List[HerbSeed]:
        """获取种子列表(包含解锁状态和购买次数)"""
        # 加载可种植药草
        plantable_herbs = self._load_plantable_herbs()
        
        # 获取玩家的灵田信息(包含解锁状态和购买次数)
        spirit_field = self.spirit_field_repo.get_by_user_id(user_id)
        
        # 如果灵田不存在,使用空的解锁状态
        unlocked_seeds = set()
        seed_purchase_count = {}
        
        if spirit_field:
            unlocked_seeds = spirit_field.unlocked_seeds
            seed_purchase_count = spirit_field.seed_purchase_count
        
        # 创建种子列表
        seed_list = []
        for herb in plantable_herbs:
            herb_id = herb["id"]
            is_unlocked = herb_id in unlocked_seeds
            purchase_count = seed_purchase_count.get(herb_id, 0)
            
            seed = self._create_seed_from_herb(herb, is_unlocked, purchase_count)
            seed_list.append(seed)
        
        # 按品级和价格排序
        rank_order = {"凡品": 1, "珍品": 2, "圣品": 3, "帝品": 4, "道品": 5, "仙品": 6, "神品": 7}
        seed_list.sort(key=lambda s: (rank_order.get(s.herb_rank, 99), s.seed_price))
        
        return seed_list
    
    def _check_unlock_threshold(self, purchase_count: int) -> bool:
        """检查是否达到解锁阈值(5次)"""
        return purchase_count >= self.UNLOCK_THRESHOLD
    
    def buy_seed(self, user_id: str, seed_name: str, quantity: int = 1) -> str:
        """
        购买种子(已解锁的种子免费获取)
        
        Args:
            user_id: 用户ID
            seed_name: 种子名称(可以是药草名称或种子名称)
            quantity: 购买数量
            
        Returns:
            购买结果消息
        """
        # 验证数量
        if quantity <= 0:
            return "❌ 购买数量必须大于0"
        
        # 加载可种植药草
        plantable_herbs = self._load_plantable_herbs()
        
        # 查找对应的药草(支持药草名称或种子名称)
        target_herb = None
        for herb in plantable_herbs:
            herb_name = herb["name"]
            if herb_name == seed_name or f"{herb_name}种子" == seed_name:
                target_herb = herb
                break
        
        if not target_herb:
            return f"❌ 未找到种子: {seed_name}"
        
        herb_id = target_herb["id"]
        herb_name = target_herb["name"]
        herb_rank = target_herb["rank"]
        herb_price = target_herb["price"]
        
        # 计算种子价格
        seed_price = HerbSeed.calculate_seed_price(herb_price)
        total_cost = seed_price * quantity
        
        # 获取玩家信息
        player = self.player_repo.get_by_id(user_id)
        if not player:
            return "❌ 玩家不存在"
        
        # 获取或创建灵田
        spirit_field = self.spirit_field_repo.get_by_user_id(user_id)
        if not spirit_field:
            return "❌ 灵田不存在,请先创建角色"
        
        # 检查种子是否已解锁
        is_unlocked = spirit_field.is_seed_unlocked(herb_id)
        
        if is_unlocked:
            # 已解锁种子,免费获取
            self.storage_ring_repo.add_item(user_id, f"{herb_name}种子", quantity)
            return f"✨ {herb_name}种子已解锁,免费获得 {quantity} 个种子!"
        
        # 未解锁种子,需要支付灵石
        # 验证灵石是否足够
        if player.gold < total_cost:
            return f"❌ 灵石不足!需要 {total_cost:,} 灵石,当前 {player.gold:,} 灵石"
        
        # 扣除灵石
        self.player_repo.add_gold(user_id, -total_cost)
        
        # 添加种子到储物袋
        self.storage_ring_repo.add_item(user_id, f"{herb_name}种子", quantity)
        
        # 更新购买次数(每次购买增加购买数量)
        for _ in range(quantity):
            spirit_field.increment_seed_purchase(herb_id)
        
        # 检查是否达到解锁条件
        newly_unlocked = spirit_field.check_and_unlock_seed(herb_id)
        
        # 保存灵田数据
        self.spirit_field_repo.save(spirit_field)
        
        # 构建返回消息
        result_msg = f"✅ 成功购买 {quantity} 个{herb_name}种子,花费 {total_cost:,} 灵石"
        
        if newly_unlocked:
            result_msg += f"\n🎉 恭喜!{herb_name}种子已永久解锁!以后种植时不再需要购买种子!"
        else:
            current_count = spirit_field.seed_purchase_count.get(herb_id, 0)
            if current_count < self.UNLOCK_THRESHOLD:
                result_msg += f"\n📊 {herb_name}解锁进度: {current_count}/{self.UNLOCK_THRESHOLD}次购买"
        
        return result_msg
