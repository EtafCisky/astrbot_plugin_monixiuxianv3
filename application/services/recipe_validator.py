"""配方验证器服务"""
from dataclasses import dataclass, field
from typing import List, Dict, Set
import json
from pathlib import Path

from ...domain.models.recipe import Recipe
from ...core.alchemy_constants import (
    RANK_LEVELS, VALID_RANKS, COST_RATIO_MIN, COST_RATIO_MAX
)
from .cost_calculator import CostCalculator


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, message: str):
        """添加错误"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """添加警告"""
        self.warnings.append(message)


class RecipeValidator:
    """配方验证器，验证配方的所有约束"""
    
    def __init__(self, valid_materials: Set[str] = None, items_data: Dict = None, pills_data: List = None):
        """
        初始化验证器
        
        Args:
            valid_materials: 有效材料名称集合
            items_data: 物品数据
            pills_data: 丹药数据
        """
        if valid_materials is None:
            valid_materials = self._load_valid_materials()
        self.valid_materials = valid_materials
        
        if items_data is None:
            items_data = self._load_items_data()
        self.items_data = items_data
        
        if pills_data is None:
            pills_data = self._load_pills_data()
        self.pills_data = pills_data
        
        self.cost_calculator = CostCalculator(items_data)
        
        # 创建丹药价格映射
        self.pill_prices = self._create_pill_price_map()
    
    def _load_items_data(self) -> Dict:
        """加载物品数据（从插件config目录）"""
        # 使用插件目录的config路径
        items_path = Path(__file__).parent.parent.parent / "config" / "items.json"
        with open(items_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_pills_data(self) -> List:
        """加载突破丹药数据（从插件config目录）"""
        # 使用插件目录的config路径
        pills_path = Path(__file__).parent.parent.parent / "config" / "pills.json"
        with open(pills_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_valid_materials(self) -> Set[str]:
        """加载有效材料名称"""
        items_data = self._load_items_data()
        materials = set()
        for item_info in items_data.values():
            if item_info.get("type") == "材料":
                materials.add(item_info["name"])
        return materials
    
    def _create_pill_price_map(self) -> Dict[str, int]:
        """创建丹药ID到价格的映射"""
        price_map = {}
        
        # 从items.json中提取丹药价格
        for item_id, item_info in self.items_data.items():
            if item_info.get("type") == "丹药":
                price_map[item_id] = item_info["price"]
        
        # 从pills.json中提取突破丹药价格
        for pill in self.pills_data:
            price_map[pill["id"]] = pill["price"]
        
        return price_map
    
    def validate_recipe(self, recipe: Recipe) -> ValidationResult:
        """
        验证配方的所有约束
        
        Args:
            recipe: 要验证的配方
            
        Returns:
            验证结果
        """
        result = ValidationResult(is_valid=True)
        
        # 验证基本字段
        self._validate_basic_fields(recipe, result)
        
        # 验证材料引用有效性
        self._validate_material_references(recipe, result)
        
        # 验证炼丹等级要求范围
        self._validate_level_requirement(recipe, result)
        
        # 验证成功率范围
        self._validate_success_rate(recipe, result)
        
        # 验证材料等级匹配
        self._validate_material_rank_matching(recipe, result)
        
        # 验证经济平衡
        self._validate_economic_balance(recipe, result)
        
        return result
    
    def _validate_basic_fields(self, recipe: Recipe, result: ValidationResult):
        """验证基本字段"""
        if not recipe.id or recipe.id.strip() == "":
            result.add_error(f"配方ID不能为空")
        
        if not recipe.pill_id or recipe.pill_id.strip() == "":
            result.add_error(f"丹药ID不能为空")
        
        if not recipe.name or recipe.name.strip() == "":
            result.add_error(f"丹药名称不能为空")
        
        if recipe.rank not in VALID_RANKS:
            result.add_error(f"无效的品质等级: {recipe.rank}")
        
        if not (0 <= recipe.level_required <= 20):
            result.add_error(f"炼丹等级要求必须在0-20之间，当前为: {recipe.level_required}")
        
        if not (25 <= recipe.success_rate <= 95):
            result.add_error(f"成功率必须在25-95之间，当前为: {recipe.success_rate}")
        
        if not isinstance(recipe.materials, dict) or len(recipe.materials) == 0:
            result.add_error(f"材料列表不能为空")
        else:
            for material, quantity in recipe.materials.items():
                if quantity <= 0:
                    result.add_error(f"材料 '{material}' 的数量必须为正整数，当前为: {quantity}")
        
        if recipe.cost <= 0:
            result.add_error(f"成本必须为正数，当前为: {recipe.cost}")
    
    def _validate_material_references(self, recipe: Recipe, result: ValidationResult):
        """验证材料引用有效性"""
        for material_name in recipe.materials.keys():
            if material_name not in self.valid_materials:
                result.add_warning(f"配方 {recipe.id} 引用了不存在的材料: {material_name}")
    
    def _validate_level_requirement(self, recipe: Recipe, result: ValidationResult):
        """验证炼丹等级要求范围"""
        if recipe.rank not in RANK_LEVELS:
            return
        
        min_level, max_level = RANK_LEVELS[recipe.rank]["level_range"]
        if not (min_level <= recipe.level_required <= max_level):
            result.add_warning(
                f"配方 {recipe.id} 的等级要求 {recipe.level_required} "
                f"不符合 {recipe.rank} 品质的规定范围 ({min_level}-{max_level})"
            )
    
    def _validate_success_rate(self, recipe: Recipe, result: ValidationResult):
        """验证成功率范围"""
        if recipe.rank not in RANK_LEVELS:
            return
        
        min_rate, max_rate = RANK_LEVELS[recipe.rank]["success_rate_range"]
        if not (min_rate <= recipe.success_rate <= max_rate):
            result.add_warning(
                f"配方 {recipe.id} 的成功率 {recipe.success_rate}% "
                f"不符合 {recipe.rank} 品质的规定范围 ({min_rate}%-{max_rate}%)"
            )
    
    def _validate_material_rank_matching(self, recipe: Recipe, result: ValidationResult):
        """验证材料等级匹配"""
        # 计算各等级材料的成本占比
        total_cost = recipe.cost
        if total_cost <= 0:
            return
        
        rank_costs = {"凡品": 0, "珍品": 0, "圣品": 0}
        
        for material_name, quantity in recipe.materials.items():
            price = self.cost_calculator.get_material_price(material_name)
            if price is None:
                continue
            
            material_cost = price * quantity
            
            # 判断材料等级
            if price <= 200:  # 凡品材料
                rank_costs["凡品"] += material_cost
            elif price <= 5000:  # 珍品材料
                rank_costs["珍品"] += material_cost
            else:  # 圣品材料
                rank_costs["圣品"] += material_cost
        
        # 根据丹药品质验证材料等级匹配
        if recipe.rank == "凡品":
            if rank_costs["凡品"] / total_cost < 0.5:
                result.add_warning(
                    f"配方 {recipe.id} 是凡品丹药，但凡品材料成本占比不足50%"
                )
        elif recipe.rank in ["灵品", "珍品"]:
            if rank_costs["珍品"] / total_cost < 0.5:
                result.add_warning(
                    f"配方 {recipe.id} 是{recipe.rank}丹药，但珍品材料成本占比不足50%"
                )
        elif recipe.rank == "圣品":
            if rank_costs["圣品"] / total_cost < 0.3:
                result.add_warning(
                    f"配方 {recipe.id} 是圣品丹药，但圣品材料成本占比不足30%"
                )
        elif recipe.rank in ["帝品", "道品", "仙品", "神品"]:
            if rank_costs["圣品"] / total_cost < 0.6:
                result.add_warning(
                    f"配方 {recipe.id} 是{recipe.rank}丹药，但圣品材料成本占比不足60%"
                )
    
    def _validate_economic_balance(self, recipe: Recipe, result: ValidationResult):
        """验证经济平衡"""
        pill_price = self.pill_prices.get(recipe.pill_id)
        if pill_price is None:
            result.add_warning(f"配方 {recipe.id} 对应的丹药 {recipe.pill_id} 价格未找到")
            return
        
        ratio = self.cost_calculator.get_cost_ratio(recipe.cost, pill_price)
        if not self.cost_calculator.validate_cost_balance(recipe.cost, pill_price):
            result.add_warning(
                f"配方 {recipe.id} 的成本比率为 {ratio:.1%}，"
                f"超出推荐范围 ({COST_RATIO_MIN:.0%}-{COST_RATIO_MAX:.0%})"
            )
