"""田地仓储"""
from typing import Optional, List

from ...domain.models.spirit_field import Plot, PlantedHerb
from ..storage import JSONStorage
from .spirit_field_repo import SpiritFieldRepository


class PlotRepository:
    """
    田地仓储实现
    
    提供田地级别的操作接口,但实际上通过 SpiritFieldRepository 操作
    因为 Plot 是 SpiritField 聚合根的一部分,不应该独立持久化
    """
    
    def __init__(self, storage: JSONStorage, spirit_field_repo: SpiritFieldRepository):
        """
        初始化田地仓储
        
        Args:
            storage: JSON 存储管理器
            spirit_field_repo: 灵田仓储
        """
        self.storage = storage
        self.spirit_field_repo = spirit_field_repo
    
    def get_by_user_id(self, user_id: str) -> List[Plot]:
        """
        根据用户ID获取所有田地
        
        Args:
            user_id: 用户ID
            
        Returns:
            田地列表,如果灵田不存在则返回空列表
        """
        spirit_field = self.spirit_field_repo.get_by_user_id(user_id)
        if spirit_field is None:
            return []
        return spirit_field.plots
    
    def create_plots(self, user_id: str, count: int) -> List[Plot]:
        """
        为用户创建指定数量的田地
        
        Args:
            user_id: 用户ID
            count: 要创建的田地数量
            
        Returns:
            创建的田地列表
        """
        spirit_field = self.spirit_field_repo.get_by_user_id(user_id)
        if spirit_field is None:
            raise ValueError(f"用户 {user_id} 的灵田不存在")
        
        # 创建新田地
        new_plots = []
        for i in range(count):
            new_plot_id = len(spirit_field.plots) + 1
            new_plot = Plot(
                plot_id=new_plot_id,
                user_id=user_id,
                planted_herb=None
            )
            spirit_field.plots.append(new_plot)
            new_plots.append(new_plot)
        
        # 保存灵田
        self.spirit_field_repo.save(spirit_field)
        
        return new_plots
    
    def update_plot(self, user_id: str, plot_id: int, planted_herb: Optional[PlantedHerb]) -> None:
        """
        更新田地的种植信息
        
        Args:
            user_id: 用户ID
            plot_id: 田地ID
            planted_herb: 已种植的药草,None表示清空田地
        """
        spirit_field = self.spirit_field_repo.get_by_user_id(user_id)
        if spirit_field is None:
            raise ValueError(f"用户 {user_id} 的灵田不存在")
        
        # 查找并更新田地
        plot_found = False
        for plot in spirit_field.plots:
            if plot.plot_id == plot_id:
                plot.planted_herb = planted_herb
                plot_found = True
                break
        
        if not plot_found:
            raise ValueError(f"田地 {plot_id} 不存在")
        
        # 保存灵田
        self.spirit_field_repo.save(spirit_field)
    
    def delete_plot(self, user_id: str, plot_id: int) -> None:
        """
        删除田地(清空种植信息)
        
        Args:
            user_id: 用户ID
            plot_id: 田地ID
        """
        # 删除田地实际上就是清空种植信息
        self.update_plot(user_id, plot_id, None)
    
    def get_plot_by_id(self, user_id: str, plot_id: int) -> Optional[Plot]:
        """
        根据田地ID获取单个田地
        
        Args:
            user_id: 用户ID
            plot_id: 田地ID
            
        Returns:
            田地对象,不存在则返回None
        """
        plots = self.get_by_user_id(user_id)
        for plot in plots:
            if plot.plot_id == plot_id:
                return plot
        return None
