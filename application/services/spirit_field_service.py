"""灵田服务"""
import json
import random
import time
from typing import Dict, Optional, Tuple

from ...core.config import ConfigManager
from ...core.constants import SpiritFieldConstants
from ...core.exceptions import XiuxianException
from ...domain.models.spirit_field import SpiritField, Plot, PlantedHerb
from ...infrastructure.repositories.spirit_field_repo import SpiritFieldRepository
from ...infrastructure.repositories.plot_repo import PlotRepository
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository


class SpiritFieldService:
    """灵田服务"""
    
    def __init__(
        self,
        spirit_field_repo: SpiritFieldRepository,
        plot_repo: PlotRepository,
        player_repo: PlayerRepository,
        storage_ring_repo: StorageRingRepository,
        config_manager: ConfigManager
    ):
        self.spirit_field_repo = spirit_field_repo
        self.plot_repo = plot_repo
        self.player_repo = player_repo
        self.storage_ring_repo = storage_ring_repo
        self.config_manager = config_manager
        
        # 加载可种植药草配置
        self._load_plantable_herbs()
    
    def _load_plantable_herbs(self) -> None:
        """从items.json加载可种植药草"""
        config_path = self.config_manager.config_dir / "items.json"
        if not config_path.exists():
            raise XiuxianException("配置文件items.json不存在")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            items_data = json.load(f)
        
        # 筛选出材料类型的药草
        self.plantable_herbs = {}
        for item_id, item_data in items_data.items():
            if item_data.get("type") == "材料":
                # 检查是否为药草（根据名称特征判断）
                name = item_data.get("name", "")
                # 药草通常包含这些字：草、芝、参、花、根、子、果、莲、藤等
                herb_keywords = ["草", "芝", "参", "花", "根", "子", "果", "莲", "藤", "叶", "药", "精", "皮", "荷", "杞", "楂", "梗", "芍", "芎", "风", "芥", "翘", "英", "夏", "术", "芪", "归", "苓"]
                if any(keyword in name for keyword in herb_keywords):
                    self.plantable_herbs[name] = {
                        "id": item_id,
                        "name": name,
                        "rank": item_data.get("rank", "凡品"),
                        "price": item_data.get("price", 100)
                    }
    
    def expand_field(self, user_id: str) -> str:
        """
        开垦灵田（创建或扩展）
        
        Args:
            user_id: 用户ID
            
        Returns:
            操作结果消息
        """
        # 检查玩家是否存在
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise XiuxianException("❌ 你还未踏入修仙之路,请先使用'我要修仙'创建角色")
        
        # 检查是否已有灵田
        spirit_field = self.spirit_field_repo.get_by_user_id(user_id)
        
        if spirit_field is None:
            # 首次开垦：创建灵田（初始3个田地，免费）
            spirit_field = self.spirit_field_repo.create(user_id, capacity=3)
            
            return (
                "🎉 开垦灵田成功！\n"
                "━━━━━━━━━━━━━━━\n"
                "获得3块灵田\n"
                "━━━━━━━━━━━━━━━\n"
                "💡 提示：\n"
                "• 使用「种子商店」购买种子\n"
                "• 使用「种植 [药草名]」种植药草\n"
                "• 使用「收获」收获成熟药草\n"
                "• 继续使用「开垦灵田」扩展田地"
            )
        else:
            # 扩展灵田：检查是否可以升级
            if not spirit_field.can_upgrade():
                max_capacity = SpiritFieldConstants.UPGRADE_CONFIG["max_capacity"]
                return f"❌ 灵田已达最大容量({max_capacity}块田地)"
            
            # 计算升级费用
            upgrade_cost = spirit_field.calculate_upgrade_cost()
            
            # 检查玩家灵石
            if player.gold < upgrade_cost:
                return (
                    f"❌ 灵石不足!\n"
                    f"开垦需要: {upgrade_cost:,}灵石\n"
                    f"当前拥有: {player.gold:,}灵石"
                )
            
            # 扣除灵石
            player.gold -= upgrade_cost
            self.player_repo.save(player)
            
            # 升级灵田
            old_capacity = spirit_field.capacity
            spirit_field.upgrade()
            new_capacity = spirit_field.capacity
            
            # 保存灵田
            self.spirit_field_repo.save(spirit_field)
            
            return (
                f"✅ 开垦灵田成功!\n"
                f"田地数量: {old_capacity} → {new_capacity}块\n"
                f"消耗灵石: {upgrade_cost:,}"
            )
    
    def get_or_create_spirit_field(self, user_id: str) -> SpiritField:
        """获取或创建灵田"""
        # 检查玩家是否存在
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise XiuxianException("❌ 你还未踏入修仙之路,请先使用'我要修仙'创建角色")
        
        # 获取或创建灵田
        spirit_field = self.spirit_field_repo.get_by_user_id(user_id)
        if spirit_field is None:
            spirit_field = self.spirit_field_repo.create(user_id, capacity=3)
        
        return spirit_field
    
    def plant_herb(self, user_id: str, herb_name: str) -> str:
        """
        种植药草
        
        种植逻辑:
        1. 检查药草是否可种植
        2. 检查种子是否已解锁
        3. 如果已解锁且储物袋无种子,自动给予1个种子
        4. 如果未解锁或储物袋有种子,验证并扣除种子
        5. 验证田地是否有空闲
        6. 记录种植信息
        
        Args:
            user_id: 用户ID
            herb_name: 药草名称
            
        Returns:
            种植结果消息
        """
        # 获取或创建灵田
        spirit_field = self.get_or_create_spirit_field(user_id)
        
        # 检查药草是否可种植
        if herb_name not in self.plantable_herbs:
            return f"❌ 【{herb_name}】不是可种植的药草"
        
        herb_info = self.plantable_herbs[herb_name]
        herb_id = herb_info["id"]
        herb_rank = herb_info["rank"]
        
        # 构造种子名称
        seed_name = f"{herb_name}种子"
        
        # 检查种子是否已解锁
        is_unlocked = spirit_field.is_seed_unlocked(herb_id)
        
        # 获取储物袋中的种子数量
        seed_count = self.storage_ring_repo.get_item_count(user_id, seed_name)
        
        # 种植逻辑: 如果已解锁且储物袋无种子,自动给予种子
        auto_provided = False
        if is_unlocked and seed_count == 0:
            # 自动给予1个种子
            items = self.storage_ring_repo.get_storage_ring_items(user_id)
            items[seed_name] = 1
            self.storage_ring_repo.set_storage_ring_items(user_id, items)
            seed_count = 1
            auto_provided = True
        
        # 验证种子数量
        if seed_count == 0:
            return f"❌ 你的储物袋中没有【{seed_name}】"
        
        # 检查是否有空闲田地
        available_plot = spirit_field.get_available_plot()
        if available_plot is None:
            occupied = len(spirit_field.get_occupied_plots())
            return f"❌ 灵田已满!当前{occupied}/{spirit_field.capacity}个田地已使用"
        
        # 扣除种子(如果不是自动给予的)
        if not auto_provided:
            items = self.storage_ring_repo.get_storage_ring_items(user_id)
            items[seed_name] -= 1
            if items[seed_name] <= 0:
                del items[seed_name]
            self.storage_ring_repo.set_storage_ring_items(user_id, items)
        
        # 计算成熟时间
        current_time = int(time.time())
        grow_time = self._calculate_grow_time(herb_rank)
        mature_time = current_time + grow_time
        
        # 种植药草
        available_plot.plant(
            herb_id=herb_id,
            herb_name=herb_name,
            herb_rank=herb_rank,
            plant_time=current_time,
            mature_time=mature_time
        )
        
        # 保存灵田
        self.spirit_field_repo.save(spirit_field)
        
        # 格式化成熟时间显示
        grow_time_display = self._format_grow_time(grow_time)
        
        # 构造返回消息
        occupied = len(spirit_field.get_occupied_plots())
        msg = f"🌱 成功种植【{herb_name}】!\n"
        
        if auto_provided:
            msg += f"✨ 【{seed_name}】已解锁,自动给予种子进行种植\n"
        
        msg += (
            f"品级: {herb_rank}\n"
            f"成熟时间: 约{grow_time_display}\n"
            f"当前种植: {occupied}/{spirit_field.capacity}"
        )
        
        return msg
    
    def _calculate_grow_time(self, herb_rank: str) -> int:
        """
        根据品级计算成熟时间
        
        Args:
            herb_rank: 药草品级
            
        Returns:
            成熟时间(秒)
        """
        config = SpiritFieldConstants.GROW_TIME_CONFIG.get(herb_rank)
        if config is None:
            # 默认使用凡品的时间
            config = SpiritFieldConstants.GROW_TIME_CONFIG["凡品"]
        
        min_time = config["min"]
        max_time = config["max"]
        
        # 在范围内随机生成成熟时间
        return random.randint(min_time, max_time)
    
    def _format_grow_time(self, seconds: int) -> str:
        """
        格式化成熟时间显示
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的时间字符串
        """
        if seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}分钟"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours}小时"
        else:
            days = seconds // 86400
            return f"{days}天"
    
    def get_field_status(self, user_id: str) -> Dict:
        """
        获取灵田状态
        
        Args:
            user_id: 用户ID
            
        Returns:
            灵田状态信息
        """
        # 检查玩家是否存在
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise XiuxianException("❌ 你还未踏入修仙之路,请先使用'我要修仙'创建角色")
        
        # 获取灵田（不自动创建）
        spirit_field = self.spirit_field_repo.get_by_user_id(user_id)
        if spirit_field is None:
            raise XiuxianException("❌ 你还没有灵田！\n💡 使用「开垦灵田」创建灵田")
        
        current_time = int(time.time())
        
        # 统计田地状态
        occupied_plots = spirit_field.get_occupied_plots()
        mature_plots = spirit_field.get_mature_plots(current_time)
        
        # 构造田地详情列表
        plot_details = []
        for plot in spirit_field.plots:
            if plot.is_empty():
                plot_details.append({
                    "plot_id": plot.plot_id,
                    "status": "空闲",
                    "herb_name": None,
                    "herb_rank": None,
                    "is_mature": False,
                    "remaining_time": None
                })
            else:
                is_mature = plot.is_mature(current_time)
                remaining_time = None if is_mature else plot.planted_herb.format_remaining_time(current_time)
                
                plot_details.append({
                    "plot_id": plot.plot_id,
                    "status": "已成熟" if is_mature else "生长中",
                    "herb_name": plot.planted_herb.herb_name,
                    "herb_rank": plot.planted_herb.herb_rank,
                    "is_mature": is_mature,
                    "remaining_time": remaining_time
                })
        
        return {
            "capacity": spirit_field.capacity,
            "used": len(occupied_plots),
            "available": spirit_field.capacity - len(occupied_plots),
            "mature_count": len(mature_plots),
            "plots": plot_details
        }
    
    def harvest_all(self, user_id: str) -> Dict:
        """
        收获所有成熟的药草
        
        Args:
            user_id: 用户ID
            
        Returns:
            收获结果信息
        """
        spirit_field = self.get_or_create_spirit_field(user_id)
        current_time = int(time.time())
        
        # 获取所有已成熟的田地
        mature_plots = spirit_field.get_mature_plots(current_time)
        
        if not mature_plots:
            return {
                "success": False,
                "message": "❌ 没有可收获的药草"
            }
        
        # 收获药草
        harvested_herbs = {}
        for plot in mature_plots:
            # 生成收获数量(2-4个随机)
            harvest_amount = self._generate_harvest_amount()
            
            # 收获药草
            herb = plot.harvest()
            
            # 累计收获数量
            if herb.herb_name in harvested_herbs:
                harvested_herbs[herb.herb_name] += harvest_amount
            else:
                harvested_herbs[herb.herb_name] = harvest_amount
        
        # 将药草添加到储物袋
        items = self.storage_ring_repo.get_storage_ring_items(user_id)
        for herb_name, amount in harvested_herbs.items():
            if herb_name in items:
                items[herb_name] += amount
            else:
                items[herb_name] = amount
        
        self.storage_ring_repo.set_storage_ring_items(user_id, items)
        
        # 保存灵田
        self.spirit_field_repo.save(spirit_field)
        
        return {
            "success": True,
            "harvested_herbs": harvested_herbs,
            "total_plots": len(mature_plots)
        }
    
    def _generate_harvest_amount(self) -> int:
        """
        生成收获数量(2-4随机)
        
        Returns:
            收获数量
        """
        return random.randint(2, 4)
