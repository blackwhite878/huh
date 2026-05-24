"""
行政區拓撲圖 - 開發前凍結
Used for administrative district expansion in search pipeline.
"""

TOPOLOGY_GRAPH = {

    # ════════════════════════════════════════════════════════════
    # 柔佛 (JOHOR)
    # ════════════════════════════════════════════════════════════

    # ─── 新山都會區 ──────────────────────────────────────────
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
        "display_name": "古來（高州）",
        "level_1_adjacent": ["pasir_gudang", "tebrau"],
        "level_2_secondary": ["johor_bahru_city"],
        "level_3_pan_urban": "johor_bahru_district"
    },

    # ─── 麻坡都會區 ──────────────────────────────────────────
    "muar": {
        "display_name": "麻坡",
        "level_1_adjacent": ["bukit_bakri", "sungai_mati", "pagoh"],
        "level_2_secondary": ["batu_pahat_town", "yong_peng", "segamat_town"],
        "level_3_pan_urban": "muar_district"
    },
    "bukit_bakri": {
        "display_name": "武吉峇吉里",
        "level_1_adjacent": ["muar", "sungai_mati"],
        "level_2_secondary": ["pagoh", "yong_peng"],
        "level_3_pan_urban": "muar_district"
    },
    "sungai_mati": {
        "display_name": "雙溪馬迪",
        "level_1_adjacent": ["muar", "bukit_bakri"],
        "level_2_secondary": ["pagoh"],
        "level_3_pan_urban": "muar_district"
    },
    "pagoh": {
        "display_name": "巴峇",
        "level_1_adjacent": ["muar", "segamat_town"],
        "level_2_secondary": ["bukit_bakri", "yong_peng"],
        "level_3_pan_urban": "muar_district"
    },

    # ─── 峇株巴轄都會區 ──────────────────────────────────────
    "batu_pahat_town": {
        "display_name": "峇株巴轄",
        "level_1_adjacent": ["yong_peng", "ayer_hitam", "rengit"],
        "level_2_secondary": ["muar", "kluang_town", "pontian_town"],
        "level_3_pan_urban": "batu_pahat_district"
    },
    "yong_peng": {
        "display_name": "永平",
        "level_1_adjacent": ["batu_pahat_town", "ayer_hitam"],
        "level_2_secondary": ["muar", "kluang_town"],
        "level_3_pan_urban": "batu_pahat_district"
    },
    "ayer_hitam": {
        "display_name": "黑水",
        "level_1_adjacent": ["batu_pahat_town", "yong_peng"],
        "level_2_secondary": ["kluang_town", "rengit"],
        "level_3_pan_urban": "batu_pahat_district"
    },
    "rengit": {
        "display_name": "令金",
        "level_1_adjacent": ["batu_pahat_town"],
        "level_2_secondary": ["ayer_hitam", "pontian_town"],
        "level_3_pan_urban": "batu_pahat_district"
    },

    # ─── 居鑾都會區 ──────────────────────────────────────────
    "kluang_town": {
        "display_name": "居鑾",
        "level_1_adjacent": ["simpang_renggam", "mengkibol", "ayer_hitam"],
        "level_2_secondary": ["batu_pahat_town", "segamat_town", "mersing_town"],
        "level_3_pan_urban": "kluang_district"
    },
    "simpang_renggam": {
        "display_name": "新邦令金",
        "level_1_adjacent": ["kluang_town", "mengkibol"],
        "level_2_secondary": ["ayer_hitam"],
        "level_3_pan_urban": "kluang_district"
    },
    "mengkibol": {
        "display_name": "門吉波",
        "level_1_adjacent": ["kluang_town", "simpang_renggam"],
        "level_2_secondary": ["segamat_town"],
        "level_3_pan_urban": "kluang_district"
    },

    # ─── 笨珍縣 ──────────────────────────────────────────────
    "pontian_town": {
        "display_name": "笨珍",
        "level_1_adjacent": ["kukup", "pekan_nanas"],
        "level_2_secondary": ["gelang_patah", "johor_bahru_city", "rengit"],
        "level_3_pan_urban": "pontian_district"
    },
    "kukup": {
        "display_name": "龜咯",
        "level_1_adjacent": ["pontian_town"],
        "level_2_secondary": ["pekan_nanas"],
        "level_3_pan_urban": "pontian_district"
    },
    "pekan_nanas": {
        "display_name": "菠蘿市",
        "level_1_adjacent": ["pontian_town"],
        "level_2_secondary": ["kukup", "gelang_patah"],
        "level_3_pan_urban": "pontian_district"
    },

    # ─── 昔加末縣 ────────────────────────────────────────────
    "segamat_town": {
        "display_name": "昔加末",
        "level_1_adjacent": ["gemas", "labis", "pagoh"],
        "level_2_secondary": ["kluang_town", "muar", "seremban_city"],
        "level_3_pan_urban": "segamat_district"
    },
    "gemas": {
        "display_name": "格馬士",
        "level_1_adjacent": ["segamat_town", "labis"],
        "level_2_secondary": ["seremban_city"],
        "level_3_pan_urban": "segamat_district"
    },
    "labis": {
        "display_name": "拉美士",
        "level_1_adjacent": ["segamat_town", "gemas"],
        "level_2_secondary": ["kluang_town"],
        "level_3_pan_urban": "segamat_district"
    },

    # ─── 民石縣 ──────────────────────────────────────────────
    "mersing_town": {
        "display_name": "民石",
        "level_1_adjacent": ["jemaluang"],
        "level_2_secondary": ["kota_tinggi", "kluang_town"],
        "level_3_pan_urban": "mersing_district"
    },
    "jemaluang": {
        "display_name": "者蒙浪",
        "level_1_adjacent": ["mersing_town"],
        "level_2_secondary": ["kota_tinggi"],
        "level_3_pan_urban": "mersing_district"
    },

    # ─── 柔佛泛城區節點 ──────────────────────────────────────
    "johor_bahru_district": {"display_name": "新山縣（全域）", "is_pan_urban": True},
    "muar_district":        {"display_name": "麻坡縣（全域）", "is_pan_urban": True},
    "batu_pahat_district":  {"display_name": "峇株巴轄縣（全域）", "is_pan_urban": True},
    "kluang_district":      {"display_name": "居鑾縣（全域）", "is_pan_urban": True},
    "pontian_district":     {"display_name": "笨珍縣（全域）", "is_pan_urban": True},
    "segamat_district":     {"display_name": "昔加末縣（全域）", "is_pan_urban": True},
    "mersing_district":     {"display_name": "民石縣（全域）", "is_pan_urban": True},


    # ════════════════════════════════════════════════════════════
    # 吉隆坡聯邦直轄區 (KUALA LUMPUR FT)
    # ════════════════════════════════════════════════════════════

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
        "display_name": "富都",
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
        "display_name": "雙溪毛糯",
        "level_1_adjacent": ["cheras", "pudu"],
        "level_2_secondary": ["wangsa_maju"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },
    "pandan_indah": {
        "display_name": "班丹英達",
        "level_1_adjacent": ["ampang"],
        "level_2_secondary": ["kuala_lumpur_city"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },
    "sri_hartamas": {
        "display_name": "斯里阿達瑪斯",
        "level_1_adjacent": ["mont_kiara", "kepong"],
        "level_2_secondary": ["kuala_lumpur_city"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },

    "kuala_lumpur_federal_territory": {
        "display_name": "吉隆坡聯邦直轄區（全域）",
        "is_pan_urban": True
    },


    # ════════════════════════════════════════════════════════════
    # 布城聯邦直轄區 (PUTRAJAYA FT)
    # ════════════════════════════════════════════════════════════

    "putrajaya": {
        "display_name": "布城（Putrajaya）",
        "level_1_adjacent": ["cyberjaya", "sepang_town"],
        "level_2_secondary": ["puchong", "salak_tinggi", "nilai"],
        "level_3_pan_urban": "putrajaya_federal_territory"
    },

    "putrajaya_federal_territory": {
        "display_name": "布城聯邦直轄區（全域）",
        "is_pan_urban": True
    },


    # ════════════════════════════════════════════════════════════
    # 納閩聯邦直轄區 (LABUAN FT)
    # ════════════════════════════════════════════════════════════

    "labuan_town": {
        "display_name": "納閩市區",
        "level_1_adjacent": ["labuan_airport_area"],
        "level_2_secondary": [],
        "level_3_pan_urban": "labuan_federal_territory"
    },
    "labuan_airport_area": {
        "display_name": "納閩機場周邊",
        "level_1_adjacent": ["labuan_town"],
        "level_2_secondary": [],
        "level_3_pan_urban": "labuan_federal_territory"
    },

    "labuan_federal_territory": {
        "display_name": "納閩聯邦直轄區（全域）",
        "is_pan_urban": True
    },


    # ════════════════════════════════════════════════════════════
    # 雪蘭莪 (SELANGOR)
    # ════════════════════════════════════════════════════════════

    # ─── 八打靈 / PJ 都會區 ──────────────────────────────────
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
        "level_2_secondary": ["shah_alam", "cheras", "cyberjaya"],
        "level_3_pan_urban": "petaling_district"
    },
    "shah_alam": {
        "display_name": "沙阿南",
        "level_1_adjacent": ["subang_jaya", "puchong", "klang_town"],
        "level_2_secondary": ["petaling_jaya", "port_klang"],
        "level_3_pan_urban": "petaling_district"
    },
    "kajang": {
        "display_name": "加影",
        "level_1_adjacent": ["cheras", "semenyih"],
        "level_2_secondary": ["puchong", "nilai"],
        "level_3_pan_urban": "hulu_langat_district"
    },
    "semenyih": {
        "display_name": "士毛月",
        "level_1_adjacent": ["kajang"],
        "level_2_secondary": ["cheras", "nilai"],
        "level_3_pan_urban": "hulu_langat_district"
    },

    # ─── 巴生都會區 ──────────────────────────────────────────
    "klang_town": {
        "display_name": "巴生",
        "level_1_adjacent": ["port_klang", "meru", "kapar"],
        "level_2_secondary": ["shah_alam", "subang_jaya", "banting"],
        "level_3_pan_urban": "klang_district"
    },
    "port_klang": {
        "display_name": "巴生港口",
        "level_1_adjacent": ["klang_town", "kapar"],
        "level_2_secondary": ["meru", "banting"],
        "level_3_pan_urban": "klang_district"
    },
    "meru": {
        "display_name": "美露",
        "level_1_adjacent": ["klang_town", "kapar"],
        "level_2_secondary": ["shah_alam", "port_klang"],
        "level_3_pan_urban": "klang_district"
    },
    "kapar": {
        "display_name": "加埔",
        "level_1_adjacent": ["klang_town", "port_klang", "meru"],
        "level_2_secondary": ["kuala_selangor"],
        "level_3_pan_urban": "klang_district"
    },

    # ─── 雪邦 / 賽城都會區 ───────────────────────────────────
    "cyberjaya": {
        "display_name": "賽城",
        "level_1_adjacent": ["putrajaya", "sepang_town"],
        "level_2_secondary": ["puchong", "nilai", "salak_tinggi"],
        "level_3_pan_urban": "sepang_district"
    },
    "sepang_town": {
        "display_name": "雪邦",
        "level_1_adjacent": ["cyberjaya", "salak_tinggi", "putrajaya"],
        "level_2_secondary": ["nilai", "banting"],
        "level_3_pan_urban": "sepang_district"
    },
    "salak_tinggi": {
        "display_name": "沙叻丁宜",
        "level_1_adjacent": ["sepang_town", "cyberjaya"],
        "level_2_secondary": ["putrajaya", "nilai"],
        "level_3_pan_urban": "sepang_district"
    },

    # ─── 其他雪蘭莪城鎮 ──────────────────────────────────────
    "rawang": {
        "display_name": "冷岳",
        "level_1_adjacent": ["serendah"],
        "level_2_secondary": ["kuala_lumpur_city", "kepong", "kuala_kubu_baharu"],
        "level_3_pan_urban": "gombak_district"
    },
    "serendah": {
        "display_name": "雪冷達",
        "level_1_adjacent": ["rawang"],
        "level_2_secondary": ["kuala_kubu_baharu"],
        "level_3_pan_urban": "hulu_selangor_district"
    },
    "kuala_kubu_baharu": {
        "display_name": "瓜拉古武新埠",
        "level_1_adjacent": ["serendah"],
        "level_2_secondary": ["rawang"],
        "level_3_pan_urban": "hulu_selangor_district"
    },
    "banting": {
        "display_name": "萬廷",
        "level_1_adjacent": ["morib"],
        "level_2_secondary": ["klang_town", "sepang_town"],
        "level_3_pan_urban": "kuala_langat_district"
    },
    "morib": {
        "display_name": "摩立",
        "level_1_adjacent": ["banting"],
        "level_2_secondary": ["port_klang"],
        "level_3_pan_urban": "kuala_langat_district"
    },
    "kuala_selangor": {
        "display_name": "瓜拉雪蘭莪",
        "level_1_adjacent": ["sabak_bernam"],
        "level_2_secondary": ["kapar", "rawang"],
        "level_3_pan_urban": "kuala_selangor_district"
    },
    "sabak_bernam": {
        "display_name": "沙白安南",
        "level_1_adjacent": ["kuala_selangor"],
        "level_2_secondary": [],
        "level_3_pan_urban": "sabak_bernam_district"
    },

    # ─── 雪蘭莪泛城區節點 ────────────────────────────────────
    "petaling_district":       {"display_name": "八打靈縣（全域）", "is_pan_urban": True},
    "klang_district":          {"display_name": "巴生縣（全域）", "is_pan_urban": True},
    "sepang_district":         {"display_name": "雪邦縣（全域）", "is_pan_urban": True},
    "hulu_langat_district":    {"display_name": "烏魯冷岳縣（全域）", "is_pan_urban": True},
    "gombak_district":         {"display_name": "鵝嘜縣（全域）", "is_pan_urban": True},
    "hulu_selangor_district":  {"display_name": "烏魯雪蘭莪縣（全域）", "is_pan_urban": True},
    "kuala_langat_district":   {"display_name": "瓜拉冷岳縣（全域）", "is_pan_urban": True},
    "kuala_selangor_district": {"display_name": "瓜拉雪蘭莪縣（全域）", "is_pan_urban": True},
    "sabak_bernam_district":   {"display_name": "沙白安南縣（全域）", "is_pan_urban": True},
    "selangor_state":          {"display_name": "雪蘭莪州（全域）", "is_pan_urban": True},


    # ════════════════════════════════════════════════════════════
    # 檳城 (PENANG)
    # ════════════════════════════════════════════════════════════

    # ─── 檳島（東北縣）──────────────────────────────────────
    "georgetown": {
        "display_name": "喬治市",
        "level_1_adjacent": ["tanjung_tokong", "jelutong", "bayan_lepas"],
        "level_2_secondary": ["batu_ferringhi", "tanjung_bungah", "sungai_ara", "bayan_baru"],
        "level_3_pan_urban": "penang_island_district"
    },
    "tanjung_tokong": {
        "display_name": "東棟",
        "level_1_adjacent": ["georgetown", "tanjung_bungah"],
        "level_2_secondary": ["batu_ferringhi"],
        "level_3_pan_urban": "penang_island_district"
    },
    "tanjung_bungah": {
        "display_name": "武吉槍城",
        "level_1_adjacent": ["tanjung_tokong", "batu_ferringhi"],
        "level_2_secondary": ["georgetown"],
        "level_3_pan_urban": "penang_island_district"
    },
    "batu_ferringhi": {
        "display_name": "峇都丁宜",
        "level_1_adjacent": ["tanjung_bungah"],
        "level_2_secondary": ["tanjung_tokong", "georgetown"],
        "level_3_pan_urban": "penang_island_district"
    },
    "jelutong": {
        "display_name": "日落洞",
        "level_1_adjacent": ["georgetown", "bayan_lepas"],
        "level_2_secondary": ["bayan_baru"],
        "level_3_pan_urban": "penang_island_district"
    },
    "bayan_lepas": {
        "display_name": "峇眼拉惹",
        "level_1_adjacent": ["georgetown", "jelutong", "bayan_baru"],
        "level_2_secondary": ["sungai_ara", "balik_pulau"],
        "level_3_pan_urban": "penang_island_district"
    },
    "bayan_baru": {
        "display_name": "峇眼峇魯",
        "level_1_adjacent": ["bayan_lepas", "jelutong"],
        "level_2_secondary": ["sungai_ara", "georgetown"],
        "level_3_pan_urban": "penang_island_district"
    },
    "sungai_ara": {
        "display_name": "雙溪阿拉",
        "level_1_adjacent": ["bayan_lepas", "bayan_baru"],
        "level_2_secondary": ["balik_pulau"],
        "level_3_pan_urban": "penang_island_district"
    },
    "balik_pulau": {
        "display_name": "峇六拜",
        "level_1_adjacent": ["sungai_ara"],
        "level_2_secondary": ["bayan_lepas"],
        "level_3_pan_urban": "penang_island_district"
    },

    # ─── 威省（北威 / 中威 / 南威）──────────────────────────
    "butterworth": {
        "display_name": "北海",
        "level_1_adjacent": ["bukit_mertajam", "kepala_batas"],
        "level_2_secondary": ["nibong_tebal", "batu_kawan"],
        "level_3_pan_urban": "seberang_perai_district"
    },
    "bukit_mertajam": {
        "display_name": "大山腳",
        "level_1_adjacent": ["butterworth", "nibong_tebal", "batu_kawan"],
        "level_2_secondary": ["kepala_batas"],
        "level_3_pan_urban": "seberang_perai_district"
    },
    "kepala_batas": {
        "display_name": "峇都交灣（北威）",
        "level_1_adjacent": ["butterworth"],
        "level_2_secondary": ["bukit_mertajam"],
        "level_3_pan_urban": "seberang_perai_district"
    },
    "nibong_tebal": {
        "display_name": "雙溪賴",
        "level_1_adjacent": ["bukit_mertajam", "batu_kawan"],
        "level_2_secondary": ["butterworth"],
        "level_3_pan_urban": "seberang_perai_district"
    },
    "batu_kawan": {
        "display_name": "峇都交灣（南威工業區）",
        "level_1_adjacent": ["nibong_tebal", "bukit_mertajam"],
        "level_2_secondary": ["butterworth"],
        "level_3_pan_urban": "seberang_perai_district"
    },

    # ─── 檳城泛城區節點 ──────────────────────────────────────
    "penang_island_district":  {"display_name": "檳島縣（全域）", "is_pan_urban": True},
    "seberang_perai_district": {"display_name": "威省縣（全域）", "is_pan_urban": True},
    "penang_state":            {"display_name": "檳城州（全域）", "is_pan_urban": True},


    # ════════════════════════════════════════════════════════════
    # 霹靂 (PERAK)
    # ════════════════════════════════════════════════════════════

    # ─── 怡保都會區（近打谷）────────────────────────────────
    "ipoh_city": {
        "display_name": "怡保",
        "level_1_adjacent": ["batu_gajah", "lahat", "chemor"],
        "level_2_secondary": ["taiping_town", "kampar", "teluk_intan"],
        "level_3_pan_urban": "kinta_district"
    },
    "batu_gajah": {
        "display_name": "武吉加禮",
        "level_1_adjacent": ["ipoh_city", "lahat"],
        "level_2_secondary": ["kampar", "chemor"],
        "level_3_pan_urban": "kinta_district"
    },
    "lahat": {
        "display_name": "拉惹哥打",
        "level_1_adjacent": ["ipoh_city", "batu_gajah"],
        "level_2_secondary": ["kampar"],
        "level_3_pan_urban": "kinta_district"
    },
    "chemor": {
        "display_name": "遮末",
        "level_1_adjacent": ["ipoh_city"],
        "level_2_secondary": ["batu_gajah"],
        "level_3_pan_urban": "kinta_district"
    },

    # ─── 金保 ────────────────────────────────────────────────
    "kampar": {
        "display_name": "金保",
        "level_1_adjacent": ["batu_gajah", "teluk_intan"],
        "level_2_secondary": ["ipoh_city"],
        "level_3_pan_urban": "kampar_district"
    },

    # ─── 太平都會區 ──────────────────────────────────────────
    "taiping_town": {
        "display_name": "太平",
        "level_1_adjacent": ["simpang_town", "batu_kurau"],
        "level_2_secondary": ["ipoh_city", "lumut"],
        "level_3_pan_urban": "larut_matang_district"
    },
    "simpang_town": {
        "display_name": "新邦波賴",
        "level_1_adjacent": ["taiping_town"],
        "level_2_secondary": ["batu_kurau"],
        "level_3_pan_urban": "larut_matang_district"
    },
    "batu_kurau": {
        "display_name": "武吉古魯",
        "level_1_adjacent": ["taiping_town", "simpang_town"],
        "level_2_secondary": [],
        "level_3_pan_urban": "larut_matang_district"
    },

    # ─── 曼絨 / 安順 ─────────────────────────────────────────
    "manjung_town": {
        "display_name": "曼絨（實兆遠）",
        "level_1_adjacent": ["lumut", "sitiawan"],
        "level_2_secondary": ["teluk_intan", "taiping_town"],
        "level_3_pan_urban": "manjung_district"
    },
    "lumut": {
        "display_name": "南馬",
        "level_1_adjacent": ["manjung_town", "sitiawan"],
        "level_2_secondary": ["teluk_intan"],
        "level_3_pan_urban": "manjung_district"
    },
    "sitiawan": {
        "display_name": "斯里曼絨",
        "level_1_adjacent": ["lumut", "manjung_town"],
        "level_2_secondary": ["teluk_intan"],
        "level_3_pan_urban": "manjung_district"
    },
    "teluk_intan": {
        "display_name": "安順",
        "level_1_adjacent": ["kampar"],
        "level_2_secondary": ["lumut", "ipoh_city"],
        "level_3_pan_urban": "hilir_perak_district"
    },

    # ─── 霹靂泛城區節點 ──────────────────────────────────────
    "kinta_district":       {"display_name": "近打縣（全域）", "is_pan_urban": True},
    "kampar_district":      {"display_name": "金保縣（全域）", "is_pan_urban": True},
    "larut_matang_district":{"display_name": "拉律瑪登縣（全域）", "is_pan_urban": True},
    "manjung_district":     {"display_name": "曼絨縣（全域）", "is_pan_urban": True},
    "hilir_perak_district": {"display_name": "下霹靂縣（全域）", "is_pan_urban": True},
    "perak_state":          {"display_name": "霹靂州（全域）", "is_pan_urban": True},


    # ════════════════════════════════════════════════════════════
    # 吉打 (KEDAH)
    # ════════════════════════════════════════════════════════════

    # ─── 亞羅士打都會區 ──────────────────────────────────────
    "alor_setar_city": {
        "display_name": "亞羅士打",
        "level_1_adjacent": ["kubang_pasu", "pendang", "kota_setar_south"],
        "level_2_secondary": ["jitra", "sungai_petani_city"],
        "level_3_pan_urban": "alor_setar_district"
    },
    "kota_setar_south": {
        "display_name": "哥打士達南區",
        "level_1_adjacent": ["alor_setar_city", "pendang"],
        "level_2_secondary": ["sungai_petani_city"],
        "level_3_pan_urban": "alor_setar_district"
    },
    "kubang_pasu": {
        "display_name": "古邦巴素（日得拉）",
        "level_1_adjacent": ["alor_setar_city", "jitra"],
        "level_2_secondary": ["changlun"],
        "level_3_pan_urban": "kubang_pasu_district"
    },
    "jitra": {
        "display_name": "日得拉",
        "level_1_adjacent": ["kubang_pasu", "changlun"],
        "level_2_secondary": ["alor_setar_city"],
        "level_3_pan_urban": "kubang_pasu_district"
    },
    "changlun": {
        "display_name": "曾隆",
        "level_1_adjacent": ["jitra"],
        "level_2_secondary": ["kubang_pasu"],
        "level_3_pan_urban": "kubang_pasu_district"
    },
    "pendang": {
        "display_name": "本當",
        "level_1_adjacent": ["alor_setar_city", "sungai_petani_city"],
        "level_2_secondary": ["kota_setar_south"],
        "level_3_pan_urban": "pendang_district"
    },

    # ─── 雙溪大年都會區 ──────────────────────────────────────
    "sungai_petani_city": {
        "display_name": "雙溪大年",
        "level_1_adjacent": ["kulim", "bedong", "gurun"],
        "level_2_secondary": ["alor_setar_city", "baling", "pendang"],
        "level_3_pan_urban": "kuala_muda_district"
    },
    "kulim": {
        "display_name": "居林",
        "level_1_adjacent": ["sungai_petani_city", "bedong"],
        "level_2_secondary": ["baling", "alor_setar_city"],
        "level_3_pan_urban": "kulim_district"
    },
    "bedong": {
        "display_name": "明德",
        "level_1_adjacent": ["sungai_petani_city", "kulim", "gurun"],
        "level_2_secondary": ["alor_setar_city"],
        "level_3_pan_urban": "kuala_muda_district"
    },
    "gurun": {
        "display_name": "古倫",
        "level_1_adjacent": ["sungai_petani_city", "bedong"],
        "level_2_secondary": ["alor_setar_city"],
        "level_3_pan_urban": "kuala_muda_district"
    },
    "baling": {
        "display_name": "巴林",
        "level_1_adjacent": ["sungai_petani_city"],
        "level_2_secondary": ["kulim", "alor_setar_city"],
        "level_3_pan_urban": "baling_district"
    },

    # ─── 蘭卡威 ──────────────────────────────────────────────
    "langkawi_kuah": {
        "display_name": "瓜埠（蘭卡威行政中心）",
        "level_1_adjacent": ["langkawi_pantai_cenang"],
        "level_2_secondary": [],
        "level_3_pan_urban": "langkawi_district"
    },
    "langkawi_pantai_cenang": {
        "display_name": "珍南海灘",
        "level_1_adjacent": ["langkawi_kuah"],
        "level_2_secondary": [],
        "level_3_pan_urban": "langkawi_district"
    },

    # ─── 吉打泛城區節點 ──────────────────────────────────────
    "alor_setar_district": {"display_name": "哥打士達縣（全域）", "is_pan_urban": True},
    "kubang_pasu_district": {"display_name": "古邦巴素縣（全域）", "is_pan_urban": True},
    "kuala_muda_district":  {"display_name": "瓜拉姆達縣（全域）", "is_pan_urban": True},
    "kulim_district":       {"display_name": "居林縣（全域）", "is_pan_urban": True},
    "pendang_district":     {"display_name": "本當縣（全域）", "is_pan_urban": True},
    "baling_district":      {"display_name": "巴林縣（全域）", "is_pan_urban": True},
    "langkawi_district":    {"display_name": "蘭卡威縣（全域）", "is_pan_urban": True},
    "kedah_state":          {"display_name": "吉打州（全域）", "is_pan_urban": True},


    # ════════════════════════════════════════════════════════════
    # 玻璃市 (PERLIS)
    # ════════════════════════════════════════════════════════════

    "kangar": {
        "display_name": "加央",
        "level_1_adjacent": ["arau", "simpang_empat_perlis"],
        "level_2_secondary": ["padang_besar"],
        "level_3_pan_urban": "perlis_state"
    },
    "arau": {
        "display_name": "阿魯（玻璃市皇城）",
        "level_1_adjacent": ["kangar"],
        "level_2_secondary": ["simpang_empat_perlis", "padang_besar"],
        "level_3_pan_urban": "perlis_state"
    },
    "simpang_empat_perlis": {
        "display_name": "四路口",
        "level_1_adjacent": ["kangar", "arau"],
        "level_2_secondary": ["padang_besar"],
        "level_3_pan_urban": "perlis_state"
    },
    "padang_besar": {
        "display_name": "巴東勿剎（泰馬口岸）",
        "level_1_adjacent": ["kangar"],
        "level_2_secondary": ["arau"],
        "level_3_pan_urban": "perlis_state"
    },

    "perlis_state": {"display_name": "玻璃市州（全域）", "is_pan_urban": True},


    # ════════════════════════════════════════════════════════════
    # 吉蘭丹 (KELANTAN)
    # ════════════════════════════════════════════════════════════

    # ─── 哥打巴魯都會區 ──────────────────────────────────────
    "kota_bharu_city": {
        "display_name": "哥打巴魯",
        "level_1_adjacent": ["pasir_mas", "tumpat", "bachok"],
        "level_2_secondary": ["tanah_merah", "machang"],
        "level_3_pan_urban": "kota_bharu_district"
    },
    "pasir_mas": {
        "display_name": "巴西馬",
        "level_1_adjacent": ["kota_bharu_city", "tumpat"],
        "level_2_secondary": ["bachok", "tanah_merah"],
        "level_3_pan_urban": "pasir_mas_district"
    },
    "tumpat": {
        "display_name": "登達",
        "level_1_adjacent": ["kota_bharu_city", "pasir_mas"],
        "level_2_secondary": ["bachok"],
        "level_3_pan_urban": "tumpat_district"
    },
    "bachok": {
        "display_name": "巴卓",
        "level_1_adjacent": ["kota_bharu_city"],
        "level_2_secondary": ["pasir_mas", "tanah_merah"],
        "level_3_pan_urban": "bachok_district"
    },
    "tanah_merah": {
        "display_name": "丹那美拉",
        "level_1_adjacent": ["machang"],
        "level_2_secondary": ["kota_bharu_city", "bachok"],
        "level_3_pan_urban": "tanah_merah_district"
    },
    "machang": {
        "display_name": "馬樟",
        "level_1_adjacent": ["tanah_merah"],
        "level_2_secondary": ["kota_bharu_city", "kuala_krai"],
        "level_3_pan_urban": "machang_district"
    },
    "kuala_krai": {
        "display_name": "瓜拉吉賴",
        "level_1_adjacent": ["machang"],
        "level_2_secondary": ["gua_musang"],
        "level_3_pan_urban": "kuala_krai_district"
    },
    "gua_musang": {
        "display_name": "話望生",
        "level_1_adjacent": ["kuala_krai"],
        "level_2_secondary": [],
        "level_3_pan_urban": "gua_musang_district"
    },

    # ─── 吉蘭丹泛城區節點 ────────────────────────────────────
    "kota_bharu_district": {"display_name": "哥打巴魯縣（全域）", "is_pan_urban": True},
    "pasir_mas_district":  {"display_name": "巴西馬縣（全域）", "is_pan_urban": True},
    "tumpat_district":     {"display_name": "登達縣（全域）", "is_pan_urban": True},
    "bachok_district":     {"display_name": "巴卓縣（全域）", "is_pan_urban": True},
    "tanah_merah_district":{"display_name": "丹那美拉縣（全域）", "is_pan_urban": True},
    "machang_district":    {"display_name": "馬樟縣（全域）", "is_pan_urban": True},
    "kuala_krai_district": {"display_name": "瓜拉吉賴縣（全域）", "is_pan_urban": True},
    "gua_musang_district": {"display_name": "話望生縣（全域）", "is_pan_urban": True},
    "kelantan_state":      {"display_name": "吉蘭丹州（全域）", "is_pan_urban": True},


    # ════════════════════════════════════════════════════════════
    # 登嘉樓 (TERENGGANU)
    # ════════════════════════════════════════════════════════════

    # ─── 瓜拉登嘉樓都會區 ────────────────────────────────────
    "kuala_terengganu_city": {
        "display_name": "瓜拉登嘉樓",
        "level_1_adjacent": ["kuala_nerus", "marang"],
        "level_2_secondary": ["dungun_town", "setiu"],
        "level_3_pan_urban": "kuala_terengganu_district"
    },
    "kuala_nerus": {
        "display_name": "瓜拉尼魯斯",
        "level_1_adjacent": ["kuala_terengganu_city", "setiu"],
        "level_2_secondary": ["marang"],
        "level_3_pan_urban": "kuala_nerus_district"
    },
    "marang": {
        "display_name": "馬蘭",
        "level_1_adjacent": ["kuala_terengganu_city"],
        "level_2_secondary": ["kuala_nerus", "dungun_town"],
        "level_3_pan_urban": "marang_district"
    },
    "setiu": {
        "display_name": "士底吾",
        "level_1_adjacent": ["kuala_nerus"],
        "level_2_secondary": ["kuala_terengganu_city"],
        "level_3_pan_urban": "setiu_district"
    },

    # ─── 甘馬挽 ──────────────────────────────────────────────
    "kemaman_town": {
        "display_name": "甘馬挽（蔡士）",
        "level_1_adjacent": ["kerteh", "chukai"],
        "level_2_secondary": ["dungun_town", "kuantan_city"],
        "level_3_pan_urban": "kemaman_district"
    },
    "chukai": {
        "display_name": "砰砰",
        "level_1_adjacent": ["kemaman_town", "kerteh"],
        "level_2_secondary": ["dungun_town"],
        "level_3_pan_urban": "kemaman_district"
    },
    "kerteh": {
        "display_name": "格地",
        "level_1_adjacent": ["kemaman_town", "chukai"],
        "level_2_secondary": ["dungun_town"],
        "level_3_pan_urban": "kemaman_district"
    },

    # ─── 龍運 ────────────────────────────────────────────────
    "dungun_town": {
        "display_name": "龍運",
        "level_1_adjacent": ["paka"],
        "level_2_secondary": ["kemaman_town", "marang"],
        "level_3_pan_urban": "dungun_district"
    },
    "paka": {
        "display_name": "巴卡",
        "level_1_adjacent": ["dungun_town"],
        "level_2_secondary": ["kerteh"],
        "level_3_pan_urban": "dungun_district"
    },

    # ─── 勿述 ────────────────────────────────────────────────
    "besut_town": {
        "display_name": "勿述",
        "level_1_adjacent": ["jerteh"],
        "level_2_secondary": ["setiu"],
        "level_3_pan_urban": "besut_district"
    },
    "jerteh": {
        "display_name": "者泰",
        "level_1_adjacent": ["besut_town"],
        "level_2_secondary": ["setiu"],
        "level_3_pan_urban": "besut_district"
    },

    # ─── 登嘉樓泛城區節點 ────────────────────────────────────
    "kuala_terengganu_district": {"display_name": "瓜拉登嘉樓縣（全域）", "is_pan_urban": True},
    "kuala_nerus_district":      {"display_name": "瓜拉尼魯斯縣（全域）", "is_pan_urban": True},
    "marang_district":           {"display_name": "馬蘭縣（全域）", "is_pan_urban": True},
    "setiu_district":            {"display_name": "士底吾縣（全域）", "is_pan_urban": True},
    "kemaman_district":          {"display_name": "甘馬挽縣（全域）", "is_pan_urban": True},
    "dungun_district":           {"display_name": "龍運縣（全域）", "is_pan_urban": True},
    "besut_district":            {"display_name": "勿述縣（全域）", "is_pan_urban": True},
    "terengganu_state":          {"display_name": "登嘉樓州（全域）", "is_pan_urban": True},


    # ════════════════════════════════════════════════════════════
    # 彭亨 (PAHANG)
    # ════════════════════════════════════════════════════════════

    # ─── 關丹都會區 ──────────────────────────────────────────
    "kuantan_city": {
        "display_name": "關丹",
        "level_1_adjacent": ["beserah", "semambu", "indera_mahkota"],
        "level_2_secondary": ["cherating", "gebeng", "pekan"],
        "level_3_pan_urban": "kuantan_district"
    },
    "beserah": {
        "display_name": "武吉沙惹",
        "level_1_adjacent": ["kuantan_city", "cherating"],
        "level_2_secondary": ["semambu"],
        "level_3_pan_urban": "kuantan_district"
    },
    "semambu": {
        "display_name": "實文丹",
        "level_1_adjacent": ["kuantan_city", "indera_mahkota"],
        "level_2_secondary": ["gebeng"],
        "level_3_pan_urban": "kuantan_district"
    },
    "indera_mahkota": {
        "display_name": "英德馬哈它",
        "level_1_adjacent": ["kuantan_city", "semambu"],
        "level_2_secondary": ["gebeng"],
        "level_3_pan_urban": "kuantan_district"
    },
    "cherating": {
        "display_name": "珍拉丁",
        "level_1_adjacent": ["beserah"],
        "level_2_secondary": ["kuantan_city"],
        "level_3_pan_urban": "kuantan_district"
    },
    "gebeng": {
        "display_name": "格賓（工業區）",
        "level_1_adjacent": ["semambu", "indera_mahkota"],
        "level_2_secondary": ["kuantan_city"],
        "level_3_pan_urban": "kuantan_district"
    },
    "pekan": {
        "display_name": "北根（皇城）",
        "level_1_adjacent": ["kuantan_city"],
        "level_2_secondary": ["beserah"],
        "level_3_pan_urban": "pekan_district"
    },

    # ─── 文冬 ────────────────────────────────────────────────
    "bentong_town": {
        "display_name": "文冬",
        "level_1_adjacent": ["karak"],
        "level_2_secondary": ["kuantan_city", "temerloh_town"],
        "level_3_pan_urban": "bentong_district"
    },
    "karak": {
        "display_name": "喀叻",
        "level_1_adjacent": ["bentong_town"],
        "level_2_secondary": ["temerloh_town"],
        "level_3_pan_urban": "bentong_district"
    },

    # ─── 直鑾（Temerloh）────────────────────────────────────
    "temerloh_town": {
        "display_name": "直鑾",
        "level_1_adjacent": ["mentakab"],
        "level_2_secondary": ["bentong_town", "kuantan_city"],
        "level_3_pan_urban": "temerloh_district"
    },
    "mentakab": {
        "display_name": "文德甲",
        "level_1_adjacent": ["temerloh_town"],
        "level_2_secondary": [],
        "level_3_pan_urban": "temerloh_district"
    },

    # ─── 金馬崙高原 ──────────────────────────────────────────
    "tanah_rata": {
        "display_name": "打拿叻（金馬崙高原）",
        "level_1_adjacent": ["brinchang"],
        "level_2_secondary": [],
        "level_3_pan_urban": "cameron_highlands_district"
    },
    "brinchang": {
        "display_name": "林慶（金馬崙高原）",
        "level_1_adjacent": ["tanah_rata"],
        "level_2_secondary": [],
        "level_3_pan_urban": "cameron_highlands_district"
    },

    # ─── 勞勿 ────────────────────────────────────────────────
    "raub_town": {
        "display_name": "勞勿",
        "level_1_adjacent": [],
        "level_2_secondary": ["bentong_town", "temerloh_town"],
        "level_3_pan_urban": "raub_district"
    },

    # ─── 彭亨泛城區節點 ──────────────────────────────────────
    "kuantan_district":           {"display_name": "關丹縣（全域）", "is_pan_urban": True},
    "pekan_district":             {"display_name": "北根縣（全域）", "is_pan_urban": True},
    "bentong_district":           {"display_name": "文冬縣（全域）", "is_pan_urban": True},
    "temerloh_district":          {"display_name": "直鑾縣（全域）", "is_pan_urban": True},
    "cameron_highlands_district": {"display_name": "金馬崙縣（全域）", "is_pan_urban": True},
    "raub_district":              {"display_name": "勞勿縣（全域）", "is_pan_urban": True},
    "pahang_state":               {"display_name": "彭亨州（全域）", "is_pan_urban": True},


    # ════════════════════════════════════════════════════════════
    # 森美蘭 (NEGERI SEMBILAN)
    # ════════════════════════════════════════════════════════════

    # ─── 芙蓉 / 汝來都會區 ───────────────────────────────────
    "seremban_city": {
        "display_name": "芙蓉",
        "level_1_adjacent": ["senawang", "nilai", "labu"],
        "level_2_secondary": ["port_dickson", "kuala_pilah", "gemas"],
        "level_3_pan_urban": "seremban_district"
    },
    "senawang": {
        "display_name": "士拿旺",
        "level_1_adjacent": ["seremban_city", "nilai"],
        "level_2_secondary": ["labu"],
        "level_3_pan_urban": "seremban_district"
    },
    "nilai": {
        "display_name": "汝來",
        "level_1_adjacent": ["seremban_city", "senawang", "labu"],
        "level_2_secondary": ["cyberjaya", "putrajaya", "sepang_town"],
        "level_3_pan_urban": "nilai_district"
    },
    "labu": {
        "display_name": "拉務",
        "level_1_adjacent": ["nilai", "seremban_city"],
        "level_2_secondary": ["senawang"],
        "level_3_pan_urban": "nilai_district"
    },

    # ─── 波德申 ──────────────────────────────────────────────
    "port_dickson": {
        "display_name": "波德申",
        "level_1_adjacent": ["linggi"],
        "level_2_secondary": ["seremban_city", "klang_town"],
        "level_3_pan_urban": "port_dickson_district"
    },
    "linggi": {
        "display_name": "靈宜",
        "level_1_adjacent": ["port_dickson"],
        "level_2_secondary": ["seremban_city"],
        "level_3_pan_urban": "port_dickson_district"
    },

    # ─── 其他城鎮 ────────────────────────────────────────────
    "kuala_pilah": {
        "display_name": "瓜拉比勒",
        "level_1_adjacent": [],
        "level_2_secondary": ["seremban_city", "tampin"],
        "level_3_pan_urban": "kuala_pilah_district"
    },
    "tampin": {
        "display_name": "淡邊",
        "level_1_adjacent": [],
        "level_2_secondary": ["seremban_city", "gemas"],
        "level_3_pan_urban": "tampin_district"
    },
    "bahau": {
        "display_name": "芭亞",
        "level_1_adjacent": [],
        "level_2_secondary": ["kuala_pilah", "seremban_city"],
        "level_3_pan_urban": "rembau_jempol_district"
    },

    # ─── 森美蘭泛城區節點 ────────────────────────────────────
    "seremban_district":      {"display_name": "芙蓉縣（全域）", "is_pan_urban": True},
    "nilai_district":         {"display_name": "汝來縣（全域）", "is_pan_urban": True},
    "port_dickson_district":  {"display_name": "波德申縣（全域）", "is_pan_urban": True},
    "kuala_pilah_district":   {"display_name": "瓜拉比勒縣（全域）", "is_pan_urban": True},
    "tampin_district":        {"display_name": "淡邊縣（全域）", "is_pan_urban": True},
    "rembau_jempol_district": {"display_name": "林茂/仁保縣（全域）", "is_pan_urban": True},
    "negeri_sembilan_state":  {"display_name": "森美蘭州（全域）", "is_pan_urban": True},


    # ════════════════════════════════════════════════════════════
    # 馬六甲 (MELAKA)
    # ════════════════════════════════════════════════════════════

    # ─── 馬六甲市都會區 ──────────────────────────────────────
    "melaka_city_centre": {
        "display_name": "馬六甲古城區",
        "level_1_adjacent": ["ayer_keroh", "bukit_baru", "klebang"],
        "level_2_secondary": ["batu_berendam", "cheng", "alor_gajah_town"],
        "level_3_pan_urban": "melaka_tengah_district"
    },
    "ayer_keroh": {
        "display_name": "愛極樂",
        "level_1_adjacent": ["melaka_city_centre", "bukit_baru"],
        "level_2_secondary": ["batu_berendam", "cheng"],
        "level_3_pan_urban": "melaka_tengah_district"
    },
    "bukit_baru": {
        "display_name": "武吉峇魯",
        "level_1_adjacent": ["melaka_city_centre", "ayer_keroh"],
        "level_2_secondary": ["klebang"],
        "level_3_pan_urban": "melaka_tengah_district"
    },
    "klebang": {
        "display_name": "吉里望",
        "level_1_adjacent": ["melaka_city_centre"],
        "level_2_secondary": ["bukit_baru"],
        "level_3_pan_urban": "melaka_tengah_district"
    },
    "batu_berendam": {
        "display_name": "峇都勿蘭丹",
        "level_1_adjacent": ["ayer_keroh", "cheng"],
        "level_2_secondary": ["melaka_city_centre"],
        "level_3_pan_urban": "melaka_tengah_district"
    },
    "cheng": {
        "display_name": "正字",
        "level_1_adjacent": ["batu_berendam", "ayer_keroh"],
        "level_2_secondary": ["melaka_city_centre"],
        "level_3_pan_urban": "melaka_tengah_district"
    },

    # ─── 亞羅牙也 / 者先 ─────────────────────────────────────
    "alor_gajah_town": {
        "display_name": "亞羅牙也",
        "level_1_adjacent": ["masjid_tanah"],
        "level_2_secondary": ["melaka_city_centre", "jasin_town"],
        "level_3_pan_urban": "alor_gajah_district"
    },
    "masjid_tanah": {
        "display_name": "土廟",
        "level_1_adjacent": ["alor_gajah_town"],
        "level_2_secondary": ["melaka_city_centre"],
        "level_3_pan_urban": "alor_gajah_district"
    },
    "jasin_town": {
        "display_name": "者先",
        "level_1_adjacent": [],
        "level_2_secondary": ["alor_gajah_town", "melaka_city_centre"],
        "level_3_pan_urban": "jasin_district"
    },

    # ─── 馬六甲泛城區節點 ────────────────────────────────────
    "melaka_tengah_district": {"display_name": "馬六甲中央縣（全域）", "is_pan_urban": True},
    "alor_gajah_district":    {"display_name": "亞羅牙也縣（全域）", "is_pan_urban": True},
    "jasin_district":         {"display_name": "者先縣（全域）", "is_pan_urban": True},
    "melaka_state":           {"display_name": "馬六甲州（全域）", "is_pan_urban": True},


    # ════════════════════════════════════════════════════════════
    # 砂拉越 (SARAWAK)
    # ════════════════════════════════════════════════════════════

    # ─── 古晉都會區 ──────────────────────────────────────────
    "kuching_city": {
        "display_name": "古晉",
        "level_1_adjacent": ["kota_samarahan", "padawan"],
        "level_2_secondary": ["serian", "bau", "lundu"],
        "level_3_pan_urban": "kuching_district"
    },
    "kota_samarahan": {
        "display_name": "哥打薩馬拉漢",
        "level_1_adjacent": ["kuching_city", "padawan"],
        "level_2_secondary": ["serian"],
        "level_3_pan_urban": "samarahan_district"
    },
    "padawan": {
        "display_name": "巴達旺",
        "level_1_adjacent": ["kuching_city", "kota_samarahan"],
        "level_2_secondary": ["bau"],
        "level_3_pan_urban": "kuching_district"
    },
    "serian": {
        "display_name": "石里安",
        "level_1_adjacent": ["kota_samarahan"],
        "level_2_secondary": ["kuching_city", "bau"],
        "level_3_pan_urban": "serian_district"
    },
    "bau": {
        "display_name": "包",
        "level_1_adjacent": ["kuching_city", "padawan"],
        "level_2_secondary": ["lundu"],
        "level_3_pan_urban": "bau_district"
    },
    "lundu": {
        "display_name": "倫都",
        "level_1_adjacent": ["bau"],
        "level_2_secondary": ["kuching_city"],
        "level_3_pan_urban": "lundu_district"
    },

    # ─── 詩巫都會區 ──────────────────────────────────────────
    "sibu_city": {
        "display_name": "詩巫",
        "level_1_adjacent": ["dalat", "mukah_town"],
        "level_2_secondary": ["sarikei_town", "kapit"],
        "level_3_pan_urban": "sibu_district"
    },
    "dalat": {
        "display_name": "大拿督",
        "level_1_adjacent": ["sibu_city", "mukah_town"],
        "level_2_secondary": [],
        "level_3_pan_urban": "mukah_district"
    },
    "mukah_town": {
        "display_name": "木膠",
        "level_1_adjacent": ["sibu_city", "dalat"],
        "level_2_secondary": [],
        "level_3_pan_urban": "mukah_district"
    },
    "sarikei_town": {
        "display_name": "泗里街",
        "level_1_adjacent": [],
        "level_2_secondary": ["sibu_city"],
        "level_3_pan_urban": "sarikei_district"
    },
    "kapit": {
        "display_name": "卡必",
        "level_1_adjacent": [],
        "level_2_secondary": ["sibu_city"],
        "level_3_pan_urban": "kapit_district"
    },

    # ─── 美里都會區 ──────────────────────────────────────────
    "miri_city": {
        "display_name": "美里",
        "level_1_adjacent": ["bintulu_town", "niah"],
        "level_2_secondary": ["marudi", "limbang_town"],
        "level_3_pan_urban": "miri_district"
    },
    "bintulu_town": {
        "display_name": "民都魯",
        "level_1_adjacent": ["miri_city"],
        "level_2_secondary": ["sibu_city", "mukah_town"],
        "level_3_pan_urban": "bintulu_district"
    },
    "niah": {
        "display_name": "尼亞",
        "level_1_adjacent": ["miri_city"],
        "level_2_secondary": ["bintulu_town"],
        "level_3_pan_urban": "subis_district"
    },
    "marudi": {
        "display_name": "馬魯帝",
        "level_1_adjacent": [],
        "level_2_secondary": ["miri_city"],
        "level_3_pan_urban": "baram_district"
    },
    "limbang_town": {
        "display_name": "林夢",
        "level_1_adjacent": [],
        "level_2_secondary": ["miri_city"],
        "level_3_pan_urban": "limbang_district"
    },

    # ─── 砂拉越泛城區節點 ────────────────────────────────────
    "kuching_district":   {"display_name": "古晉區（全域）", "is_pan_urban": True},
    "samarahan_district": {"display_name": "薩馬拉漢區（全域）", "is_pan_urban": True},
    "serian_district":    {"display_name": "石里安區（全域）", "is_pan_urban": True},
    "bau_district":       {"display_name": "包區（全域）", "is_pan_urban": True},
    "lundu_district":     {"display_name": "倫都區（全域）", "is_pan_urban": True},
    "sibu_district":      {"display_name": "詩巫區（全域）", "is_pan_urban": True},
    "mukah_district":     {"display_name": "木膠區（全域）", "is_pan_urban": True},
    "sarikei_district":   {"display_name": "泗里街區（全域）", "is_pan_urban": True},
    "kapit_district":     {"display_name": "卡必區（全域）", "is_pan_urban": True},
    "miri_district":      {"display_name": "美里區（全域）", "is_pan_urban": True},
    "bintulu_district":   {"display_name": "民都魯區（全域）", "is_pan_urban": True},
    "subis_district":     {"display_name": "蘇比斯區（全域）", "is_pan_urban": True},
    "baram_district":     {"display_name": "峇南區（全域）", "is_pan_urban": True},
    "limbang_district":   {"display_name": "林夢區（全域）", "is_pan_urban": True},
    "sarawak_state":      {"display_name": "砂拉越州（全域）", "is_pan_urban": True},


    # ════════════════════════════════════════════════════════════
    # 沙巴 (SABAH)
    # ════════════════════════════════════════════════════════════

    # ─── 亞庇都會區 ──────────────────────────────────────────
    "kota_kinabalu_city": {
        "display_name": "亞庇",
        "level_1_adjacent": ["likas", "penampang", "putatan"],
        "level_2_secondary": ["tuaran", "kota_belud", "papar"],
        "level_3_pan_urban": "kota_kinabalu_district"
    },
    "likas": {
        "display_name": "里卡斯",
        "level_1_adjacent": ["kota_kinabalu_city", "penampang"],
        "level_2_secondary": ["tuaran"],
        "level_3_pan_urban": "kota_kinabalu_district"
    },
    "penampang": {
        "display_name": "比南邦",
        "level_1_adjacent": ["kota_kinabalu_city", "likas", "putatan"],
        "level_2_secondary": ["papar"],
        "level_3_pan_urban": "penampang_district"
    },
    "putatan": {
        "display_name": "布達坦",
        "level_1_adjacent": ["kota_kinabalu_city", "penampang"],
        "level_2_secondary": ["papar"],
        "level_3_pan_urban": "penampang_district"
    },
    "tuaran": {
        "display_name": "土阿蘭",
        "level_1_adjacent": ["kota_kinabalu_city", "kota_belud"],
        "level_2_secondary": ["likas"],
        "level_3_pan_urban": "tuaran_district"
    },
    "kota_belud": {
        "display_name": "古打毛律",
        "level_1_adjacent": ["tuaran"],
        "level_2_secondary": ["kota_kinabalu_city"],
        "level_3_pan_urban": "kota_belud_district"
    },
    "papar": {
        "display_name": "保佛",
        "level_1_adjacent": ["penampang", "putatan"],
        "level_2_secondary": ["kota_kinabalu_city"],
        "level_3_pan_urban": "papar_district"
    },

    # ─── 山打根都會區 ────────────────────────────────────────
    "sandakan_city": {
        "display_name": "山打根",
        "level_1_adjacent": ["beluran"],
        "level_2_secondary": ["kinabatangan", "lahad_datu_town"],
        "level_3_pan_urban": "sandakan_district"
    },
    "beluran": {
        "display_name": "貝魯蘭",
        "level_1_adjacent": ["sandakan_city"],
        "level_2_secondary": ["kinabatangan"],
        "level_3_pan_urban": "beluran_district"
    },
    "kinabatangan": {
        "display_name": "根地咬河流域",
        "level_1_adjacent": ["sandakan_city"],
        "level_2_secondary": ["lahad_datu_town"],
        "level_3_pan_urban": "kinabatangan_district"
    },

    # ─── 斗湖都會區 ──────────────────────────────────────────
    "tawau_city": {
        "display_name": "斗湖",
        "level_1_adjacent": ["semporna", "lahad_datu_town"],
        "level_2_secondary": ["keningau"],
        "level_3_pan_urban": "tawau_district"
    },
    "semporna": {
        "display_name": "仙本那",
        "level_1_adjacent": ["tawau_city"],
        "level_2_secondary": ["lahad_datu_town"],
        "level_3_pan_urban": "semporna_district"
    },
    "lahad_datu_town": {
        "display_name": "拿篤",
        "level_1_adjacent": ["tawau_city", "sandakan_city"],
        "level_2_secondary": ["semporna", "keningau"],
        "level_3_pan_urban": "lahad_datu_district"
    },

    # ─── 內陸 ────────────────────────────────────────────────
    "keningau": {
        "display_name": "根納鎮",
        "level_1_adjacent": ["tambunan"],
        "level_2_secondary": ["kota_kinabalu_city", "tawau_city"],
        "level_3_pan_urban": "keningau_district"
    },
    "tambunan": {
        "display_name": "坦布南",
        "level_1_adjacent": ["keningau"],
        "level_2_secondary": ["ranau"],
        "level_3_pan_urban": "tambunan_district"
    },
    "ranau": {
        "display_name": "拿奴",
        "level_1_adjacent": ["tambunan"],
        "level_2_secondary": ["kota_belud"],
        "level_3_pan_urban": "ranau_district"
    },

    # ─── 沙巴泛城區節點 ──────────────────────────────────────
    "kota_kinabalu_district": {"display_name": "亞庇縣（全域）", "is_pan_urban": True},
    "penampang_district":     {"display_name": "比南邦縣（全域）", "is_pan_urban": True},
    "tuaran_district":        {"display_name": "土阿蘭縣（全域）", "is_pan_urban": True},
    "kota_belud_district":    {"display_name": "古打毛律縣（全域）", "is_pan_urban": True},
    "papar_district":         {"display_name": "保佛縣（全域）", "is_pan_urban": True},
    "sandakan_district":      {"display_name": "山打根縣（全域）", "is_pan_urban": True},
    "beluran_district":       {"display_name": "貝魯蘭縣（全域）", "is_pan_urban": True},
    "kinabatangan_district":  {"display_name": "根地咬縣（全域）", "is_pan_urban": True},
    "tawau_district":         {"display_name": "斗湖縣（全域）", "is_pan_urban": True},
    "semporna_district":      {"display_name": "仙本那縣（全域）", "is_pan_urban": True},
    "lahad_datu_district":    {"display_name": "拿篤縣（全域）", "is_pan_urban": True},
    "keningau_district":      {"display_name": "根納縣（全域）", "is_pan_urban": True},
    "tambunan_district":      {"display_name": "坦布南縣（全域）", "is_pan_urban": True},
    "ranau_district":         {"display_name": "拿奴縣（全域）", "is_pan_urban": True},
    "sabah_state":            {"display_name": "沙巴州（全域）", "is_pan_urban": True},
}


def get_search_districts(target_district: str, expansion_level: int) -> list[str]:
    """
    根據目標區和擴張級別，返回應當納入搜索的行政區列表。

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