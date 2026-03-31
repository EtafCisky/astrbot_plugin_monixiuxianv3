"""数据库表结构定义"""
import time
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PlayerTable(Base):
    """玩家表"""
    __tablename__ = 'players'
    
    # 主键
    user_id = Column(String(64), primary_key=True, comment='用户ID')
    
    # 基础信息
    nickname = Column(String(32), nullable=False, default='', comment='道号')
    cultivation_type = Column(String(16), nullable=False, comment='修炼类型：灵修/体修')
    spiritual_root = Column(String(32), nullable=False, comment='灵根')
    
    # 境界和修为
    level_index = Column(Integer, nullable=False, default=0, comment='境界索引')
    experience = Column(Integer, nullable=False, default=0, comment='修为')
    
    # 资源
    gold = Column(Integer, nullable=False, default=0, comment='灵石')
    
    # 状态
    state = Column(String(16), nullable=False, default='idle', comment='状态')
    cultivation_start_time = Column(Integer, nullable=False, default=0, comment='闭关开始时间')
    
    # 属性
    hp = Column(Integer, nullable=False, default=100, comment='当前气血')
    max_hp = Column(Integer, nullable=False, default=100, comment='最大气血')
    mp = Column(Integer, nullable=False, default=100, comment='当前真元')
    max_mp = Column(Integer, nullable=False, default=100, comment='最大真元')
    
    # 战斗属性
    physical_damage = Column(Integer, nullable=False, default=10, comment='物理攻击')
    magic_damage = Column(Integer, nullable=False, default=10, comment='法术攻击')
    physical_defense = Column(Integer, nullable=False, default=5, comment='物理防御')
    magic_defense = Column(Integer, nullable=False, default=5, comment='法术防御')
    mental_power = Column(Integer, nullable=False, default=100, comment='神识')
    
    # 装备（JSON格式存储完整装备信息）
    equipped_weapon = Column(Text, nullable=True, comment='已装备武器（JSON）')
    equipped_armor = Column(Text, nullable=True, comment='已装备防具（JSON）')
    equipped_main_technique = Column(Text, nullable=True, comment='已装备主功法（JSON）')
    equipped_techniques = Column(Text, nullable=True, comment='已装备副功法列表（JSON）')
    
    # 储物戒
    storage_ring = Column(String(64), nullable=False, default='基础储物戒', comment='储物戒名称')
    storage_ring_items = Column(Text, nullable=True, comment='储物戒物品（JSON）')
    
    # 丹药背包
    pills_inventory = Column(Text, nullable=True, comment='丹药背包（JSON）')
    
    # 宗门
    sect_id = Column(String(64), nullable=True, comment='宗门ID')
    sect_position = Column(String(16), nullable=True, comment='宗门职位')
    
    # 时间戳
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()), comment='创建时间')
    updated_at = Column(Integer, nullable=False, default=lambda: int(time.time()), onupdate=lambda: int(time.time()), comment='更新时间')
    last_signin_at = Column(Integer, nullable=True, comment='最后签到时间')
    
    # 索引
    __table_args__ = (
        Index('idx_level', 'level_index'),
        Index('idx_gold', 'gold'),
        Index('idx_sect', 'sect_id'),
    )


class PlayerStateTable(Base):
    """玩家状态表（闭关、历练等）"""
    __tablename__ = 'player_states'
    
    user_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), primary_key=True)
    state_type = Column(String(16), nullable=False, comment='状态类型')
    start_time = Column(Integer, nullable=False, comment='开始时间')
    end_time = Column(Integer, nullable=True, comment='结束时间')
    extra_data = Column(Text, nullable=True, comment='额外数据（JSON）')


class ItemTable(Base):
    """物品表"""
    __tablename__ = 'items'
    
    item_id = Column(String(64), primary_key=True, comment='物品ID')
    name = Column(String(64), nullable=False, comment='物品名称')
    item_type = Column(String(16), nullable=False, comment='物品类型')
    rarity = Column(String(16), nullable=False, comment='稀有度')
    description = Column(Text, nullable=True, comment='描述')
    
    # 属性加成（JSON格式）
    attributes = Column(Text, nullable=True, comment='属性加成')
    
    # 价格
    buy_price = Column(Integer, nullable=False, default=0, comment='购买价格')
    sell_price = Column(Integer, nullable=False, default=0, comment='出售价格')
    
    # 使用限制
    required_level = Column(Integer, nullable=False, default=0, comment='需求境界')


class PlayerItemTable(Base):
    """玩家物品表（背包）"""
    __tablename__ = 'player_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), nullable=False)
    item_id = Column(String(64), ForeignKey('items.item_id'), nullable=False)
    quantity = Column(Integer, nullable=False, default=1, comment='数量')
    obtained_at = Column(Integer, nullable=False, default=lambda: int(time.time()), comment='获得时间')
    
    __table_args__ = (
        Index('idx_user_item', 'user_id', 'item_id'),
    )


class SectTable(Base):
    """宗门表"""
    __tablename__ = 'sects'
    
    sect_id = Column(String(64), primary_key=True, comment='宗门ID')
    name = Column(String(32), nullable=False, unique=True, comment='宗门名称')
    leader_id = Column(String(64), ForeignKey('players.user_id'), nullable=False, comment='宗主ID')
    
    # 宗门属性
    level = Column(Integer, nullable=False, default=1, comment='宗门等级')
    experience = Column(Integer, nullable=False, default=0, comment='宗门经验')
    funds = Column(Integer, nullable=False, default=0, comment='宗门资金')
    
    # 成员限制
    max_members = Column(Integer, nullable=False, default=50, comment='最大成员数')
    
    # 时间戳
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))
    
    __table_args__ = (
        Index('idx_sect_name', 'name'),
    )


class CombatLogTable(Base):
    """战斗日志表"""
    __tablename__ = 'combat_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    attacker_id = Column(String(64), ForeignKey('players.user_id'), nullable=False, comment='攻击者ID')
    defender_id = Column(String(64), nullable=True, comment='防御者ID（玩家或Boss）')
    combat_type = Column(String(16), nullable=False, comment='战斗类型')
    
    # 战斗结果
    winner_id = Column(String(64), nullable=True, comment='胜利者ID')
    combat_log = Column(Text, nullable=True, comment='战斗日志（JSON）')
    
    # 奖励
    gold_reward = Column(Integer, nullable=False, default=0, comment='灵石奖励')
    exp_reward = Column(Integer, nullable=False, default=0, comment='修为奖励')
    
    # 时间戳
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))
    
    __table_args__ = (
        Index('idx_attacker', 'attacker_id'),
        Index('idx_combat_time', 'created_at'),
    )


class ShopTable(Base):
    """商店表"""
    __tablename__ = 'shops'
    
    shop_id = Column(String(64), primary_key=True, comment='商店ID')
    last_refresh_time = Column(Integer, nullable=False, default=0, comment='上次刷新时间')
    items_json = Column(Text, nullable=True, comment='商品列表（JSON）')


class BankAccountTable(Base):
    """银行账户表"""
    __tablename__ = 'bank_accounts'
    
    user_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), primary_key=True)
    balance = Column(Integer, nullable=False, default=0, comment='存款余额')
    last_interest_time = Column(Integer, nullable=False, default=0, comment='上次计息时间')
    total_deposited = Column(Integer, nullable=False, default=0, comment='累计存款')
    total_withdrawn = Column(Integer, nullable=False, default=0, comment='累计取款')


class LoanTable(Base):
    """贷款表"""
    __tablename__ = 'loans'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), nullable=False, comment='用户ID')
    principal = Column(Integer, nullable=False, comment='本金')
    interest_rate = Column(Float, nullable=False, comment='日利率')
    borrowed_at = Column(Integer, nullable=False, comment='借款时间')
    due_at = Column(Integer, nullable=False, comment='到期时间')
    loan_type = Column(String(16), nullable=False, default='normal', comment='贷款类型')
    status = Column(Integer, nullable=False, default=1, comment='状态：1=进行中，2=已还清，3=已逾期')
    
    __table_args__ = (
        Index('idx_loan_user_status', 'user_id', 'status'),
        Index('idx_loan_due', 'due_at'),
    )


class BankTransactionTable(Base):
    """银行交易记录表"""
    __tablename__ = 'bank_transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), nullable=False, comment='用户ID')
    trans_type = Column(String(16), nullable=False, comment='交易类型')
    amount = Column(Integer, nullable=False, comment='金额')
    balance_after = Column(Integer, nullable=False, comment='交易后余额')
    description = Column(String(128), nullable=False, comment='描述')
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()), comment='创建时间')
    
    __table_args__ = (
        Index('idx_user_time', 'user_id', 'created_at'),
    )


class SystemConfigTable(Base):
    """系统配置表"""
    __tablename__ = 'system_config'
    
    key = Column(String(64), primary_key=True, comment='配置键')
    value = Column(Text, nullable=False, comment='配置值')
    updated_at = Column(Integer, nullable=False, default=lambda: int(time.time()))


class CombatCooldownTable(Base):
    """战斗冷却表"""
    __tablename__ = 'combat_cooldowns'
    
    user_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), primary_key=True)
    last_duel_time = Column(Integer, nullable=False, default=0, comment='上次决斗时间')
    last_spar_time = Column(Integer, nullable=False, default=0, comment='上次切磋时间')


class DBVersionTable(Base):
    """数据库版本表"""
    __tablename__ = 'db_version'
    
    version = Column(Integer, primary_key=True, comment='版本号')
    applied_at = Column(Integer, nullable=False, default=lambda: int(time.time()), comment='应用时间')


class PendingGiftTable(Base):
    """待处理赠予表"""
    __tablename__ = 'pending_gifts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    receiver_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), nullable=False, comment='接收者ID')
    sender_id = Column(String(64), nullable=False, comment='发送者ID')
    sender_name = Column(String(32), nullable=False, comment='发送者名称')
    item_name = Column(String(64), nullable=False, comment='物品名称')
    count = Column(Integer, nullable=False, default=1, comment='数量')
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()), comment='创建时间')
    expires_at = Column(Integer, nullable=False, comment='过期时间')
    
    __table_args__ = (
        Index('idx_receiver', 'receiver_id'),
        Index('idx_expires', 'expires_at'),
    )


class BossTable(Base):
    """Boss表"""
    __tablename__ = 'bosses'
    
    boss_id = Column(Integer, primary_key=True, autoincrement=True, comment='BossID')
    boss_name = Column(String(64), nullable=False, comment='Boss名称')
    boss_level = Column(String(16), nullable=False, comment='Boss境界')
    hp = Column(Integer, nullable=False, comment='当前HP')
    max_hp = Column(Integer, nullable=False, comment='最大HP')
    atk = Column(Integer, nullable=False, comment='攻击力')
    defense = Column(Integer, nullable=False, default=0, comment='防御力（减伤%）')
    stone_reward = Column(Integer, nullable=False, default=0, comment='灵石奖励')
    create_time = Column(Integer, nullable=False, default=lambda: int(time.time()), comment='创建时间')
    status = Column(Integer, nullable=False, default=1, comment='状态：1=存活，0=已击败')
    
    __table_args__ = (
        Index('idx_status', 'status'),
    )


class BountyTaskTable(Base):
    """悬赏任务表"""
    __tablename__ = 'bounty_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), nullable=False, comment='用户ID')
    bounty_id = Column(Integer, nullable=False, comment='悬赏模板ID')
    bounty_name = Column(String(64), nullable=False, comment='悬赏名称')
    target_type = Column(String(32), nullable=False, comment='目标类型')
    target_count = Column(Integer, nullable=False, comment='目标数量')
    current_progress = Column(Integer, nullable=False, default=0, comment='当前进度')
    rewards = Column(Text, nullable=False, comment='奖励信息（JSON）')
    start_time = Column(Integer, nullable=False, default=lambda: int(time.time()), comment='开始时间')
    expire_time = Column(Integer, nullable=False, comment='过期时间')
    status = Column(Integer, nullable=False, default=1, comment='状态：1=进行中，2=已完成，0=已取消，3=已过期')
    
    __table_args__ = (
        Index('idx_bounty_user_status', 'user_id', 'status'),
        Index('idx_bounty_expire', 'expire_time'),
    )


class RiftTable(Base):
    """秘境表"""
    __tablename__ = 'rifts'
    
    rift_id = Column(Integer, primary_key=True, autoincrement=True, comment='秘境ID')
    rift_name = Column(String(64), nullable=False, comment='秘境名称')
    rift_level = Column(Integer, nullable=False, default=1, comment='秘境等级（1-3）')
    required_level = Column(Integer, nullable=False, default=0, comment='需求境界索引')
    exp_reward_min = Column(Integer, nullable=False, default=1000, comment='最小修为奖励')
    exp_reward_max = Column(Integer, nullable=False, default=5000, comment='最大修为奖励')
    gold_reward_min = Column(Integer, nullable=False, default=500, comment='最小灵石奖励')
    gold_reward_max = Column(Integer, nullable=False, default=2000, comment='最大灵石奖励')
    description = Column(Text, nullable=True, comment='描述')
    
    __table_args__ = (
        Index('idx_rift_level', 'rift_level'),
    )


class BlessedLandTable(Base):
    """洞天福地表"""
    __tablename__ = 'blessed_lands'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='ID')
    user_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), nullable=False, unique=True, comment='用户ID')
    land_type = Column(Integer, nullable=False, default=1, comment='洞天类型：1-5')
    land_name = Column(String(32), nullable=False, default='小洞天', comment='洞天名称')
    level = Column(Integer, nullable=False, default=1, comment='洞天等级')
    exp_bonus = Column(Float, nullable=False, default=0.05, comment='修为加成')
    gold_per_hour = Column(Integer, nullable=False, default=100, comment='每小时灵石产出')
    last_collect_time = Column(Integer, nullable=False, default=0, comment='上次收取时间')
    
    __table_args__ = (
        Index('idx_blessed_lands_user', 'user_id'),
    )


class SpiritFarmTable(Base):
    """灵田表"""
    __tablename__ = 'spirit_farms'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='ID')
    user_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), nullable=False, unique=True, comment='用户ID')
    level = Column(Integer, nullable=False, default=1, comment='灵田等级')
    crops = Column(Text, nullable=False, default='[]', comment='作物列表（JSON）')
    
    __table_args__ = (
        Index('idx_spirit_farms_user', 'user_id'),
    )


class SpiritEyeTable(Base):
    """天地灵眼表"""
    __tablename__ = 'spirit_eyes'
    
    eye_id = Column(Integer, primary_key=True, autoincrement=True, comment='灵眼ID')
    eye_type = Column(Integer, nullable=False, default=1, comment='灵眼类型：1-4')
    eye_name = Column(String(32), nullable=False, default='下品灵眼', comment='灵眼名称')
    exp_per_hour = Column(Integer, nullable=False, default=500, comment='每小时修为产出')
    spawn_time = Column(Integer, nullable=False, comment='生成时间')
    owner_id = Column(String(64), ForeignKey('players.user_id', ondelete='SET NULL'), nullable=True, comment='拥有者ID')
    owner_name = Column(String(32), nullable=True, comment='拥有者名称')
    claim_time = Column(Integer, nullable=True, comment='占领时间')
    last_collect_time = Column(Integer, nullable=False, default=0, comment='上次收取时间')
    
    __table_args__ = (
        Index('idx_spirit_eyes_owner', 'owner_id'),
    )


class DualCultivationTable(Base):
    """双修冷却表"""
    __tablename__ = 'dual_cultivation'
    
    user_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), primary_key=True, comment='用户ID')
    last_dual_time = Column(Integer, nullable=False, default=0, comment='上次双修时间')


class DualCultivationRequestTable(Base):
    """双修请求表"""
    __tablename__ = 'dual_cultivation_requests'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='请求ID')
    from_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), nullable=False, comment='发起者ID')
    from_name = Column(String(32), nullable=False, comment='发起者名称')
    target_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), nullable=False, comment='目标ID')
    created_at = Column(Integer, nullable=False, comment='创建时间')
    expires_at = Column(Integer, nullable=False, comment='过期时间')
    
    __table_args__ = (
        Index('idx_dual_requests_target', 'target_id'),
        Index('idx_dual_requests_expires', 'expires_at'),
    )


class ImpartInfoTable(Base):
    """传承信息表"""
    __tablename__ = 'impart_info'
    
    user_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), primary_key=True, comment='用户ID')
    impart_hp_per = Column(Float, nullable=False, default=0.0, comment='HP加成百分比')
    impart_mp_per = Column(Float, nullable=False, default=0.0, comment='MP加成百分比')
    impart_atk_per = Column(Float, nullable=False, default=0.0, comment='攻击加成百分比')
    impart_know_per = Column(Float, nullable=False, default=0.0, comment='会心加成百分比')
    impart_burst_per = Column(Float, nullable=False, default=0.0, comment='爆伤加成百分比')
    impart_mix_exp = Column(Integer, nullable=False, default=0, comment='混合经验')
    
    __table_args__ = (
        Index('idx_impart_atk', 'impart_atk_per'),
    )


class SpiritFieldTable(Base):
    """灵田系统表"""
    __tablename__ = 'spirit_fields'
    
    user_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), primary_key=True, comment='用户ID')
    capacity = Column(Integer, nullable=False, default=3, comment='田地总容量')
    unlocked_seeds = Column(Text, nullable=False, default='[]', comment='已解锁的种子ID列表（JSON）')
    seed_purchase_count = Column(Text, nullable=False, default='{}', comment='种子购买次数（JSON）')
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()), comment='创建时间')
    updated_at = Column(Integer, nullable=False, default=lambda: int(time.time()), onupdate=lambda: int(time.time()), comment='更新时间')
    
    __table_args__ = (
        Index('idx_spirit_field_user', 'user_id'),
    )


class SpiritFieldPlotTable(Base):
    """灵田田地表"""
    __tablename__ = 'spirit_field_plots'
    
    plot_id = Column(Integer, primary_key=True, autoincrement=True, comment='田地ID')
    user_id = Column(String(64), ForeignKey('players.user_id', ondelete='CASCADE'), nullable=False, comment='用户ID')
    herb_id = Column(String(64), nullable=True, comment='药草物品ID')
    herb_name = Column(String(64), nullable=True, comment='药草名称')
    herb_rank = Column(String(16), nullable=True, comment='药草品级')
    plant_time = Column(Integer, nullable=True, comment='种植时间（Unix时间戳）')
    mature_time = Column(Integer, nullable=True, comment='成熟时间（Unix时间戳）')
    
    __table_args__ = (
        Index('idx_plot_user', 'user_id'),
        Index('idx_plot_mature', 'mature_time'),
    )


