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
    price: int               # 出售价格（单价）
    quantity: int = 1        # 上架数量
    reference_price: Optional[int] = None  # 参考价格
    created_at: int = 0      # 上架时间戳
    
    def __post_init__(self):
        """初始化后处理"""
        if self.created_at == 0:
            self.created_at = int(time.time())
        if self.quantity < 1:
            self.quantity = 1
    
    def calculate_tax(self, buy_quantity: int = None) -> int:
        """
        计算交易税（15%）
        
        Args:
            buy_quantity: 购买数量，如果为None则使用全部数量
        
        Returns:
            交易税金额
        """
        qty = buy_quantity if buy_quantity is not None else self.quantity
        return int(self.price * qty * 0.15)
    
    def calculate_seller_revenue(self, buy_quantity: int = None) -> int:
        """
        计算卖家实际收入（85%）
        
        Args:
            buy_quantity: 购买数量，如果为None则使用全部数量
        
        Returns:
            卖家收入金额
        """
        qty = buy_quantity if buy_quantity is not None else self.quantity
        total_price = self.price * qty
        return total_price - self.calculate_tax(qty)
    
    def get_total_price(self, buy_quantity: int = None) -> int:
        """
        获取总价
        
        Args:
            buy_quantity: 购买数量，如果为None则使用全部数量
        
        Returns:
            总价
        """
        qty = buy_quantity if buy_quantity is not None else self.quantity
        return self.price * qty
