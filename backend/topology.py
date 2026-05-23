"""
行政區拓撲圖 - 開發前凍結
Used for administrative district expansion in search pipeline.
"""

TOPOLOGY_GRAPH = {
    # ─── 柔佛巴魯 ────────────────────────────────────────────
    "johor_bahru_city": {
        "display_name": "新山市區",
        "level_1_adjacent": ["skudai", "tebrau", "larkin", "stulang"],
        "level_2_secondary": ["kulai", "pasir_gudang", "senai", "gelang_patah"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "skudai": {
        "display_name": "士古來",
        "level_1_adjacent": ["johor_bahru_city", "gelang_patah", "senai"],
        "level_2_secondary": ["kulai", "tebrau", "larkin"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "tebrau": {
        "display_name": "地不佬",
        "level_1_adjacent": ["johor_bahru_city", "pasir_gudang", "stulang"],
        "level_2_secondary": ["kota_tinggi", "larkin", "senai"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "iskandar_puteri": {
        "display_name": "依斯干達公主城（舊稱：努沙再也）",
        "level_1_adjacent": ["gelang_patah", "skudai", "johor_bahru_city"],
        "level_2_secondary": ["kulai", "senai"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "gelang_patah": {
        "display_name": "格令勿刹",
        "level_1_adjacent": ["iskandar_puteri", "skudai", "kulai"],
        "level_2_secondary": ["johor_bahru_city", "senai"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "pasir_gudang": {
        "display_name": "巴西古當",
        "level_1_adjacent": ["tebrau", "kota_tinggi"],
        "level_2_secondary": ["johor_bahru_city", "stulang"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "senai": {
        "display_name": "士乃",
        "level_1_adjacent": ["skudai", "kulai", "gelang_patah"],
        "level_2_secondary": ["johor_bahru_city", "iskandar_puteri"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "kulai": {
        "display_name": "古來",
        "level_1_adjacent": ["senai", "gelang_patah", "skudai"],
        "level_2_secondary": ["iskandar_puteri", "johor_bahru_city"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "larkin": {
        "display_name": "拉曼",
        "level_1_adjacent": ["johor_bahru_city", "tebrau"],
        "level_2_secondary": ["skudai", "stulang"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "stulang": {
        "display_name": "士馬當",
        "level_1_adjacent": ["johor_bahru_city", "larkin", "tebrau"],
        "level_2_secondary": ["pasir_gudang"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "kota_tinggi": {
        "display_name": "高州",
        "level_1_adjacent": ["pasir_gudang", "tebrau"],
        "level_2_secondary": ["johor_bahru_city"],
        "level_3_pan_urban": "johor_bahru_district"
    },

    # ─── 吉隆坡 ──────────────────────────────────────────────
    "kuala_lumpur_city": {
        "display_name": "吉隆坡市中心（KLCC / Bukit Bintang）",
        "level_1_adjacent": ["mont_kiara", "chow_kit", "ampang", "pudu"],
        "level_2_secondary": ["petaling_jaya", "kepong", "puchong", "wangsa_maju"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },
    "mont_kiara": {
        "display_name": "孟沙（Mont Kiara）",
        "level_1_adjacent": ["kuala_lumpur_city", "kepong", "sri_hartamas"],
        "level_2_secondary": ["petaling_jaya", "damansara"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },
    "ampang": {
        "display_name": "安邦",
        "level_1_adjacent": ["kuala_lumpur_city", "wangsa_maju", "cheras"],
        "level_2_secondary": ["pandan_indah", "pudu"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },
    "cheras": {
        "display_name": "蕉賴",
        "level_1_adjacent": ["ampang", "pudu", "sg_besi"],
        "level_2_secondary": ["puchong", "kajang"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },
    "pudu": {
        "display_name": "蒲種",
        "level_1_adjacent": ["kuala_lumpur_city", "cheras", "ampang"],
        "level_2_secondary": ["wangsa_maju", "sg_besi"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },
    "wangsa_maju": {
        "display_name": "旺沙瑪朱",
        "level_1_adjacent": ["ampang", "pudu"],
        "level_2_secondary": ["cheras", "kuala_lumpur_city"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },
    "chow_kit": {
        "display_name": "周奇",
        "level_1_adjacent": ["kuala_lumpur_city", "kepong"],
        "level_2_secondary": ["mont_kiara"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },
    "kepong": {
        "display_name": "甲洞",
        "level_1_adjacent": ["chow_kit", "mont_kiara"],
        "level_2_secondary": ["kuala_lumpur_city", "sri_hartamas"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },
    "sg_besi": {
        "display_name": "双溪毛糯",
        "level_1_adjacent": ["cheras", "pudu"],
        "level_2_secondary": ["wangsa_maju"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },
    "pandan_indah": {
        "display_name": "班丹英达",
        "level_1_adjacent": ["ampang"],
        "level_2_secondary": ["kuala_lumpur_city"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },
    "sri_hartamas": {
        "display_name": "三田林",
        "level_1_adjacent": ["mont_kiara", "kepong"],
        "level_2_secondary": ["kuala_lumpur_city"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },

    # ─── 八打靈再也 ──────────────────────────────────────────
    "petaling_jaya": {
        "display_name": "八打靈再也（PJ）",
        "level_1_adjacent": ["subang_jaya", "damansara", "kuala_lumpur_city"],
        "level_2_secondary": ["puchong", "shah_alam", "mont_kiara"],
        "level_3_pan_urban": "petaling_district"
    },
    "subang_jaya": {
        "display_name": "莎阿南花園（Subang Jaya）",
        "level_1_adjacent": ["petaling_jaya", "puchong", "shah_alam"],
        "level_2_secondary": ["damansara", "kuala_lumpur_city"],
        "level_3_pan_urban": "petaling_district"
    },
    "damansara": {
        "display_name": "白沙羅（Damansara）",
        "level_1_adjacent": ["petaling_jaya", "mont_kiara", "subang_jaya"],
        "level_2_secondary": ["kuala_lumpur_city", "kepong"],
        "level_3_pan_urban": "petaling_district"
    },
    "puchong": {
        "display_name": "蒲種",
        "level_1_adjacent": ["petaling_jaya", "subang_jaya"],
        "level_2_secondary": ["shah_alam", "cheras"],
        "level_3_pan_urban": "petaling_district"
    },
    "shah_alam": {
        "display_name": "沙阿南",
        "level_1_adjacent": ["subang_jaya", "puchong"],
        "level_2_secondary": ["petaling_jaya"],
        "level_3_pan_urban": "petaling_district"
    },
    "kajang": {
        "display_name": "加影",
        "level_1_adjacent": ["cheras"],
        "level_2_secondary": ["puchong"],
        "level_3_pan_urban": "petaling_district"
    },

    # ─── 泛市區節點（Level 3 終點）─────────────────────────────
    "johor_bahru_district": {
        "display_name": "新山縣（全域）",
        "is_pan_urban": True
    },
    "kuala_lumpur_federal_territory": {
        "display_name": "吉隆坡聯邦直轄區（全域）",
        "is_pan_urban": True
    },
    "petaling_district": {
        "display_name": "八打靈縣（全域）",
        "is_pan_urban": True
    },
}


def get_search_districts(target_district: str, expansion_level: int) -> list[str]:
    """
    根據目標區和擴張級別，返���應當納入搜索的行政區列表。

    Level 0: 目標區
    Level 1: 目標區 + 相鄰區
    Level 2: Level 1 + 次級輻射區
    Level 3: 整個泛市區（縣/市）
    """
    if target_district not in TOPOLOGY_GRAPH:
        raise ValueError(f"未知行政區：{target_district}")

    node = TOPOLOGY_GRAPH[target_district]

    if expansion_level == 0:
        return [target_district]
    elif expansion_level == 1:
        return [target_district] + node.get("level_1_adjacent", [])
    elif expansion_level == 2:
        return (
            [target_district]
            + node.get("level_1_adjacent", [])
            + node.get("level_2_secondary", [])
        )
    elif expansion_level == 3:
        pan_urban = node.get("level_3_pan_urban")
        return [pan_urban] if pan_urban else []
    else:
        return []

