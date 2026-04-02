"""玩家命令处理器"""
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import At

from ...application.services.player_service import PlayerService
from ...core.exceptions import (
    PlayerAlreadyExistsException,
    InvalidParameterException
)
from ...domain.enums import CultivationType, PlayerState
from ...utils.spirit_root_generator import SpiritRootGenerator
from ..decorators import require_player
from ..formatters import PlayerFormatter


class PlayerHandler:
    """玩家命令处理器"""
    
    def __init__(
        self,
        player_service: PlayerService,
        spirit_root_generator: SpiritRootGenerator,
        container=None
    ):
        self.player_service = player_service
        self.spirit_root_generator = spirit_root_generator
        self.container = container
    
    async def handle_create_player(
        self,
        event: AstrMessageEvent,
        cultivation_type: str = ""
    ):
        """
        处理创建角色命令
        
        Args:
            event: 消息事件
            cultivation_type: 修炼类型（"灵修"或"体修"）
        """
        user_id = event.get_sender_id()
        
        # 如果没有提供修炼类型，显示帮助信息
        if not cultivation_type or cultivation_type.strip() == "":
            help_msg = PlayerFormatter.format_create_help()
            yield event.plain_result(help_msg)
            return
        
        # 验证修炼类型
        cultivation_type = cultivation_type.strip()
        try:
            cult_type = CultivationType.from_string(cultivation_type)
        except ValueError:
            yield event.plain_result("❌ 职业选择错误！请选择「灵修」或「体修」。")
            return
        
        # 创建玩家
        try:
            # 获取QQ昵称
            sender_name = event.get_sender_name()
            
            player = self.player_service.create_player(user_id, cult_type, sender_name)
            
            # 获取灵根信息用于显示
            root_name = player.spiritual_root.replace("灵根", "")
            spirit_root_info = self.spirit_root_generator.generate_random_root()
            # 这里简化处理，实际应该从已生成的灵根获取描述
            # 为了演示，我们重新查找描述
            from ...utils.spirit_root_generator import SpiritRootGenerator
            description = SpiritRootGenerator.ROOT_DESCRIPTIONS.get(
                root_name,
                "【未知】神秘的灵根"
            )
            
            # 创建临时的灵根信息对象用于格式化
            from ...domain.value_objects import SpiritRootInfo
            temp_root_info = SpiritRootInfo(
                name=root_name,
                speed_multiplier=1.0,
                description=description
            )
            
            # 格式化输出
            sender_name = event.get_sender_name()
            message = PlayerFormatter.format_create_success(
                player,
                temp_root_info,
                sender_name
            )
            
            yield event.plain_result(message)
            
        except PlayerAlreadyExistsException:
            yield event.plain_result("❌ 道友，你已踏入仙途，无需重复此举。")
        except Exception as e:
            yield event.plain_result(f"❌ 创建角色失败：{str(e)}")
    
    @require_player
    async def handle_player_info(self, event: AstrMessageEvent, player):
        """
        处理查看信息命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
        """
        try:
            # 获取境界名称
            level_name = self.player_service.get_level_name(player)
            
            # 获取突破所需修为
            required_exp = self.player_service.get_required_exp(player)
            
            # 获取装备属性加成
            from ...application.services.equipment_service import EquipmentService
            from ...infrastructure.repositories.equipment_repo import EquipmentRepository
            from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository
            
            equipment_repo = EquipmentRepository(
                self.player_service.player_repo.storage,
                self.container.config_manager().config_dir
            )
            storage_ring_repo = StorageRingRepository(self.player_service.player_repo.storage)
            
            equipment_service = EquipmentService(
                equipment_repo,
                self.player_service.player_repo,
                storage_ring_repo
            )
            equipment_bonuses = equipment_service.get_equipment_bonuses(player.user_id)
            
            # 计算战力（包含装备加成）
            combat_power = player.calculate_power()
            combat_power += (
                equipment_bonuses.magic_damage +
                equipment_bonuses.physical_damage +
                equipment_bonuses.magic_defense +
                equipment_bonuses.physical_defense +
                equipment_bonuses.mental_power // 10
            )
            
            # 获取宗门信息（暂时使用默认值）
            sect_name = "无宗门"
            position_name = "散修"
            
            # 格式化输出
            message = PlayerFormatter.format_player_info(
                player,
                level_name,
                required_exp,
                combat_power,
                sect_name,
                position_name,
                equipment_bonuses
            )
            
            yield event.plain_result(message)
            
        except Exception as e:
            yield event.plain_result(f"❌ 查看信息失败：{str(e)}")
    
    @require_player
    async def handle_check_in(self, event: AstrMessageEvent, player):
        """
        处理签到命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
        """
        try:
            # 执行签到
            reward_gold = self.player_service.check_in(player)
            
            # 格式化输出
            message = PlayerFormatter.format_check_in_success(
                reward_gold,
                player.gold
            )
            
            yield event.plain_result(message)
            
        except ValueError as e:
            yield event.plain_result(f"❌ {str(e)}\n请明日再来。")
        except Exception as e:
            yield event.plain_result(f"❌ 签到失败：{str(e)}")
    
    @require_player
    async def handle_change_nickname(
        self,
        event: AstrMessageEvent,
        player,
        new_nickname: str = ""
    ):
        """
        处理改道号命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
            new_nickname: 新道号
        """
        if not new_nickname or new_nickname.strip() == "":
            yield event.plain_result(
                "❌ 请提供新道号\n"
                "💡 使用方法：改道号 新的道号"
            )
            return
        
        try:
            # 修改道号
            self.player_service.change_nickname(player, new_nickname)
            
            # 格式化输出
            message = PlayerFormatter.format_nickname_changed(new_nickname)
            
            yield event.plain_result(message)
            
        except InvalidParameterException as e:
            yield event.plain_result(f"❌ {e.message}")
        except Exception as e:
            yield event.plain_result(f"❌ 修改道号失败：{str(e)}")

    async def handle_rebirth(
        self,
        event: AstrMessageEvent,
        confirm_text: str = ""
    ):
        """
        处理弃道重修命令
        
        Args:
            event: 消息事件
            confirm_text: 确认文本（必须为"确认"才执行）
        """
        import time
        from ...core.exceptions import BusinessException
        
        user_id = event.get_sender_id()
        
        # 检查玩家是否存在
        player = self.player_service.get_player(user_id)
        if not player:
            yield event.plain_result(
                "❌ 你还未踏入修仙之路！\n"
                "💡 发送「我要修仙」开始你的修仙之旅"
            )
            return
        
        # 检查3天冷却
        current_time = int(time.time())
        cooldown_key = f"rebirth_cooldown_{user_id}"
        
        # 从系统配置获取上次重修时间
        config_repo = None
        try:
            # 使用注入的容器获取仓储
            if self.container:
                from ...infrastructure.repositories.system_config_repo import SystemConfigRepository
                config_repo = SystemConfigRepository(self.container.json_storage())
            
            last_rebirth_str = config_repo.get_config(cooldown_key) if config_repo else None
            if last_rebirth_str:
                last_rebirth_time = int(last_rebirth_str)
                cooldown_seconds = 3 * 24 * 3600  # 3天
                
                if current_time - last_rebirth_time < cooldown_seconds:
                    remaining = cooldown_seconds - (current_time - last_rebirth_time)
                    remaining_days = remaining // 86400
                    remaining_hours = (remaining % 86400) // 3600
                    
                    yield event.plain_result(
                        f"❌ 弃道重修冷却中！\n"
                        f"还需等待：{remaining_days}天{remaining_hours}小时"
                    )
                    return
        except Exception as e:
            # 如果获取配置失败，允许继续（可能是首次使用）
            pass
        
        # 检查玩家状态
        if player.state != PlayerState.IDLE:
            yield event.plain_result(
                "❌ 你当前正在进行其他活动，无法弃道重修！\n"
                "请先完成当前活动（闭关/历练/秘境等）"
            )
            return
        
        # 检查是否有贷款
        try:
            # 使用注入的容器获取仓储
            bank_repo = None
            if self.container:
                from ...infrastructure.repositories.bank_repo import BankRepository
                bank_repo = BankRepository(self.container.json_storage())
            
            active_loans = bank_repo.get_active_loans(user_id) if bank_repo else []
            if active_loans:
                yield event.plain_result(
                    "❌ 你还有未还清的贷款，无法弃道重修！\n"
                    "请先使用「还款」命令还清所有贷款"
                )
                return
        except Exception:
            # 如果检查失败，允许继续
            pass
        
        # 如果没有提供确认文本，显示警告
        if not confirm_text or confirm_text.strip() != "确认":
            yield event.plain_result(
                "⚠️ 弃道重修将删除当前角色的所有数据，并无法撤回！\n"
                "限制：每3天只能重修一次，且必须在空闲状态、无贷款时使用。\n"
                "━━━━━━━━━━━━━━━\n"
                "若你已做好准备，请发送：\n"
                "弃道重修 确认"
            )
            return
        
        # 执行删除
        try:
            self.player_service.delete_player(user_id)
            
            # 记录重修时间
            try:
                if config_repo:
                    config_repo.set_config(cooldown_key, str(current_time))
            except Exception:
                pass
            
            yield event.plain_result(
                "💀 你选择了弃道重修，旧生一切化为尘埃。\n"
                "━━━━━━━━━━━━━━━\n"
                "可立即使用「我要修仙」重新踏上仙途。\n"
                "（3天内不可再次重修）"
            )
            
        except Exception as e:
            yield event.plain_result(f"❌ 弃道重修失败：{str(e)}")

    async def handle_admin_add_gold(
        self,
        event: AstrMessageEvent,
        args: str = ""
    ):
        """
        处理管理员增加灵石命令（需要管理员权限）
        
        Args:
            event: 消息事件
            args: 参数字符串，格式："数量 @用户" 或 "数量 用户ID"
        """
        # 手动检查管理员权限
        user_id = str(event.get_sender_id())
        
        # 从容器获取配置管理器
        if not self.container:
            yield event.plain_result("❌ 系统错误：容器未初始化")
            return
        
        config_manager = self.container.config_manager()
        admin_list = config_manager.settings.access_control.admins
        
        # 检查是否为管理员
        if not admin_list or user_id not in admin_list:
            yield event.plain_result(
                "❌ 权限不足！\n"
                "💡 此命令仅限管理员使用"
            )
            return
        
        # 解析参数
        if not args or args.strip() == "":
            yield event.plain_result(
                "❌ 参数错误！\n"
                "💡 使用方法：增加灵石 数量 @用户\n"
                "示例：增加灵石 10000 @张三"
            )
            return
        
        try:
            # 解析参数：数量
            parts = args.strip().split()
            if len(parts) < 1:
                yield event.plain_result(
                    "❌ 参数不足！\n"
                    "💡 使用方法：增加灵石 数量 @用户"
                )
                return
            
            # 获取数量
            try:
                amount = int(parts[0])
                if amount <= 0:
                    yield event.plain_result("❌ 数量必须大于0！")
                    return
            except ValueError:
                yield event.plain_result("❌ 数量必须是有效的数字！")
                return
            
            # 获取目标用户ID（参考combat_handler的_get_target_id方法）
            target_user_id = None
            
            # 优先从参数获取数字ID
            if len(parts) >= 2:
                cleaned = parts[1].strip().lstrip("@")
                if cleaned.isdigit():
                    target_user_id = cleaned
            
            # 如果参数中没有ID，从At组件获取
            if not target_user_id:
                message_chain = []
                if hasattr(event, "message_obj") and event.message_obj:
                    message_chain = getattr(event.message_obj, "message", []) or []
                
                # 遍历消息链，找到命令后面的At组件
                found_command = False
                for component in message_chain:
                    # 检查是否是文本组件且包含命令
                    if hasattr(component, "text"):
                        text = getattr(component, "text", "")
                        if "增加灵石" in text:
                            found_command = True
                            # 检查文本中是否包含数字ID（在命令之后）
                            # 例如："增加灵石 10000 123456789"
                            import re
                            match = re.search(r'增加灵石\s+\d+\s+(\d+)', text)
                            if match:
                                target_user_id = match.group(1)
                                break
                            continue
                    
                    # 如果已经找到命令，且当前是At组件
                    if found_command and isinstance(component, At):
                        # 尝试多个可能的属性名
                        candidate = None
                        for attr in ("qq", "target", "uin", "user_id"):
                            candidate = getattr(component, attr, None)
                            if candidate:
                                break
                        
                        if candidate:
                            target_user_id = str(candidate).lstrip("@")
                            break
            
            if not target_user_id:
                yield event.plain_result(
                    "❌ 未找到目标用户！\n"
                    "💡 使用方法：增加灵石 数量 @用户 或 增加灵石 数量 用户ID"
                )
                return
            
            # 检查目标玩家是否存在
            target_player = self.player_service.get_player(target_user_id)
            if not target_player:
                yield event.plain_result(
                    f"❌ 目标用户（{target_user_id}）还未踏入修仙之路！"
                )
                return
            
            # 增加灵石
            old_gold = target_player.gold
            target_player.gold += amount
            self.player_service.player_repo.save(target_player)
            
            # 格式化输出
            yield event.plain_result(
                "✅ 灵石增加成功！\n"
                "━━━━━━━━━━━━━━━\n"
                f"目标用户：{target_player.nickname}\n"
                f"增加数量：{amount:,} 灵石\n"
                f"原有灵石：{old_gold:,}\n"
                f"当前灵石：{target_player.gold:,}"
            )
            
        except Exception as e:
            yield event.plain_result(f"❌ 增加灵石失败：{str(e)}")

    async def handle_admin_reduce_gold(
        self,
        event: AstrMessageEvent,
        args: str = ""
    ):
        """
        处理管理员减少灵石命令（需要管理员权限）
        
        Args:
            event: 消息事件
            args: 参数字符串，格式："数量 @用户" 或 "数量 用户ID"
        """
        # 手动检查管理员权限
        user_id = str(event.get_sender_id())
        
        # 从容器获取配置管理器
        if not self.container:
            yield event.plain_result("❌ 系统错误：容器未初始化")
            return
        
        config_manager = self.container.config_manager()
        admin_list = config_manager.settings.access_control.admins
        
        # 检查是否为管理员
        if not admin_list or user_id not in admin_list:
            yield event.plain_result(
                "❌ 权限不足！\n"
                "💡 此命令仅限管理员使用"
            )
            return
        
        # 解析参数
        if not args or args.strip() == "":
            yield event.plain_result(
                "❌ 参数错误！\n"
                "💡 使用方法：减少灵石 数量 @用户\n"
                "示例：减少灵石 10000 @张三"
            )
            return
        
        try:
            # 解析参数：数量
            parts = args.strip().split()
            if len(parts) < 1:
                yield event.plain_result(
                    "❌ 参数不足！\n"
                    "💡 使用方法：减少灵石 数量 @用户"
                )
                return
            
            # 获取数量
            try:
                amount = int(parts[0])
                if amount <= 0:
                    yield event.plain_result("❌ 数量必须大于0！")
                    return
            except ValueError:
                yield event.plain_result("❌ 数量必须是有效的数字！")
                return
            
            # 获取目标用户ID（参考combat_handler的_get_target_id方法）
            target_user_id = None
            
            # 优先从参数获取数字ID
            if len(parts) >= 2:
                cleaned = parts[1].strip().lstrip("@")
                if cleaned.isdigit():
                    target_user_id = cleaned
            
            # 如果参数中没有ID，从At组件获取
            if not target_user_id:
                message_chain = []
                if hasattr(event, "message_obj") and event.message_obj:
                    message_chain = getattr(event.message_obj, "message", []) or []
                
                # 遍历消息链，找到命令后面的At组件
                found_command = False
                for component in message_chain:
                    # 检查是否是文本组件且包含命令
                    if hasattr(component, "text"):
                        text = getattr(component, "text", "")
                        if "减少灵石" in text:
                            found_command = True
                            # 检查文本中是否包含数字ID（在命令之后）
                            # 例如："减少灵石 10000 123456789"
                            import re
                            match = re.search(r'减少灵石\s+\d+\s+(\d+)', text)
                            if match:
                                target_user_id = match.group(1)
                                break
                            continue
                    
                    # 如果已经找到命令，且当前是At组件
                    if found_command and isinstance(component, At):
                        # 尝试多个可能的属性名
                        candidate = None
                        for attr in ("qq", "target", "uin", "user_id"):
                            candidate = getattr(component, attr, None)
                            if candidate:
                                break
                        
                        if candidate:
                            target_user_id = str(candidate).lstrip("@")
                            break
            
            if not target_user_id:
                yield event.plain_result(
                    "❌ 未找到目标用户！\n"
                    "💡 使用方法：减少灵石 数量 @用户 或 减少灵石 数量 用户ID"
                )
                return
            
            # 检查目标玩家是否存在
            target_player = self.player_service.get_player(target_user_id)
            if not target_player:
                yield event.plain_result(
                    f"❌ 目标用户（{target_user_id}）还未踏入修仙之路！"
                )
                return
            
            # 减少灵石
            old_gold = target_player.gold
            target_player.gold = max(0, target_player.gold - amount)  # 确保不会变成负数
            actual_reduced = old_gold - target_player.gold
            self.player_service.player_repo.save(target_player)
            
            # 格式化输出
            result_msg = "✅ 灵石减少成功！\n" + "━━━━━━━━━━━━━━━\n"
            result_msg += f"目标用户：{target_player.nickname}\n"
            result_msg += f"减少数量：{actual_reduced:,} 灵石\n"
            result_msg += f"原有灵石：{old_gold:,}\n"
            result_msg += f"当前灵石：{target_player.gold:,}"
            
            if actual_reduced < amount:
                result_msg += f"\n\n⚠️ 注意：目标用户灵石不足，实际减少 {actual_reduced:,} 灵石"
            
            yield event.plain_result(result_msg)
            
        except Exception as e:
            yield event.plain_result(f"❌ 减少灵石失败：{str(e)}")

    async def handle_admin_change_spirit_root(
        self,
        event: AstrMessageEvent,
        args: str = ""
    ):
        """
        处理管理员修改灵根命令（需要管理员权限）
        
        Args:
            event: 消息事件
            args: 参数字符串，格式："灵根类型 @用户" 或 "灵根类型 用户ID"
        """
        # 手动检查管理员权限
        user_id = str(event.get_sender_id())
        
        # 从容器获取配置管理器
        if not self.container:
            yield event.plain_result("❌ 系统错误：容器未初始化")
            return
        
        config_manager = self.container.config_manager()
        admin_list = config_manager.settings.access_control.admins
        
        # 检查是否为管理员
        if not admin_list or user_id not in admin_list:
            yield event.plain_result(
                "❌ 权限不足！\n"
                "💡 此命令仅限管理员使用"
            )
            return
        
        # 解析参数
        if not args or args.strip() == "":
            yield event.plain_result(
                "❌ 参数错误！\n"
                "💡 使用方法：修改灵根 灵根类型 @用户\n"
                "示例：修改灵根 天金灵根 @张三\n"
                "━━━━━━━━━━━━━━━\n"
                "可用灵根类型：\n"
                "• 伪灵根\n"
                "• 四灵根：金木水火、金木水土、金木火土、金水火土、木水火土\n"
                "• 三灵根：金木水、金木火、金木土、金水火、金水土、金火土、木水火、木水土、木火土、水火土\n"
                "• 双灵根：金木、金水、金火、金土、木水、木火、木土、水火、水土、火土\n"
                "• 五行单灵根：金、木、水、火、土\n"
                "• 变异灵根：雷、冰、风、暗、光\n"
                "• 天灵根：天金、天木、天水、天火、天土、天雷\n"
                "• 传说级：阴阳、融合\n"
                "• 神话级：混沌\n"
                "• 禁忌级：先天道体、神圣体质"
            )
            return
        
        try:
            # 解析参数：灵根类型
            parts = args.strip().split()
            if len(parts) < 1:
                yield event.plain_result(
                    "❌ 参数不足！\n"
                    "💡 使用方法：修改灵根 灵根类型 @用户"
                )
                return
            
            # 获取灵根类型
            spirit_root = parts[0].strip()
            
            # 验证灵根类型（添加"灵根"后缀如果没有）
            if not spirit_root.endswith("灵根"):
                spirit_root = spirit_root + "灵根"
            
            # 验证灵根是否有效（从 SpiritRootGenerator 获取所有灵根）
            valid_roots = [
                # 伪灵根
                "伪灵根",
                # 四灵根
                "金木水火灵根", "金木水土灵根", "金木火土灵根", "金水火土灵根", "木水火土灵根",
                # 三灵根
                "金木水灵根", "金木火灵根", "金木土灵根", "金水火灵根", "金水土灵根", "金火土灵根",
                "木水火灵根", "木水土灵根", "木火土灵根", "水火土灵根",
                # 双灵根
                "金木灵根", "金水灵根", "金火灵根", "金土灵根", "木水灵根", "木火灵根", "木土灵根",
                "水火灵根", "水土灵根", "火土灵根",
                # 五行单灵根
                "金灵根", "木灵根", "水灵根", "火灵根", "土灵根",
                # 变异灵根
                "雷灵根", "冰灵根", "风灵根", "暗灵根", "光灵根",
                # 天灵根
                "天金灵根", "天木灵根", "天水灵根", "天火灵根", "天土灵根", "天雷灵根",
                # 传说级
                "阴阳灵根", "融合灵根",
                # 神话级
                "混沌灵根",
                # 禁忌级体质
                "先天道体灵根", "神圣体质灵根"
            ]
            
            if spirit_root not in valid_roots:
                yield event.plain_result(
                    f"❌ 无效的灵根类型：{spirit_root}\n"
                    f"可用灵根：{'、'.join(valid_roots)}"
                )
                return
            
            # 获取目标用户ID（使用与增加灵石相同的逻辑）
            target_user_id = None
            
            # 优先从参数获取数字ID
            if len(parts) >= 2:
                cleaned = parts[1].strip().lstrip("@")
                if cleaned.isdigit():
                    target_user_id = cleaned
            
            # 如果参数中没有ID，从At组件获取
            if not target_user_id:
                message_chain = []
                if hasattr(event, "message_obj") and event.message_obj:
                    message_chain = getattr(event.message_obj, "message", []) or []
                
                # 遍历消息链，找到命令后面的At组件
                found_command = False
                for component in message_chain:
                    # 检查是否是文本组件且包含命令
                    if hasattr(component, "text"):
                        text = getattr(component, "text", "")
                        if "修改灵根" in text:
                            found_command = True
                            # 检查文本中是否包含数字ID（在命令之后）
                            import re
                            match = re.search(r'修改灵根\s+\S+\s+(\d+)', text)
                            if match:
                                target_user_id = match.group(1)
                                break
                            continue
                    
                    # 如果已经找到命令，且当前是At组件
                    if found_command and isinstance(component, At):
                        # 尝试多个可能的属性名
                        candidate = None
                        for attr in ("qq", "target", "uin", "user_id"):
                            candidate = getattr(component, attr, None)
                            if candidate:
                                break
                        
                        if candidate:
                            target_user_id = str(candidate).lstrip("@")
                            break
            
            if not target_user_id:
                yield event.plain_result(
                    "❌ 未找到目标用户！\n"
                    "💡 使用方法：修改灵根 灵根类型 @用户 或 修改灵根 灵根类型 用户ID"
                )
                return
            
            # 检查目标玩家是否存在
            target_player = self.player_service.get_player(target_user_id)
            if not target_player:
                yield event.plain_result(
                    f"❌ 目标用户（{target_user_id}）还未踏入修仙之路！"
                )
                return
            
            # 修改灵根
            old_root = target_player.spiritual_root
            target_player.spiritual_root = spirit_root
            self.player_service.player_repo.save(target_player)
            
            # 格式化输出
            yield event.plain_result(
                "✅ 灵根修改成功！\n"
                "━━━━━━━━━━━━━━━\n"
                f"目标用户：{target_player.nickname}\n"
                f"原有灵根：{old_root}\n"
                f"当前灵根：{target_player.spiritual_root}"
            )
            
        except Exception as e:
            yield event.plain_result(f"❌ 修改灵根失败：{str(e)}")

    async def handle_admin_add_experience(
        self,
        event: AstrMessageEvent,
        args: str = ""
    ):
        """
        处理管理员增加修为命令（需要管理员权限）
        
        Args:
            event: 消息事件
            args: 参数字符串，格式："数量 @用户" 或 "数量 用户ID"
        """
        # 手动检查管理员权限
        user_id = str(event.get_sender_id())
        
        # 从容器获取配置管理器
        if not self.container:
            yield event.plain_result("❌ 系统错误：容器未初始化")
            return
        
        config_manager = self.container.config_manager()
        admin_list = config_manager.settings.access_control.admins
        
        # 检查是否为管理员
        if not admin_list or user_id not in admin_list:
            yield event.plain_result(
                "❌ 权限不足！\n"
                "💡 此命令仅限管理员使用"
            )
            return
        
        # 解析参数
        if not args or args.strip() == "":
            yield event.plain_result(
                "❌ 参数错误！\n"
                "💡 使用方法：增加修为 数量 @用户\n"
                "示例：增加修为 100000 @张三"
            )
            return
        
        try:
            # 解析参数：数量
            parts = args.strip().split()
            if len(parts) < 1:
                yield event.plain_result(
                    "❌ 参数不足！\n"
                    "💡 使用方法：增加修为 数量 @用户"
                )
                return
            
            # 获取数量
            try:
                amount = int(parts[0])
                if amount <= 0:
                    yield event.plain_result("❌ 数量必须大于0！")
                    return
            except ValueError:
                yield event.plain_result("❌ 数量必须是有效的数字！")
                return
            
            # 获取目标用户ID（使用与增加灵石相同的逻辑）
            target_user_id = None
            
            # 优先从参数获取数字ID
            if len(parts) >= 2:
                cleaned = parts[1].strip().lstrip("@")
                if cleaned.isdigit():
                    target_user_id = cleaned
            
            # 如果参数中没有ID，从At组件获取
            if not target_user_id:
                message_chain = []
                if hasattr(event, "message_obj") and event.message_obj:
                    message_chain = getattr(event.message_obj, "message", []) or []
                
                # 遍历消息链，找到命令后面的At组件
                found_command = False
                for component in message_chain:
                    # 检查是否是文本组件且包含命令
                    if hasattr(component, "text"):
                        text = getattr(component, "text", "")
                        if "增加修为" in text:
                            found_command = True
                            # 检查文本中是否包含数字ID（在命令之后）
                            import re
                            match = re.search(r'增加修为\s+\d+\s+(\d+)', text)
                            if match:
                                target_user_id = match.group(1)
                                break
                            continue
                    
                    # 如果已经找到命令，且当前是At组件
                    if found_command and isinstance(component, At):
                        # 尝试多个可能的属性名
                        candidate = None
                        for attr in ("qq", "target", "uin", "user_id"):
                            candidate = getattr(component, attr, None)
                            if candidate:
                                break
                        
                        if candidate:
                            target_user_id = str(candidate).lstrip("@")
                            break
            
            if not target_user_id:
                yield event.plain_result(
                    "❌ 未找到目标用户！\n"
                    "💡 使用方法：增加修为 数量 @用户 或 增加修为 数量 用户ID"
                )
                return
            
            # 检查目标玩家是否存在
            target_player = self.player_service.get_player(target_user_id)
            if not target_player:
                yield event.plain_result(
                    f"❌ 目标用户（{target_user_id}）还未踏入修仙之路！"
                )
                return
            
            # 增加修为
            old_exp = target_player.experience
            target_player.experience += amount
            self.player_service.player_repo.save(target_player)
            
            # 格式化输出
            yield event.plain_result(
                "✅ 修为增加成功！\n"
                "━━━━━━━━━━━━━━━\n"
                f"目标用户：{target_player.nickname}\n"
                f"增加数量：{amount:,} 修为\n"
                f"原有修为：{old_exp:,}\n"
                f"当前修为：{target_player.experience:,}"
            )
            
        except Exception as e:
            yield event.plain_result(f"❌ 增加修为失败：{str(e)}")

    async def handle_admin_change_sect_position(
        self,
        event: AstrMessageEvent,
        args: str = ""
    ):
        """
        处理管理员修改宗门岗位命令（需要管理员权限）
        
        Args:
            event: 消息事件
            args: 参数字符串，格式："岗位ID @用户" 或 "岗位ID 用户ID"
        """
        # 手动检查管理员权限
        user_id = str(event.get_sender_id())
        
        # 从容器获取配置管理器
        if not self.container:
            yield event.plain_result("❌ 系统错误：容器未初始化")
            return
        
        config_manager = self.container.config_manager()
        admin_list = config_manager.settings.access_control.admins
        
        # 检查是否为管理员
        if not admin_list or user_id not in admin_list:
            yield event.plain_result(
                "❌ 权限不足！\n"
                "💡 此命令仅限管理员使用"
            )
            return
        
        # 解析参数
        if not args or args.strip() == "":
            yield event.plain_result(
                "❌ 参数错误！\n"
                "💡 使用方法：修改宗门岗位 岗位ID @用户\n"
                "示例：修改宗门岗位 0 @张三\n"
                "━━━━━━━━━━━━━━━\n"
                "岗位ID说明：\n"
                "• 0 - 宗主\n"
                "• 1 - 长老\n"
                "• 2 - 亲传弟子\n"
                "• 3 - 内门弟子\n"
                "• 4 - 外门弟子"
            )
            return
        
        try:
            # 解析参数：岗位ID
            parts = args.strip().split()
            if len(parts) < 1:
                yield event.plain_result(
                    "❌ 参数不足！\n"
                    "💡 使用方法：修改宗门岗位 岗位ID @用户"
                )
                return
            
            # 获取岗位ID
            try:
                position_id = int(parts[0])
                if position_id < 0 or position_id > 4:
                    yield event.plain_result("❌ 岗位ID必须在0-4之间！")
                    return
            except ValueError:
                yield event.plain_result("❌ 岗位ID必须是有效的数字（0-4）！")
                return
            
            # 岗位名称映射
            position_names = {
                0: "宗主",
                1: "长老",
                2: "亲传弟子",
                3: "内门弟子",
                4: "外门弟子"
            }
            
            # 获取目标用户ID（使用与增加灵石相同的逻辑）
            target_user_id = None
            
            # 优先从参数获取数字ID
            if len(parts) >= 2:
                cleaned = parts[1].strip().lstrip("@")
                if cleaned.isdigit():
                    target_user_id = cleaned
            
            # 如果参数中没有ID，从At组件获取
            if not target_user_id:
                message_chain = []
                if hasattr(event, "message_obj") and event.message_obj:
                    message_chain = getattr(event.message_obj, "message", []) or []
                
                # 遍历消息链，找到命令后面的At组件
                found_command = False
                for component in message_chain:
                    # 检查是否是文本组件且包含命令
                    if hasattr(component, "text"):
                        text = getattr(component, "text", "")
                        if "修改宗门岗位" in text:
                            found_command = True
                            # 检查文本中是否包含数字ID（在命令之后）
                            import re
                            match = re.search(r'修改宗门岗位\s+\d+\s+(\d+)', text)
                            if match:
                                target_user_id = match.group(1)
                                break
                            continue
                    
                    # 如果已经找到命令，且当前是At组件
                    if found_command and isinstance(component, At):
                        # 尝试多个可能的属性名
                        candidate = None
                        for attr in ("qq", "target", "uin", "user_id"):
                            candidate = getattr(component, attr, None)
                            if candidate:
                                break
                        
                        if candidate:
                            target_user_id = str(candidate).lstrip("@")
                            break
            
            if not target_user_id:
                yield event.plain_result(
                    "❌ 未找到目标用户！\n"
                    "💡 使用方法：修改宗门岗位 岗位ID @用户 或 修改宗门岗位 岗位ID 用户ID"
                )
                return
            
            # 检查目标玩家是否存在
            target_player = self.player_service.get_player(target_user_id)
            if not target_player:
                yield event.plain_result(
                    f"❌ 目标用户（{target_user_id}）还未踏入修仙之路！"
                )
                return
            
            # 检查玩家是否加入宗门
            if not target_player.sect_id or target_player.sect_id == 0:
                yield event.plain_result(
                    f"❌ 目标用户（{target_player.nickname}）还未加入任何宗门！"
                )
                return
            
            # 修改宗门岗位
            old_position = target_player.sect_position if target_player.sect_position is not None else 4
            old_position_name = position_names.get(old_position, "未知")
            
            target_player.sect_position = position_id
            self.player_service.player_repo.save(target_player)
            
            # 格式化输出
            yield event.plain_result(
                "✅ 宗门岗位修改成功！\n"
                "━━━━━━━━━━━━━━━\n"
                f"目标用户：{target_player.nickname}\n"
                f"原有岗位：{old_position_name}\n"
                f"当前岗位：{position_names[position_id]}"
            )
            
        except Exception as e:
            yield event.plain_result(f"❌ 修改宗门岗位失败：{str(e)}")

    async def handle_admin_add_item(
        self,
        event: AstrMessageEvent,
        args: str = ""
    ):
        """
        处理管理员增加道具命令（需要管理员权限）
        
        Args:
            event: 消息事件
            args: 参数字符串，格式："道具名称 数量 @用户" 或 "道具名称 数量 用户ID"
        """
        # 手动检查管理员权限
        user_id = str(event.get_sender_id())
        
        # 从容器获取配置管理器
        if not self.container:
            yield event.plain_result("❌ 系统错误：容器未初始化")
            return
        
        config_manager = self.container.config_manager()
        admin_list = config_manager.settings.access_control.admins
        
        # 检查是否为管理员
        if not admin_list or user_id not in admin_list:
            yield event.plain_result(
                "❌ 权限不足！\n"
                "💡 此命令仅限管理员使用"
            )
            return
        
        # 解析参数
        if not args or args.strip() == "":
            yield event.plain_result(
                "❌ 参数错误！\n"
                "💡 使用方法：增加道具 道具名称 数量 @用户\n"
                "示例：增加道具 灵草 10 @张三"
            )
            return
        
        try:
            # 调试：打印接收到的参数
            from astrbot.api import logger
            logger.info(f"【增加道具】接收到的args: '{args}'")
            logger.info(f"【增加道具】args类型: {type(args)}")
            
            # 尝试从消息文本中提取完整参数
            full_text = ""
            if hasattr(event, "message_str"):
                full_text = event.message_str
                logger.info(f"【增加道具】message_str: '{full_text}'")
            elif hasattr(event, "get_message_str"):
                full_text = event.get_message_str()
                logger.info(f"【增加道具】get_message_str(): '{full_text}'")
            
            # 如果能获取到完整消息，从中提取参数
            if full_text and "增加道具" in full_text:
                # 移除命令部分，只保留参数
                import re
                match = re.search(r'增加道具\s+(.+)', full_text)
                if match:
                    args = match.group(1).strip()
                    logger.info(f"【增加道具】从完整消息提取的args: '{args}'")
            
            # 解析参数：道具名称 数量 用户ID
            parts = args.strip().split()
            logger.info(f"【增加道具】分割后的parts: {parts}")
            logger.info(f"【增加道具】parts数量: {len(parts)}")
            
            # 至少需要3个参数：道具名 数量 用户ID
            if len(parts) < 3:
                yield event.plain_result(
                    "❌ 参数不足！\n"
                    "💡 使用方法：增加道具 道具名称 数量 @用户 或 增加道具 道具名称 数量 用户ID\n"
                    f"示例：增加道具 灵草 10 @张三 或 增加道具 灵草 10 123456789\n"
                    f"调试信息：接收到 {len(parts)} 个参数"
                )
                return
            
            # 获取道具名称
            item_name = parts[0]
            
            # 获取数量
            try:
                count = int(parts[1])
                if count <= 0:
                    yield event.plain_result("❌ 数量必须大于0！")
                    return
            except ValueError:
                yield event.plain_result("❌ 数量必须是有效的数字！")
                return
            
            # 获取目标用户ID
            target_user_id = None
            
            # 从第3个参数获取用户ID（可能带@符号）
            cleaned = parts[2].strip().lstrip("@")
            if cleaned.isdigit():
                target_user_id = cleaned
            
            # 如果参数中没有ID，从At组件获取
            if not target_user_id:
                message_chain = []
                if hasattr(event, "message_obj") and event.message_obj:
                    message_chain = getattr(event.message_obj, "message", []) or []
                
                # 遍历消息链，找到命令后面的At组件
                found_command = False
                for component in message_chain:
                    # 检查是否是文本组件且包含命令
                    if hasattr(component, "text"):
                        text = getattr(component, "text", "")
                        if "增加道具" in text:
                            found_command = True
                            # 检查文本中是否包含数字ID（在命令之后）
                            # 例如："增加道具 灵草 10 123456789"
                            import re
                            match = re.search(r'增加道具\s+\S+\s+\d+\s+(\d+)', text)
                            if match:
                                target_user_id = match.group(1)
                                break
                            continue
                    
                    # 如果已经找到命令，且当前是At组件
                    if found_command and isinstance(component, At):
                        # 尝试多个可能的属性名
                        candidate = None
                        for attr in ("qq", "target", "uin", "user_id"):
                            candidate = getattr(component, attr, None)
                            if candidate:
                                break
                        
                        if candidate:
                            target_user_id = str(candidate).lstrip("@")
                            break
            
            if not target_user_id:
                yield event.plain_result(
                    "❌ 未找到目标用户！\n"
                    "💡 使用方法：增加道具 道具名称 数量 @用户 或 增加道具 道具名称 数量 用户ID"
                )
                return
            
            # 检查目标玩家是否存在
            target_player = self.player_service.get_player(target_user_id)
            if not target_player:
                yield event.plain_result(
                    f"❌ 目标用户（{target_user_id}）还未踏入修仙之路！"
                )
                return
            
            # 获取储物戒服务
            storage_ring_service = self.container.storage_ring_service()
            
            # 添加道具到储物戒
            success, message = storage_ring_service.store_item(
                target_user_id,
                item_name,
                count,
                silent=True
            )
            
            if success:
                # 获取当前储物戒信息
                ring_info = storage_ring_service.get_storage_ring_info(target_user_id)
                item_count = storage_ring_service.get_item_count(target_user_id, item_name)
                
                # 格式化输出
                yield event.plain_result(
                    "✅ 道具增加成功！\n"
                    "━━━━━━━━━━━━━━━\n"
                    f"目标用户：{target_player.nickname}\n"
                    f"道具名称：{item_name}\n"
                    f"增加数量：{count}\n"
                    f"当前拥有：{item_count}\n"
                    f"储物戒：{ring_info['name']}（{ring_info['used']}/{ring_info['capacity']}格）"
                )
            else:
                yield event.plain_result(f"❌ 增加道具失败：{message}")
            
        except Exception as e:
            yield event.plain_result(f"❌ 增加道具失败：{str(e)}")
