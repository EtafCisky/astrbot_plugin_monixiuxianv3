"""银行命令处理器"""
import time
from typing import AsyncGenerator
from astrbot.api.event import AstrMessageEvent

from ...application.services.bank_service import BankService
from ...core.exceptions import GameException


class BankHandler:
    """银行命令处理器"""
    
    def __init__(self, bank_service: BankService):
        self.bank_service = bank_service
    
    async def handle_bank_info(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理查看银行信息命令"""
        try:
            user_id = event.get_sender_id()
            
            # 获取银行信息
            info = self.bank_service.get_bank_info(user_id)
            
            # 从银行信息中获取玩家灵石（bank_service 内部已经获取了 player）
            # 我们需要重新获取一次来显示当前持有灵石
            from ...core.container import Container
            from ...core.config import ConfigManager
            
            # 这里需要从外部传入 config_manager，暂时使用 bank_service 的
            # 直接从 bank_service 获取 player_repo
            player = self.bank_service.player_repo.get_player(user_id)
            
            msg_lines = [
                "🏦 灵石银行",
                "━━━━━━━━━━━━━━━",
                f"💰 存款余额：{info.balance:,} 灵石",
                f"📈 待领利息：{info.pending_interest:,} 灵石",
                f"📊 日利率：0.1%（复利）",
                "━━━━━━━━━━━━━━━",
                f"💎 持有灵石：{player.gold:,}",
            ]
            
            # 显示贷款信息
            if info.has_loan():
                loan_info = self.bank_service.get_loan_info(user_id)
                if loan_info:
                    loan_type_name = "突破贷款" if loan_info.loan_type == "breakthrough" else "普通贷款"
                    status = "⚠️ 已逾期！" if loan_info.is_overdue else f"剩余 {loan_info.days_remaining} 天"
                    msg_lines.extend([
                        "━━━━━━━━━━━━━━━",
                        f"📋 当前贷款（{loan_type_name}）",
                        f"   本金：{loan_info.principal:,} 灵石",
                        f"   当前利息：{loan_info.current_interest:,} 灵石",
                        f"   应还总额：{loan_info.total_due:,} 灵石",
                        f"   状态：{status}",
                    ])
            
            msg_lines.extend([
                "━━━━━━━━━━━━━━━",
                "💡 指令：",
                "  存灵石 <数量>",
                "  取灵石 <数量>",
                "  领取利息",
                "  贷款 <数量>",
                "  还款",
            ])
            
            yield event.plain_result("\n".join(msg_lines))
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"查询银行信息失败：{e}")
    
    async def handle_deposit(self, event: AstrMessageEvent, amount: str = "") -> AsyncGenerator:
        """处理存款命令"""
        try:
            user_id = event.get_sender_id()
            
            # 解析金额
            if not amount:
                yield event.plain_result("❌ 请输入存款金额，例如：存灵石 10000")
                return
            
            try:
                amount_int = int(amount)
            except ValueError:
                yield event.plain_result("❌ 金额必须是数字")
                return
            
            result = self.bank_service.deposit(user_id, amount_int)
            yield event.plain_result(f"✅ {result}")
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"存款失败：{e}")
    
    async def handle_withdraw(self, event: AstrMessageEvent, amount: str = "") -> AsyncGenerator:
        """处理取款命令"""
        try:
            user_id = event.get_sender_id()
            
            # 解析金额
            if not amount:
                yield event.plain_result("❌ 请输入取款金额，例如：取灵石 10000")
                return
            
            try:
                amount_int = int(amount)
            except ValueError:
                yield event.plain_result("❌ 金额必须是数字")
                return
            
            result = self.bank_service.withdraw(user_id, amount_int)
            yield event.plain_result(f"✅ {result}")
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"取款失败：{e}")
    
    async def handle_claim_interest(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理领取利息命令"""
        try:
            user_id = event.get_sender_id()
            result = self.bank_service.claim_interest(user_id)
            yield event.plain_result(f"✅ {result}")
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"领取利息失败：{e}")
    
    async def handle_loan(self, event: AstrMessageEvent, amount: str = "") -> AsyncGenerator:
        """处理贷款命令"""
        try:
            user_id = event.get_sender_id()
            
            # 如果没有输入金额，显示帮助
            if not amount:
                yield event.plain_result(
                    "🏦 贷款说明\n"
                    "━━━━━━━━━━━━━━━\n"
                    "📌 普通贷款：\n"
                    "   日利率：0.5%\n"
                    "   期限：7天\n"
                    "   额度：1,000 - 1,000,000 灵石\n"
                    "━━━━━━━━━━━━━━━\n"
                    "⚠️ 请按时还款，避免逾期\n"
                    "━━━━━━━━━━━━━━━\n"
                    "💡 用法：贷款 <金额>\n"
                    "   例如：贷款 50000"
                )
                return
            
            # 解析金额
            try:
                amount_int = int(amount)
            except ValueError:
                yield event.plain_result("❌ 金额必须是数字")
                return
            
            result = self.bank_service.borrow(user_id, amount_int, "normal")
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"贷款失败：{e}")
    
    async def handle_repay(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理还款命令"""
        try:
            user_id = event.get_sender_id()
            result = self.bank_service.repay(user_id)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"还款失败：{e}")
    
    async def handle_breakthrough_loan(self, event: AstrMessageEvent, amount: str = "") -> AsyncGenerator:
        """处理突破贷款命令"""
        try:
            user_id = event.get_sender_id()
            
            # 如果没有输入金额，显示帮助
            if not amount:
                yield event.plain_result(
                    "🏦 突破贷款说明\n"
                    "━━━━━━━━━━━━━━━\n"
                    "📌 专为突破准备的短期贷款：\n"
                    "   日利率：0.8%（较高）\n"
                    "   期限：3天（较短）\n"
                    "   额度：1,000 - 1,000,000 灵石\n"
                    "━━━━━━━━━━━━━━━\n"
                    "✨ 突破成功后自动还款\n"
                    "━━━━━━━━━━━━━━━\n"
                    "⚠️ 请按时还款，避免逾期\n"
                    "━━━━━━━━━━━━━━━\n"
                    "💡 用法：突破贷款 <金额>"
                )
                return
            
            # 解析金额
            try:
                amount_int = int(amount)
            except ValueError:
                yield event.plain_result("❌ 金额必须是数字")
                return
            
            result = self.bank_service.borrow(user_id, amount_int, "breakthrough")
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"突破贷款失败：{e}")
