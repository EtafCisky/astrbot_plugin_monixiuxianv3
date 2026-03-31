"""灵田命令处理器"""
from astrbot.api.event import AstrMessageEvent

from ...application.services.spirit_field_service import SpiritFieldService


class SpiritFieldHandler:
    """灵田命令处理器"""
    
    def __init__(self, spirit_field_service: SpiritFieldService):
        self.spirit_field_service = spirit_field_service
    
    async def handle_create_field(self, event: AstrMessageEvent):
        """处理 /开垦灵田 命令 - 创建或扩展灵田"""
        user_id = str(event.get_sender_id())
        
        try:
            # 创建或扩展灵田
            result = self.spirit_field_service.expand_field(user_id)
            yield event.plain_result(result)
            
        except Exception as e:
            yield event.plain_result(str(e))
    
    async def handle_field_status(self, event: AstrMessageEvent):
        """处理 /灵田 命令 - 显示灵田状态"""
        user_id = str(event.get_sender_id())
        
        try:
            # 获取灵田状态
            status = self.spirit_field_service.get_field_status(user_id)
            
            # 格式化输出
            msg = self._format_field_status(status)
            yield event.plain_result(msg)
            
        except Exception as e:
            yield event.plain_result(str(e))
    
    async def handle_plant(self, event: AstrMessageEvent, herb_name: str = ""):
        """处理 /种植 [药草名称] 命令 - 种植药草"""
        user_id = str(event.get_sender_id())
        
        if not herb_name:
            yield event.plain_result(
                "🌱 种植系统\n"
                "━━━━━━━━━━━━━━━\n"
                "在灵田中种植药草种子，等待成熟后收获材料！\n"
                "━━━━━━━━━━━━━━━\n"
                "💡 使用方法：\n"
                "  /种植 灵草\n"
                "  /种植 血莲子\n"
                "━━━━━━━━━━━━━━━\n"
                "📝 提示：\n"
                "• 需要先在种子商店购买种子\n"
                "• 不同品级药草成熟时间不同\n"
                "• 购买同一种子5次后永久解锁"
            )
            return
        
        try:
            # 种植药草
            result = self.spirit_field_service.plant_herb(user_id, herb_name)
            yield event.plain_result(result)
            
        except Exception as e:
            yield event.plain_result(str(e))
    
    async def handle_harvest(self, event: AstrMessageEvent):
        """处理 /收获 命令 - 收获所有成熟药草"""
        user_id = str(event.get_sender_id())
        
        try:
            # 收获所有成熟药草
            result = self.spirit_field_service.harvest_all(user_id)
            
            if not result["success"]:
                yield event.plain_result(result["message"])
                return
            
            # 格式化收获结果
            msg = self._format_harvest_result(result)
            yield event.plain_result(msg)
            
        except Exception as e:
            yield event.plain_result(str(e))
    
    async def handle_upgrade(self, event: AstrMessageEvent):
        """处理 /灵田升级 命令 - 升级灵田容量"""
        user_id = str(event.get_sender_id())
        
        try:
            # 升级灵田
            result = self.spirit_field_service.upgrade_field(user_id)
            yield event.plain_result(result)
            
        except Exception as e:
            yield event.plain_result(str(e))
    
    def _format_field_status(self, status: dict) -> str:
        """格式化灵田状态显示"""
        capacity = status["capacity"]
        used = status["used"]
        available = status["available"]
        mature_count = status["mature_count"]
        plots = status["plots"]
        
        msg = "🌾 灵田状态\n"
        msg += "━━━━━━━━━━━━━━━\n"
        msg += f"田地容量: {used}/{capacity}\n"
        msg += f"可用田地: {available}\n"
        msg += f"成熟药草: {mature_count}\n"
        msg += "━━━━━━━━━━━━━━━\n"
        
        # 显示每个田地的状态
        for plot in plots:
            plot_id = plot["plot_id"]
            status_text = plot["status"]
            
            if plot["herb_name"]:
                herb_name = plot["herb_name"]
                herb_rank = plot["herb_rank"]
                
                if plot["is_mature"]:
                    msg += f"田地{plot_id}: 【{herb_name}】({herb_rank}) ✅已成熟\n"
                else:
                    remaining = plot["remaining_time"]
                    msg += f"田地{plot_id}: 【{herb_name}】({herb_rank}) ⏳{remaining}\n"
            else:
                msg += f"田地{plot_id}: 空闲 💤\n"
        
        msg += "━━━━━━━━━━━━━━━\n"
        msg += "💡 提示：\n"
        msg += "• /种植 [药草名] - 种植药草\n"
        msg += "• /收获 - 收获成熟药草\n"
        msg += "• /灵田升级 - 扩展田地容量"
        
        return msg
    
    def _format_harvest_result(self, result: dict) -> str:
        """格式化收获结果显示"""
        harvested_herbs = result["harvested_herbs"]
        total_plots = result["total_plots"]
        
        msg = "🎉 收获成功！\n"
        msg += "━━━━━━━━━━━━━━━\n"
        msg += f"收获田地: {total_plots}个\n"
        msg += "━━━━━━━━━━━━━━━\n"
        msg += "获得材料:\n"
        
        for herb_name, amount in harvested_herbs.items():
            msg += f"  • {herb_name} × {amount}\n"
        
        msg += "━━━━━━━━━━━━━━━\n"
        msg += "💡 材料已存入储物袋"
        
        return msg
