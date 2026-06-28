BASE_FOOD_CLAUSES = [
    {"no": "GB 7718 4.1.2", "title": "食品名称应真实反映食品属性，不得误导消费者"},
    {"no": "GB 7718 4.1.3", "title": "配料表应按要求标示，复合配料和食品添加剂标示应清晰"},
    {"no": "GB 7718 4.1.5", "title": "净含量和规格应清晰标示，计量单位应规范"},
    {"no": "GB 7718 4.1.6", "title": "制造者、经销者名称地址和联系方式应依法标示"},
    {"no": "GB 7718 4.1.7", "title": "日期标示和贮存条件应清晰、醒目、不可篡改"},
    {"no": "GB 28050", "title": "营养成分表基础项目应包含能量、蛋白质、脂肪、碳水化合物、钠及 NRV%"},
]

from .legal_catalog import build_expanded_seed_standards


NUTRITION_CLAUSES = [
    {"no": "GB 28050 4.1", "title": "预包装食品营养标签应标示能量、核心营养素含量值及其占营养素参考值百分比"},
    {"no": "GB 28050 4.2", "title": "核心营养素包括蛋白质、脂肪、碳水化合物和钠"},
    {"no": "GB 28050 6", "title": "营养声称和营养成分功能声称应符合标准规定条件"},
]


COMMON_SAFETY_CLAUSES = [
    {"no": "GB 2760", "title": "食品添加剂应符合使用范围、最大使用量和残留量要求"},
    {"no": "GB 2761", "title": "食品中真菌毒素限量应符合适用品类要求"},
    {"no": "GB 2762", "title": "铅、镉、砷、汞等污染物限量应符合适用品类要求"},
    {"no": "GB 29921", "title": "预包装食品中致病菌限量应符合适用品类要求"},
]


SEED_INDUSTRIES = [
    {"name": "食品检测", "code": "food", "description": "预包装食品标签、配料、净含量、营养声称与常规安全项目审核。"},
    {"name": "乳制品检测", "code": "dairy", "description": "液态乳、乳粉、发酵乳等乳制品标签和理化/微生物检测审核。"},
    {"name": "罐头食品检测", "code": "canned_food", "description": "畜禽、水产、果蔬等罐头食品标签、商业无菌与污染物审核。"},
    {"name": "速冻食品检测", "code": "frozen_food", "description": "速冻面米、调制食品、水产制品等标签、贮存和微生物审核。"},
    {"name": "膨化食品检测", "code": "puffed_food", "description": "薯片、锅巴、谷物膨化等标签、油脂氧化和污染物审核。"},
    {"name": "糖果制品检测", "code": "candy", "description": "硬糖、凝胶糖果、巧克力等标签、添加剂和理化指标审核。"},
    {"name": "宠物食品检测", "code": "pet_food", "description": "宠物配合饲料、添加剂预混合饲料、零食标签与安全项目审核。"},
    {"name": "电子电器检测", "code": "electronics", "description": "电子电器产品认证、铭牌、说明书、安规与 EMC 检测审核。"},
]


SEED_STANDARDS = {
    "food": [
        {"code": "GB 7718-2011", "name": "预包装食品标签通则", "version": "2011", "effective_date": "2012-04-20", "clauses": BASE_FOOD_CLAUSES},
        {"code": "GB 28050-2011", "name": "预包装食品营养标签通则", "version": "2011", "effective_date": "2013-01-01", "clauses": NUTRITION_CLAUSES},
        {"code": "GB 2760-2024", "name": "食品安全国家标准 食品添加剂使用标准", "version": "2024", "effective_date": "2025-02-08", "clauses": [{"no": "通用", "title": "食品添加剂使用范围与限量"}]},
        {"code": "GB 2761-2017", "name": "食品安全国家标准 食品中真菌毒素限量", "version": "2017", "effective_date": "2017-09-17", "clauses": [{"no": "通用", "title": "黄曲霉毒素、脱氧雪腐镰刀菌烯醇等真菌毒素限量"}]},
        {"code": "GB 2762-2022", "name": "食品安全国家标准 食品中污染物限量", "version": "2022", "effective_date": "2023-06-30", "clauses": [{"no": "通用", "title": "铅、镉、砷、汞等污染物限量"}]},
        {"code": "GB 29921-2021", "name": "食品安全国家标准 预包装食品中致病菌限量", "version": "2021", "effective_date": "2021-11-22", "clauses": [{"no": "通用", "title": "沙门氏菌、金黄色葡萄球菌、单核细胞增生李斯特氏菌等致病菌限量"}]},
    ],
    "dairy": [
        {"code": "GB 7718-2011", "name": "预包装食品标签通则", "version": "2011", "effective_date": "2012-04-20", "clauses": BASE_FOOD_CLAUSES},
        {"code": "GB 28050-2011", "name": "预包装食品营养标签通则", "version": "2011", "effective_date": "2013-01-01", "clauses": NUTRITION_CLAUSES},
        {"code": "GB 19301-2010", "name": "食品安全国家标准 生乳", "version": "2010", "effective_date": "2010-06-01", "clauses": [{"no": "4", "title": "感官、理化、污染物和微生物要求"}]},
        {"code": "GB 19302-2010", "name": "食品安全国家标准 发酵乳", "version": "2010", "effective_date": "2010-12-01", "clauses": [{"no": "4", "title": "感官、理化和微生物要求"}]},
        {"code": "GB 19645-2010", "name": "食品安全国家标准 巴氏杀菌乳", "version": "2010", "effective_date": "2010-12-01", "clauses": [{"no": "4", "title": "感官、理化和微生物要求"}]},
        {"code": "GB 25190-2010", "name": "食品安全国家标准 灭菌乳", "version": "2010", "effective_date": "2010-12-01", "clauses": [{"no": "4", "title": "理化指标和污染物要求"}]},
        {"code": "GB 25191-2010", "name": "食品安全国家标准 调制乳", "version": "2010", "effective_date": "2010-12-01", "clauses": [{"no": "4", "title": "理化、污染物和微生物要求"}]},
        {"code": "GB 2762-2022", "name": "食品安全国家标准 食品中污染物限量", "version": "2022", "effective_date": "2023-06-30", "clauses": COMMON_SAFETY_CLAUSES},
    ],
    "canned_food": [
        {"code": "GB 7718-2011", "name": "预包装食品标签通则", "version": "2011", "effective_date": "2012-04-20", "clauses": BASE_FOOD_CLAUSES},
        {"code": "GB 7098-2015", "name": "食品安全国家标准 罐头食品", "version": "2015", "effective_date": "2016-11-13", "clauses": [{"no": "3.4", "title": "商业无菌要求"}, {"no": "3.3", "title": "污染物和真菌毒素限量"}]},
        {"code": "GB 4789.26-2013", "name": "食品安全国家标准 食品微生物学检验 商业无菌检验", "version": "2013", "effective_date": "2014-06-01", "clauses": [{"no": "方法", "title": "罐头食品商业无菌检验方法"}]},
        {"code": "GB 2762-2022", "name": "食品安全国家标准 食品中污染物限量", "version": "2022", "effective_date": "2023-06-30", "clauses": COMMON_SAFETY_CLAUSES},
    ],
    "frozen_food": [
        {"code": "GB 7718-2011", "name": "预包装食品标签通则", "version": "2011", "effective_date": "2012-04-20", "clauses": BASE_FOOD_CLAUSES},
        {"code": "GB 19295-2021", "name": "食品安全国家标准 速冻面米与调制食品", "version": "2021", "effective_date": "2022-03-07", "clauses": [{"no": "3", "title": "原料、感官、污染物和微生物要求"}]},
        {"code": "GB 29921-2021", "name": "食品安全国家标准 预包装食品中致病菌限量", "version": "2021", "effective_date": "2021-11-22", "clauses": COMMON_SAFETY_CLAUSES},
    ],
    "puffed_food": [
        {"code": "GB 7718-2011", "name": "预包装食品标签通则", "version": "2011", "effective_date": "2012-04-20", "clauses": BASE_FOOD_CLAUSES},
        {"code": "GB 17401-2014", "name": "食品安全国家标准 膨化食品", "version": "2014", "effective_date": "2015-05-24", "clauses": [{"no": "3", "title": "酸价、过氧化值、污染物和微生物要求"}]},
        {"code": "GB 5009.227-2023", "name": "食品安全国家标准 食品中过氧化值的测定", "version": "2023", "effective_date": "2024-03-06", "clauses": [{"no": "方法", "title": "油脂氧化相关过氧化值测定"}]},
        {"code": "GB 5009.229-2016", "name": "食品安全国家标准 食品中酸价的测定", "version": "2016", "effective_date": "2017-03-01", "clauses": [{"no": "方法", "title": "油脂酸败相关酸价测定"}]},
    ],
    "candy": [
        {"code": "GB 7718-2011", "name": "预包装食品标签通则", "version": "2011", "effective_date": "2012-04-20", "clauses": BASE_FOOD_CLAUSES},
        {"code": "GB 17399-2016", "name": "食品安全国家标准 糖果", "version": "2016", "effective_date": "2017-06-23", "clauses": [{"no": "3", "title": "感官、污染物、微生物和食品添加剂要求"}]},
        {"code": "GB 9678.2-2014", "name": "巧克力、代可可脂巧克力及其制品", "version": "2014", "effective_date": "2015-05-24", "clauses": [{"no": "标签", "title": "可可脂/代可可脂相关标示"}]},
        {"code": "GB 2760-2024", "name": "食品安全国家标准 食品添加剂使用标准", "version": "2024", "effective_date": "2025-02-08", "clauses": COMMON_SAFETY_CLAUSES},
    ],
    "pet_food": [
        {"code": "农业农村部公告第20号", "name": "宠物饲料管理办法及配套规范", "version": "2018", "effective_date": "2018-06-01", "clauses": [{"no": "宠物饲料标签规定", "title": "产品名称、原料组成、成分分析保证值、适用阶段、净含量"}]},
        {"code": "GB/T 31216-2014", "name": "全价宠物食品 犬粮", "version": "2014", "effective_date": "2015-03-08", "clauses": [{"no": "8", "title": "标签、营养成分和卫生指标"}]},
        {"code": "GB/T 31217-2014", "name": "全价宠物食品 猫粮", "version": "2014", "effective_date": "2015-03-08", "clauses": [{"no": "8", "title": "标签、营养成分和卫生指标"}]},
        {"code": "GB 13078-2017", "name": "饲料卫生标准", "version": "2017", "effective_date": "2018-05-01", "clauses": [{"no": "通用", "title": "霉菌毒素、重金属、微生物等卫生指标"}]},
    ],
    "electronics": [
        {"code": "GB 4943.1-2022", "name": "音视频、信息技术和通信技术设备 第1部分：安全要求", "version": "2022", "effective_date": "2023-08-01", "clauses": [{"no": "F", "title": "标识、说明和警示"}]},
        {"code": "GB/T 9254.1-2021", "name": "信息技术设备、多媒体设备和接收机 电磁兼容 发射要求", "version": "2021", "effective_date": "2022-07-01", "clauses": [{"no": "通用", "title": "EMC 发射要求"}]},
        {"code": "GB 17625.1-2022", "name": "电磁兼容 限值 谐波电流发射限值", "version": "2022", "effective_date": "2024-07-01", "clauses": [{"no": "通用", "title": "谐波电流发射限值"}]},
        {"code": "CNCA-C08-01", "name": "强制性产品认证实施规则 音视频设备", "version": "现行", "effective_date": "", "clauses": [{"no": "认证单元", "title": "CCC 认证单元划分、型式试验和获证后监督要求"}]},
        {"code": "CCC目录", "name": "强制性产品认证目录适用要求", "version": "现行", "effective_date": "", "clauses": [{"no": "适用范围", "title": "判断是否属于强制认证产品"}]},
    ],
}

SEED_STANDARDS = build_expanded_seed_standards(SEED_STANDARDS)


COMMON_FOOD_RULES = [
    {"standard_code": "GB 7718-2011", "name": "产品名称必填", "rule_type": "deterministic", "field_key": "product_name", "trigger": "产品名称", "risk_level": "medium", "suggestion": "请标注能真实反映食品属性的产品名称。"},
    {"standard_code": "GB 7718-2011", "name": "配料表必填", "rule_type": "deterministic", "field_key": "ingredients", "trigger": "配料", "risk_level": "medium", "suggestion": "请按配料加入量递减顺序标示配料表，复合配料和食品添加剂标示应清晰。"},
    {"standard_code": "GB 7718-2011", "name": "净含量必填", "rule_type": "deterministic", "field_key": "net_content", "trigger": "净含量", "risk_level": "medium", "suggestion": "请标注净含量和规格，并核对计量单位。"},
    {"standard_code": "GB 7718-2011", "name": "生产者信息必填", "rule_type": "deterministic", "field_key": "manufacturer", "trigger": "生产者、地址、联系方式", "risk_level": "medium", "suggestion": "请标注生产者或经销者名称、地址和联系方式。"},
    {"standard_code": "GB 7718-2011", "name": "日期和保质期必填", "rule_type": "deterministic", "field_key": "shelf_life", "trigger": "生产日期、保质期、贮存条件", "risk_level": "medium", "suggestion": "请清晰标注生产日期、保质期和贮存条件。"},
    {"standard_code": "GB 7718-2011", "name": "食品生产许可证编号格式", "rule_type": "deterministic", "field_key": "license_no", "trigger": "SC+14位数字", "risk_level": "medium", "suggestion": "请标注有效食品生产许可证编号，格式应为 SC 加 14 位数字。"},
    {"standard_code": "GB 28050-2011", "name": "营养成分表必填项", "rule_type": "deterministic", "field_key": "nutrition", "trigger": "能量、蛋白质、脂肪、碳水化合物、钠", "risk_level": "high", "suggestion": "请补全营养成分表基础 5 项，并核对 NRV%。"},
    {"standard_code": "GB 2760-2024", "name": "添加剂合规风险", "rule_type": "ai", "field_key": "ingredients", "trigger": "山梨酸、苯甲酸、糖精钠、甜蜜素、安赛蜜、柠檬黄、日落黄、防腐剂、色素、甜味剂", "risk_level": "medium", "suggestion": "请核对食品添加剂使用范围和限量；必要时增加添加剂检测项目。"},
    {"standard_code": "GB 2762-2022", "name": "污染物限量风险", "rule_type": "ai", "field_key": "product_type", "trigger": "谷物、水产、肉制品、蔬菜、水果、坚果、婴幼儿", "risk_level": "medium", "suggestion": "请按适用品类核对污染物限量，必要时增加铅、镉、砷、汞等项目。"},
    {"standard_code": "GB 29921-2021", "name": "致病菌限量风险", "rule_type": "ai", "field_key": "product_type", "trigger": "即食、冷藏、速冻、乳、肉、蛋、水产、调制食品", "risk_level": "medium", "suggestion": "请按品类核对致病菌限量，必要时增加沙门氏菌、金黄色葡萄球菌等微生物项目。"},
    {"standard_code": "GB 7718-2011", "name": "绝对化宣传用语", "rule_type": "ai", "field_key": "claims", "trigger": "最好、第一、最安全、100%、纯天然、零添加、无任何、顶级、唯一", "risk_level": "high", "suggestion": "删除或弱化绝对化、无依据的功效化描述，改为客观表述。"},
]


SEED_RULES = {
    "food": COMMON_FOOD_RULES,
    "dairy": COMMON_FOOD_RULES + [
        {"standard_code": "GB 25190-2010", "name": "乳制品类别和灭菌/发酵属性", "rule_type": "deterministic", "field_key": "product_type", "trigger": "灭菌乳/发酵乳/调制乳/乳粉/巴氏杀菌乳", "risk_level": "medium", "suggestion": "请明确乳制品类别，并与执行标准、配料和工艺属性保持一致。"},
        {"standard_code": "GB 19302-2010", "name": "乳蛋白/脂肪关键指标", "rule_type": "ai", "field_key": "nutrition", "trigger": "蛋白质、脂肪、非脂乳固体、乳酸菌", "risk_level": "medium", "suggestion": "建议检测乳蛋白、脂肪等关键指标，核对是否支撑标签声称。"},
        {"standard_code": "GB 2762-2022", "name": "乳制品污染物风险", "rule_type": "ai", "field_key": "product_type", "trigger": "生乳、乳粉、调制乳、发酵乳", "risk_level": "medium", "suggestion": "建议结合品类检测铅、黄曲霉毒素 M1 等安全指标。"},
    ],
    "canned_food": COMMON_FOOD_RULES + [
        {"standard_code": "GB 7098-2015", "name": "罐头商业无菌风险", "rule_type": "ai", "field_key": "claims", "trigger": "即食、常温、罐头、商业无菌", "risk_level": "high", "suggestion": "罐头食品建议进行商业无菌项目确认，并核对杀菌工艺和贮存条件。"},
        {"standard_code": "GB 7098-2015", "name": "罐头品类与贮存条件", "rule_type": "deterministic", "field_key": "storage_condition", "trigger": "常温/阴凉/避光/开启后冷藏", "risk_level": "medium", "suggestion": "请根据罐头产品类型标注合理贮存条件和开启后食用提示。"},
    ],
    "frozen_food": COMMON_FOOD_RULES + [
        {"standard_code": "GB 19295-2021", "name": "速冻贮存条件", "rule_type": "deterministic", "field_key": "storage_condition", "trigger": "-18℃/冷冻/速冻", "risk_level": "high", "suggestion": "请明确标注速冻食品贮存条件，如 -18℃ 以下保存。"},
        {"standard_code": "GB 19295-2021", "name": "速冻微生物风险", "rule_type": "ai", "field_key": "product_type", "trigger": "速冻面米、速冻调制、肉馅、水产、即食", "risk_level": "medium", "suggestion": "建议按产品属性增加菌落总数、大肠菌群或致病菌项目。"},
    ],
    "puffed_food": COMMON_FOOD_RULES + [
        {"standard_code": "GB 17401-2014", "name": "膨化食品油脂氧化风险", "rule_type": "ai", "field_key": "product_name", "trigger": "膨化、油炸、薯片、锅巴、虾条、米果", "risk_level": "medium", "suggestion": "建议检测酸价和过氧化值，核对油脂氧化风险。"},
        {"standard_code": "GB 17401-2014", "name": "膨化食品微生物风险", "rule_type": "ai", "field_key": "product_type", "trigger": "直接入口、膨化、夹心、含肉、含乳", "risk_level": "medium", "suggestion": "建议结合产品配料和食用方式确认微生物检测项目。"},
    ],
    "candy": COMMON_FOOD_RULES + [
        {"standard_code": "GB 2760-2024", "name": "糖果添加剂和甜味剂风险", "rule_type": "ai", "field_key": "ingredients", "trigger": "甜味剂、色素、防腐剂、山梨酸、苯甲酸、糖醇、糖精钠、甜蜜素、安赛蜜", "risk_level": "medium", "suggestion": "请核对食品添加剂使用范围和限量，必要时检测甜味剂/色素/防腐剂。"},
        {"standard_code": "GB 9678.2-2014", "name": "巧克力代可可脂标示风险", "rule_type": "ai", "field_key": "ingredients", "trigger": "代可可脂、可可脂、巧克力、类巧克力", "risk_level": "medium", "suggestion": "请核对可可脂、代可可脂相关名称和配料标示，避免品名误导。"},
    ],
    "pet_food": [
        {"standard_code": "农业农村部公告第20号", "name": "宠物食品产品名称", "rule_type": "deterministic", "field_key": "product_name", "trigger": "产品名称", "risk_level": "medium", "suggestion": "请标注能反映宠物饲料属性的产品名称，并避免与适用宠物、产品类型不一致。"},
        {"standard_code": "农业农村部公告第20号", "name": "宠物食品适用对象声明", "rule_type": "deterministic", "field_key": "target_pet", "trigger": "犬/猫/全阶段/幼年/成年", "risk_level": "medium", "suggestion": "请明确标注适用宠物类型和生命阶段。"},
        {"standard_code": "农业农村部公告第20号", "name": "成分分析保证值", "rule_type": "deterministic", "field_key": "nutrition", "trigger": "粗蛋白、粗脂肪、粗纤维、粗灰分、水分", "risk_level": "high", "suggestion": "请标注宠物食品成分分析保证值，并核对检测数据。"},
        {"standard_code": "农业农村部公告第20号", "name": "宠物食品原料组成", "rule_type": "deterministic", "field_key": "ingredients", "trigger": "原料组成", "risk_level": "medium", "suggestion": "请按要求标注原料组成，避免使用无依据功效声称。"},
        {"standard_code": "农业农村部公告第20号", "name": "宠物食品净含量", "rule_type": "deterministic", "field_key": "net_content", "trigger": "净含量", "risk_level": "medium", "suggestion": "请标注净含量，并使用规范计量单位。"},
        {"standard_code": "宠物饲料标签规定", "name": "宠物食品生产者信息", "rule_type": "deterministic", "field_key": "manufacturer", "trigger": "生产企业、地址、联系方式", "risk_level": "medium", "suggestion": "请补充生产者、委托方或经销者名称、地址和联系方式。"},
        {"standard_code": "宠物饲料标签规定", "name": "宠物食品日期和保质期", "rule_type": "deterministic", "field_key": "shelf_life", "trigger": "生产日期、保质期、批号", "risk_level": "medium", "suggestion": "请清晰标注生产日期、批号和保质期。"},
        {"standard_code": "宠物饲料标签规定", "name": "宠物食品贮存条件", "rule_type": "deterministic", "field_key": "storage_condition", "trigger": "贮存/保存/储存", "risk_level": "medium", "suggestion": "请标注与产品形态匹配的贮存条件。"},
        {"standard_code": "宠物饲料标签规定", "name": "宠物食品饲喂说明", "rule_type": "deterministic", "field_key": "feeding_instruction", "trigger": "饲喂/喂食/使用方法", "risk_level": "medium", "suggestion": "请补充饲喂方法、建议喂食量或使用说明，便于消费者正确使用。"},
        {"standard_code": "宠物饲料标签规定", "name": "宠物食品添加剂组成风险", "rule_type": "ai", "field_key": "ingredients", "trigger": "添加剂、营养性添加剂、诱食剂、防腐剂、抗氧化剂、着色剂、调味剂", "risk_level": "medium", "suggestion": "如使用添加剂，请按要求标注添加剂组成或相关类别信息。"},
        {"standard_code": "宠物饲料标签规定", "name": "宠物食品注意事项", "rule_type": "deterministic", "field_key": "manual_warning", "trigger": "注意事项/警示/请勿", "risk_level": "low", "suggestion": "建议标注开封后保存、喂食安全或不适用情形等注意事项。"},
        {"standard_code": "GB 13078-2017", "name": "宠物食品卫生指标风险", "rule_type": "ai", "field_key": "ingredients", "trigger": "鱼粉、肉粉、肝、谷物、花生、霉菌、重金属", "risk_level": "medium", "suggestion": "建议结合原料组成检测卫生指标、霉菌毒素或重金属。"},
        {"standard_code": "农业农村部公告第20号", "name": "宠物食品功效化宣传风险", "rule_type": "ai", "field_key": "claims", "trigger": "治疗、治愈、预防疾病、增强免疫、改善泪痕、药用、处方、特效", "risk_level": "high", "suggestion": "请删除或弱化疾病治疗、药用或缺乏依据的功效化描述。"},
    ],
    "electronics": [
        {"standard_code": "GB 4943.1-2022", "name": "电子产品名称必填", "rule_type": "deterministic", "field_key": "product_name", "trigger": "产品名称", "risk_level": "medium", "suggestion": "请在铭牌、包装或说明书中标注清晰的产品名称。"},
        {"standard_code": "GB 4943.1-2022", "name": "型号规格必填", "rule_type": "deterministic", "field_key": "model_no", "trigger": "型号", "risk_level": "medium", "suggestion": "请在铭牌或说明书中标注产品型号规格。"},
        {"standard_code": "GB 4943.1-2022", "name": "额定参数必填", "rule_type": "deterministic", "field_key": "rating", "trigger": "额定输入/输出/电压/电流/功率/频率", "risk_level": "high", "suggestion": "请标注额定电压、电流、频率或功率等关键安全参数。"},
        {"standard_code": "GB 4943.1-2022", "name": "电子产品制造商信息", "rule_type": "deterministic", "field_key": "manufacturer", "trigger": "制造商、生产者、地址、联系方式", "risk_level": "medium", "suggestion": "请补充制造商或责任方名称、地址和必要联系方式。"},
        {"standard_code": "GB 4943.1-2022", "name": "安全标准或执行标准", "rule_type": "deterministic", "field_key": "execution_standard", "trigger": "GB/执行标准/安全标准", "risk_level": "medium", "suggestion": "请标注适用的安全标准、执行标准或在说明书中提供合规依据。"},
        {"standard_code": "CCC目录", "name": "CCC/安全认证标识", "rule_type": "deterministic", "field_key": "certification", "trigger": "认证标识或安全标准引用", "risk_level": "high", "suggestion": "请核对产品是否属于强制认证目录，并补充认证编号或合规说明。"},
        {"standard_code": "GB 4943.1-2022", "name": "说明书警示语", "rule_type": "deterministic", "field_key": "manual_warning", "trigger": "安全警示", "risk_level": "medium", "suggestion": "请补充必要的使用警示、安装条件和安全注意事项。"},
        {"standard_code": "GB/T 9254.1-2021", "name": "EMC 发射风险", "rule_type": "ai", "field_key": "product_name", "trigger": "适配器、信息技术设备、多媒体、蓝牙、无线、开关电源", "risk_level": "medium", "suggestion": "建议按产品属性增加 EMC 发射或预扫项目。"},
        {"standard_code": "GB 31241-2022", "name": "锂电池安全风险", "rule_type": "ai", "field_key": "product_name", "trigger": "锂电池、电池组、移动电源、充电宝、便携式、电池包", "risk_level": "high", "suggestion": "如产品含锂电池或电池组，请核对 GB 31241 适用性并补充电池安全检测资料。"},
        {"standard_code": "GB 26572-2025", "name": "限用物质标识风险", "rule_type": "ai", "field_key": "claims", "trigger": "RoHS、环保使用期限、限用物质、有害物质、铅、汞、镉、六价铬", "risk_level": "medium", "suggestion": "请核对电子电气产品限用物质标识和检测资料。"},
    ],
}


SEED_FIELDS = {
    "food": ["product_name", "product_type", "ingredients", "nutrition", "net_content", "license_no", "manufacturer", "address", "shelf_life", "production_date", "expiry_date", "claims", "storage_condition", "execution_standard"],
    "dairy": ["product_name", "product_type", "ingredients", "nutrition", "net_content", "license_no", "manufacturer", "address", "shelf_life", "production_date", "expiry_date", "claims", "storage_condition", "execution_standard"],
    "canned_food": ["product_name", "product_type", "ingredients", "nutrition", "net_content", "license_no", "manufacturer", "address", "shelf_life", "production_date", "expiry_date", "claims", "storage_condition", "execution_standard"],
    "frozen_food": ["product_name", "product_type", "ingredients", "nutrition", "net_content", "license_no", "manufacturer", "address", "shelf_life", "production_date", "expiry_date", "claims", "storage_condition", "execution_standard"],
    "puffed_food": ["product_name", "product_type", "ingredients", "nutrition", "net_content", "license_no", "manufacturer", "address", "shelf_life", "production_date", "expiry_date", "claims", "storage_condition", "execution_standard"],
    "candy": ["product_name", "product_type", "ingredients", "nutrition", "net_content", "license_no", "manufacturer", "address", "shelf_life", "production_date", "expiry_date", "claims", "storage_condition", "execution_standard"],
    "pet_food": ["product_name", "product_type", "ingredients", "additives", "nutrition", "target_pet", "net_content", "manufacturer", "address", "phone", "shelf_life", "production_date", "expiry_date", "storage_condition", "feeding_instruction", "manual_warning", "claims", "execution_standard"],
    "electronics": ["product_name", "product_type", "model_no", "rating", "certification", "manufacturer", "address", "phone", "execution_standard", "manual_warning", "claims"],
}


SEED_ITEMS = {
    "food": [
        {"code": "F001", "name": "标签审核", "method_standard": "GB 7718 / GB 28050", "price": 300, "cycle_days": 3, "sample_amount": "标签图片或样品包装", "package_name": "标签合规套餐"},
        {"code": "F002", "name": "营养成分 5 项", "method_standard": "GB 5009 系列", "judgment_standard": "GB 28050", "price": 500, "cycle_days": 5, "sample_amount": "不少于500g", "package_name": "营养标签套餐"},
        {"code": "F003", "name": "重金属 4 项", "method_standard": "GB 5009.11/12/15/17", "judgment_standard": "GB 2762", "price": 480, "cycle_days": 5, "sample_amount": "不少于500g", "package_name": "污染物套餐"},
        {"code": "F004", "name": "食品添加剂筛查", "method_standard": "GB 5009 / GB 2760", "judgment_standard": "GB 2760", "price": 680, "cycle_days": 7, "sample_amount": "不少于500g", "package_name": "添加剂套餐"},
    ],
    "dairy": [
        {"code": "D001", "name": "乳制品标签审核", "method_standard": "GB 7718 / GB 28050", "price": 320, "cycle_days": 3, "sample_amount": "标签或包装", "package_name": "乳制品合规套餐"},
        {"code": "D002", "name": "蛋白质/脂肪/非脂乳固体", "method_standard": "GB 5009 系列", "price": 620, "cycle_days": 5, "sample_amount": "不少于500mL或500g", "package_name": "乳制品理化套餐"},
        {"code": "D003", "name": "乳制品微生物", "method_standard": "GB 4789 系列", "price": 580, "cycle_days": 5, "sample_amount": "不少于5个独立包装", "package_name": "乳制品微生物套餐"},
    ],
    "canned_food": [
        {"code": "C001", "name": "罐头标签审核", "method_standard": "GB 7718 / GB 7098", "price": 320, "cycle_days": 3, "sample_amount": "标签或包装", "package_name": "罐头合规套餐"},
        {"code": "C002", "name": "商业无菌", "method_standard": "GB 4789.26", "judgment_standard": "GB 7098", "price": 760, "cycle_days": 10, "sample_amount": "不少于6罐", "package_name": "罐头安全套餐"},
        {"code": "C003", "name": "罐头污染物", "method_standard": "GB 5009 系列", "judgment_standard": "GB 2762", "price": 520, "cycle_days": 5, "sample_amount": "不少于500g", "package_name": "污染物套餐"},
    ],
    "frozen_food": [
        {"code": "Z001", "name": "速冻标签审核", "method_standard": "GB 7718 / GB 19295", "price": 320, "cycle_days": 3, "sample_amount": "标签或包装", "package_name": "速冻合规套餐"},
        {"code": "Z002", "name": "速冻微生物", "method_standard": "GB 4789 系列", "judgment_standard": "GB 19295", "price": 620, "cycle_days": 5, "sample_amount": "不少于5个独立包装", "package_name": "速冻微生物套餐"},
    ],
    "puffed_food": [
        {"code": "PF001", "name": "膨化食品标签审核", "method_standard": "GB 7718 / GB 17401", "price": 300, "cycle_days": 3, "sample_amount": "标签或包装", "package_name": "膨化合规套餐"},
        {"code": "PF002", "name": "酸价/过氧化值", "method_standard": "GB 5009.229 / GB 5009.227", "judgment_standard": "GB 17401", "price": 420, "cycle_days": 5, "sample_amount": "不少于500g", "package_name": "油脂氧化套餐"},
    ],
    "candy": [
        {"code": "S001", "name": "糖果标签审核", "method_standard": "GB 7718 / GB 17399", "price": 300, "cycle_days": 3, "sample_amount": "标签或包装", "package_name": "糖果合规套餐"},
        {"code": "S002", "name": "甜味剂/色素/防腐剂", "method_standard": "GB 5009 系列", "judgment_standard": "GB 2760", "price": 780, "cycle_days": 7, "sample_amount": "不少于500g", "package_name": "添加剂套餐"},
    ],
    "pet_food": [
        {"code": "P001", "name": "宠物食品标签审核", "method_standard": "农业农村部公告第20号", "price": 350, "cycle_days": 3, "sample_amount": "包装或标签图片", "package_name": "宠物食品合规套餐"},
        {"code": "P002", "name": "粗蛋白/粗脂肪/水分", "method_standard": "GB/T 6432/6433/6435", "price": 420, "cycle_days": 5, "sample_amount": "不少于500g", "package_name": "营养指标套餐"},
        {"code": "P003", "name": "宠物食品卫生指标", "method_standard": "GB/T 13079 / 13080 / 13091", "price": 880, "cycle_days": 7, "sample_amount": "不少于1kg", "package_name": "宠物食品安全套餐"},
    ],
    "electronics": [
        {"code": "E001", "name": "铭牌与说明书审核", "method_standard": "GB 4943.1", "price": 450, "cycle_days": 3, "sample_amount": "铭牌图片和说明书", "package_name": "电子电器合规套餐"},
        {"code": "E002", "name": "安规摸底测试", "method_standard": "GB 4943.1", "price": 1800, "cycle_days": 7, "sample_amount": "整机2台", "package_name": "安规测试套餐"},
        {"code": "E003", "name": "EMC 发射预扫", "method_standard": "GB/T 9254.1", "price": 2200, "cycle_days": 7, "sample_amount": "整机1台及电源适配器", "package_name": "EMC 套餐"},
    ],
}


SEED_MODELS = [
    {"provider": "deepseek", "model": "deepseek-chat", "supports_vision": False, "supports_json": True, "supports_tools": True, "default_for_text": True, "api_key_hint": "DEEPSEEK_API_KEY"},
    {"provider": "tokenskingdom", "model": "gpt-5.5", "base_url": "https://api.tokenskingdom.com/v1", "supports_vision": True, "supports_json": True, "supports_tools": False, "default_for_vision": True, "api_key_hint": "TOKENSKINGDOM_API_KEY"},
    {"provider": "qwen", "model": "qwen-plus", "supports_vision": False, "supports_json": True, "supports_tools": True, "api_key_hint": "DASHSCOPE_API_KEY"},
    {"provider": "openai", "model": "gpt-4.1", "supports_vision": True, "supports_json": True, "supports_tools": True, "api_key_hint": "OPENAI_API_KEY"},
    {"provider": "claude", "model": "claude-sonnet-4", "supports_vision": True, "supports_json": True, "supports_tools": True, "api_key_hint": "ANTHROPIC_API_KEY"},
    {"provider": "doubao", "model": "doubao-vision-pro", "supports_vision": True, "supports_json": True, "supports_tools": False, "api_key_hint": "ARK_API_KEY"},
]
