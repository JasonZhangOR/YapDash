"""Starter preset based on the selected Delta Force terms."""

WORDS = (
    "跑刀 猛攻 夺舍 花来 刘涛 修脚 卡战备 堵桥 拉闸 丢包撤 撤离点 劝架 塞裤裆 大红 出红了 "
    "曼德尔砖 非洲之星 海洋之泪 暖气片 火箭燃料 芝士套 制式券 六套 金弹 红狼 威龙 蜂医 露娜 "
    "乌鲁鲁 盾狗 赛伊德 牢赛 牢太 左边有人 右边有人 后面有人 楼上有人 有脚步 封烟 打残了 倒一个 还有一队"
).split()

EFFECTS = {
    "左边有人": ("signal", 2, "auto"),
    "右边有人": ("signal", 2, "auto"),
    "有脚步": ("urgent", 3, "top"),
    "后面有人": ("urgent", 3, "bottom"),
    "楼上有人": ("urgent", 3, "top"),
    "出红了": ("comic", 4, "top"),
    "非洲之星": ("gold", 4, "bottom"),
    "花来": ("sticker", 3, "scroll"),
    "牢赛": ("urgent", 3, "top"),
    "刘涛": ("gold", 4, "scroll"),
    "六套": ("gold", 4, "scroll"),
}

ALIASES = {"六套": "刘涛"}
