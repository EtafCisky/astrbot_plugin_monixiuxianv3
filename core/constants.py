"""常量定义"""

class Commands:
    """命令名称常量"""
    # 玩家系统
    CREATE_PLAYER = "我要修仙"
    PLAYER_INFO = "我的信息"
    CHECK_IN = "签到"
    CHANGE_NICKNAME = "改道号"
    REBIRTH = "弃道重修"
    HELP = "帮助"
    
    # 修炼系统
    START_CULTIVATION = "闭关"
    END_CULTIVATION = "出关"
    
    # 突破系统
    BREAKTHROUGH = "突破"
    BREAKTHROUGH_INFO = "突破信息"
    
    # 战斗系统
    SPAR = "切磋"
    DUEL = "决斗"
    COMBAT_LOG = "战斗记录"
    
    # 储物戒系统
    STORAGE_RING = "储物戒"
    DISCARD_ITEM = "丢弃"
    GIFT_ITEM = "赠予"
    UPGRADE_RING = "更换储物戒"
    SEARCH_ITEM = "搜索物品"
    
    # 装备系统
    EQUIP = "装备"
    EQUIP_WEAPON = "装备武器"
    EQUIP_ARMOR = "装备防具"
    EQUIP_TECHNIQUE = "装备功法"
    UNEQUIP = "卸下"
    EQUIPMENT_INFO = "我的装备"
    
    # 背包系统
    BACKPACK = "我的背包"
    USE_ITEM = "使用"
    
    # 丹药系统
    USE_PILL = "服用丹药"
    SEARCH_PILL = "搜索丹药"
    
    # 炼丹系统
    ALCHEMY_RECIPES = "丹药配方"
    CRAFT_PILL = "炼丹"
    QUERY_RECIPE = "查询配方"
    QUERY_RECIPE_BY_RANK = "查询品质配方"
    ALCHEMY_INFO = "炼丹信息"
    
    # 商店系统
    PILL_PAVILION = "丹阁"
    WEAPON_PAVILION = "器阁"
    TREASURE_PAVILION = "百宝阁"
    BUY = "购买"
    
    # 市场系统
    MARKET = "市场"
    VIEW_MARKET = "查看市场"
    LIST_ITEM = "市场上架"
    BUY_MARKET_ITEM = "购买"
    UNLIST_ITEM = "市场下架"
    
    # 宗门系统
    CREATE_SECT = "创建宗门"
    JOIN_SECT = "加入宗门"
    LEAVE_SECT = "退出宗门"
    SECT_INFO = "宗门信息"
    SECT_LIST = "宗门列表"
    SECT_DONATE = "宗门捐献"
    SECT_TASK = "宗门任务"
    CHANGE_POSITION = "变更职位"
    TRANSFER_OWNERSHIP = "宗主传位"
    KICK_MEMBER = "踢出成员"
    
    # 历练系统
    ADVENTURE_INFO = "历练信息"
    START_ADVENTURE = "开始历练"
    ADVENTURE_STATUS = "历练状态"
    COMPLETE_ADVENTURE = "完成历练"
    
    # 秘境系统
    RIFT_LIST = "秘境列表"
    ENTER_RIFT = "探索秘境"
    FINISH_EXPLORATION = "完成探索"
    EXIT_RIFT = "退出秘境"
    
    # Boss系统
    BOSS_INFO = "世界Boss"
    CHALLENGE_BOSS = "挑战Boss"
    SPAWN_BOSS = "生成Boss"
    
    # 悬赏系统
    BOUNTY_LIST = "悬赏令"
    ACCEPT_BOUNTY = "接取悬赏"
    BOUNTY_STATUS = "悬赏状态"
    COMPLETE_BOUNTY = "完成悬赏"
    ABANDON_BOUNTY = "放弃悬赏"
    
    # 银行系统
    BANK_INFO = "银行"
    DEPOSIT = "存灵石"
    WITHDRAW = "取灵石"
    CLAIM_INTEREST = "领取利息"
    LOAN = "贷款"
    REPAY = "还款"
    BREAKTHROUGH_LOAN = "突破贷款"
    
    # 洞天福地系统
    BLESSED_LAND_INFO = "洞天信息"
    PURCHASE_BLESSED_LAND = "购买洞天"
    UPGRADE_BLESSED_LAND = "升级洞天"
    COLLECT_BLESSED_LAND = "洞天收取"
    
    # 灵田系统（新种子-药草系统）
    FARM_INFO = "灵田"  # 需求 10.1: /灵田 或 /lingtian
    FARM_INFO_ALT = "lingtian"  # 需求 10.1: 备用命令
    FARM_INFO_ALT2 = "灵田信息"  # 备用命令（与帮助文档一致）
    FARM_INFO_ALT3 = "我的灵田"  # 备用命令（用户习惯）
    PLANT_HERB = "种植"  # 需求 10.2: /种植 [药草名称]
    HARVEST = "收获"  # 需求 10.3: /收获
    UPGRADE_FARM = "灵田升级"  # 需求 10.5: /灵田升级
    SEED_SHOP = "种子商店"  # 需求 10.4: /种子商店
    BUY_SEED = "购买种子"  # 需求 10.6: /购买种子 [种子名称] [数量]
    
    # 旧灵田系统（已废弃，保留用于兼容）
    CREATE_FARM = "开垦灵田"
    OLD_FARM_INFO = "灵田信息"
    OLD_UPGRADE_FARM = "升级灵田"
    
    # 天地灵眼系统
    SPIRIT_EYE_INFO = "灵眼信息"
    CLAIM_SPIRIT_EYE = "抢占灵眼"
    COLLECT_SPIRIT_EYE = "灵眼收取"
    RELEASE_SPIRIT_EYE = "释放灵眼"
    
    # 双修系统
    DUAL_CULTIVATION = "双修"
    ACCEPT_DUAL = "接受双修"
    REJECT_DUAL = "拒绝双修"
    
    # 传承系统
    IMPART_INFO = "传承信息"
    IMPART_CHALLENGE = "传承挑战"
    IMPART_RANKING = "传承排行"
    
    # 排行榜
    RANK_LEVEL = "境界排行"
    RANK_POWER = "战力排行"
    RANK_WEALTH = "灵石排行"
    RANK_SECT = "宗门排行"
    RANK_DEPOSIT = "存款排行"
    RANK_CONTRIBUTION = "贡献排行"
    
    # 管理员命令
    ADMIN_ADD_GOLD = "增加灵石"
    ADMIN_REDUCE_GOLD = "减少灵石"
    ADMIN_CHANGE_SPIRIT_ROOT = "修改灵根"
    ADMIN_ADD_EXPERIENCE = "增加修为"
    ADMIN_CHANGE_SECT_POSITION = "修改宗门岗位"
    ADMIN_ADD_ITEM = "增加道具"


class GameConstants:
    """游戏常量"""
    # 修炼相关
    MAX_CULTIVATION_HOURS = 24  # 最大闭关时长（小时）
    BASE_CULTIVATION_EXP_PER_MINUTE = 10  # 每分钟基础修为
    
    # 签到相关
    DAILY_SIGNIN_GOLD_MIN = 50  # 签到最少灵石
    DAILY_SIGNIN_GOLD_MAX = 200  # 签到最多灵石
    
    # 战斗相关
    COMBAT_COOLDOWN_SECONDS = 60  # 战斗冷却时间（秒）
    
    # 商店相关
    SHOP_REFRESH_HOURS = 24  # 商店刷新时间（小时）
    
    # 宗门相关
    SECT_CREATE_COST = 10000  # 创建宗门费用
    SECT_MAX_MEMBERS = 50  # 宗门最大人数
    
    # 突破相关
    BREAKTHROUGH_SUCCESS_BASE_RATE = 0.5  # 突破基础成功率
    BREAKTHROUGH_COOLDOWN_HOURS = 1  # 突破冷却时间（小时）


class ErrorMessages:
    """错误消息常量"""
    PLAYER_NOT_FOUND = "❌ 你还未踏入修仙之路！\n💡 发送「我要修仙」开始你的修仙之旅"
    PLAYER_ALREADY_EXISTS = "❌ 你已经踏入修仙之路了！"
    INVALID_STATE = "❌ 当前状态无法执行此操作"
    INSUFFICIENT_GOLD = "❌ 灵石不足"
    INSUFFICIENT_EXP = "❌ 修为不足"
    ITEM_NOT_FOUND = "❌ 物品不存在"
    COOLDOWN_NOT_READY = "❌ 冷却时间未到"
    INVALID_PARAMETER = "❌ 参数错误"


class SuccessMessages:
    """成功消息常量"""
    PLAYER_CREATED = "🎉 恭喜道友踏入修仙之路！"
    CULTIVATION_STARTED = "🧘 开始闭关修炼..."
    CULTIVATION_ENDED = "✨ 出关成功！"
    BREAKTHROUGH_SUCCESS = "🎊 突破成功！"
    ITEM_PURCHASED = "✅ 购买成功！"
    ITEM_SOLD = "✅ 出售成功！"


class SpiritFieldConstants:
    """灵田系统常量"""
    # 成熟时间配置（秒）
    GROW_TIME_CONFIG = {
        "凡品": {
            "min": 3600,      # 1小时
            "max": 7200       # 2小时
        },
        "珍品": {
            "min": 21600,     # 6小时
            "max": 43200      # 12小时
        },
        "圣品": {
            "min": 86400,     # 1天
            "max": 259200     # 3天
        },
        "帝品": {
            "min": 432000,    # 5天
            "max": 604800     # 7天
        },
        "道品": {
            "min": 864000,    # 10天
            "max": 864000     # 10天
        },
        "仙品": {
            "min": 1296000,   # 15天
            "max": 1296000    # 15天
        },
        "神品": {
            "min": 1728000,   # 20天
            "max": 1728000    # 20天
        }
    }
    
    # 种子解锁配置
    SEED_UNLOCK_CONFIG = {
        "unlock_threshold": 5,      # 解锁所需购买次数
        "free_after_unlock": True   # 解锁后是否免费
    }
    
    # 灵田升级配置
    UPGRADE_CONFIG = {
        "max_capacity": 15,         # 最大田地数
        "upgrade_increment": 2,     # 每次升级增加的田地数
        "cost_multiplier": 10000    # 升级费用 = 当前容量 × 10000
    }
