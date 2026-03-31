"""成本计算器服务"""
import json
from typing import Dict, Optional
from pathlib import Path

from ...core.alchemy_constants import COST_RATIO_MIN, COST_RATIO_MAX


class CostCalculator:
    """成本计算器，计算配方的总制作成本"""
    
    def __init__(self, items_data: Optional[Dict] = None):
        """
        初始化成本计算器
        
        Args:
            items_data: 物品数据字典，如果为None则从配置文件加载
        """
        if items_data is None:
            items_data = self._load_items_data()
        
        self.material_prices = self._extract_material_prices(items_data)
    
    def _load_items_data(self) -> Dict:
        """从配置文件加载物品数据（从插件config目录）"""
        # 使用插件目录的config路径
        items_path = Path(__file__).parent.parent.parent / "config" / "items.json"
        with open(items_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _extract_material_prices(self, items_data: Dict) -> Dict[str, int]:
        """
        从物品数据中提取材料价格
        
        Args:
            items_data: 物品数据字典
            
        Returns:
            材料名称到价格的映射
        """
        material_prices = {}
        for item_id, item_info in items_data.items():
            if item_info.get("type") == "材料":
                material_prices[item_info["name"]] = item_info["price"]
        return material_prices
    
    def calculate_recipe_cost(self, materials: Dict[str, int]) -> int:
        """
        计算配方的总成本
        
        Args:
            materials: 材料字典，键为材料名称，值为所需数量
            
        Returns:
            总成本
            
        Raises:
            ValueError: 如果材料不存在
        """
        total_cost = 0
        for material_name, quantity in materials.items():
            if material_name not in self.material_prices:
                raise ValueError(f"材料 '{material_name}' 不存在于物品数据中")
            total_cost += self.material_prices[material_name] * quantity
        return total_cost
    
    def validate_cost_balance(self, recipe_cost: int, pill_price: int) -> bool:
        """
        验证成本是否在售价的110%-130%范围内
        
        Args:
            recipe_cost: 配方成本
            pill_price: 丹药售价
            
        Returns:
            是否在合理范围内
        """
        if pill_price <= 0:
            return False
        ratio = recipe_cost / pill_price
        return COST_RATIO_MIN <= ratio <= COST_RATIO_MAX
    
    def get_cost_ratio(self, recipe_cost: int, pill_price: int) -> float:
        """
        计算成本与售价的比率
        
        Args:
            recipe_cost: 配方成本
            pill_price: 丹药售价
            
        Returns:
            成本比率（如1.2表示成本是售价的120%）
        """
        if pill_price <= 0:
            return 0.0
        return recipe_cost / pill_price
    
    def get_material_price(self, material_name: str) -> Optional[int]:
        """
        获取材料价格
        
        Args:
            material_name: 材料名称
            
        Returns:
            材料价格，如果不存在返回None
        """
        return self.material_prices.get(material_name)
