"""ژن‌های پنل‌های تشخیصی — CPIC، CGP، Carrier، PRS."""

# پنل استاندارد فارماکوژنومیک CPIC (۱۸ ژن)
CPIC_PANEL_GENES = frozenset({
    "CYP2D6", "CYP2C19", "CYP2C9", "CYP3A5", "CYP4F2",
    "TPMT", "NUDT15", "DPYD", "UGT1A1", "SLCO1B1",
    "VKORC1", "HLA-B", "HLA-A", "G6PD", "IFNL3",
    "ABCG2", "RYR1", "CACNA1S", "MT-RNR1", "CFTR",
})

PHARMACOGENOMIC_GENES = CPIC_PANEL_GENES  # سازگاری با کد موجود

# ژن‌های actionable سرطان (CGP / NCCN)
CGP_ACTIONABLE_GENES = frozenset({
    "BRCA1", "BRCA2", "ATM", "PALB2", "CHEK2", "TP53",
    "MLH1", "MSH2", "MSH6", "PMS2", "EPCAM", "BARD1",
    "RAD51C", "RAD51D", "BRIP1", "CDK12", "STK11", "PTEN",
    "NF1", "RET", "SDHB", "SDHC", "SDHD", "VHL", "MET",
    "ERBB2", "BRAF", "KRAS", "NRAS", "PIK3CA",
})

# غربالگری ناقل (Carrier Screening) — قبل از بارداری
CARRIER_SCREENING_GENES = frozenset({
    "CFTR", "SMN1", "HBB", "PAH", "GAA", "ACADM", "HEXA",
    "GBA", "HBA1", "HBA2", "SERPINA1", "FMR1", "DMD",
    "GALT", "BTD", "IVD", "ASL", "ASS1", "OTC", "G6PD",
    "SMA", "PKHD1", "ATP7B", "MEFV",
})

# SNPهای PRS (نمونه — در production از PGS Catalog)
PRS_TRAITS = {
    "coronary_artery_disease": {
        "name_fa": "بیماری عروق کرونر",
        "snps": ["rs10757274", "rs1333049", "rs4977574"],
        "weights": [0.15, 0.12, 0.10],
    },
    "type_2_diabetes": {
        "name_fa": "دیابت نوع ۲",
        "snps": ["rs7903146", "rs1801282", "rs5219"],
        "weights": [0.18, 0.11, 0.09],
    },
    "breast_cancer": {
        "name_fa": "سرطان پستان",
        "snps": ["rs2981582", "rs3803662", "rs889312"],
        "weights": [0.14, 0.13, 0.11],
    },
    "colorectal_cancer": {
        "name_fa": "سرطان روده بزرگ",
        "snps": ["rs6983267", "rs4779584", "rs10795668"],
        "weights": [0.12, 0.10, 0.08],
    },
}
