from dataclasses import dataclass


@dataclass(frozen=True)
class RoutingProfile:
    code: str
    priority: int
    keywords: tuple[str, ...]
    exclusions: tuple[str, ...] = ()


ROUTING_PROFILES: tuple[RoutingProfile, ...] = (
    RoutingProfile(
        code="pet_food",
        priority=90,
        keywords=("宠物", "犬粮", "猫粮", "全价", "宠物饲料", "宠物食品", "粗蛋白", "粗脂肪", "成分分析保证值", "适用宠物"),
    ),
    RoutingProfile(
        code="electronics",
        priority=88,
        keywords=("额定", "型号", "ccc", "cqc", "电源", "适配器", "输入", "输出", "频率", "安规", "emc", "电磁兼容", "锂电池", "电池组", "铭牌"),
        exclusions=("营养", "配料", "净含量", "保质期"),
    ),
    RoutingProfile(
        code="dairy",
        priority=78,
        keywords=("发酵乳", "灭菌乳", "调制乳", "乳粉", "生牛乳", "巴氏杀菌乳", "奶酪", "酸奶", "乳饮料", "乳清", "干酪", "稀奶油"),
    ),
    RoutingProfile(
        code="canned_food",
        priority=76,
        keywords=("罐头", "商业无菌", "罐藏", "马口铁", "杀菌釜", "罐装辅助食品"),
    ),
    RoutingProfile(
        code="frozen_food",
        priority=74,
        keywords=("速冻", "冷冻", "-18", "－18", "冻藏", "冷链", "水饺", "汤圆", "包子", "速冻面米", "速冻调制"),
    ),
    RoutingProfile(
        code="puffed_food",
        priority=72,
        keywords=("膨化", "薯片", "锅巴", "虾条", "米果", "酸价", "过氧化值", "油炸型"),
    ),
    RoutingProfile(
        code="candy",
        priority=70,
        keywords=("糖果", "巧克力", "凝胶糖果", "硬糖", "软糖", "甜味剂", "糖醇", "代可可脂", "果冻"),
    ),
    RoutingProfile(
        code="food",
        priority=10,
        keywords=("食品", "配料", "净含量", "营养成分", "生产许可证", "保质期", "贮存条件", "执行标准"),
    ),
)


def classify_industry_code(text: str) -> str:
    normalized = (text or "").lower()
    best_code = "food"
    best_score = 0
    for profile in ROUTING_PROFILES:
        if profile.exclusions and any(word.lower() in normalized for word in profile.exclusions):
            exclusion_penalty = 3
        else:
            exclusion_penalty = 0
        hits = sum(1 for word in profile.keywords if word.lower() in normalized)
        score = hits * 10 + profile.priority - exclusion_penalty
        if hits and score > best_score:
            best_score = score
            best_code = profile.code
    return best_code
