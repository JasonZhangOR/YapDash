"""Optional voice keyword packs. Proper names can use pronunciation matching."""

from dataclasses import dataclass

import delta_pack


@dataclass(frozen=True)
class Pack:
    name: str
    words: tuple
    sound_words: frozenset
    example_word: str
    example: str


def pack(name, example_word, example, names, calls):
    sound_words = names.split()
    return Pack(name, tuple(sound_words + calls.split()), frozenset(sound_words), example_word, example)


DELTA = Pack("三角洲行动", tuple(delta_pack.WORDS), delta_pack.SOUND_WORDS, "牢赛", "东楼有牢赛")

CS2 = pack("CS2", "香蕉道", "香蕉道有两个，包掉了",
    """荒漠迷城 炼狱小镇 炙热沙城 核子危机 死亡游乐园 殒命大厦 远古遗迹 阿努比斯
    列车停放站 死城之谜 古堡激战 香蕉道 甜甜圈 匪口 警家 匪家 匪桥 匪厅 匪二楼
    拱门 警亭 三明治 跳台 沙袋位 棺材位 长管 短管 魔男位 黄房 红箱 秘密通道
    纪念品龙狙 格洛克 沙漠之鹰 沙鹰 法玛斯 加利尔 鸟狙 电击枪 拆弹器 雷钳""",
    """反恐精英 沙二 沙漠二 沙漠2 迷城 小镇 核电站 大厦 游乐园 遗迹 火车
    Dust2 D2 Mirage Inferno Nuke Overpass Ancient Anubis Vertigo Train Cache
    A点 B点 A包点 B包点 A大 A小 B大 B小 A门 B门 中门 中路 中远 中近
    A一 A二楼 B二楼 A1 A2 B1 B2 A坡 B坡 A厅 B厅 A平台 B平台
    VIP 跳台下 二楼下 二楼出口 短箱 长箱 三箱 双箱 白车 蓝车 白箱 爆头位
    警超市 超市窗口 超市门 匪跳 匪斜 警中 中路窗口 地下通道 下水道
    书房 墓地 马棚 石板 木桶 喷泉 锅炉房 沙包 教堂 连接位 工地 工地下
    外场 内场 铁板 三楼 大仓 小黄房 通风管 斜坡房 控制室 玻璃房 正门
    AK47 AK-47 AK M4A4 M4A1-S M4A1 AWP USP-S USP P250 P90 MP9 MAC-10 MAC10
    Glock Deagle Scout SSG08 FAMAS Galil AUG SG553 Tec-9 Five-SeveN UMP45 XM1014
    大狙 吹风机 连狙 消音M4 消音手枪 双枪 内格夫 全甲 半甲 头甲 无甲 有钳子 没钳子
    手枪局 长枪局 经济局 起枪局 强起局 赛点局 加时局 ECO 半起 全起 强起 保枪 发枪
    给把枪 掉把枪 捡大狙 对面没钱 对面强起 存钱局 奖金重置
    烟雾弹 闪光弹 燃烧瓶 高爆雷 诱饵弹 警家烟 拱门烟 跳台烟 VIP烟 中门烟 过点烟
    单向烟 过点闪 弹墙闪 背身闪 瞬爆闪 全白 半白 吃闪了 背闪 双架 反清 补枪 拉枪线
    转点 转A 转B 回防 守包 下包 拆包 假拆 假下 下默认包 包掉了 包匪 雷包 C4
    没时间拆 保大狙 藏枪 摸后路 架过点 别漏脚步 爆弹 一换一 一打二 一打三 残局 ACE""")

VALORANT = pack("瓦洛兰特（无畏契约）", "爆能器", "爆能器掉在中路了",
    """无畏契约 瓦洛兰特 瓦罗兰特 捷风 雷兹 芮娜 夜露 霓虹 不死鸟 壹决
    炼狱 幽影 蝰蛇 星礈 海神 暮蝶 铁臂 猎枭 斯凯 黑梦 盖可 贤者 零
    奇乐 尚勃勒 钱包 钢锁 维斯 钛狐 幻棱 禁灭 迷核 遐思 爆能器 源工重镇 隐世修所 霓虹町 亚海悬城
    森寒冬港 微风岛屿 裂变峡谷 莲华古城 日落之城 幽邃地窟 盐海矿镇 深海明珠 天枢云阙
    蜂刺 雄鹿 判官 骇灵 狂徒 幻影 戍卫 正义 冥驹 飞将 奥丁 战神 獠犬 鬼魅 莽侠""",
    """Jett Raze Reyna Yoru Neon Phoenix Iso Brimstone Brim Omen Viper Astra Harbor Clove
    Breach Sova Skye Fade Gekko KAY/O KAYO K/O Sage Cypher Killjoy KJ Chamber Deadlock Vyse Tejo Waylay Veto Miks Hush
    白毛 炸弹妹 女皇 凤凰 火男 猎人 奶妈 奶爸 保安 烟男 炼狱大叔 K刀 机器人 鹰妹 一突 二突
    决斗位 控场位 先锋位 哨卫位 烟位 信息位 双决斗 双烟阵容 单烟 双先锋
    Bind Haven Split Ascent Icebox Breeze Fracture Lotus Sunset Abyss Corrode Pearl Summit
    三包点 双塔 冰箱 天堂 地狱 车库 浴室 钩子 窗口 短道 长廊 绳索区 管道 双门 旋转门
    A点 B点 C点 A大 B大 C大 A小 B小 C小 A厅 B厅 C厅 A塔 B塔 A包点 B包点 C包点
    中路 市场 树房 船屋 传送门 门洞 A连接 B连接 C连接 警家 匪家 高台下 高台上
    Spike 下包 安包 拆包 假拆 滴包 半拆 拆了一半 下默认包 掉包了 包点有人 守包 回防
    大绝点 终极点 大招点 吃球 控球 拿球 差一个点 大招好了 没有大招 开大了
    烟墙 毒墙 毒幕 毒球 毒蝰大 冰墙 奶墙 封墙 奶一口 拉一下 复活我
    侦察箭 探点箭 电箭 无人机 放狗 放鹰 探点狗 震荡 弹墙闪 反清闪 闪进点
    拆绊线 绊线 摄像头 监控位 炮台 蜂群 纳米蜂群 禁锢 屏障球 震荡箭
    炸药包 双炸药包 风刀 飓刃 封烟 球烟 单向烟 隔断烟 烟散了 进烟 混烟
    Vandal Phantom Operator OP Marshal Outlaw Guardian Bulldog Sheriff Ghost Classic
    Shorty Frenzy Spectre Stinger Bucky Judge Odin Ares 大狙 鸟狙 喷子 发枪 求枪
    短炮 标配 狂怒 重甲 轻甲 半甲 满甲 手枪局 红利局 奖励局 长枪局 ECO 强起局
    再生护甲 转点 转A 转B 转C 等技能 反摸 架侧身 集合进点 别单拉 同步拉 补枪 交叉火力""")

ARKNIGHTS = pack("明日方舟（通用）", "桃金娘", "桃金娘先下，这波要回费",
    """明日方舟 罗德岛 龙门币 合成玉 至纯源石 招聘许可 加急许可 理智液 源岩 固源岩
    聚酸酯 异铁 凝胶 扭转醇 轻锰矿 研磨石 三水锰矿 双极纳米片 聚合剂 晶体电子单元
    阿米娅 凯尔希 能天使 德克萨斯 拉普兰德 银灰 初雪 崖心 讯使 角峰 推进之王
    风笛 桃金娘 极境 琴柳 嵯峨 伊内丝 缪尔赛思 芬 砾 红豆 凛冬 清道夫
    煌 棘刺 山 史尔特尔 玛恩纳 耀骑士临光 百炼嘉维尔 锏 羽毛笔 拉普 银老板
    星熊 塞雷娅 泥岩 瑕光 年 临光 森蚺 号角 斑点 蛇屠箱 古米 雷蛇
    蓝毒 白金 灰喉 天火 白面鸮 闪灵 夜莺 白雪 黑 白铁 空弦 早露
    菲亚梅塔 提丰 维什戴尔 假日威龙陈 迷迭香 鸿雪 守林人 陨星 流星
    艾雅法拉 伊芙利特 刻俄柏 澄闪 林 夕 异客 莫斯提马 小火龙 小羊 小刻 粉毛
    铃兰 安洁莉娜 浊心斯卡蒂 斯卡蒂 歌蕾蒂娅 乌尔比安 幽灵鲨 归溟幽灵鲨
    令 稀音 麦哲伦 灵知 塑心 濯尘芙蓉 蜜莓 桑葚 纯烬艾雅法拉 絮雨 华法琳 赫默
    傀影 麒麟R夜刀 缄默德克萨斯 归溟鲨 异德 焰尾 艾丽妮 阿斯卡纶 逻各斯
    荒芜拉普兰德 新约能天使 娜仁图亚 斥罪 见行者 孑 红蒂 水陈 叔叔 真银斩 黄昏
    塔露拉 冻河 奥尔佳 凛御银灰 黑键 赫拉格 多萝西 温蒂 水月""",
    """博士 刀客塔 干员 助战干员 支援单位 先锋 近卫 重装 狙击 术师 医疗 辅助 特种
    快速复活 快活 召唤师 执旗手 领主 强攻手 解放者 剑豪 术战者 无畏者 铁卫 守护者
    不屈者 要塞 神射手 速射手 投掷手 炮手 轰击术师 驭械术师 中坚术师 群愈师
    疗养师 咒愈师 吟游者 护佑者 行商 处决者 推击手 钩索师 伏击客
    集成战略 肉鸽 生息演算 危机合约 剿灭作战 保全派驻 矩阵 卫戍协议 公开招募 公招
    干员寻访 高级资深干员 资深干员 保底 歪了 潜能 满潜 精英化 精一 精二 开模组
    模组数据块 模组条 专精 专一 专二 专三 一技能 二技能 三技能 七级技能
    部署费用 再部署 阻挡数 阻挡三 挡二 挡三 回费 爆费 卡费 撤退回费 费用不够
    技力 光环 技力回转 自动回复 攻击回复 受击回复 初始技力 法抗 真伤 物理闪避
    元素损伤 神经损伤 灼燃损伤 凋亡损伤 沉默 眩晕 寒冷 冻结 束缚 停顿
    高台位 地面位 蓝门 红门 漏怪 漏飞机 接敌 漏了一只 撤了重下 暖机 永续
    代理指挥 代理作战 理智 作战记录 基建 制造站 贸易站 会客室 加工站 训练室 控制中枢""")

GARRISON = pack("明日方舟 · 卫戍协议", "冻结补给", "先冻结补给，下回合三连",
    """卫戍协议 卫戍规程 卫戍认证 同盟模拟 标准模拟 极速模拟 调度中心 物资调配处
    整备区 战场区 联防阶段 领袖轮 精锐化 核心盟约 附加盟约 协防干员 特许干员
    联合模拟 独立模拟 险境模拟 绝境模拟 终极模拟 冻结补给 干员晋升 三连 调度资金 自编干员 原型干员 奖励干员 寻呼模块
    隐秘核心 同盟密钥 卫戍节点 功勋兑换处 见钱眼开玩偶
    叙拉古 阿戈尔 卡西米尔 谢拉格 萨尔贡 维多利亚 乌萨斯 莱塔尼亚 伊比利亚
    黑白相易 沙洲梦魇 猎人战法 骑士团长 不融信念 自发制造 量体裁衣 献身护卫
    简易通讯机 紧急调度券 天马之枪 天马之盔 卡西米尔竞技旗 骑士戒律 叙拉古正装
    家族徽章 骑士储蓄罐 盟约之币 可靠怀表
    斯卡蒂 玛恩纳 耀骑士临光 乌尔比安 维什戴尔 澄闪 艾丽妮 史尔特尔 阿米娅
    纯烬艾雅法拉 荒芜拉普兰德 缪尔赛思 新约能天使 司霆惊蛰 圣聆初雪 怒潮凛冬
    斩业星熊 维娜维多利亚 塔露拉 贝洛内 歌蕾蒂娅 银灰 棘刺 娜仁图亚 巫恋 贾维""",
    """舟棋 方舟自走棋 卫戍 盟约 入门协议 规程等级 序列一 开放期 修订期 终止期
    模拟简报 模拟强度 变换策略 最终领袖轮 关键目标 快速搜寻 精确搜寻 创建同盟 成就奖杯 终端主题
    单人模拟 自选编队 战斗预览 选策略 选阵营 选干员 五阶自选 六阶自选 自选干员
    调配池 补给池 干员池 共享卡池 卡队友牌 禁用盟约 核心阵营 隐藏势力
    核心羁绊 附加羁绊 羁绊层数 临时层数 永久层数 叠层 叠层数 凑羁绊 开羁绊
    三炎 六炎 大炎队 叙拉古队 六叙拉古 六卡西米尔 六谢拉格 六阿戈尔 萨尔贡队
    投资人 远见 奇迹 精准 坚守 突袭 不屈 迅捷 助力 灵巧 独行 绝技 调和 奥术 聚合
    投资人体系 奇迹流 远见流 协防位 精锐状态 初始干员 精锐干员 补位干员 第一盟约
    战前选择 休整期 休整阶段 战斗期 作战阶段 联防 联防场地 常规场地 最终领袖
    领袖单位 领袖回合 首领轮 Boss轮 打领袖 接联防 帮我联防 这波联防 准备联防
    特训敌人 特训轮 悬赏敌人 机变阶段 萨米的意志 帝国余晖 阿利斯泰尔 目标生命 目标生命值 完美作战 最终作战 完成准备
    策略区 主动策略 被动效果 拖拽使用 选策略位 让选 选牌顺位 战场站位 交换站位 调站位
    装备区 手牌区 待部署区 干员区 备战区 后备区 整备位 备战席 格子满了 手牌满了
    锁商店 锁店 锁牌 留牌 解冻补给 解锁商店 免费刷新 手动刷新 刷商店
    升调度 升商店 升本 一本 二本 三本 四本 五本 六本 升四本 升五本 升六本 跳本
    刷牌 搜牌 找对子 留对子 三连了 碰三连 差一张 拿精锐 合精锐 升精锐
    刷新资金 剩余资金 买干员 卖干员 出售干员 拿装备 买装备 替换装备
    基础装备 初始装备 进阶装备 合成装备 装备合并 装备槽 销毁装备 拿怀表 拿正装
    阵营牌 过渡牌 核心牌 挂件牌 协防牌 整备区生效 战场区生效 前排倒了
    召唤物 射击台 部署位 特训波 领袖波 装备给谁 最后一轮 漏怪了 保目标血""")

PACKS = (DELTA, CS2, VALORANT, ARKNIGHTS, GARRISON)
PROCESS_GAMES = {
    "deltaforce.exe": DELTA,
    "deltaforceclient-win64-shipping.exe": DELTA,
    "cs2.exe": CS2,
    "valorant-win64-shipping.exe": VALORANT,
}
BUILTIN_WORDS = frozenset(word.casefold() for item in PACKS for word in item.words)
SOUND_WORDS = frozenset().union(*(item.sound_words for item in PACKS))
LATIN_WORDS = frozenset(word.casefold() for item in PACKS for word in item.words if word.isascii())
SOLO_NAMES = frozenset(word for item in (ARKNIGHTS, VALORANT) for word in item.words if len(word) == 1)
# Misheard forms observed in local SenseVoice audio tests.
TRANSCRIPTION_VARIANTS = (("曹金娘", "桃金娘"),)

# Reviewed alternatives map to the original keyword for captions and cooldowns.
REVIEWED_ALIASES = (
    ("米垃圾", "荒漠迷城"), ("Mirage", "荒漠迷城"), ("Inferno", "炼狱小镇"),
    ("沙二", "炙热沙城"), ("沙2", "炙热沙城"), ("Nuke", "核子危机"),
    ("游乐园", "死亡游乐园"), ("遗迹", "远古遗迹"), ("叉车", "死城之谜"),
    ("Cache", "死城之谜"), ("Deagle", "沙鹰"), ("咖喱", "加利尔"),
    ("钳子", "雷钳"), ("CS", "反恐精英"), ("Boss", "领袖轮"),
    ("场下", "整备区"), ("场上", "战场区"), ("小盟约", "附加盟约"),
    ("大盟约", "核心盟约"), ("匹配", "联合模拟"), ("绝境", "绝境模拟"),
    ("终极", "终极模拟"), ("锁", "冻结补给"), ("合成", "干员晋升"),
    ("电台", "寻呼模块"), ("电话", "简易通讯机"),
)
