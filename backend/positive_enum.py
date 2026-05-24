"""
PPP Enumeration - Positive Property Preferences.
Separate from NPP_ENUM_FULL because NPP is semantically a *negative* dictionary
used in tier_classification() conflict math. Mixing positives would corrupt
ranking. Keep them in different namespaces.
"""

PPP_ENUM_FULL: dict[str, str] = {
    # 安全 / 管理
    "needs_security":       "需要保安",
    "needs_gated":          "需門禁社區",

    # 交通
    "needs_near_mrt":       "靠近 MRT",
    "needs_near_lrt":       "靠近 LRT",
    "needs_near_highway":   "靠近高速入口",

    # 樓層 / 朝向
    "needs_high_floor":     "需高樓層",
    "needs_south_facing":   "需南向",
    "needs_natural_light":  "需自然採光",
    "needs_balcony":        "需陽台",

    # 設施
    "needs_pool":           "需游泳池",
    "needs_gym":            "需健身房",
    "needs_parking":        "需停車位",
    "needs_covered_parking":"需室內停車",
    "needs_lift":           "需電梯",

    # 周邊
    "needs_near_school":    "近學校",
    "needs_near_mall":      "近商場",
    "needs_near_hospital":  "近醫院",

    # 其他
    "pet_friendly":         "可養寵物",
    "furnished":            "附家具",
    "new_building":         "新樓盤",
}
