"""储物戒命令处理器"""
from astrbot.api.event import AstrMessageEvent
from astrbot.api.all import At, Plain

from ...application.services.storage_ring_service import StorageRingService
from ...application.services.player_service import PlayerService
from ..decorators import require_player


class StorageRingHandler:
    """储物戒命令处理器"""
    
    def __init__(
        self,
        storage_ring_service: StorageRingService,
        player_service: PlayerService
    ):
        self.storage_ring_service = storage_ring_service
        self.player_service = player_service
    
    @require_player
    async def handle_storage_ring(self, event: AstrMessageEvent, player):
        """显示储物戒信息"""
        user_id = event.get_sender_id()
        display_name = event.get_sender_name()
        
        # 获取储物戒信息
        ring_info = self.storage_ring_service.get_storage_ring_info(user_id)
        
        lines = [
            f"=== {display_name} 的储物戒 ===\n",
            f"【{ring_info['name']}】（{ring_info['rank']}）\n",
            f"{ring_info['description']}\n",
            f"\n容量：{ring_info['used']}/{ring_info['capacity']}格\n",
            f"━━━━━━━━━━━━━━━\n",
        ]
        
        # 按分类显示存储的物品
        items = ring_info['items']
        if items:
            categorized = self.storage_ring_service.categorize_items(items)
            for category, cat_items in categorized.items():
                if cat_items:
                    lines.append(f"【{category}】\n")
                    for item_name, count in cat_items:
                        # 获取参考价格
                        ref_price = self.storage_ring_service.get_reference_price(item_name)
                        
                        if count > 1:
                            if ref_price:
                                lines.append(f"  · {item_name}×{count} (参考价:{ref_price})\n")
                            else:
                                lines.append(f"  · {item_name}×{count}\n")
                        else:
                            if ref_price:
                                lines.append(f"  · {item_name} (参考价:{ref_price})\n")
                            else:
                                lines.append(f"  · {item_name}\n")
        else:
            lines.append("【存储物品】空\n")
        
        # 空间警告
        warning = self.storage_ring_service.get_space_warning(user_id)
        if warning:
            lines.append(f"\n{warning}\n")
        
        lines.append(f"\n{'=' * 28}\n")
        lines.append(f"查看：查看物品 物品名\n")
        lines.append(f"搜索：搜索物品 关键词\n")
        lines.append(f"升级：更换储物戒 储物戒名")
        
        yield event.plain_result("".join(lines))
    
    @require_player
    async def handle_discard_item(self, event: AstrMessageEvent, player, args: str = ""):
        """丢弃储物戒中的物品"""
        user_id = event.get_sender_id()
        
        if not args or args.strip() == "":
            yield event.plain_result(
                f"请指定要丢弃的物品\n"
                f"用法：丢弃 物品名 [数量]\n"
                f"示例：丢弃 精铁 5\n"
                f"⚠️ 丢弃的物品将永久销毁！"
            )
            return
        
        args = args.strip()
        parts = args.rsplit(" ", 1)
        
        # 解析物品名和数量
        if len(parts) == 2 and parts[1].isdigit():
            item_name = parts[0]
            count = int(parts[1])
        else:
            item_name = args
            count = 1
        
        if count <= 0:
            yield event.plain_result("数量必须大于0")
            return
        
        # 丢弃物品
        success, message = self.storage_ring_service.discard_item(user_id, item_name, count)
        
        if success:
            yield event.plain_result(f"🗑️ {message}")
        else:
            yield event.plain_result(f"❌ {message}")
    
    @require_player
    async def handle_gift_item(self, event: AstrMessageEvent, player, args: str = ""):
        """赠予物品给其他玩家"""
        user_id = event.get_sender_id()
        sender_name = event.get_sender_name()
        
        target_id = None
        item_name = None
        count = 1
        
        # 从消息链中提取 At 组件和 Plain 文本
        text_parts = []
        at_components = []
        message_chain = event.message_obj.message if hasattr(event, 'message_obj') and event.message_obj else []
        
        for comp in message_chain:
            if isinstance(comp, Plain):
                text_parts.append(comp.text)
            elif isinstance(comp, At):
                at_components.append(comp)
        
        # 合并文本内容
        full_text = "".join(text_parts).strip()
        
        # 查找"赠予"命令的位置
        command_index = full_text.find("赠予")
        
        if command_index == -1:
            # 没找到命令，可能是通过命令触发的
            command_index = 0
        
        # 只处理命令之后的At组件
        # 通过检查At组件在消息链中的位置来判断
        found_command = False
        for comp in message_chain:
            if isinstance(comp, Plain) and "赠予" in comp.text:
                found_command = True
                continue
            
            # 只获取命令后面的At组件
            if found_command and isinstance(comp, At) and target_id is None:
                # 兼容多种At属性名
                for attr in ("qq", "target", "uin", "user_id"):
                    candidate = getattr(comp, attr, None)
                    if candidate:
                        target_id = str(candidate).lstrip("@")
                        break
                if target_id:
                    break
        
        # 移除命令前缀
        text_content = full_text
        for prefix in ["#赠予", "/赠予", "赠予"]:
            if text_content.startswith(prefix):
                text_content = text_content[len(prefix):].strip()
                break
        
        # 如果没有从At组件获取到target_id，尝试从文本解析纯数字QQ号
        if not target_id and text_content:
            parts = text_content.split(None, 1)
            if len(parts) >= 1:
                potential_id = parts[0].lstrip('@')
                if potential_id.isdigit() and len(potential_id) >= 5:
                    target_id = potential_id
                    text_content = parts[1].strip() if len(parts) > 1 else ""
        
        # 解析物品名和数量
        if text_content:
            parts = text_content.rsplit(" ", 1)
            if len(parts) == 2 and parts[1].isdigit():
                item_name = parts[0].strip()
                count = int(parts[1])
            else:
                item_name = text_content.strip()
        
        # 验证必要参数
        if not target_id:
            yield event.plain_result(
                f"请指定赠予对象\n"
                f"用法：赠予 @某人 物品名 [数量]\n"
                f"或：赠予 QQ号 物品名 [数量]\n"
                f"示例：赠予 123456789 精铁 5"
            )
            return
        
        if not item_name:
            yield event.plain_result("请指定要赠予的物品名称")
            return
        
        if count <= 0:
            yield event.plain_result("数量必须大于0")
            return
        
        # 赠予物品
        success, message = self.storage_ring_service.gift_item(
            sender_id=user_id,
            sender_name=sender_name,
            receiver_id=target_id,
            item_name=item_name,
            count=count
        )
        
        if success:
            yield event.plain_result(message)
        else:
            yield event.plain_result(f"❌ {message}")
    
    @require_player
    async def handle_upgrade_ring(self, event: AstrMessageEvent, player, ring_name: str = ""):
        """升级/更换储物戒"""
        user_id = event.get_sender_id()
        
        if not ring_name or ring_name.strip() == "":
            # 显示可用的储物戒列表
            rings = self.storage_ring_service.get_all_storage_rings()
            current_ring = self.storage_ring_service.storage_ring_repo.get_storage_ring_name(user_id)
            current_capacity = self.storage_ring_service.get_ring_capacity(current_ring)
            
            lines = [
                f"=== 储物戒列表 ===\n",
                f"当前：【{current_ring}】({current_capacity}格)\n",
                f"━━━━━━━━━━━━━━━\n",
            ]
            
            for ring in rings:
                # 标记当前装备
                if ring["name"] == current_ring:
                    marker = "✓ "
                elif ring["capacity"] <= current_capacity:
                    marker = "✗ "  # 容量不高于当前的
                else:
                    marker = "  "
                
                level_name = self.storage_ring_service._format_required_level(ring["required_level_index"])
                lines.append(
                    f"{marker}【{ring['name']}】({ring['rank']})\n"
                    f"    容量：{ring['capacity']}格 | 需求：{level_name}\n"
                )
            
            lines.append(f"\n用法：更换储物戒 储物戒名")
            lines.append("\n注：储物戒只能升级，不能卸下")
            
            yield event.plain_result("".join(lines))
            return
        
        ring_name = ring_name.strip()
        
        # 升级储物戒
        success, message = self.storage_ring_service.upgrade_ring(user_id, ring_name)
        
        if success:
            yield event.plain_result(f"✅ {message}")
        else:
            yield event.plain_result(f"❌ {message}")
    
    @require_player
    async def handle_search_item(self, event: AstrMessageEvent, player, keyword: str = ""):
        """搜索储物戒中的物品"""
        user_id = event.get_sender_id()
        
        if not keyword or keyword.strip() == "":
            yield event.plain_result(
                f"请指定搜索关键词\n"
                f"用法：搜索物品 关键词\n"
                f"示例：搜索物品 灵草"
            )
            return
        
        keyword = keyword.strip().lower()
        items = self.storage_ring_service.storage_ring_repo.get_storage_ring_items(user_id)
        
        # 模糊搜索
        matched = []
        for item_name, count in items.items():
            if keyword in item_name.lower():
                matched.append((item_name, count))
        
        if not matched:
            yield event.plain_result(f"未找到包含「{keyword}」的物品")
            return
        
        lines = [f"=== 搜索结果：{keyword} ===\n"]
        for item_name, count in matched:
            # 获取参考价格
            ref_price = self.storage_ring_service.get_reference_price(item_name)
            if ref_price:
                lines.append(f"  · {item_name}×{count} (参考价:{ref_price})\n")
            else:
                lines.append(f"  · {item_name}×{count}\n")
        lines.append(f"\n共找到 {len(matched)} 种物品")
        
        yield event.plain_result("".join(lines))
    
    @require_player
    async def handle_view_item(self, event: AstrMessageEvent, player, item_name: str = ""):
        """查看物品详细信息"""
        user_id = event.get_sender_id()
        
        if not item_name or item_name.strip() == "":
            yield event.plain_result(
                "请指定要查看的物品名称\n"
                "用法：查看物品 <物品名>\n"
                "示例：查看物品 筑基丹"
            )
            return
        
        item_name = item_name.strip()
        
        # 检查储物戒中是否有该物品
        items = self.storage_ring_service.storage_ring_repo.get_storage_ring_items(user_id)
        if item_name not in items:
            yield event.plain_result(f"❌ 储物戒中没有【{item_name}】")
            return
        
        count = items[item_name]
        
        # 获取物品详细信息
        item_info = self.storage_ring_service.get_item_details(item_name)
        
        if not item_info:
            yield event.plain_result(f"❌ 未找到【{item_name}】的详细信息")
            return
        
        # 格式化显示
        lines = [
            f"=== {item_name} ===\n",
            f"数量：{count}\n",
        ]
        
        if item_info.get('rank'):
            lines.append(f"品级：{item_info['rank']}\n")
        
        if item_info.get('type'):
            lines.append(f"类型：{item_info['type']}\n")
        
        if item_info.get('price'):
            lines.append(f"参考价：{item_info['price']}灵石\n")
        
        lines.append("━━━━━━━━━━━━━━━\n")
        
        # 显示效果
        if item_info.get('data'):
            effects = self.storage_ring_service.format_item_effects(item_info['data'])
            lines.append(f"效果：{effects}\n")
        else:
            lines.append("效果：无\n")
        
        # 显示介绍
        if item_info.get('description'):
            lines.append(f"介绍：{item_info['description']}\n")
        
        yield event.plain_result("".join(lines))
