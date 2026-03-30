"""市场仓储"""
from typing import Optional, List, Dict, Any

from ...domain.models.market import MarketListing
from ..storage import JSONStorage, TimestampConverter
from .base import BaseRepository


class MarketRepository(BaseRepository[MarketListing]):
    """市场仓储实现"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化市场仓储
        
        Args:
            storage: JSON 存储管理器
        """
        super().__init__(storage, "market_listings.json")
    
    def get_by_id(self, listing_id: str) -> Optional[MarketListing]:
        """
        根据上架ID获取上架记录
        
        Args:
            listing_id: 上架ID
            
        Returns:
            上架记录对象，不存在则返回None
        """
        data = self.storage.get(self.filename, listing_id)
        if data is None:
            return None
        return self._to_domain(data)
    
    def get_listing(self, listing_id: str) -> Optional[MarketListing]:
        """
        获取上架记录（get_by_id 的别名）
        
        Args:
            listing_id: 上架ID
            
        Returns:
            上架记录对象，不存在则返回None
        """
        return self.get_by_id(listing_id)
    
    def create_listing(self, listing: MarketListing) -> None:
        """
        创建上架记录
        
        Args:
            listing: 上架记录对象
        """
        self.save(listing)
    
    def save(self, listing: MarketListing) -> None:
        """
        保存上架记录（创建或更新）
        
        Args:
            listing: 上架记录对象
        """
        data = self._to_dict(listing)
        self.storage.set(self.filename, listing.listing_id, data)
    
    def delete(self, listing_id: str) -> None:
        """
        删除上架记录
        
        Args:
            listing_id: 上架ID
        """
        self.storage.delete(self.filename, listing_id)
    
    def delete_listing(self, listing_id: str) -> None:
        """
        删除上架记录（delete 的别名）
        
        Args:
            listing_id: 上架ID
        """
        self.delete(listing_id)
    
    def exists(self, listing_id: str) -> bool:
        """
        检查上架记录是否存在
        
        Args:
            listing_id: 上架ID
            
        Returns:
            是否存在
        """
        return self.storage.exists(self.filename, listing_id)

    def get_all_listings(self) -> List[MarketListing]:
        """
        获取所有上架记录
        
        Returns:
            上架记录列表
        """
        results = self.storage.query(self.filename)
        return [self._to_domain(data) for data in results]
    
    def get_listings_by_seller(self, seller_id: str) -> List[MarketListing]:
        """
        获取指定卖家的所有上架记录
        
        Args:
            seller_id: 卖家用户ID
            
        Returns:
            上架记录列表
        """
        results = self.storage.query(
            self.filename,
            filter_fn=lambda x: x.get('seller_id') == seller_id
        )
        return [self._to_domain(data) for data in results]
    
    def _to_domain(self, data: Dict[str, Any]) -> MarketListing:
        """
        将字典数据转换为领域对象
        
        Args:
            data: 字典数据
            
        Returns:
            MarketListing 对象
        """
        # 转换时间戳
        created_at = TimestampConverter.from_iso8601(data.get('created_at'))
        if created_at is None:
            created_at = 0
        
        return MarketListing(
            listing_id=data['listing_id'],
            seller_id=data['seller_id'],
            seller_name=data['seller_name'],
            item_name=data['item_name'],
            price=data['price'],
            reference_price=data.get('reference_price'),
            created_at=created_at
        )
    
    def _to_dict(self, listing: MarketListing) -> Dict[str, Any]:
        """
        将领域对象转换为字典数据
        
        Args:
            listing: MarketListing 对象
            
        Returns:
            字典数据
        """
        return {
            'listing_id': listing.listing_id,
            'seller_id': listing.seller_id,
            'seller_name': listing.seller_name,
            'item_name': listing.item_name,
            'price': listing.price,
            'reference_price': listing.reference_price,
            'created_at': TimestampConverter.to_iso8601(listing.created_at)
        }
