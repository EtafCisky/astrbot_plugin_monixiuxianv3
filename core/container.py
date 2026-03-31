"""依赖注入容器"""
from pathlib import Path
from typing import Optional

from astrbot.api import logger

from .config import ConfigManager


class Container:
    """
    依赖注入容器
    
    管理所有组件的生命周期和依赖关系
    """
    
    def __init__(self, data_dir: Optional[Path] = None, config_manager: Optional[ConfigManager] = None):
        """
        初始化容器
        
        Args:
            data_dir: 数据目录路径
            config_manager: 配置管理器实例（如果不提供则创建新实例）
        """
        self.data_dir = data_dir
        
        # 单例组件
        self._config_manager: Optional[ConfigManager] = config_manager
        self._json_storage = None
        
        # 仓储层（每次创建新实例）
        # 将在后续实现
        
        # 服务层（每次创建新实例）
        # 将在后续实现
    
    def config_manager(self) -> ConfigManager:
        """获取配置管理器（单例）"""
        if self._config_manager is None:
            raise RuntimeError("配置管理器未初始化，请在创建 Container 时传入 config_manager 参数")
        return self._config_manager
    
    def json_storage(self):
        """获取 JSON 存储（单例）"""
        if self._json_storage is None:
            from ..infrastructure.storage.json_storage import JSONStorage
            
            # 从配置管理器获取 JSON 存储配置
            config = self.config_manager()
            json_config = config.settings.json_storage
            
            # 如果有 data_dir，使用 data_dir 下的路径，否则使用配置中的路径
            if self.data_dir:
                storage_dir = self.data_dir / json_config.data_dir
            else:
                storage_dir = Path(json_config.data_dir)
            
            logger.info(f"【修仙V3】初始化 JSON 存储: {storage_dir}")
            logger.info(f"【修仙V3】缓存启用: {json_config.enable_cache}, 锁超时: {json_config.lock_timeout}秒, 最大备份: {json_config.max_backups}")
            
            self._json_storage = JSONStorage(
                data_dir=storage_dir,
                enable_cache=json_config.enable_cache,
                lock_timeout=json_config.lock_timeout,
                max_backups=json_config.max_backups
            )
        return self._json_storage
    
    # 仓储层工厂方法
    def player_repository(self):
        """获取玩家仓储"""
        from ..infrastructure.repositories.player_repo import PlayerRepository
        storage = self.json_storage()
        return PlayerRepository(storage)
    
    def combat_repository(self):
        """获取战斗仓储"""
        from ..infrastructure.repositories.combat_repo import CombatRepository
        storage = self.json_storage()
        return CombatRepository(storage)
    
    def storage_ring_repository(self):
        """获取储物戒仓储"""
        from ..infrastructure.repositories.storage_ring_repo import StorageRingRepository
        storage = self.json_storage()
        return StorageRingRepository(storage)
    
    def equipment_repository(self):
        """获取装备仓储"""
        from ..infrastructure.repositories.equipment_repo import EquipmentRepository
        storage = self.json_storage()
        # 使用ConfigManager的config_dir（调用方法获取实例）
        config_dir = self.config_manager().config_dir
        return EquipmentRepository(storage, config_dir)
    
    def shop_repository(self):
        """获取商店仓储"""
        from ..infrastructure.repositories.shop_repo import ShopRepository
        storage = self.json_storage()
        return ShopRepository(storage)
    
    def sect_repository(self):
        """获取宗门仓储"""
        from ..infrastructure.repositories.sect_repo import SectRepository
        storage = self.json_storage()
        return SectRepository(storage)
    
    def rift_repository(self):
        """获取秘境仓储"""
        from ..infrastructure.repositories.rift_repo import RiftRepository
        storage = self.json_storage()
        return RiftRepository(storage)
    
    def boss_repository(self):
        """获取Boss仓储"""
        from ..infrastructure.repositories.boss_repo import BossRepository
        storage = self.json_storage()
        return BossRepository(storage)
    
    def bounty_repository(self):
        """获取悬赏仓储"""
        from ..infrastructure.repositories.bounty_repo import BountyRepository
        storage = self.json_storage()
        return BountyRepository(storage)
    
    def bank_repository(self):
        """获取银行仓储"""
        from ..infrastructure.repositories.bank_repo import BankRepository
        storage = self.json_storage()
        return BankRepository(storage)
    
    def blessed_land_repository(self):
        """获取洞天福地仓储"""
        from ..infrastructure.repositories.blessed_land_repo import BlessedLandRepository
        storage = self.json_storage()
        return BlessedLandRepository(storage)
    
    def spirit_farm_repository(self):
        """获取灵田仓储"""
        from ..infrastructure.repositories.spirit_farm_repo import SpiritFarmRepository
        storage = self.json_storage()
        return SpiritFarmRepository(storage)
    
    def spirit_eye_repository(self):
        """获取天地灵眼仓储"""
        from ..infrastructure.repositories.spirit_eye_repo import SpiritEyeRepository
        storage = self.json_storage()
        return SpiritEyeRepository(storage)
    
    def dual_cultivation_repository(self):
        """获取双修仓储"""
        from ..infrastructure.repositories.dual_cultivation_repo import DualCultivationRepository
        storage = self.json_storage()
        return DualCultivationRepository(storage)
    
    def impart_repository(self):
        """获取传承仓储"""
        from ..infrastructure.repositories.impart_repo import ImpartRepository
        storage = self.json_storage()
        return ImpartRepository(storage)
    
    def market_repository(self):
        """获取市场仓储"""
        from ..infrastructure.repositories.market_repo import MarketRepository
        storage = self.json_storage()
        return MarketRepository(storage)
    
    def spirit_field_repository(self):
        """获取灵田仓储"""
        from ..infrastructure.repositories.spirit_field_repo import SpiritFieldRepository
        storage = self.json_storage()
        return SpiritFieldRepository(storage)
    
    def plot_repository(self):
        """获取田地仓储"""
        from ..infrastructure.repositories.plot_repo import PlotRepository
        storage = self.json_storage()
        spirit_field_repo = self.spirit_field_repository()
        return PlotRepository(storage, spirit_field_repo)
    
    # 工具类工厂方法
    def spirit_root_generator(self):
        """获取灵根生成器"""
        from ..utils.spirit_root_generator import SpiritRootGenerator
        return SpiritRootGenerator(self.config_manager())
    
    # 服务层工厂方法
    def player_service(self):
        """获取玩家服务"""
        from ..application.services.player_service import PlayerService
        return PlayerService(
            self.player_repository(),
            self.config_manager()
        )
    
    def cultivation_service(self):
        """获取修炼服务"""
        from ..application.services.cultivation_service import CultivationService
        return CultivationService(
            self.player_repository(),
            self.config_manager(),
            self.spirit_root_generator()
        )
    
    def breakthrough_service(self):
        """获取突破服务"""
        from ..application.services.breakthrough_service import BreakthroughService
        return BreakthroughService(
            self.player_repository(),
            self.config_manager()
        )
    
    def combat_service(self):
        """获取战斗服务"""
        from ..application.services.combat_service import CombatService
        return CombatService(
            self.player_repository(),
            self.combat_repository(),
            self.config_manager()
        )
    
    def storage_ring_service(self):
        """获取储物戒服务"""
        from ..application.services.storage_ring_service import StorageRingService
        return StorageRingService(
            self.storage_ring_repository(),
            self.player_repository(),
            self.config_manager()
        )
    
    def equipment_service(self):
        """获取装备服务"""
        from ..application.services.equipment_service import EquipmentService
        return EquipmentService(
            self.equipment_repository(),
            self.player_repository(),
            self.storage_ring_repository()
        )
    
    def pill_service(self):
        """获取丹药服务"""
        from ..application.services.pill_service import PillService
        return PillService(
            self.player_repository(),
            self.storage_ring_repository(),
            self.config_manager()
        )
    
    def alchemy_service(self):
        """获取炼丹服务"""
        from ..application.services.alchemy_service import AlchemyService
        return AlchemyService(
            self.player_repository(),
            self.storage_ring_repository(),
            self.config_manager()
        )
    
    def shop_service(self):
        """获取商店服务"""
        from ..application.services.shop_service import ShopService
        return ShopService(
            self.shop_repository(),
            self.player_repository(),
            self.storage_ring_repository(),
            self.config_manager()
        )
    
    def sect_service(self):
        """获取宗门服务"""
        from ..application.services.sect_service import SectService
        return SectService(
            self.sect_repository(),
            self.player_repository(),
            self.config_manager()
        )
    
    def adventure_service(self):
        """获取历练服务"""
        from ..application.services.adventure_service import AdventureService
        return AdventureService(
            self.player_repository(),
            self.storage_ring_repository(),
            self.config_manager(),
            self.bounty_repository()  # 添加悬赏仓储
        )
    
    def rift_service(self):
        """获取秘境服务"""
        from ..application.services.rift_service import RiftService
        return RiftService(
            self.player_repository(),
            self.rift_repository(),
            self.storage_ring_repository(),
            self.config_manager(),
            self.bounty_repository()
        )
    
    def boss_service(self):
        """获取Boss服务"""
        from ..application.services.boss_service import BossService
        return BossService(
            self.player_repository(),
            self.boss_repository(),
            self.storage_ring_repository(),
            self.config_manager()
        )
    
    def bounty_service(self):
        """获取悬赏服务"""
        from ..application.services.bounty_service import BountyService
        return BountyService(
            self.bounty_repository(),
            self.player_repository(),
            self.storage_ring_repository(),
            self.config_manager()
        )
    
    def bank_service(self):
        """获取银行服务"""
        from ..application.services.bank_service import BankService
        return BankService(
            self.player_repository(),
            self.bank_repository(),
            self.config_manager()
        )
    
    def blessed_land_service(self):
        """获取洞天福地服务"""
        from ..application.services.blessed_land_service import BlessedLandService
        return BlessedLandService(
            self.player_repository(),
            self.blessed_land_repository(),
            self.config_manager()
        )
    
    def spirit_farm_service(self):
        """获取灵田服务"""
        from ..application.services.spirit_farm_service import SpiritFarmService
        return SpiritFarmService(
            self.player_repository(),
            self.spirit_farm_repository(),
            self.storage_ring_repository(),
            self.config_manager()
        )
    
    def spirit_eye_service(self):
        """获取天地灵眼服务"""
        from ..application.services.spirit_eye_service import SpiritEyeService
        return SpiritEyeService(
            self.player_repository(),
            self.spirit_eye_repository(),
            self.config_manager()
        )
    
    def dual_cultivation_service(self):
        """获取双修服务"""
        from ..application.services.dual_cultivation_service import DualCultivationService
        return DualCultivationService(
            self.dual_cultivation_repository(),
            self.player_repository(),
            self.config_manager(),
            self.spirit_root_generator()
        )
    
    def impart_service(self):
        """获取传承服务"""
        from ..application.services.impart_service import ImpartService
        return ImpartService(
            self.impart_repository(),
            self.player_repository(),
            self.config_manager()
        )
    
    def ranking_service(self):
        """获取排行榜服务"""
        from ..application.services.ranking_service import RankingService
        return RankingService(
            self.player_repository(),
            self.sect_repository(),
            self.bank_repository(),
            self.config_manager()
        )
    
    def market_service(self):
        """获取市场服务"""
        from ..application.services.market_service import MarketService
        return MarketService(
            self.market_repository(),
            self.player_repository(),
            self.storage_ring_repository(),
            self.storage_ring_service(),
            self.config_manager()
        )
    
    def spirit_field_service(self):
        """获取灵田服务（新种子-药草系统）"""
        from ..application.services.spirit_field_service import SpiritFieldService
        return SpiritFieldService(
            self.spirit_field_repository(),
            self.plot_repository(),
            self.player_repository(),
            self.storage_ring_repository(),
            self.config_manager()
        )
    
    def seed_shop_service(self):
        """获取种子商店服务"""
        from ..application.services.seed_shop_service import SeedShopService
        return SeedShopService(
            self.player_repository(),
            self.storage_ring_repository(),
            self.spirit_field_repository(),
            self.config_manager()
        )
    
    def cleanup(self):
        """清理资源"""
        # JSON 存储不需要显式关闭连接
        # 清理缓存引用
        if self._json_storage:
            self._json_storage = None
            logger.info("【修仙V3】JSON 存储已清理")

