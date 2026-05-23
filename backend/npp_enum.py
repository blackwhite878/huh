"""
NPP Enumeration - Negative Property Preferences (常量凍結)
Format: internal_key -> display_label
All comparisons use internal_key (snake_case)
Display labels are for frontend and LLM prompts only.
"""

NPP_ENUM_FULL: dict[str, str] = {
    # 朝向類
    "west_facing": "西晒",
    "east_facing": "東晒",
    "no_natural_light": "無自然採光",
    "no_balcony": "無陽台",

    # 樓層類
    "high_floor": "高樓層",
    "low_floor": "低樓層",
    "top_floor": "頂樓",
    "ground_floor": "地層",

    # 交通類
    "far_from_mrt": "遠地鐵",
    "far_from_bus": "遠巴士站",
    "far_from_highway": "遠高速入口",

    # 設施類
    "no_pool": "無游泳池",
    "no_gym": "無健身房",
    "no_security": "無保安",
    "no_parking": "無停車位",
    "no_visitor_parking": "無訪客停車位",
    "frequent_lift_issues": "電梯經常故障",

    # 周邊類
    "far_from_school": "遠學校",
    "far_from_hospital": "遠醫院",
    "far_from_mall": "遠商場",
    "near_industrial": "近工業區",
    "noise_area": "噪音區",
    "near_cemetery": "近墓地",
    "near_power_lines": "近高壓電線",
    "near_mosque": "近清真寺",

    # 房型類
    "open_kitchen": "開放式廚房",
    "no_storage": "無儲藏室",
    "small_unit": "小戶型",

    # 樓盤狀態類
    "high_tenant_mix": "租戶混雜",
    "high_vacancy": "空置率高",

    # 樓齡類
    "old_building": "樓齡過高",
    "incomplete_project": "未完工項目",

    # 管理類
    "high_maintenance_fee": "高管理費",
    "low_maintenance": "低維護水平",
}

# Internal key set for validation
NPP_ENUM = set(NPP_ENUM_FULL.keys())


def validate_npp_tags(tags: list[str]) -> bool:
    """Check if all tags are in the frozen NPP_ENUM."""
    return all(tag in NPP_ENUM for tag in tags)

