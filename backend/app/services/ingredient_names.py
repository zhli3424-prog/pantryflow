ALIASES = {
    "番茄": "西红柿",
    "圣女果": "小番茄",
    "马铃薯": "土豆",
    "青辣椒": "青椒",
    "鸡中翅": "鸡翅",
    "鸡翅中": "鸡翅",
    "猪里脊": "猪肉",
    "里脊肉": "猪肉",
    "花椰菜": "菜花",
    "西葫芦瓜": "西葫芦",
}


def canonical_name(name: str) -> str:
    cleaned = name.strip()
    return ALIASES.get(cleaned, cleaned)
