import json
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from ..config import settings
from ..schemas.common import AppError
from ..schemas.recipe import AIRecipeList, RecommendationRequest
from .ingredient_names import canonical_name


SYSTEM_PROMPT = """你是面向中国家庭日常烹饪场景的菜谱推荐助手。
根据用户当前可用库存推荐普通家庭可以完成的菜，通常返回 3 到 5 道；合理候选不足时可以少于 3 道，不能为了凑数编造菜品。
必须遵守：
1. 优先使用距离过期最近的食材，并尽量使用现有库存。
2. 每道菜缺少食材控制在 0 到 3 种，不把常见基础油盐计入缺少食材。
3. 不使用过期、零库存或不存在的食材作为已有食材。
4. 不推荐危险、不合理或不符合普通家庭习惯的组合。
5. 库存按预计可做餐数管理；consumptions 对每种已用食材固定为 1 餐。
6. cooking_time 为整数分钟；difficulty 只能是“简单”或“中等”。
7. 步骤应具体、有顺序，普通用户可照着完成。
8. 只能从 approved_recipe_candidates 中选择，不得自创菜名、食材组合、用量或步骤。
9. 尽量避开 recently_recommended_dishes 中近期已经推荐过的菜；只有库存太少、没有合理替代时才允许重复。
10. 只输出 JSON，不输出 Markdown、代码围栏、前言或后记。
输出格式：{"recipes":[{"dish_name":"菜名","description":"简介","used_ingredients":["库存食材"],"missing_ingredients":["缺少食材"],"consumptions":[{"ingredient_name":"库存食材","quantity":1,"unit":"餐"}],"cooking_time":15,"difficulty":"简单","steps":["步骤1","步骤2"],"reason":"推荐原因"}]}"""

RECIPE_META = {
    "西红柿鸡蛋汤": ({"家常菜", "汤羹", "减脂"}, False, "炒锅"),
    "西红柿肉片汤": ({"家常菜", "汤羹"}, False, "炒锅"),
    "冬瓜肉丸汤": ({"家常菜", "汤羹"}, False, "炒锅"),
    "鱼香肉丝": ({"川菜"}, True, "炒锅"),
    "麻婆豆腐": ({"川菜"}, True, "炒锅"),
    "回锅肉": ({"川菜"}, True, "炒锅"),
    "白切鸡": ({"粤菜"}, False, "炒锅"),
    "清蒸排骨": ({"粤菜"}, False, "蒸锅"),
    "虾仁蒸蛋": ({"粤菜", "减脂"}, False, "蒸锅"),
    "西兰花炒鸡胸肉": ({"减脂"}, False, "炒锅"),
    "黄瓜拌鸡胸肉": ({"减脂"}, False, "炒锅"),
    "肉末蒸蛋": ({"家常菜"}, False, "蒸锅"),
    "空气炸锅鸡翅": ({"家常菜"}, False, "空气炸锅"),
    "空气炸锅土豆块": ({"家常菜"}, False, "空气炸锅"),
    "空气炸锅鸡胸肉": ({"减脂"}, False, "空气炸锅"),
    "水煮肉片": ({"川菜"}, True, "炒锅"),
    "酸辣土豆丝": ({"川菜"}, True, "炒锅"),
    "蒜泥白肉": ({"川菜"}, True, "炒锅"),
    "手撕包菜": ({"川菜", "家常菜"}, True, "炒锅"),
    "清蒸鱼": ({"粤菜", "减脂"}, False, "蒸锅"),
    "白灼虾": ({"粤菜", "减脂"}, False, "炒锅"),
    "冬菇蒸鸡": ({"粤菜"}, False, "蒸锅"),
    "蒸水蛋": ({"粤菜", "减脂"}, False, "蒸锅"),
    "清蒸鸡腿": ({"粤菜", "减脂"}, False, "蒸锅"),
    "豆腐蒸肉末": ({"家常菜"}, False, "蒸锅"),
    "番茄豆腐汤": ({"家常菜", "汤羹", "减脂"}, False, "炒锅"),
    "紫菜蛋花汤": ({"家常菜", "汤羹", "减脂"}, False, "炒锅"),
    "冬瓜虾皮汤": ({"家常菜", "汤羹", "减脂"}, False, "炒锅"),
    "丝瓜蛋汤": ({"家常菜", "汤羹", "减脂"}, False, "炒锅"),
    "菠菜鸡蛋汤": ({"家常菜", "汤羹", "减脂"}, False, "炒锅"),
    "玉米排骨汤": ({"家常菜", "汤羹"}, False, "炒锅"),
    "萝卜排骨汤": ({"家常菜", "汤羹"}, False, "炒锅"),
    "菌菇豆腐汤": ({"家常菜", "汤羹", "减脂"}, False, "炒锅"),
    "煎鸡胸肉": ({"减脂"}, False, "炒锅"),
    "虾仁炒西兰花": ({"减脂"}, False, "炒锅"),
}


def _mock_recommendations(
    items: list[dict[str, Any]],
    avoid_dishes: list[str],
    rotation_seed: int,
    preferences: RecommendationRequest,
) -> AIRecipeList:
    by_name = {canonical_name(item["name"]): item for item in items}
    templates = [
        ("可乐鸡翅", ["鸡翅", "可乐"], ["姜", "生抽"], 35, ["鸡翅洗净后两面划刀", "鸡翅煎至两面微黄", "加入姜、生抽和可乐", "小火焖熟后大火收汁"]),
        ("香煎鸡翅", ["鸡翅"], ["姜", "生抽"], 25, ["鸡翅洗净划刀并腌制", "小火煎至两面金黄", "确认内部熟透后出锅"]),
        ("红烧鸡翅", ["鸡翅"], ["姜", "生抽", "冰糖"], 35, ["鸡翅焯水后沥干", "炒出糖色并放入鸡翅", "加水和调味料焖熟收汁"]),
        ("空气炸锅鸡翅", ["鸡翅"], ["生抽", "蜂蜜"], 30, ["鸡翅划刀并腌制", "放入空气炸锅烤制", "中途翻面并确认熟透"]),
        ("可乐鸡腿", ["可乐", "鸡腿"], ["姜", "生抽"], 40, ["鸡腿洗净划刀", "煎至表面微黄", "加入可乐和调味料焖熟收汁"]),
        ("可乐排骨", ["可乐", "排骨"], ["姜", "生抽"], 50, ["排骨焯水洗净", "排骨煎香后加入可乐", "放入调味料炖熟收汁"]),
        ("鱼香肉丝", ["猪肉", "青椒"], ["胡萝卜", "木耳", "豆瓣酱"], 25, ["肉丝腌制，配菜切丝", "肉丝滑炒后盛出", "炒香豆瓣酱并加入配菜和肉丝"]),
        ("麻婆豆腐", ["豆腐", "猪肉"], ["豆瓣酱", "花椒"], 25, ["豆腐切块焯水", "炒香肉末和豆瓣酱", "加入豆腐烧至入味后撒花椒"]),
        ("回锅肉", ["猪肉", "青椒"], ["豆瓣酱", "蒜苗"], 30, ["猪肉煮熟后切片", "肉片煸炒出油", "加入豆瓣酱、青椒和蒜苗翻炒"]),
        ("白切鸡", ["鸡腿"], ["姜", "葱"], 40, ["鸡腿冷水下锅", "小火浸煮至完全熟透", "放凉切块并搭配姜葱蘸料"]),
        ("清蒸排骨", ["排骨"], ["蒜", "豆豉"], 40, ["排骨洗净沥干", "加入蒜和豆豉腌制", "上锅蒸至熟透"]),
        ("虾仁蒸蛋", ["虾仁", "鸡蛋"], ["葱"], 20, ["鸡蛋加温水打匀并过滤", "放入虾仁", "盖住碗口蒸熟后撒葱"]),
        ("西兰花炒鸡胸肉", ["西兰花", "鸡胸肉"], ["蒜"], 20, ["鸡胸肉切片腌制", "西兰花焯水", "炒熟鸡胸肉后加入西兰花和蒜调味"]),
        ("黄瓜拌鸡胸肉", ["黄瓜", "鸡胸肉"], ["蒜", "醋", "生抽"], 20, ["鸡胸肉煮熟后撕丝", "黄瓜切丝", "加入蒜、醋和生抽拌匀"]),
        ("冬瓜肉丸汤", ["冬瓜", "猪肉"], ["姜", "葱", "淀粉"], 30, ["猪肉调味后搅打成馅", "冬瓜切片煮开", "挤入肉丸煮熟后调味"]),
        ("西红柿炒鸡蛋", ["西红柿", "鸡蛋"], ["葱"], 15, ["西红柿切块，鸡蛋打散", "炒熟鸡蛋后盛出", "翻炒西红柿，加入鸡蛋调味"]),
        ("西红柿鸡蛋汤", ["西红柿", "鸡蛋"], ["香油"], 16, ["西红柿切块炒出汁", "加入清水煮开", "淋入蛋液并调味"]),
        ("青椒土豆丝", ["青椒", "土豆"], ["醋"], 18, ["土豆和青椒切丝", "土豆丝清水冲洗", "大火翻炒并调味"]),
        ("清炒土豆片", ["土豆"], ["蒜"], 15, ["土豆切薄片并冲洗", "热锅炒香蒜末", "加入土豆片炒熟并调味"]),
        ("青椒肉丝", ["青椒", "猪肉"], ["生抽"], 20, ["猪肉和青椒切丝", "肉丝滑炒至变色", "加入青椒快速翻炒调味"]),
        ("土豆炒肉片", ["土豆", "猪肉"], ["生抽"], 25, ["土豆切片并冲洗", "肉片炒至变色", "加入土豆片炒熟调味"]),
        ("土豆炖肉", ["土豆", "猪肉"], ["生抽", "姜"], 38, ["猪肉切块焯水", "加入调味料和清水炖煮", "放入土豆继续炖至软烂"]),
        ("肉末蒸蛋", ["猪肉", "鸡蛋"], ["葱"], 25, ["猪肉切末并调味", "鸡蛋加温水打匀", "铺上肉末蒸熟"]),
        ("西红柿肉片汤", ["西红柿", "猪肉"], ["姜"], 22, ["猪肉切片，西红柿切块", "西红柿炒出汁后加水", "放入肉片煮熟并调味"]),
        ("青椒煎蛋", ["青椒", "鸡蛋"], [], 12, ["青椒切碎，鸡蛋打散", "混合后加入少量盐", "倒入锅中煎至两面熟透"]),
        ("西红柿炖土豆", ["西红柿", "土豆"], ["蒜"], 25, ["西红柿和土豆切块", "先炒西红柿至出汁", "加入土豆和清水炖软调味"]),
        ("家常焖土豆", ["土豆"], ["生抽", "葱"], 28, ["土豆切块煎至微黄", "加入生抽和少量清水", "加盖焖软后收汁"]),
        ("蚝油生菜", ["生菜"], ["蚝油", "蒜"], 10, ["生菜洗净沥干，蒜切末", "大火爆香蒜末后放入生菜翻炒1分钟", "加入蚝油炒匀，菜叶刚软立即出锅"]),
        ("蒜蓉西兰花", ["西兰花"], ["蒜"], 12, ["西兰花切小朵，用淡盐水浸泡后洗净", "沸水焯1分钟后捞出沥干", "中火炒香蒜末，放入西兰花翻炒2分钟并调味"]),
        ("凉拌黄瓜", ["黄瓜"], ["蒜", "醋"], 8, ["黄瓜洗净拍裂后切段", "加入蒜末、醋、少量盐和糖", "拌匀后静置5分钟再食用"]),
        ("黄瓜炒鸡蛋", ["黄瓜", "鸡蛋"], ["葱"], 15, ["黄瓜切片，鸡蛋打散", "中火将鸡蛋炒至凝固后盛出", "大火炒黄瓜2分钟，倒回鸡蛋调味炒匀"]),
        ("木须肉", ["猪肉", "鸡蛋", "黄瓜"], ["木耳"], 25, ["木耳泡发洗净，黄瓜切片，猪肉切片", "鸡蛋炒熟盛出，猪肉中火炒至完全变色", "加入木耳和黄瓜炒3分钟，倒回鸡蛋调味"]),
        ("洋葱炒肉", ["洋葱", "猪肉"], ["生抽"], 18, ["洋葱切丝，猪肉切片并用少量淀粉抓匀", "中火炒肉片至完全变色后盛出", "大火炒洋葱2分钟，倒回肉片和生抽炒匀"]),
        ("芹菜炒肉", ["芹菜", "猪肉"], ["生抽"], 20, ["芹菜切段，猪肉切丝", "中火将肉丝炒至完全变色", "放入芹菜大火翻炒3分钟，加生抽和盐调味"]),
        ("青椒炒鸡蛋", ["青椒", "鸡蛋"], [], 12, ["青椒切块，鸡蛋打散", "中火炒熟鸡蛋后盛出", "大火炒青椒2分钟，倒回鸡蛋并加盐炒匀"]),
        ("土豆烧鸡块", ["土豆", "鸡腿"], ["姜", "生抽"], 40, ["鸡腿剁块焯水，土豆切块", "中火炒香姜片和鸡块，加入生抽翻匀", "加水焖20分钟，放入土豆再焖12分钟至鸡肉熟透"]),
        ("香菇炒鸡肉", ["香菇", "鸡胸肉"], ["生抽", "蒜"], 22, ["香菇切片，鸡胸肉切片腌制10分钟", "中火将鸡肉炒至完全变色后盛出", "炒香蒜和香菇，倒回鸡肉炒3分钟至熟透"]),
        ("蒜苔炒肉", ["蒜苔", "猪肉"], ["生抽"], 20, ["蒜苔切段，猪肉切丝", "中火炒肉丝至完全变色", "放入蒜苔大火炒3分钟，加生抽和盐调味"]),
        ("肉末豆腐", ["豆腐", "猪肉"], ["生抽", "葱"], 20, ["豆腐切块，猪肉切末", "中火将肉末炒散至完全变色", "加入豆腐、生抽和少量水，小火烧8分钟后撒葱"]),
        ("家常豆腐", ["豆腐", "青椒"], ["木耳", "豆瓣酱"], 25, ["豆腐切片煎至两面金黄", "中火炒香豆瓣酱，加入青椒和泡发木耳", "放回豆腐和少量水，小火烧5分钟收汁"]),
        ("番茄豆腐汤", ["西红柿", "豆腐"], ["葱"], 18, ["西红柿切块，豆腐切小块", "中火炒西红柿3分钟至出汁，加水煮开", "放入豆腐小火煮5分钟，调味后撒葱"]),
        ("紫菜蛋花汤", ["鸡蛋", "紫菜"], ["香油"], 10, ["紫菜冲洗，鸡蛋打散", "清水煮开后放入紫菜煮2分钟", "转小火淋入蛋液，凝固后调味并滴香油"]),
        ("冬瓜虾皮汤", ["冬瓜"], ["虾皮", "葱"], 18, ["冬瓜去皮切薄片，虾皮冲洗", "水开后放入冬瓜和虾皮，中火煮8分钟", "冬瓜透明后加盐调味并撒葱"]),
        ("清炒西葫芦", ["西葫芦"], ["蒜"], 12, ["西葫芦洗净切片，蒜切末", "大火炒香蒜末后放入西葫芦", "翻炒3分钟至断生，加盐炒匀立即出锅"]),
        ("西葫芦炒鸡蛋", ["西葫芦", "鸡蛋"], [], 15, ["西葫芦切片，鸡蛋打散", "中火炒熟鸡蛋后盛出", "大火炒西葫芦3分钟，倒回鸡蛋调味"]),
        ("手撕包菜", ["包菜"], ["干辣椒", "醋"], 12, ["包菜用手撕片，洗净后充分沥干", "大火爆香干辣椒，放入包菜快速翻炒2分钟", "沿锅边淋醋，加盐炒匀，保持爽脆即可"]),
        ("蒜蓉油麦菜", ["油麦菜"], ["蒜"], 10, ["油麦菜洗净切段，蒜切末", "大火炒香蒜末，先放菜梗再放菜叶", "翻炒约2分钟至刚软，加盐后立即出锅"]),
        ("菜花炒肉", ["菜花", "猪肉"], ["生抽", "蒜"], 22, ["菜花切小朵焯水1分钟，猪肉切片", "中火炒肉片至完全变色，加入蒜末", "放入菜花大火炒3分钟，加生抽调味"]),
        ("胡萝卜炒鸡蛋", ["胡萝卜", "鸡蛋"], ["葱"], 15, ["胡萝卜切细丝，鸡蛋打散", "中火炒熟鸡蛋后盛出", "炒软胡萝卜丝，倒回鸡蛋和葱花调味"]),
        ("香菇青菜", ["香菇", "青菜"], ["蒜"], 15, ["香菇切片，青菜洗净沥干", "中火炒香蒜末和香菇3分钟", "转大火放入青菜炒至断生，加盐调味"]),
        ("清蒸鸡腿", ["鸡腿"], ["姜", "葱"], 30, ["鸡腿划刀，加姜葱和少量盐腌10分钟", "水开后上锅中火蒸20分钟", "用筷子扎最厚处无血水后关火焖3分钟"]),
        ("空气炸锅土豆块", ["土豆"], ["孜然"], 25, ["土豆切块泡水后彻底擦干", "拌少量油、盐和孜然，放入炸篮", "180℃烤20分钟，中途翻面一次"]),
        ("空气炸锅鸡胸肉", ["鸡胸肉"], ["生抽", "黑胡椒"], 25, ["鸡胸肉切成均匀厚片并腌制10分钟", "放入空气炸锅，180℃烤12分钟", "翻面再烤5分钟，切开确认内部完全变白"]),
        ("水煮肉片", ["猪肉", "青菜"], ["豆瓣酱", "花椒"], 35, ["猪肉切薄片加淀粉抓匀，青菜焯熟铺碗底", "中火炒香豆瓣酱，加水煮开后逐片下肉", "肉片完全变色后连汤倒入碗中，撒花椒即可"]),
        ("酸辣土豆丝", ["土豆", "青椒"], ["醋", "干辣椒"], 15, ["土豆切细丝并冲洗掉表面淀粉", "大火爆香干辣椒，放入土豆丝炒2分钟", "加入青椒丝和醋，再炒1分钟保持爽脆"]),
        ("蒜泥白肉", ["猪肉", "黄瓜"], ["蒜", "辣椒油"], 30, ["整块猪肉冷水下锅，中小火煮至中心完全熟透", "肉放凉后切薄片，黄瓜切片垫底", "蒜末、辣椒油、生抽和醋调成汁后淋上"]),
        ("清蒸鱼", ["鱼"], ["姜", "葱", "蒸鱼豉油"], 20, ["鱼处理干净，两面划刀并铺姜丝", "水开后上锅，大火蒸8至12分钟", "鱼肉能轻松剥离鱼骨后关火，放葱丝并淋豉油"]),
        ("白灼虾", ["虾"], ["姜", "料酒"], 12, ["虾洗净去虾线", "水中放姜和料酒烧开，下虾煮2至3分钟", "虾身完全变红弯曲后立即捞出"]),
        ("冬菇蒸鸡", ["鸡腿", "香菇"], ["姜", "生抽"], 35, ["鸡腿剁块，香菇切片，加姜和生抽腌10分钟", "食材平铺盘中，水开后上锅", "中火蒸20分钟，确认鸡肉内部无血色"]),
        ("蒸水蛋", ["鸡蛋"], ["葱", "香油"], 15, ["鸡蛋打散，加入约1.5倍温水和少量盐", "过滤蛋液并盖住碗口", "水开后小火蒸10分钟，凝固后撒葱并滴香油"]),
        ("豆腐蒸肉末", ["豆腐", "猪肉"], ["葱"], 25, ["豆腐切片铺盘，猪肉剁末并调味", "肉末均匀铺在豆腐上", "水开后中火蒸15分钟，确认肉末完全熟透后撒葱"]),
        ("丝瓜炒蛋", ["丝瓜", "鸡蛋"], [], 15, ["丝瓜去皮切滚刀块，鸡蛋打散", "中火炒熟鸡蛋后盛出", "大火炒丝瓜3分钟，倒回鸡蛋调味"]),
        ("丝瓜蛋汤", ["丝瓜", "鸡蛋"], ["葱"], 15, ["丝瓜去皮切片，鸡蛋打散", "丝瓜加水煮5分钟至变软", "转小火淋入蛋液，凝固后调味并撒葱"]),
        ("菠菜鸡蛋汤", ["菠菜", "鸡蛋"], ["香油"], 12, ["菠菜洗净后沸水焯30秒，鸡蛋打散", "另起清水煮开放入菠菜", "转小火淋入蛋液，凝固后调味并滴香油"]),
        ("玉米排骨汤", ["玉米", "排骨"], ["姜"], 60, ["排骨冷水焯透并洗净，玉米切段", "排骨、姜和清水煮开后转小火炖35分钟", "加入玉米再炖15分钟，排骨软烂后加盐"]),
        ("萝卜排骨汤", ["白萝卜", "排骨"], ["姜"], 55, ["排骨冷水焯透并洗净，萝卜切块", "排骨和姜加水煮开，转小火炖30分钟", "加入萝卜再炖15分钟至软烂，加盐调味"]),
        ("菌菇豆腐汤", ["蘑菇", "豆腐"], ["葱"], 20, ["蘑菇洗净切片，豆腐切块", "中火炒蘑菇2分钟后加水煮开", "放入豆腐小火煮6分钟，调味并撒葱"]),
        ("煎鸡胸肉", ["鸡胸肉"], ["黑胡椒"], 18, ["鸡胸肉切成均匀厚片，加盐和黑胡椒腌10分钟", "平底锅少油，中小火每面煎4至5分钟", "切开最厚处确认内部完全变白后出锅"]),
        ("虾仁炒西兰花", ["虾仁", "西兰花"], ["蒜"], 15, ["西兰花切小朵焯水1分钟，虾仁去虾线", "中火炒虾仁至完全变色后盛出", "炒香蒜末和西兰花，倒回虾仁炒2分钟调味"]),
    ]
    direct_candidates: list[dict[str, Any]] = []
    partial_candidates: list[dict[str, Any]] = []
    for dish, required, missing, minutes, steps in templates:
        if dish in preferences.excluded_dishes:
            continue
        styles, is_spicy, equipment = RECIPE_META.get(
            dish, ({"家常菜"}, False, "炒锅")
        )
        if preferences.style != "不限" and preferences.style not in styles:
            continue
        if preferences.max_time and minutes > preferences.max_time:
            continue
        if preferences.spicy == "不辣" and is_spicy:
            continue
        if preferences.spicy == "辣" and not is_spicy:
            continue
        if preferences.equipment != "不限" and equipment != preferences.equipment:
            continue
        used = [name for name in required if name in by_name]
        missing_required = [name for name in required if name not in by_name]
        absent = missing_required + [
            name for name in missing if name not in preferences.pantry_items
        ]
        if used and len(absent) <= 3:
            consumptions = []
            used_names = []
            for name in used:
                item = by_name[name]
                used_names.append(item["name"])
                consumptions.append({"ingredient_name": item["name"], "quantity": 1, "unit": "餐"})
            candidate = {
                "dish_name": dish,
                "description": f"约{minutes}分钟完成，主要用到{'、'.join(required)}的{'微辣下饭菜' if is_spicy else '日常家常菜'}",
                "used_ingredients": used_names,
                "missing_ingredients": absent[:3],
                "consumptions": consumptions,
                "cooking_time": minutes,
                "difficulty": "简单",
                "steps": steps,
                "reason": f"优先使用库存中的{'、'.join(used_names)}",
            }
            (partial_candidates if missing_required else direct_candidates).append(candidate)

    avoided = set(avoid_dishes)

    def rotate_and_prioritize(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not candidates:
            return []
        offset = (rotation_seed * 4) % len(candidates)
        rotated = candidates[offset:] + candidates[:offset]
        return (
            [recipe for recipe in rotated if recipe["dish_name"] not in avoided]
            + [recipe for recipe in rotated if recipe["dish_name"] in avoided]
        )

    recipes = rotate_and_prioritize(direct_candidates)
    if len(recipes) < 3:
        recipes.extend(rotate_and_prioritize(partial_candidates)[: 4 - len(recipes)])
    if not recipes:
        raise AppError(
            400,
            "NO_REASONABLE_RECIPE",
            "当前库存暂时组合不出可靠的家常菜，请补充一种常见主料后重试",
        )
    # ponytail: fewer honest choices are better than fabricated recipes.
    return AIRecipeList.model_validate({"recipes": recipes[:4]})


def generate_recipes(
    items: list[dict[str, Any]],
    avoid_dishes: list[str] | None = None,
    rotation_seed: int = 0,
    preferences: RecommendationRequest | None = None,
) -> tuple[AIRecipeList, str]:
    avoid_dishes = avoid_dishes or []
    preferences = preferences or RecommendationRequest()
    approved = _mock_recommendations(items, avoid_dishes, rotation_seed, preferences)
    if settings.ai_provider == "mock":
        return approved, "mock"
    if not settings.ai_api_key:
        raise AppError(503, "AI_NOT_CONFIGURED", "尚未配置 AI API Key")

    client = OpenAI(
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
        timeout=settings.ai_timeout_seconds,
    )
    user_content = json.dumps(
        {
            "ingredients": items,
            "recently_recommended_dishes": avoid_dishes,
            "preferences": preferences.model_dump(mode="json"),
            "approved_recipe_candidates": approved.model_dump(mode="json")["recipes"],
        },
        ensure_ascii=False,
        default=str,
    )
    last_error = ""
    for attempt in range(2):
        prompt = user_content if attempt == 0 else f"请修正上次输出。校验错误：{last_error}\n库存：{user_content}"
        try:
            response = client.chat.completions.create(
                model=settings.ai_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
            )
            content = response.choices[0].message.content or ""
            selected = AIRecipeList.model_validate_json(content)
            approved_by_name = {recipe.dish_name: recipe for recipe in approved.recipes}
            selected_names = [recipe.dish_name for recipe in selected.recipes]
            if len(selected_names) != len(set(selected_names)):
                raise ValueError("菜名不能重复")
            if any(name not in approved_by_name for name in selected_names):
                raise ValueError("只能选择 approved_recipe_candidates 中的菜品")
            canonical = [approved_by_name[name] for name in selected_names]
            return AIRecipeList(recipes=canonical), settings.ai_model
        except (ValidationError, ValueError) as exc:
            last_error = str(exc)[:1000]
        except Exception as exc:
            raise AppError(502, "AI_REQUEST_FAILED", "AI 服务暂时不可用，请稍后重试") from exc
    raise AppError(502, "AI_RESPONSE_INVALID", "AI 返回内容格式不正确，请重新生成")
