"""
商店服务层

处理商店相关的业务逻辑。
"""
import random
import time
from typing import List, Dict, Optional, Tuple

from astrbot.api import logger

from ...domain.models.shop import Shop, ShopItem
from ...domain.models.player import Player
from ...infrastructure.repositories.shop_repo import ShopRepository
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository
from ...core.config import ConfigManager
from ...core.exceptions import BusinessException


class ShopService:
    """商店服务"""
    
    # 物品类型标签映射
    TYPE_LABEL_MAP = {
        'weapon': '武器',
        'armor': '防具',
        'main_technique': '心法',
        'technique': '功法',
        'pill': '破境丹',
        'exp_pill': '修为丹',
        'utility_pill': '功能丹',
        'material': '材料',
        'accessory': '饰品'
    }
    
    def __init__(
        self,
        shop_repo: ShopRepository,
        player_repo: PlayerRepository,
        storage_ring_repo: StorageRingRepository,
        config_manager: ConfigManager,
    ):
        """
        初始化商店服务
        
        Args:
            shop_repo: 商店仓储
            player_repo: 玩家仓储
            storage_ring_repo: 储物戒仓储
            config_manager: 配置管理器
        """
        self.shop_repo = shop_repo
        self.player_repo = player_repo
        self.storage_ring_repo = storage_ring_repo
        self.config_manager = config_manager
    
    def _get_all_sellable_items(self) -> List[Dict]:
        """获取所有可以在商店出售的物品"""
        all_items = []
        
        # 添加武器
        weapons_config = self.config_manager.get_config("weapons")
        if weapons_config:
            for weapon in weapons_config.values():
                if weapon.get('shop_weight', 0) > 0 and weapon.get('price', 0) > 0:
                    all_items.append({
                        'id': weapon['id'],
                        'name': weapon['name'],
                        'type': 'weapon',
                        'price': weapon['price'],
                        'weight': weapon['shop_weight'],
                        'rank': weapon.get('rank', '凡品'),
                        'data': weapon
                    })
        
        # 添加物品（防具、功法等）
        items_config = self.config_manager.get_config("items")
        if items_config:
            # 类型映射：中文 -> 英文（用于统一类型）
            type_mapping = {
                '丹药': 'pill',
                '材料': 'material',
                '法器': 'weapon',
                '功法': 'technique',
                '防具': 'armor',
                '饰品': 'accessory'
            }
            for item in items_config.values():
                if item.get('shop_weight', 0) > 0 and item.get('price', 0) > 0:
                    item_type = item['type']
                    # 统一转换为英文类型
                    normalized_type = type_mapping.get(item_type, item_type)
                    all_items.append({
                        'id': item.get('id', item['name']),
                        'name': item['name'],
                        'type': normalized_type,
                        'price': item['price'],
                        'weight': item['shop_weight'],
                        'rank': item.get('rank', '凡品'),
                        'data': item
                    })
        
        # 添加丹药
        pills_config = self.config_manager.get_config("pills")
        if pills_config:
            for pill in pills_config.values():
                if pill.get('shop_weight', 0) > 0 and pill.get('price', 0) > 0:
                    all_items.append({
                        'id': pill['id'],
                        'name': pill['name'],
                        'type': 'pill',
                        'price': pill['price'],
                        'weight': pill['shop_weight'],
                        'rank': pill.get('rank', '凡品'),
                        'data': pill
                    })
        
        return all_items
    
    def _weighted_random_choice(self, items: List[Dict], count: int) -> List[Dict]:
        """
        基于权重的随机选择（不重复）
        
        Args:
            items: 物品列表
            count: 选择数量
            
        Returns:
            选中的物品列表
        """
        if len(items) <= count:
            return items.copy()
        
        selected = []
        available_items = items.copy()
        
        for _ in range(count):
            if not available_items:
                break
            
            # 计算总权重
            total_weight = sum(item['weight'] for item in available_items)
            if total_weight == 0:
                # 如果所有权重都是0，则随机选择
                choice = random.choice(available_items)
            else:
                # 基于权重选择
                rand = random.uniform(0, total_weight)
                cumulative = 0
                choice = available_items[0]
                for item in available_items:
                    cumulative += item['weight']
                    if rand <= cumulative:
                        choice = item
                        break
            
            selected.append(choice)
            available_items.remove(choice)
        
        return selected
    
    def _calculate_stock(self, weight: int) -> int:
        """
        根据权重计算库存数量
        
        权重越高，物品越常见，库存越多
        权重越低，物品越稀有，库存越少（最少为1）
        
        Args:
            weight: 物品的商店权重
            
        Returns:
            库存数量（最小为1）
        """
        # 库存 = 权重 / 100，向上取整，最小为1
        stock_divisor = 100
        stock = max(1, (weight + stock_divisor - 1) // stock_divisor)
        return stock
    
    def generate_shop_items(self, item_filter=None, count: int = 10) -> List[Dict]:
        """
        生成商店物品列表
        
        Args:
            item_filter: 物品过滤函数
            count: 要生成的物品数量
            
        Returns:
            商店物品列表
        """
        all_items = self._get_all_sellable_items()
        
        # 应用过滤器
        if item_filter:
            all_items = [item for item in all_items if item_filter(item)]
        
        if not all_items:
            return []
        
        # 随机选择物品
        selected_items = self._weighted_random_choice(all_items, count)
        
        # 折扣范围
        discount_min = 0.8
        discount_max = 1.2
        
        # 生成商店物品
        shop_items = []
        for item in selected_items:
            # 随机折扣
            discount = random.uniform(discount_min, discount_max)
            final_price = int(item['price'] * discount)
            
            # 计算库存（基于权重）
            stock = self._calculate_stock(item['weight'])
            
            shop_items.append({
                'id': item['id'],
                'name': item['name'],
                'type': item['type'],
                'rank': item['rank'],
                'original_price': item['price'],
                'discount': discount,
                'price': final_price,
                'stock': stock,
                'data': item['data']
            })
        
        return shop_items
    
    def ensure_shop_refreshed(
        self, 
        shop_id: str, 
        shop_name: str,
        item_filter=None, 
        count: int = 10,
        refresh_hours: int = None
    ) -> Shop:
        """
        确保商店已刷新
        
        Args:
            shop_id: 商店ID
            shop_name: 商店名称
            item_filter: 物品过滤函数
            count: 商品数量
            refresh_hours: 刷新间隔（小时），None则从配置读取
            
        Returns:
            商店对象
        """
        # 如果没有指定刷新时间，从配置读取
        if refresh_hours is None:
            refresh_hours = self.config_manager.settings.values.pavilion_refresh_hours
        
        logger.debug(f"【商店刷新】商店ID: {shop_id}, 刷新间隔: {refresh_hours}小时")
        
        last_refresh, items_data = self.shop_repo.get_shop_data(shop_id)
        current_time = int(time.time())
        
        # 检查是否需要刷新
        should_refresh = False
        if not items_data:
            should_refresh = True
            logger.debug(f"【商店刷新】商店 {shop_id} 无数据，需要刷新")
        elif refresh_hours > 0:
            elapsed = current_time - last_refresh
            should_refresh = elapsed >= (refresh_hours * 3600)
            logger.debug(f"【商店刷新】商店 {shop_id} 距上次刷新 {elapsed}秒，需要刷新: {should_refresh}")
        
        if should_refresh:
            # 生成新商品
            items_data = self.generate_shop_items(item_filter, count)
            logger.info(f"【商店刷新】商店 {shop_id} 刷新完成，生成 {len(items_data)} 个商品")
            if items_data:
                logger.debug(f"【商店刷新】商品列表: {[item['name'] for item in items_data]}")
            self.shop_repo.update_shop_data(shop_id, current_time, items_data)
            last_refresh = current_time
        else:
            logger.debug(f"【商店刷新】商店 {shop_id} 无需刷新，当前有 {len(items_data)} 个商品")
        
        # 构建商店对象
        shop_items = [
            ShopItem(
                id=item['id'],
                name=item['name'],
                item_type=item['type'],
                rank=item['rank'],
                original_price=item['original_price'],
                discount=item['discount'],
                price=item['price'],
                stock=item['stock'],
                data=item['data']
            )
            for item in items_data
        ]
        
        return Shop(
            shop_id=shop_id,
            name=shop_name,
            items=shop_items,
            last_refresh_time=last_refresh,
            refresh_interval_hours=refresh_hours
        )
    
    def format_shop_display(self, shop: Shop) -> str:
        """
        格式化商店展示信息
        
        Args:
            shop: 商店对象
            
        Returns:
            格式化后的字符串
        """
        available_items = shop.get_available_items()
        
        if not available_items:
            return f"{shop.name}暂无物品出售"
        
        lines = [f"=== {shop.name} ===\n"]
        
        for i, item in enumerate(available_items, 1):
            type_label = self.TYPE_LABEL_MAP.get(item.item_type, '物品')
            
            # 折扣标签
            discount_text = ""
            if item.discount < 1.0:
                discount_text = f" [{int((1.0 - item.discount) * 100)}%折]"
            elif item.discount > 1.0:
                discount_text = f" [+{int((item.discount - 1.0) * 100)}%]"
            
            # 库存标签
            stock_text = f"库存紧张:{item.stock}" if item.stock <= 3 else f"库存:{item.stock}"
            
            # 获取物品效果描述
            effect_desc = self._get_item_effect_short(item)
            effect_line = f"\n   效果: {effect_desc}" if effect_desc else ""
            
            # 获取物品介绍
            description = self._get_item_description(item)
            desc_line = f"\n   介绍: {description}" if description else ""
            
            lines.append(
                f"{i}. [{item.rank}] {item.name} ({type_label}){discount_text}\n"
                f"   价格: {item.price} 灵石 {stock_text}{effect_line}{desc_line}\n"
            )
        
        # 刷新时间提示
        if shop.refresh_interval_hours > 0:
            current_time = int(time.time())
            remaining = shop.get_remaining_refresh_time(current_time)
            if remaining > 0:
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                lines.append(f"\n下次刷新: {hours}小时{minutes}分钟后")
        
        lines.append(f"\n提示: 使用 '购买 [物品名]' 购买物品")
        
        return "".join(lines)
    
    def _get_item_effect_short(self, item: ShopItem) -> str:
        """
        获取物品效果的简短描述
        
        Args:
            item: 商品对象
            
        Returns:
            效果描述
        """
        data = item.data
        effects = []
        
        # 检查各种效果
        if data.get('effect'):
            effect_data = data['effect']
            if effect_data.get('add_hp'):
                effects.append(f"恢复气血+{effect_data['add_hp']}")
            if effect_data.get('add_experience'):
                effects.append(f"修为+{effect_data['add_experience']}")
            if effect_data.get('add_max_hp'):
                effects.append(f"气血上限+{effect_data['add_max_hp']}")
            if effect_data.get('add_spiritual_power'):
                effects.append(f"灵力+{effect_data['add_spiritual_power']}")
            if effect_data.get('breakthrough_rate'):
                effects.append(f"突破成功率+{effect_data['breakthrough_rate']}%")
        
        # 装备属性
        if data.get('magic_damage'):
            effects.append(f"法伤+{data['magic_damage']}")
        if data.get('physical_damage'):
            effects.append(f"物伤+{data['physical_damage']}")
        if data.get('magic_defense'):
            effects.append(f"法防+{data['magic_defense']}")
        if data.get('physical_defense'):
            effects.append(f"物防+{data['physical_defense']}")
        if data.get('mental_power'):
            effects.append(f"精神力+{data['mental_power']}")
        if data.get('max_hp') and not data.get('effect'):  # 避免重复显示
            effects.append(f"气血上限+{data['max_hp']}")
        if data.get('exp_multiplier'):
            effects.append(f"修炼倍率+{int(data['exp_multiplier']*100)}%")
        
        # 旧版装备效果
        if data.get('equip_effects'):
            equip_effects = data['equip_effects']
            if equip_effects.get('attack'):
                effects.append(f"攻击+{equip_effects['attack']}")
            if equip_effects.get('defense'):
                effects.append(f"防御+{equip_effects['defense']}")
        
        return "、".join(effects) if effects else ""
    
    def _get_item_description(self, item: ShopItem) -> str:
        """
        获取物品介绍
        
        Args:
            item: 商品对象
            
        Returns:
            物品介绍
        """
        data = item.data
        desc = data.get('description', '')
        # 限制长度
        return desc[:40] + "..." if len(desc) > 40 else desc
    
    def buy_item(
        self, 
        user_id: str, 
        shop_id: str, 
        item_name: str, 
        quantity: int = 1
    ) -> Tuple[bool, str]:
        """
        购买物品
        
        Args:
            user_id: 用户ID
            shop_id: 商店ID
            item_name: 物品名称
            quantity: 购买数量
            
        Returns:
            (是否成功, 消息)
            
        Raises:
            BusinessException: 各种业务异常
        """
        # 获取玩家
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        # 查找商品
        last_refresh, items_data = self.shop_repo.get_shop_data(shop_id)
        
        # 调试日志
        logger.debug(f"【商店购买】商店ID: {shop_id}, 查找物品: {item_name}")
        logger.debug(f"【商店购买】商店物品数量: {len(items_data)}")
        if items_data:
            logger.debug(f"【商店购买】商店物品列表: {[item.get('name') for item in items_data]}")
        
        target_item = None
        for item in items_data:
            if item['name'] == item_name and item.get('stock', 0) > 0:
                target_item = item
                break
        
        if not target_item:
            logger.debug(f"【商店购买】在商店 {shop_id} 中未找到物品 {item_name}")
            raise BusinessException(f"没有找到【{item_name}】，请检查物品名称或等待刷新")
        
        # 检查库存
        stock = target_item.get('stock', 0)
        if quantity > stock:
            raise BusinessException(f"【{item_name}】库存不足，当前库存: {stock}")
        
        # 检查灵石
        price = target_item['price']
        total_price = price * quantity
        if player.gold < total_price:
            raise BusinessException(
                f"灵石不足！\n【{target_item['name']}】价格: {price} 灵石\n"
                f"购买数量: {quantity}\n需要灵石: {total_price}\n你的灵石: {player.gold}"
            )
        
        # 扣除库存
        success, _, remaining = self.shop_repo.decrement_item_stock(
            shop_id, item_name, quantity
        )
        if not success:
            raise BusinessException(f"【{item_name}】已售罄，请等待刷新")
        
        # 扣除灵石
        player.gold -= total_price
        
        # 根据物品类型处理（支持中英文类型）
        item_type = target_item['type']
        result_lines = []
        
        # 类型映射：中文 -> 英文
        type_mapping = {
            '丹药': 'pill',
            '材料': 'material',
            '法器': 'weapon',
            '功法': 'technique'
        }
        
        # 统一转换为英文类型
        normalized_type = type_mapping.get(item_type, item_type)
        
        if normalized_type in ['weapon', 'armor', 'main_technique', 'technique', 'accessory', 'material', 'pill', 'exp_pill', 'utility_pill']:
            # 所有物品（包括丹药）都存入储物戒
            # 直接更新player对象的storage_ring_items，避免数据覆盖问题
            if item_name in player.storage_ring_items:
                player.storage_ring_items[item_name] += quantity
            else:
                player.storage_ring_items[item_name] = quantity
            
            type_name = self.TYPE_LABEL_MAP.get(normalized_type, '物品')
            result_lines.append(f"成功购买{type_name}【{target_item['name']}】x{quantity}，已存入储物戒。")
        
        else:
            raise BusinessException(f"未知的物品类型：{item_type}（标准化后：{normalized_type}）")
        
        # 更新玩家（包含储物戒数据）
        self.player_repo.save(player)
        
        result_lines.append(f"花费灵石: {total_price}，剩余: {player.gold}")
        result_lines.append(f"剩余库存: {remaining}" if remaining > 0 else "该物品已售罄！")
        
        return True, "\n".join(result_lines)
