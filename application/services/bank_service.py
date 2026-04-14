"""银行服务"""
import time
from decimal import Decimal, ROUND_DOWN
from typing import Optional, List, Tuple

from astrbot.api import logger

from ...core.config import ConfigManager
from ...core.exceptions import GameException
from ...domain.models.bank import BankAccount, Loan, BankInfo, LoanInfo
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.bank_repo import BankRepository


class BankService:
    """银行服务"""
    
    # 默认配置
    DEFAULT_DAILY_INTEREST_RATE = 0.001  # 存款日利率 0.1%
    DEFAULT_MAX_DEPOSIT = 10000000  # 最大存款上限 1000万
    DEFAULT_LOAN_INTEREST_RATE = 0.005  # 贷款日利率 0.5%
    DEFAULT_LOAN_DURATION_DAYS = 7  # 贷款期限 7天
    DEFAULT_MAX_LOAN_AMOUNT = 1000000  # 最大贷款额度 100万
    DEFAULT_MIN_LOAN_AMOUNT = 1000  # 最小贷款额度 1000
    DEFAULT_BREAKTHROUGH_LOAN_RATE = 0.008  # 突破贷款日利率 0.8%
    DEFAULT_BREAKTHROUGH_LOAN_DURATION = 3  # 突破贷款期限 3天
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        bank_repo: BankRepository,
        config_manager: ConfigManager
    ):
        self.player_repo = player_repo
        self.bank_repo = bank_repo
        self.config_manager = config_manager
        
        # 使用默认配置（暂不支持从配置文件读取）
        self.daily_interest_rate = self.DEFAULT_DAILY_INTEREST_RATE
        self.max_deposit = self.DEFAULT_MAX_DEPOSIT
        self.loan_interest_rate = self.DEFAULT_LOAN_INTEREST_RATE
        self.loan_duration_days = self.DEFAULT_LOAN_DURATION_DAYS
        self.max_loan_amount = self.DEFAULT_MAX_LOAN_AMOUNT
        self.min_loan_amount = self.DEFAULT_MIN_LOAN_AMOUNT
        self.breakthrough_loan_rate = self.DEFAULT_BREAKTHROUGH_LOAN_RATE
        self.breakthrough_loan_duration = self.DEFAULT_BREAKTHROUGH_LOAN_DURATION
    
    # ===== 账户信息 =====
    
    def get_bank_info(self, user_id: str) -> BankInfo:
        """获取银行信息"""
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 获取银行账户
        account = self.bank_repo.get_bank_account(user_id)
        if not account:
            account = BankAccount(user_id=user_id, balance=0, last_interest_time=0)
        
        # 计算待领利息
        pending_interest = self._calculate_interest(account.balance, account.last_interest_time)
        
        # 获取贷款信息
        loan = self.bank_repo.get_active_loan(user_id)
        
        return BankInfo(
            balance=account.balance,
            last_interest_time=account.last_interest_time,
            pending_interest=pending_interest,
            loan=loan
        )
    
    def _calculate_interest(self, balance: int, last_time: int) -> int:
        """计算待领利息（使用Decimal精确计算复利）"""
        if balance <= 0 or last_time <= 0:
            return 0
        
        now = int(time.time())
        days_passed = (now - last_time) // 86400
        
        if days_passed < 1:
            return 0
        
        # 使用Decimal进行精确复利计算
        balance_d = Decimal(str(balance))
        rate_d = Decimal(str(self.daily_interest_rate))
        
        # 复利计算: balance * ((1 + rate) ^ days - 1)
        compound = (1 + rate_d) ** days_passed - 1
        interest = balance_d * compound
        
        # 向下取整返回
        return int(interest.quantize(Decimal('1'), rounding=ROUND_DOWN))
    
    # ===== 存取款 =====
    
    def deposit(self, user_id: str, amount: int) -> str:
        """存入灵石"""
        if amount <= 0:
            raise GameException("存款金额必须大于0")
        
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        if player.gold < amount:
            raise GameException(f"灵石不足！你只有 {player.gold:,} 灵石")
        
        # 获取银行账户
        account = self.bank_repo.get_bank_account(user_id)
        current_balance = account.balance if account else 0
        
        if current_balance + amount > self.max_deposit:
            raise GameException(f"存款上限为 {self.max_deposit:,} 灵石，当前余额 {current_balance:,}")
        
        # 扣除灵石
        self.player_repo.add_gold(user_id, -amount)
        
        # 更新银行账户
        new_balance = current_balance + amount
        now = int(time.time())
        last_interest_time = now if current_balance == 0 else (account.last_interest_time if account else now)
        self.bank_repo.create_or_update_bank_account(user_id, new_balance, last_interest_time)
        
        return f"成功存入 {amount:,} 灵石！\n当前余额：{new_balance:,} 灵石"
    
    def withdraw(self, user_id: str, amount: int) -> str:
        """取出灵石"""
        if amount <= 0:
            raise GameException("取款金额必须大于0")
        
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 获取银行账户
        account = self.bank_repo.get_bank_account(user_id)
        if not account or account.balance < amount:
            current = account.balance if account else 0
            raise GameException(f"余额不足！当前余额：{current:,} 灵石")
        
        # 更新银行账户
        new_balance = account.balance - amount
        self.bank_repo.create_or_update_bank_account(user_id, new_balance, account.last_interest_time)
        
        # 增加灵石
        self.player_repo.add_gold(user_id, amount)
        
        # 重新获取玩家信息
        player = self.player_repo.get_player(user_id)
        
        return f"成功取出 {amount:,} 灵石！\n当前余额：{new_balance:,} 灵石\n当前持有：{player.gold:,} 灵石"
    
    def claim_interest(self, user_id: str) -> str:
        """领取利息"""
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 获取银行账户
        account = self.bank_repo.get_bank_account(user_id)
        if not account or account.balance <= 0:
            raise GameException("你还没有存款，无法领取利息")
        
        # 计算利息
        interest = self._calculate_interest(account.balance, account.last_interest_time)
        
        if interest <= 0:
            raise GameException("利息不足1灵石，请明日再来")
        
        # 利息转入本金
        new_balance = account.balance + interest
        now = int(time.time())
        self.bank_repo.create_or_update_bank_account(user_id, new_balance, now)
        
        return f"成功领取利息 {interest:,} 灵石！\n当前余额：{new_balance:,} 灵石"
    
    # ===== 贷款 =====
    
    def get_loan_info(self, user_id: str) -> Optional[LoanInfo]:
        """获取贷款详情"""
        loan = self.bank_repo.get_active_loan(user_id)
        if not loan:
            return None
        
        now = int(time.time())
        days_borrowed = (now - loan.borrowed_at) // 86400
        days_remaining = max(0, (loan.due_at - now) // 86400)
        
        # 计算当前应还金额
        current_interest = loan.calculate_interest(now)
        total_due = loan.calculate_total_due(now)
        is_overdue = loan.is_overdue(now)
        
        return LoanInfo(
            id=loan.id,
            user_id=loan.user_id,
            principal=loan.principal,
            interest_rate=loan.interest_rate,
            borrowed_at=loan.borrowed_at,
            due_at=loan.due_at,
            loan_type=loan.loan_type,
            status=loan.status,
            days_borrowed=days_borrowed,
            days_remaining=days_remaining,
            current_interest=current_interest,
            total_due=total_due,
            is_overdue=is_overdue
        )
    
    def borrow(self, user_id: str, amount: int, loan_type: str = "normal") -> str:
        """申请贷款"""
        if amount < self.min_loan_amount:
            raise GameException(f"最小贷款金额为 {self.min_loan_amount:,} 灵石")
        
        if amount > self.max_loan_amount:
            raise GameException(f"最大贷款金额为 {self.max_loan_amount:,} 灵石")
        
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 检查是否已有贷款
        existing_loan = self.bank_repo.get_active_loan(user_id)
        if existing_loan:
            raise GameException("你已有未还清的贷款，请先还款后再申请新贷款")
        
        # 确定贷款参数
        if loan_type == "breakthrough":
            interest_rate = self.breakthrough_loan_rate
            duration_days = self.breakthrough_loan_duration
            type_name = "突破贷款"
        else:
            interest_rate = self.loan_interest_rate
            duration_days = self.loan_duration_days
            type_name = "普通贷款"
        
        # 创建贷款
        now = int(time.time())
        due_at = now + duration_days * 86400
        self.bank_repo.create_loan(user_id, amount, interest_rate, now, due_at, loan_type)
        
        # 增加灵石
        self.player_repo.add_gold(user_id, amount)
        
        # 计算到期应还
        total_interest = int(amount * interest_rate * duration_days)
        total_due = amount + total_interest
        
        # 重新获取玩家信息
        player = self.player_repo.get_player(user_id)
        
        return (
            f"💰 {type_name}成功！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"借入金额：{amount:,} 灵石\n"
            f"日利率：{interest_rate:.1%}\n"
            f"还款期限：{duration_days} 天\n"
            f"到期应还：约 {total_due:,} 灵石\n"
            f"━━━━━━━━━━━━━━━\n"
            f"当前持有：{player.gold:,} 灵石\n"
            f"⚠️ 请按时还款，避免逾期"
        )
    
    def repay(self, user_id: str) -> str:
        """还款"""
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 获取贷款信息
        loan_info = self.get_loan_info(user_id)
        if not loan_info:
            raise GameException("你当前没有需要偿还的贷款")
        
        total_due = loan_info.total_due
        
        if player.gold < total_due:
            raise GameException(
                f"灵石不足！\n"
                f"应还金额：{total_due:,} 灵石\n"
                f"（本金 {loan_info.principal:,} + 利息 {loan_info.current_interest:,}）\n"
                f"当前持有：{player.gold:,} 灵石\n"
                f"还差：{total_due - player.gold:,} 灵石"
            )
        
        # 扣除灵石
        self.player_repo.add_gold(user_id, -total_due)
        
        # 关闭贷款
        self.bank_repo.close_loan(loan_info.id)
        
        loan_type_name = "突破贷款" if loan_info.loan_type == "breakthrough" else "普通贷款"
        
        # 重新获取玩家信息
        player = self.player_repo.get_player(user_id)
        
        return (
            f"✅ 还款成功！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"贷款类型：{loan_type_name}\n"
            f"已还本金：{loan_info.principal:,} 灵石\n"
            f"已还利息：{loan_info.current_interest:,} 灵石\n"
            f"合计支付：{total_due:,} 灵石\n"
            f"━━━━━━━━━━━━━━━\n"
            f"当前持有：{player.gold:,} 灵石"
        )
    
    # ===== 逾期处理 =====
    # 暂时禁用逾期追杀功能（维护超过7天导致用户登录后被追杀）
    # TODO: 后续重新启用时需要考虑维护期间的贷款处理
    
    # def check_and_process_overdue_loans(self) -> List[dict]:
    #     """检查并处理逾期贷款 - 逾期玩家将被银行追杀致死"""
    #     now = int(time.time())
    #     overdue_loans = self.bank_repo.get_overdue_loans(now)
    #     processed = []
    #     
    #     for loan in overdue_loans:
    #         player = self.player_repo.get_player(loan.user_id)
    #         if not player:
    #             # 玩家已不存在，直接标记贷款逾期
    #             self.bank_repo.mark_loan_overdue(loan.id)
    #             continue
    #         
    #         player_name = player.user_name or f"道友{player.user_id[:6]}"
    #         
    #         # 删除玩家数据（银行追杀致死）
    #         # 注意：这里需要实现级联删除，暂时只标记贷款逾期
    #         self.bank_repo.mark_loan_overdue(loan.id)
    #         
    #         processed.append({
    #             "user_id": loan.user_id,
    #             "player_name": player_name,
    #             "principal": loan.principal,
    #             "death": True
    #         })
    #         
    #         logger.warning(f"玩家 {player_name} 贷款逾期被银行追杀")
    #     
    #     return processed
