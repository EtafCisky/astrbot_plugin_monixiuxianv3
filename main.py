"""修仙插件 V3 - 主入口"""
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, StarTools, register
from astrbot.api import logger

from .core.container import Container
from .core.constants import Commands
from .core.config import ConfigManager


@register(
    "astrbot_plugin_monixiuxianv3",
    "EtafCisky",
    "基于清晰架构重构的修仙模拟游戏插件",
    "3.7.0"
)
class XiuxianV3Plugin(Star):
    """修仙插件 V3 - 清晰架构版本"""
    
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        
        # 获取插件数据目录
        self.data_dir = StarTools.get_data_dir("astrbot_plugin_monixiuxianv3")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取 AstrBot 配置
        # 优先使用传入的 config 参数（AstrBot 4.x 方式）
        # 如果没有，则尝试从 context 获取（备用方式）
        if config is not None:
            astrbot_config = config
            logger.info(f"【修仙V3】从 config 参数获取配置: {type(config)}")
        else:
            astrbot_config = context.get_config("astrbot_plugin_monixiuxianv3")
            logger.info(f"【修仙V3】从 context 获取配置: {type(astrbot_config)}")
        
        if astrbot_config is None:
            astrbot_config = {}
            logger.warning("【修仙V3】未获取到配置，使用空字典")
        
        # 初始化配置文件（返回是否需要清空商店数据）
        self.need_clear_shop = self._initialize_config_files()
        
        # 初始化配置管理器
        config_dir = self.data_dir / "config"
        self.config_manager = ConfigManager(config_dir=config_dir, astrbot_config=astrbot_config)
        
        # 初始化依赖注入容器（传入配置管理器）
        self.container = Container(data_dir=self.data_dir, config_manager=self.config_manager)
        
        # 初始化所有 handlers
        self._setup_handlers()
    
    def _initialize_config_files(self):
        """初始化配置文件（从插件目录复制到数据目录）"""
        import shutil
        from pathlib import Path
        
        # 源配置目录（插件安装目录）
        source_config_dir = Path(__file__).parent / "config"
        # 目标配置目录（数据目录）
        target_config_dir = self.data_dir / "config"
        target_config_dir.mkdir(parents=True, exist_ok=True)
        
        # 需要复制的配置文件列表
        config_files = [
            "level_config.json",
            "body_level_config.json",
            "items.json",
            "weapons.json",
            "pills.json",
            "storage_rings.json",
            "adventure_config.json",
            "bounty_templates.json",
            "alchemy_recipes.json"
        ]
        
        # v3.4.10 版本：每次启动都强制更新 bounty_templates.json（确保悬赏时限配置生效）
        always_update_files = ["bounty_templates.json"]
        
        # 复制配置文件
        for config_file in config_files:
            source_file = source_config_dir / config_file
            target_file = target_config_dir / config_file
            
            # 判断是否需要复制
            should_copy = False
            if not target_file.exists():
                # 目标文件不存在，必须复制
                should_copy = True
                logger.info(f"【修仙V3】初始化配置文件: {config_file}")
            elif config_file in always_update_files:
                # 每次启动都强制更新的文件
                should_copy = True
                logger.info(f"【修仙V3】强制更新配置文件: {config_file} (v3.4.10)")
            
            if should_copy and source_file.exists():
                try:
                    shutil.copy2(source_file, target_file)
                    logger.info(f"【修仙V3】已复制配置文件: {config_file}")
                except Exception as e:
                    logger.error(f"【修仙V3】复制配置文件 {config_file} 失败: {e}")
        
        # 返回 False（不需要清空商店数据）
        return False

    
    def _setup_handlers(self):
        """初始化所有命令处理器"""
        from .utils.spirit_root_generator import SpiritRootGenerator
        from .presentation.handlers.player_handler import PlayerHandler
        from .presentation.handlers.help_handler import HelpHandler
        from .presentation.handlers.cultivation_handler import CultivationHandler
        from .presentation.handlers.breakthrough_handler import BreakthroughHandler
        from .presentation.handlers.combat_handler import CombatHandler
        from .presentation.handlers.storage_ring_handler import StorageRingHandler
        from .presentation.handlers.equipment_handler import EquipmentHandler
        from .presentation.handlers.pill_handler import PillHandler
        from .presentation.handlers.alchemy_handler import AlchemyHandler
        from .presentation.handlers.shop_handler import ShopHandler
        from .presentation.handlers.sect_handler import SectHandler
        from .presentation.handlers.adventure_handler import AdventureHandler
        from .presentation.handlers.rift_handler import RiftHandler
        from .presentation.handlers.boss_handler import BossHandler
        from .presentation.handlers.bounty_handler import BountyHandler
        from .presentation.handlers.bank_handler import BankHandler
        from .presentation.handlers.blessed_land_handler import BlessedLandHandler
        from .presentation.handlers.spirit_farm_handler import SpiritFarmHandler
        from .presentation.handlers.spirit_eye_handler import SpiritEyeHandler
        from .presentation.handlers.dual_cultivation_handler import DualCultivationHandler
        from .presentation.handlers.impart_handler import ImpartHandler
        from .presentation.handlers.ranking_handler import RankingHandler
        from .presentation.handlers.market_handler import MarketHandler
        from .presentation.handlers.spirit_field_handler import SpiritFieldHandler
        from .presentation.handlers.seed_shop_handler import SeedShopHandler
        
        spirit_root_gen = SpiritRootGenerator(self.config_manager)
        
        self.help_handler = HelpHandler()
        self.player_handler = PlayerHandler(
            self.container.player_service(),
            spirit_root_gen,
            self.container
        )
        self.cultivation_handler = CultivationHandler(
            self.container.cultivation_service(),
            self.container.player_service()
        )
        self.breakthrough_handler = BreakthroughHandler(
            self.container.breakthrough_service(),
            self.container.player_service()
        )
        self.combat_handler = CombatHandler(
            self.container.combat_service(),
            self.container.player_service()
        )
        self.storage_ring_handler = StorageRingHandler(
            self.container.storage_ring_service(),
            self.container.player_service()
        )
        self.equipment_handler = EquipmentHandler(
            self.container.equipment_service(),
            self.container.player_service()
        )
        self.pill_handler = PillHandler(
            self.container.pill_service(),
            self.container.player_service()
        )
        self.alchemy_handler = AlchemyHandler(
            self.container.alchemy_service(),
            self.container.player_service()
        )
        self.shop_handler = ShopHandler(
            self.container.shop_service(),
            self.container.player_service()
        )
        self.sect_handler = SectHandler(
            self.container.sect_service(),
            self.container.player_service()
        )
        self.adventure_handler = AdventureHandler(
            self.container.adventure_service()
        )
        self.rift_handler = RiftHandler(
            self.container.rift_service()
        )
        self.boss_handler = BossHandler(
            self.container.boss_service(),
            self.config_manager
        )
        self.bounty_handler = BountyHandler(
            self.container.bounty_service()
        )
        self.bank_handler = BankHandler(
            self.container.bank_service()
        )
        self.blessed_land_handler = BlessedLandHandler(
            self.container.blessed_land_service()
        )
        self.spirit_farm_handler = SpiritFarmHandler(
            self.container.spirit_farm_service()
        )
        self.spirit_eye_handler = SpiritEyeHandler(
            self.container.spirit_eye_service()
        )
        self.dual_cultivation_handler = DualCultivationHandler(
            self.container.dual_cultivation_service()
        )
        self.impart_handler = ImpartHandler(
            self.container.impart_service()
        )
        self.ranking_handler = RankingHandler(
            self.container.ranking_service(),
            self.container.player_repository()
        )
        self.market_handler = MarketHandler(
            self.container.market_service(),
            self.container.player_service()
        )
        self.spirit_field_handler = SpiritFieldHandler(
            self.container.spirit_field_service()
        )
        self.seed_shop_handler = SeedShopHandler(
            self.container.seed_shop_service()
        )
    
    async def initialize(self):
        """插件启动"""
        try:
            # JSON 存储不需要初始化数据库
            # 数据目录已在 __init__ 中创建
            logger.info("【修仙V3】JSON 存储已就绪")
            
            # 如果需要清空商店数据（版本更新时）
            if self.need_clear_shop:
                self._clear_shop_data()
            
            # 初始化秘境数据
            self._initialize_rifts()
            
            # 初始化Boss数据（如果没有存活的Boss，自动生成一个）
            self._initialize_boss()
            
            logger.info("【修仙V3】插件已启动")
        except Exception as e:
            logger.error(f"【修仙V3】插件启动失败: {e}", exc_info=True)
            raise  # 关键初始化失败应该中断启动
    
    def _clear_shop_data(self):
        """清空商店数据（用于强制刷新商店）"""
        try:
            # 使用 JSON 存储，直接删除商店文件即可
            shop_repo = self.container.shop_repository()
            
            # 获取所有商店并删除
            all_shops = shop_repo.get_all()
            for shop in all_shops:
                shop_repo.delete(shop.shop_id)
            
            logger.info("【修仙V3】商店数据已清空，下次访问将重新生成商品")
        except Exception as e:
            logger.warning(f"【修仙V3】无法清空商店数据: {e}")
    
    def _initialize_rifts(self):
        """初始化秘境数据"""
        try:
            from .domain.models.rift import Rift
            
            rift_repo = self.container.rift_repository()
            
            # 检查是否已有秘境数据
            existing_rifts = rift_repo.get_all_rifts()
            
            # 定义标准秘境配置（包含bounty_tag）
            standard_rifts = [
                {
                    "rift_id": 1,
                    "rift_name": "幽暗森林",
                    "rift_level": 1,
                    "required_level": 3,
                    "recommended_level": 10,
                    "exp_reward_min": 5000,
                    "exp_reward_max": 15000,
                    "gold_reward_min": 1000,
                    "gold_reward_max": 3000,
                    "description": "低级秘境，适合筑基期修士探索",
                    "bounty_tag": "rift_dark_forest"
                },
                {
                    "rift_id": 2,
                    "rift_name": "玄冰洞窟",
                    "rift_level": 2,
                    "required_level": 6,
                    "recommended_level": 13,
                    "exp_reward_min": 20000,
                    "exp_reward_max": 50000,
                    "gold_reward_min": 5000,
                    "gold_reward_max": 10000,
                    "description": "中级秘境，适合金丹期修士探索",
                    "bounty_tag": "rift_ice_cave"
                },
                {
                    "rift_id": 3,
                    "rift_name": "天火禁地",
                    "rift_level": 3,
                    "required_level": 9,
                    "recommended_level": 16,
                    "exp_reward_min": 80000,
                    "exp_reward_max": 150000,
                    "gold_reward_min": 15000,
                    "gold_reward_max": 30000,
                    "description": "高级秘境，适合元婴期修士探索",
                    "bounty_tag": "rift_fire_land"
                },
            ]
            
            if existing_rifts:
                # 已有数据，检查并更新bounty_tag
                logger.info("【修仙V3】检查秘境数据，更新bounty_tag...")
                for std_rift in standard_rifts:
                    existing = next((r for r in existing_rifts if r.rift_id == std_rift["rift_id"]), None)
                    if existing:
                        # 如果bounty_tag为空或不匹配，更新它
                        if not existing.bounty_tag or existing.bounty_tag != std_rift["bounty_tag"]:
                            existing.bounty_tag = std_rift["bounty_tag"]
                            rift_repo.save(existing)
                            logger.info(f"【修仙V3】更新秘境 {existing.rift_name} 的bounty_tag为 {std_rift['bounty_tag']}")
                return
            
            # 创建初始秘境
            initial_rifts = [
                Rift(
                    rift_id=0,  # 会被自动分配
                    rift_name=std["rift_name"],
                    rift_level=std["rift_level"],
                    required_level=std["required_level"],
                    recommended_level=std["recommended_level"],
                    exp_reward_min=std["exp_reward_min"],
                    exp_reward_max=std["exp_reward_max"],
                    gold_reward_min=std["gold_reward_min"],
                    gold_reward_max=std["gold_reward_max"],
                    description=std["description"],
                    bounty_tag=std["bounty_tag"]
                )
                for std in standard_rifts
            ]
            
            # 插入秘境数据
            for rift in initial_rifts:
                rift_repo.create_rift(rift)
            
            logger.info(f"【修仙V3】已创建 {len(initial_rifts)} 个初始秘境")
            
        except Exception as e:
            logger.error(f"【修仙V3】初始化秘境数据失败: {e}", exc_info=True)
            # 秘境初始化失败不应阻止插件启动，但需要记录详细错误
            logger.warning("【修仙V3】秘境功能可能无法正常使用，请检查日志")
    
    def _initialize_boss(self):
        """初始化Boss数据（如果没有存活的Boss，自动生成一个）"""
        try:
            boss_service = self.container.boss_service()
            
            # 检查是否已有存活的Boss
            existing_boss = boss_service.get_active_boss()
            if existing_boss:
                logger.info(f"【修仙V3】已有存活的Boss：{existing_boss.boss_name}")
                return  # 已有Boss，跳过初始化
            
            # 自动生成一个Boss
            boss = boss_service.auto_spawn_boss()
            logger.info(f"【修仙V3】已自动生成初始Boss：{boss.boss_name}（{boss.boss_level}境）")
            
        except Exception as e:
            logger.error(f"【修仙V3】初始化Boss数据失败: {e}", exc_info=True)
            # Boss初始化失败不应阻止插件启动，但需要记录详细错误
            logger.warning("【修仙V3】Boss功能可能无法正常使用，请检查日志或使用'生成Boss'命令手动生成")
    
    # ===== 玩家系统命令 =====
    
    @filter.command(Commands.HELP)
    async def cmd_help(self, event: AstrMessageEvent):
        """帮助"""
        async for result in self.help_handler.handle_help(event):
            yield result
    
    @filter.command(Commands.CREATE_PLAYER)
    async def cmd_create_player(self, event: AstrMessageEvent, cult_type: str = ""):
        """创建角色"""
        async for result in self.player_handler.handle_create_player(event, cult_type):
            yield result
    
    @filter.command(Commands.PLAYER_INFO)
    async def cmd_player_info(self, event: AstrMessageEvent):
        """查看信息"""
        async for result in self.player_handler.handle_player_info(event):
            yield result
    
    @filter.command(Commands.CHECK_IN)
    async def cmd_check_in(self, event: AstrMessageEvent):
        """签到"""
        async for result in self.player_handler.handle_check_in(event):
            yield result
    
    @filter.command(Commands.CHANGE_NICKNAME)
    async def cmd_change_nickname(self, event: AstrMessageEvent, new_nickname: str = ""):
        """改道号"""
        async for result in self.player_handler.handle_change_nickname(event, new_nickname):
            yield result
    
    @filter.command(Commands.REBIRTH)
    async def cmd_rebirth(self, event: AstrMessageEvent, confirm_text: str = ""):
        """弃道重修"""
        async for result in self.player_handler.handle_rebirth(event, confirm_text):
            yield result
    
    # ===== 修炼系统命令 =====
    
    @filter.command(Commands.START_CULTIVATION)
    async def cmd_start_cultivation(self, event: AstrMessageEvent):
        """开始闭关"""
        async for result in self.cultivation_handler.handle_start_cultivation(event):
            yield result
    
    @filter.command(Commands.END_CULTIVATION)
    async def cmd_end_cultivation(self, event: AstrMessageEvent):
        """结束闭关"""
        async for result in self.cultivation_handler.handle_end_cultivation(event):
            yield result
    
    # ===== 突破系统命令 =====
    
    @filter.command(Commands.BREAKTHROUGH)
    async def cmd_breakthrough(self, event: AstrMessageEvent, pill_name: str = ""):
        """突破"""
        async for result in self.breakthrough_handler.handle_breakthrough(event, pill_name):
            yield result
    
    @filter.command(Commands.BREAKTHROUGH_INFO)
    async def cmd_breakthrough_info(self, event: AstrMessageEvent):
        """突破信息"""
        async for result in self.breakthrough_handler.handle_breakthrough_info(event):
            yield result
    
    # ===== 战斗系统命令 =====
    
    @filter.command(Commands.SPAR)
    async def cmd_spar(self, event: AstrMessageEvent, target: str = ""):
        """切磋"""
        async for result in self.combat_handler.handle_spar(event, target):
            yield result
    
    @filter.command(Commands.DUEL)
    async def cmd_duel(self, event: AstrMessageEvent, target: str = ""):
        """决斗"""
        async for result in self.combat_handler.handle_duel(event, target):
            yield result
    
    @filter.command(Commands.COMBAT_LOG)
    async def cmd_combat_log(self, event: AstrMessageEvent):
        """战斗记录"""
        async for result in self.combat_handler.handle_combat_log(event):
            yield result
    
    # ===== 储物戒系统命令 =====
    
    @filter.command(Commands.STORAGE_RING)
    async def cmd_storage_ring(self, event: AstrMessageEvent):
        """储物戒"""
        async for result in self.storage_ring_handler.handle_storage_ring(event):
            yield result
    
    @filter.command(Commands.DISCARD_ITEM)
    async def cmd_discard_item(self, event: AstrMessageEvent, args: str = ""):
        """丢弃"""
        async for result in self.storage_ring_handler.handle_discard_item(event, args):
            yield result
    
    @filter.command(Commands.GIFT_ITEM)
    async def cmd_gift_item(self, event: AstrMessageEvent, args: str = ""):
        """赠予"""
        async for result in self.storage_ring_handler.handle_gift_item(event, args):
            yield result
    
    @filter.command(Commands.UPGRADE_RING)
    async def cmd_upgrade_ring(self, event: AstrMessageEvent, ring_name: str = ""):
        """更换储物戒"""
        async for result in self.storage_ring_handler.handle_upgrade_ring(event, ring_name):
            yield result
    
    @filter.command(Commands.SEARCH_ITEM)
    async def cmd_search_item(self, event: AstrMessageEvent, keyword: str = ""):
        """搜索物品"""
        async for result in self.storage_ring_handler.handle_search_item(event, keyword):
            yield result
    
    @filter.command(Commands.VIEW_ITEM)
    async def cmd_view_item(self, event: AstrMessageEvent, item_name: str = ""):
        """查看物品"""
        async for result in self.storage_ring_handler.handle_view_item(event, item_name):
            yield result
    
    # ===== 装备系统命令 =====
    
    @filter.command(Commands.EQUIPMENT_INFO)
    async def cmd_equipment_info(self, event: AstrMessageEvent):
        """我的装备"""
        async for result in self.equipment_handler.handle_show_equipment(event):
            yield result
    
    @filter.command(Commands.EQUIP)
    async def cmd_equip_item(self, event: AstrMessageEvent, item_name: str = ""):
        """装备"""
        async for result in self.equipment_handler.handle_equip_item(event, item_name):
            yield result
    
    @filter.command(Commands.UNEQUIP)
    async def cmd_unequip_item(self, event: AstrMessageEvent, item_name: str = ""):
        """卸下"""
        async for result in self.equipment_handler.handle_unequip_item(event, item_name):
            yield result
    
    # ===== 丹药系统命令 =====
    
    @filter.command(Commands.USE_PILL)
    async def cmd_use_pill(self, event: AstrMessageEvent, pill_name: str = ""):
        """服用丹药"""
        async for result in self.pill_handler.handle_use_pill(event, pill_name):
            yield result
    
    @filter.command(Commands.SEARCH_PILL)
    async def cmd_search_pills(self, event: AstrMessageEvent, keyword: str = ""):
        """搜索丹药"""
        async for result in self.pill_handler.handle_search_pills(event, keyword):
            yield result
    
    # ===== 炼丹系统命令 =====
    
    @filter.command(Commands.ALCHEMY_RECIPES)
    async def cmd_alchemy_recipes(self, event: AstrMessageEvent):
        """丹药配方"""
        async for result in self.alchemy_handler.handle_show_recipes(event):
            yield result
    
    @filter.command(Commands.CRAFT_PILL)
    async def cmd_craft_pill(self, event: AstrMessageEvent, pill_name: str = ""):
        """炼丹"""
        async for result in self.alchemy_handler.handle_craft_pill_by_name(event, pill_name):
            yield result
    
    @filter.command(Commands.QUERY_RECIPE)
    async def cmd_query_recipe(self, event: AstrMessageEvent, query: str = ""):
        """查询配方"""
        # 尝试将query解析为ID或名称
        if query.isdigit():
            async for result in self.alchemy_handler.handle_query_recipe_by_id(event, query):
                yield result
        else:
            async for result in self.alchemy_handler.handle_query_recipe_by_name(event, query):
                yield result
    
    @filter.command(Commands.QUERY_RECIPE_BY_RANK)
    async def cmd_query_recipe_by_rank(self, event: AstrMessageEvent, rank: str = ""):
        """查询品质配方"""
        async for result in self.alchemy_handler.handle_query_recipes_by_rank(event, rank):
            yield result
    
    @filter.command(Commands.ALCHEMY_INFO)
    async def cmd_alchemy_info(self, event: AstrMessageEvent):
        """炼丹信息"""
        async for result in self.alchemy_handler.handle_alchemy_info(event):
            yield result
    
    # ===== 商店系统命令 =====
    
    @filter.command(Commands.PILL_PAVILION)
    async def cmd_pill_pavilion(self, event: AstrMessageEvent):
        """丹阁"""
        async for result in self.shop_handler.handle_pill_pavilion(event):
            yield result
    
    @filter.command(Commands.WEAPON_PAVILION)
    async def cmd_weapon_pavilion(self, event: AstrMessageEvent):
        """器阁"""
        async for result in self.shop_handler.handle_weapon_pavilion(event):
            yield result
    
    @filter.command(Commands.TREASURE_PAVILION)
    async def cmd_treasure_pavilion(self, event: AstrMessageEvent):
        """百宝阁"""
        async for result in self.shop_handler.handle_treasure_pavilion(event):
            yield result
    
    @filter.command(Commands.BUY)
    async def cmd_buy(self, event: AstrMessageEvent, args: str = ""):
        """购买（商店或市场）"""
        # 如果参数看起来像UUID（包含字母和数字的混合），则是市场购买
        # 否则是商店购买
        if args and any(c.isalpha() for c in args) and any(c.isdigit() for c in args) and len(args) >= 8:
            # 市场购买
            async for result in self.market_handler.handle_buy_item(event, args):
                yield result
        else:
            # 商店购买
            async for result in self.shop_handler.handle_buy(event, args):
                yield result
    
    # ===== 市场系统命令 =====
    
    @filter.command(Commands.MARKET)
    async def cmd_market(self, event: AstrMessageEvent):
        """市场"""
        async for result in self.market_handler.handle_view_market(event):
            yield result
    
    @filter.command(Commands.VIEW_MARKET)
    async def cmd_view_market_alias(self, event: AstrMessageEvent):
        """查看市场"""
        async for result in self.market_handler.handle_view_market(event):
            yield result
    
    @filter.command(Commands.LIST_ITEM)
    async def cmd_list_item(self, event: AstrMessageEvent, item_name: str = "", price: str = ""):
        """市场上架"""
        async for result in self.market_handler.handle_list_item(event, item_name, price):
            yield result
    
    @filter.command(Commands.UNLIST_ITEM)
    async def cmd_unlist_item(self, event: AstrMessageEvent, listing_id: str = ""):
        """市场下架"""
        async for result in self.market_handler.handle_unlist_item(event, listing_id):
            yield result
    
    # ===== 灵田系统命令（新种子-药草系统）=====
    
    @filter.command(Commands.CREATE_FARM)
    async def cmd_create_farm(self, event: AstrMessageEvent):
        """开垦灵田"""
        async for result in self.spirit_field_handler.handle_create_field(event):
            yield result
    
    @filter.command(Commands.FARM_INFO)
    async def cmd_farm_info(self, event: AstrMessageEvent):
        """灵田"""
        async for result in self.spirit_field_handler.handle_field_status(event):
            yield result
    
    @filter.command(Commands.FARM_INFO_ALT)
    async def cmd_farm_info_alt(self, event: AstrMessageEvent):
        """lingtian"""
        async for result in self.spirit_field_handler.handle_field_status(event):
            yield result
    
    @filter.command(Commands.FARM_INFO_ALT2)
    async def cmd_farm_info_alt2(self, event: AstrMessageEvent):
        """灵田信息"""
        async for result in self.spirit_field_handler.handle_field_status(event):
            yield result
    
    @filter.command(Commands.FARM_INFO_ALT3)
    async def cmd_farm_info_alt3(self, event: AstrMessageEvent):
        """我的灵田"""
        async for result in self.spirit_field_handler.handle_field_status(event):
            yield result
    
    @filter.command(Commands.PLANT_HERB)
    async def cmd_plant_herb(self, event: AstrMessageEvent, herb_name: str = ""):
        """种植"""
        async for result in self.spirit_field_handler.handle_plant(event, herb_name):
            yield result
    
    @filter.command(Commands.HARVEST)
    async def cmd_harvest(self, event: AstrMessageEvent):
        """收获"""
        async for result in self.spirit_field_handler.handle_harvest(event):
            yield result
    
    @filter.command(Commands.UPGRADE_FARM)
    async def cmd_upgrade_farm(self, event: AstrMessageEvent):
        """灵田升级"""
        async for result in self.spirit_field_handler.handle_upgrade(event):
            yield result
    
    @filter.command(Commands.SEED_SHOP)
    async def cmd_seed_shop(self, event: AstrMessageEvent):
        """种子商店"""
        async for result in self.seed_shop_handler.handle_shop(event):
            yield result
    
    @filter.command(Commands.BUY_SEED)
    async def cmd_buy_seed(self, event: AstrMessageEvent, seed_name: str = "", quantity: str = "1"):
        """购买种子"""
        async for result in self.seed_shop_handler.handle_buy(event, seed_name, quantity):
            yield result
    
    # ===== 宗门系统命令 =====
    
    @filter.command(Commands.CREATE_SECT)
    async def cmd_create_sect(self, event: AstrMessageEvent, sect_name: str = ""):
        """创建宗门"""
        async for result in self.sect_handler.handle_create_sect(event, sect_name):
            yield result
    
    @filter.command(Commands.JOIN_SECT)
    async def cmd_join_sect(self, event: AstrMessageEvent, sect_name: str = ""):
        """加入宗门"""
        async for result in self.sect_handler.handle_join_sect(event, sect_name):
            yield result
    
    @filter.command(Commands.LEAVE_SECT)
    async def cmd_leave_sect(self, event: AstrMessageEvent):
        """退出宗门"""
        async for result in self.sect_handler.handle_leave_sect(event):
            yield result
    
    @filter.command(Commands.SECT_INFO)
    async def cmd_sect_info(self, event: AstrMessageEvent):
        """宗门信息"""
        async for result in self.sect_handler.handle_sect_info(event):
            yield result
    
    @filter.command(Commands.SECT_LIST)
    async def cmd_sect_list(self, event: AstrMessageEvent):
        """宗门列表"""
        async for result in self.sect_handler.handle_sect_list(event):
            yield result
    
    @filter.command(Commands.SECT_DONATE)
    async def cmd_sect_donate(self, event: AstrMessageEvent, amount: str = ""):
        """宗门捐献"""
        async for result in self.sect_handler.handle_donate(event, amount):
            yield result
    
    @filter.command(Commands.SECT_TASK)
    async def cmd_sect_task(self, event: AstrMessageEvent):
        """宗门任务"""
        async for result in self.sect_handler.handle_sect_task(event):
            yield result
    
    @filter.command(Commands.CHANGE_POSITION)
    async def cmd_change_position(self, event: AstrMessageEvent, args: str = ""):
        """变更职位"""
        async for result in self.sect_handler.handle_change_position(event, args):
            yield result
    
    @filter.command(Commands.TRANSFER_OWNERSHIP)
    async def cmd_transfer_ownership(self, event: AstrMessageEvent, target_id: str = ""):
        """宗主传位"""
        async for result in self.sect_handler.handle_transfer_ownership(event, target_id):
            yield result
    
    @filter.command(Commands.KICK_MEMBER)
    async def cmd_kick_member(self, event: AstrMessageEvent, target_id: str = ""):
        """踢出成员"""
        async for result in self.sect_handler.handle_kick_member(event, target_id):
            yield result
    
    # ===== 历练系统命令 =====
    
    @filter.command(Commands.ADVENTURE_INFO)
    async def cmd_adventure_info(self, event: AstrMessageEvent):
        """历练信息"""
        async for result in self.adventure_handler.handle_adventure_info(event):
            yield result
    
    @filter.command(Commands.START_ADVENTURE)
    async def cmd_start_adventure(self, event: AstrMessageEvent, route_name: str = ""):
        """开始历练"""
        async for result in self.adventure_handler.handle_start_adventure(event, route_name):
            yield result
    
    @filter.command(Commands.ADVENTURE_STATUS)
    async def cmd_adventure_status(self, event: AstrMessageEvent):
        """历练状态"""
        async for result in self.adventure_handler.handle_adventure_status(event):
            yield result
    
    @filter.command(Commands.COMPLETE_ADVENTURE)
    async def cmd_complete_adventure(self, event: AstrMessageEvent):
        """完成历练"""
        async for result in self.adventure_handler.handle_complete_adventure(event):
            yield result
    
    # ===== 秘境系统命令 =====
    
    @filter.command(Commands.RIFT_LIST)
    async def cmd_rift_list(self, event: AstrMessageEvent):
        """秘境列表"""
        async for result in self.rift_handler.handle_rift_list(event):
            yield result
    
    @filter.command(Commands.ENTER_RIFT)
    async def cmd_enter_rift(self, event: AstrMessageEvent, rift_id: str = ""):
        """探索秘境"""
        async for result in self.rift_handler.handle_enter_rift(event, rift_id):
            yield result
    
    @filter.command(Commands.FINISH_EXPLORATION)
    async def cmd_finish_exploration(self, event: AstrMessageEvent):
        """完成探索"""
        async for result in self.rift_handler.handle_finish_exploration(event):
            yield result
    
    @filter.command(Commands.EXIT_RIFT)
    async def cmd_exit_rift(self, event: AstrMessageEvent):
        """退出秘境"""
        async for result in self.rift_handler.handle_exit_rift(event):
            yield result
    
    # ===== Boss系统命令 =====
    
    @filter.command(Commands.BOSS_INFO)
    async def cmd_boss_info(self, event: AstrMessageEvent):
        """世界Boss"""
        async for result in self.boss_handler.handle_boss_info(event):
            yield result
    
    @filter.command(Commands.CHALLENGE_BOSS)
    async def cmd_challenge_boss(self, event: AstrMessageEvent):
        """挑战Boss"""
        async for result in self.boss_handler.handle_challenge_boss(event):
            yield result
    
    @filter.command(Commands.SPAWN_BOSS)
    async def cmd_spawn_boss(self, event: AstrMessageEvent):
        """生成Boss（管理员）"""
        async for result in self.boss_handler.handle_spawn_boss(event):
            yield result
    
    # ===== 管理员命令 =====
    
    @filter.command(Commands.ADMIN_ADD_GOLD)
    async def cmd_admin_add_gold(self, event: AstrMessageEvent, args: str = ""):
        """增加灵石（管理员）"""
        async for result in self.player_handler.handle_admin_add_gold(event, args):
            yield result
    
    @filter.command(Commands.ADMIN_REDUCE_GOLD)
    async def cmd_admin_reduce_gold(self, event: AstrMessageEvent, args: str = ""):
        """减少灵石（管理员）"""
        async for result in self.player_handler.handle_admin_reduce_gold(event, args):
            yield result
    
    @filter.command(Commands.ADMIN_CHANGE_SPIRIT_ROOT)
    async def cmd_admin_change_spirit_root(self, event: AstrMessageEvent, args: str = ""):
        """修改灵根（管理员）"""
        async for result in self.player_handler.handle_admin_change_spirit_root(event, args):
            yield result
    
    @filter.command(Commands.ADMIN_ADD_EXPERIENCE)
    async def cmd_admin_add_experience(self, event: AstrMessageEvent, args: str = ""):
        """增加修为（管理员）"""
        async for result in self.player_handler.handle_admin_add_experience(event, args):
            yield result
    
    @filter.command(Commands.ADMIN_CHANGE_SECT_POSITION)
    async def cmd_admin_change_sect_position(self, event: AstrMessageEvent, args: str = ""):
        """修改宗门岗位（管理员）"""
        async for result in self.player_handler.handle_admin_change_sect_position(event, args):
            yield result
    
    @filter.command(Commands.ADMIN_ADD_ITEM)
    async def cmd_admin_add_item(self, event: AstrMessageEvent, args: str = ""):
        """增加道具（管理员）"""
        async for result in self.player_handler.handle_admin_add_item(event, args):
            yield result
    
    # ===== 悬赏系统命令 =====
    
    @filter.command(Commands.BOUNTY_LIST)
    async def cmd_bounty_list(self, event: AstrMessageEvent):
        """悬赏令"""
        async for result in self.bounty_handler.handle_bounty_list(event):
            yield result
    
    @filter.command(Commands.ACCEPT_BOUNTY)
    async def cmd_accept_bounty(self, event: AstrMessageEvent, bounty_id: str = ""):
        """接取悬赏"""
        async for result in self.bounty_handler.handle_accept_bounty(event, bounty_id):
            yield result
    
    @filter.command(Commands.BOUNTY_STATUS)
    async def cmd_bounty_status(self, event: AstrMessageEvent):
        """悬赏状态"""
        async for result in self.bounty_handler.handle_bounty_status(event):
            yield result
    
    @filter.command(Commands.COMPLETE_BOUNTY)
    async def cmd_complete_bounty(self, event: AstrMessageEvent):
        """完成悬赏"""
        async for result in self.bounty_handler.handle_complete_bounty(event):
            yield result
    
    @filter.command(Commands.ABANDON_BOUNTY)
    async def cmd_abandon_bounty(self, event: AstrMessageEvent):
        """放弃悬赏"""
        async for result in self.bounty_handler.handle_abandon_bounty(event):
            yield result
    
    # ===== 银行系统命令 =====
    
    @filter.command(Commands.BANK_INFO)
    async def cmd_bank_info(self, event: AstrMessageEvent):
        """灵石银行"""
        async for result in self.bank_handler.handle_bank_info(event):
            yield result
    
    @filter.command(Commands.DEPOSIT)
    async def cmd_deposit(self, event: AstrMessageEvent, amount: str = ""):
        """存灵石"""
        async for result in self.bank_handler.handle_deposit(event, amount):
            yield result
    
    @filter.command(Commands.WITHDRAW)
    async def cmd_withdraw(self, event: AstrMessageEvent, amount: str = ""):
        """取灵石"""
        async for result in self.bank_handler.handle_withdraw(event, amount):
            yield result
    
    @filter.command(Commands.CLAIM_INTEREST)
    async def cmd_claim_interest(self, event: AstrMessageEvent):
        """领取利息"""
        async for result in self.bank_handler.handle_claim_interest(event):
            yield result
    
    @filter.command(Commands.LOAN)
    async def cmd_loan(self, event: AstrMessageEvent, amount: str = ""):
        """贷款"""
        async for result in self.bank_handler.handle_loan(event, amount):
            yield result
    
    @filter.command(Commands.REPAY)
    async def cmd_repay(self, event: AstrMessageEvent):
        """还款"""
        async for result in self.bank_handler.handle_repay(event):
            yield result
    
    @filter.command(Commands.BREAKTHROUGH_LOAN)
    async def cmd_breakthrough_loan(self, event: AstrMessageEvent, amount: str = ""):
        """突破贷款"""
        async for result in self.bank_handler.handle_breakthrough_loan(event, amount):
            yield result
    
    # ===== 洞天福地系统命令 =====
    
    @filter.command(Commands.BLESSED_LAND_INFO)
    async def cmd_blessed_land_info(self, event: AstrMessageEvent):
        """洞天信息"""
        async for result in self.blessed_land_handler.handle_blessed_land_info(event):
            yield result
    
    @filter.command(Commands.PURCHASE_BLESSED_LAND)
    async def cmd_purchase_blessed_land(self, event: AstrMessageEvent, land_type: str = ""):
        """购买洞天"""
        async for result in self.blessed_land_handler.handle_purchase(event, land_type):
            yield result
    
    @filter.command(Commands.UPGRADE_BLESSED_LAND)
    async def cmd_upgrade_blessed_land(self, event: AstrMessageEvent):
        """升级洞天"""
        async for result in self.blessed_land_handler.handle_upgrade(event):
            yield result
    
    @filter.command(Commands.COLLECT_BLESSED_LAND)
    async def cmd_collect_blessed_land(self, event: AstrMessageEvent):
        """洞天收取"""
        async for result in self.blessed_land_handler.handle_collect(event):
            yield result
    
    # ===== 灵田系统命令 ===== (暂时关闭)
    
    # @filter.command(Commands.FARM_INFO)
    # async def cmd_farm_info(self, event: AstrMessageEvent):
    #     """灵田信息"""
    #     async for result in self.spirit_farm_handler.handle_farm_info(event):
    #         yield result
    
    # @filter.command(Commands.CREATE_FARM)
    # async def cmd_create_farm(self, event: AstrMessageEvent):
    #     """开垦灵田"""
    #     async for result in self.spirit_farm_handler.handle_create_farm(event):
    #         yield result
    
    # @filter.command(Commands.PLANT_HERB)
    # async def cmd_plant_herb(self, event: AstrMessageEvent, herb_name: str = ""):
    #     """种植"""
    #     async for result in self.spirit_farm_handler.handle_plant(event, herb_name):
    #         yield result
    
    # @filter.command(Commands.HARVEST)
    # async def cmd_harvest(self, event: AstrMessageEvent):
    #     """收获"""
    #     async for result in self.spirit_farm_handler.handle_harvest(event):
    #         yield result
    
    # @filter.command(Commands.UPGRADE_FARM)
    # async def cmd_upgrade_farm(self, event: AstrMessageEvent):
    #     """升级灵田"""
    #     async for result in self.spirit_farm_handler.handle_upgrade_farm(event):
    #         yield result
    
    # ===== 天地灵眼系统命令 =====
    
    @filter.command(Commands.SPIRIT_EYE_INFO)
    async def cmd_spirit_eye_info(self, event: AstrMessageEvent):
        """灵眼信息"""
        async for result in self.spirit_eye_handler.handle_spirit_eye_info(event):
            yield result
    
    @filter.command(Commands.CLAIM_SPIRIT_EYE)
    async def cmd_claim_spirit_eye(self, event: AstrMessageEvent, eye_id: str = ""):
        """抢占灵眼"""
        async for result in self.spirit_eye_handler.handle_claim(event, eye_id):
            yield result
    
    @filter.command(Commands.COLLECT_SPIRIT_EYE)
    async def cmd_collect_spirit_eye(self, event: AstrMessageEvent):
        """灵眼收取"""
        async for result in self.spirit_eye_handler.handle_collect(event):
            yield result
    
    @filter.command(Commands.RELEASE_SPIRIT_EYE)
    async def cmd_release_spirit_eye(self, event: AstrMessageEvent):
        """释放灵眼"""
        async for result in self.spirit_eye_handler.handle_release(event):
            yield result
    
    # ===== 双修系统命令 =====
    
    @filter.command(Commands.DUAL_CULTIVATION)
    async def cmd_dual_cultivation(self, event: AstrMessageEvent, target: str = ""):
        """双修"""
        async for result in self.dual_cultivation_handler.handle_dual_request(event, target):
            yield result
    
    @filter.command(Commands.ACCEPT_DUAL)
    async def cmd_accept_dual(self, event: AstrMessageEvent):
        """接受双修"""
        async for result in self.dual_cultivation_handler.handle_accept(event):
            yield result
    
    @filter.command(Commands.REJECT_DUAL)
    async def cmd_reject_dual(self, event: AstrMessageEvent):
        """拒绝双修"""
        async for result in self.dual_cultivation_handler.handle_reject(event):
            yield result
    
    # ===== 传承系统命令 =====
    
    @filter.command(Commands.IMPART_INFO)
    async def cmd_impart_info(self, event: AstrMessageEvent):
        """传承信息"""
        async for result in self.impart_handler.handle_impart_info(event):
            yield result
    
    @filter.command(Commands.IMPART_CHALLENGE)
    async def cmd_impart_challenge(self, event: AstrMessageEvent, target_info: str = ""):
        """传承挑战"""
        async for result in self.impart_handler.handle_impart_challenge(event, target_info):
            yield result
    
    @filter.command(Commands.IMPART_RANKING)
    async def cmd_impart_ranking(self, event: AstrMessageEvent):
        """传承排行"""
        async for result in self.impart_handler.handle_impart_ranking(event):
            yield result
    
    # ===== 排行榜系统命令 =====
    
    @filter.command(Commands.RANK_LEVEL)
    async def cmd_rank_level(self, event: AstrMessageEvent):
        """境界排行"""
        async for result in self.ranking_handler.handle_rank_level(event):
            yield result
    
    @filter.command(Commands.RANK_POWER)
    async def cmd_rank_power(self, event: AstrMessageEvent):
        """战力排行"""
        async for result in self.ranking_handler.handle_rank_power(event):
            yield result
    
    @filter.command(Commands.RANK_WEALTH)
    async def cmd_rank_wealth(self, event: AstrMessageEvent):
        """灵石排行"""
        async for result in self.ranking_handler.handle_rank_wealth(event):
            yield result
    
    @filter.command(Commands.RANK_SECT)
    async def cmd_rank_sect(self, event: AstrMessageEvent):
        """宗门排行"""
        async for result in self.ranking_handler.handle_rank_sect(event):
            yield result
    
    @filter.command(Commands.RANK_DEPOSIT)
    async def cmd_rank_deposit(self, event: AstrMessageEvent):
        """存款排行"""
        async for result in self.ranking_handler.handle_rank_deposit(event):
            yield result
    
    @filter.command(Commands.RANK_CONTRIBUTION)
    async def cmd_rank_contribution(self, event: AstrMessageEvent):
        """贡献排行"""
        async for result in self.ranking_handler.handle_rank_sect_contribution(event):
            yield result
    
    # ===== 其他命令将在后续实现 =====
    
    async def terminate(self):
        """插件关闭"""
        try:
            # 清理容器资源（包括关闭数据库连接）
            self.container.cleanup()
            
            logger.info("【修仙V3】插件已关闭")
        except Exception as e:
            logger.error(f"【修仙V3】插件关闭失败: {e}")
