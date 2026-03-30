"""
市场服务层

处理玩家交易市场相关的业务逻辑。
"""
import uuid
import json
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path

from ...domain.models.market import MarketListing
from ...domain.models.player import Player
from ...infrastructure.repositories.market_repo import MarketRepository
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository
from ...application.services.storage_ring_service import StorageRingService
from ...core.config import ConfigManager
from ...core.exceptions import BusinessException


class MarketService:
    """市场业务服务"""
    
    def __init__(
        self,
        market_repo: MarketRepository,
        player_repo: PlayerRepository,
        storage_ring_repo: StorageRingRepository,
        storage_ring_service: StorageRingService,
        config_manager: ConfigManager
    ):
        """
        初始化市场服务
        
        Args:
            market_repo: 市场仓储
            player_repo: 玩家仓储
            storage_ring_repo: 储物戒仓储
            storage_ring_service: 储物戒服务
            config_manager: 配置管理器
        """
        self.market_repo = market_repo
        self.player_repo = player_repo
        self.storage_ring_repo = storage_ring_repo
        self.storage_ring_service = storage_ring_service
        self.config_manager = config_manager
    
    def list_item(
        self,
        user_id: str,
        item_name: str,
        price: int
    ) -> Tuple[bool, str, Optional[MarketListing]]:
        """
        上架物品
        
        Args:
            user_id: 用户ID
            item_name: 物品名称
            price: 出售价格
            
        Returns:
            (是否成功, 消息, 上架记录)
            
        Raises:
            BusinessException: 业务异常
        """
        # 验证玩家存在
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        # 验证价格为正数
        if price <= 0:
            raise BusinessException("价格必须为正数")
        
        # 验证物品在储物戒中
        if not self.storage_ring_repo.has_item(user_id, item_name):
            raise BusinessException(f"储物戒中没有{item_name}")
        
        # 从储物戒移除物品
        success = self.storage_ring_repo.remove_item(user_id, item_name, 1)
        if not success:
            raise BusinessException(f"从储物戒移除{item_name}失败")
        
        # 获取参考价格
        reference_price = self.get_reference_price(item_name)
        
        # 生成上架ID
        listing_id = str(uuid.uuid4())
        
        # 创建上架记录
        listing = MarketListing(
            listing_id=listing_id,
            seller_id=user_id,
            seller_name=player.nickname,
            item_name=item_name,
            price=price,
            reference_price=reference_price
        )
        
        # 保存上架记录
        self.market_repo.create_listing(listing)
        
        # 构建消息
        ref_price_msg = f"（参考价格：{reference_price}灵石）" if reference_price else "（无参考价格）"
        message = f"成功上架{item_name}，售价{price}灵石{ref_price_msg}"
        
        return True, message, listing

    def view_market(self) -> List[MarketListing]:
        """
        查看市场所有物品
        
        Returns:
            上架物品列表
        """
        return self.market_repo.get_all_listings()
    
    def buy_item(
        self,
        buyer_id: str,
        listing_id: str
    ) -> Tuple[bool, str, Dict]:
        """
        购买物品
        
        Args:
            buyer_id: 买家用户ID
            listing_id: 上架ID
            
        Returns:
            (是否成功, 消息, 交易详情)
            
        Raises:
            BusinessException: 业务异常
        """
        # 验证买家存在
        buyer = self.player_repo.get_by_id(buyer_id)
        if not buyer:
            raise BusinessException("玩家不存在")
        
        # 验证上架记录存在
        listing = self.market_repo.get_listing(listing_id)
        if not listing:
            raise BusinessException("该物品已下架或不存在")
        
        # 不能购买自己的物品
        if listing.seller_id == buyer_id:
            raise BusinessException("不能购买自己的物品")
        
        # 验证买家金额充足
        if buyer.gold < listing.price:
            raise BusinessException(f"灵石不足，需要{listing.price}灵石，当前{buyer.gold}灵石")
        
        # 验证买家储物戒未满
        # 检查是否有新物品（不在储物戒中）
        current_count = self.storage_ring_repo.get_item_count(buyer_id, listing.item_name)
        if current_count == 0:
            # 新物品需要占用一个格子
            available_slots = self.storage_ring_service.get_available_slots(buyer_id)
            if available_slots <= 0:
                raise BusinessException("储物戒已满，无法添加物品")
        
        # 获取卖家
        seller = self.player_repo.get_by_id(listing.seller_id)
        if not seller:
            raise BusinessException("卖家不存在")
        
        # 计算税收和卖家收入
        tax = listing.calculate_tax()
        seller_revenue = listing.calculate_seller_revenue()
        
        # 扣除买家金额
        buyer.consume_gold(listing.price)
        self.player_repo.save(buyer)
        
        # 转账给卖家
        seller.add_gold(seller_revenue)
        self.player_repo.save(seller)
        
        # 将物品添加到买家储物戒
        self.storage_ring_repo.add_item(buyer_id, listing.item_name, 1)
        
        # 删除上架记录
        self.market_repo.delete_listing(listing_id)
        
        # 构建交易详情
        transaction_details = {
            "item_name": listing.item_name,
            "price": listing.price,
            "tax": tax,
            "seller_revenue": seller_revenue,
            "seller_name": listing.seller_name,
            "buyer_name": buyer.nickname
        }
        
        message = f"成功购买{listing.item_name}，花费{listing.price}灵石"
        
        return True, message, transaction_details

    def unlist_item(
        self,
        user_id: str,
        listing_id: str
    ) -> Tuple[bool, str]:
        """
        下架物品
        
        Args:
            user_id: 用户ID
            listing_id: 上架ID
            
        Returns:
            (是否成功, 消息)
            
        Raises:
            BusinessException: 业务异常
        """
        # 验证玩家存在
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        # 验证上架记录存在
        listing = self.market_repo.get_listing(listing_id)
        if not listing:
            raise BusinessException("该物品已下架或不存在")
        
        # 验证该上架记录属于该玩家
        if listing.seller_id != user_id:
            raise BusinessException("只能下架自己的物品")
        
        # 验证卖家储物戒未满
        # 检查是否有该物品（如果有则不需要新格子）
        current_count = self.storage_ring_repo.get_item_count(user_id, listing.item_name)
        if current_count == 0:
            # 新物品需要占用一个格子
            available_slots = self.storage_ring_service.get_available_slots(user_id)
            if available_slots <= 0:
                raise BusinessException("储物戒已满，无法添加物品")
        
        # 将物品返回到卖家储物戒
        self.storage_ring_repo.add_item(user_id, listing.item_name, 1)
        
        # 删除上架记录
        self.market_repo.delete_listing(listing_id)
        
        message = f"成功下架{listing.item_name}"
        
        return True, message
    
    def get_reference_price(self, item_name: str) -> Optional[int]:
        """
        获取物品参考价格
        
        Args:
            item_name: 物品名称
            
        Returns:
            参考价格，如果没有则返回None
        """
        # 从丹药配置获取
        pills_config = self._load_config("pills.json")
        if pills_config:
            for pill in pills_config:
                if pill.get("name") == item_name:
                    # 优先使用 price 字段
                    if "price" in pill:
                        return pill["price"]
                    # 其次使用 gold_cost 字段
                    if "gold_cost" in pill:
                        return pill["gold_cost"]
        
        # 从武器配置获取
        weapons_config = self._load_config("weapons.json")
        if weapons_config:
            for weapon in weapons_config:
                if weapon.get("name") == item_name:
                    if "price" in weapon:
                        return weapon["price"]
                    if "gold_cost" in weapon:
                        return weapon["gold_cost"]
        
        # 从通用物品配置获取
        items_config = self._load_config("items.json")
        if items_config:
            # items.json 是字典格式
            if isinstance(items_config, dict):
                for item_id, item_data in items_config.items():
                    if item_data.get("name") == item_name:
                        if "price" in item_data:
                            return item_data["price"]
                        if "gold_cost" in item_data:
                            return item_data["gold_cost"]
        
        return None
    
    def _load_config(self, filename: str) -> Optional[Any]:
        """
        加载配置文件
        
        Args:
            filename: 配置文件名
            
        Returns:
            配置数据，加载失败返回None
        """
        try:
            # 尝试从配置管理器获取配置目录
            config_dir = self.config_manager.config_dir
            config_path = config_dir / filename
            
            if not config_path.exists():
                return None
            
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
