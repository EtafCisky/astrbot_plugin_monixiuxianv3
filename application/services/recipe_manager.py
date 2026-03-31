"""配方管理器服务"""
import json
from typing import List, Optional, Dict
from pathlib import Path

from ...domain.models.recipe import Recipe
from .recipe_validator import RecipeValidator, ValidationResult


class RecipeManager:
    """配方管理器，负责加载、验证和查询配方"""
    
    def __init__(self, recipes_file_path: Optional[str] = None):
        """
        初始化配方管理器
        
        Args:
            recipes_file_path: 配方文件路径，如果为None则使用默认路径
        """
        if recipes_file_path is None:
            # 使用插件目录的config路径
            recipes_file_path = str(
                Path(__file__).parent.parent.parent / "config" / "alchemy_recipes.json"
            )
        self.recipes_file_path = recipes_file_path
        self.recipes: List[Recipe] = []
        self.recipes_by_id: Dict[str, Recipe] = {}
        self.recipes_by_pill_id: Dict[str, Recipe] = {}
        self.recipes_by_name: Dict[str, Recipe] = {}
        self.validator = RecipeValidator()
    
    def load_recipes(self, file_path: Optional[str] = None) -> List[Recipe]:
        """
        从JSON文件加载所有配方
        
        Args:
            file_path: 配方文件路径，如果为None则使用初始化时的路径
            
        Returns:
            配方列表
            
        Raises:
            FileNotFoundError: 配方文件不存在
            json.JSONDecodeError: JSON格式错误
            ValueError: 数据结构错误
        """
        if file_path is None:
            file_path = self.recipes_file_path
        
        # 检查文件是否存在
        if not Path(file_path).exists():
            raise FileNotFoundError(f"配方文件不存在: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                recipes_data = json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"配方文件格式错误: {e.msg}",
                e.doc,
                e.pos
            )
        
        if not isinstance(recipes_data, list):
            raise ValueError("配方数据必须是数组格式")
        
        self.recipes = []
        self.recipes_by_id = {}
        self.recipes_by_pill_id = {}
        self.recipes_by_name = {}
        
        for recipe_data in recipes_data:
            try:
                recipe = Recipe.from_dict(recipe_data)
                self.add_recipe(recipe)
            except KeyError as e:
                raise ValueError(f"配方缺少必需字段: {e}")
            except Exception as e:
                raise ValueError(f"配方数据错误: {e}")
        
        return self.recipes
    
    def add_recipe(self, recipe: Recipe):
        """
        添加新配方
        
        Args:
            recipe: 要添加的配方
            
        Raises:
            ValueError: 配方ID重复
        """
        if recipe.id in self.recipes_by_id:
            raise ValueError(f"配方ID重复: {recipe.id}")
        
        self.recipes.append(recipe)
        self.recipes_by_id[recipe.id] = recipe
        self.recipes_by_pill_id[recipe.pill_id] = recipe
        self.recipes_by_name[recipe.name] = recipe
    
    def get_recipe_by_id(self, recipe_id: str) -> Optional[Recipe]:
        """
        通过配方ID查询配方
        
        Args:
            recipe_id: 配方ID
            
        Returns:
            配方对象，如果不存在返回None
        """
        return self.recipes_by_id.get(recipe_id)
    
    def get_recipe_by_pill_id(self, pill_id: str) -> Optional[Recipe]:
        """
        通过丹药ID查询配方
        
        Args:
            pill_id: 丹药ID
            
        Returns:
            配方对象，如果不存在返回None
        """
        return self.recipes_by_pill_id.get(pill_id)
    
    def get_recipe_by_name(self, name: str) -> Optional[Recipe]:
        """
        通过丹药名称查询配方
        
        Args:
            name: 丹药名称
            
        Returns:
            配方对象，如果不存在返回None
        """
        return self.recipes_by_name.get(name)
    
    def get_recipes_by_rank(self, rank: str) -> List[Recipe]:
        """
        查询指定品质的所有配方
        
        Args:
            rank: 品质等级
            
        Returns:
            配方列表
        """
        return [recipe for recipe in self.recipes if recipe.rank == rank]
    
    def validate_recipe(self, recipe: Recipe) -> ValidationResult:
        """
        验证配方的有效性
        
        Args:
            recipe: 要验证的配方
            
        Returns:
            验证结果
        """
        return self.validator.validate_recipe(recipe)
    
    def validate_all_recipes(self) -> Dict[str, ValidationResult]:
        """
        验证所有已加载的配方
        
        Returns:
            配方ID到验证结果的映射
        """
        results = {}
        for recipe in self.recipes:
            results[recipe.id] = self.validate_recipe(recipe)
        return results
    
    def save_recipes(self, file_path: Optional[str] = None):
        """
        保存配方到JSON文件
        
        Args:
            file_path: 保存路径，如果为None则使用初始化时的路径
        """
        if file_path is None:
            file_path = self.recipes_file_path
        
        recipes_data = [recipe.to_dict() for recipe in self.recipes]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(recipes_data, f, ensure_ascii=False, indent=2)
    
    def get_all_recipes(self) -> List[Recipe]:
        """
        获取所有配方
        
        Returns:
            配方列表
        """
        return self.recipes.copy()
