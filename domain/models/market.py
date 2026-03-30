"""市场领域模型"""
from dataclasses import dataclass
from typing import Optional
import time


@dataclass
class MarketListing:
    """市场上架物品"""
    listing_id: str          # 上架ID（唯一标识）
    seller_id: str           # 卖家用户ID
    seller_name: str         # 卖家昵称
    item_name: str           # 物品名称
    price: int               # 出售价格
    reference_price: Optional[int] = None  # 参考价格
    created_at: int = 0      # 上架时间戳
    
    def __post_init__(self):
        """初始化后处理"""
        if self.created_at == 0:
            self.created_at = int(time.time())
    
    def calculate_tax(self) -> int:
        """
        计算交易税（15%）
        
        Returns:
            交易税金额
        """
        return int(self.price * 0.15)
    
    def calculate_seller_revenue(self) -> int:
        """
        计算卖家实际收入（85%）
        
        Returns:
            卖家收入金额
        """
        return self.price - self.calculate_tax()
