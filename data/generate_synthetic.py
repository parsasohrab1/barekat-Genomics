"""تولید داده‌های سنتتیک ژنومیکس و فارماکوژنومیکس."""

import numpy as np
import pandas as pd


def generate_synthetic_genomics_data(n_samples: int = 1000, n_snps: int = 50) -> pd.DataFrame:
    """
    تولید داده‌های سنتتیک ژنومیکس و فارماکوژنومیکس.

    پارامترها:
        n_samples: تعداد نمونه‌ها (بیماران)
        n_snps: تعداد جایگاه‌های ژنی (SNP)

    بازگشت: دیتافریم پانداس شامل داده‌های ژنوتیپ و فنوتیپ
    """
    np.random.seed(42)

    age = np.random.normal(55, 15, n_samples).astype(int)
    age = np.clip(age, 18, 90)
    gender = np.random.choice(["Male", "Female"], n_samples, p=[0.48, 0.52])

    snp_data = {}
    for i in range(n_snps):
        maf = np.random.uniform(0.05, 0.4)
        p = maf
        q = 1 - p
        genotype_probs = [q**2, 2 * q * p, p**2]
        snp_data[f"SNP_{i+1}"] = np.random.choice([0, 1, 2], n_samples, p=genotype_probs)

    for i in range(0, n_snps - 1, 2):
        snp_data[f"SNP_{i+2}"] = np.clip(
            snp_data[f"SNP_{i+1}"] + np.random.normal(0, 0.5, n_samples), 0, 2
        ).astype(int)

    drug_response_prob = np.zeros(n_samples)
    for i in range(n_samples):
        risk_score = 0
        if snp_data["SNP_5"][i] == 2:
            risk_score += 0.4
        elif snp_data["SNP_5"][i] == 1:
            risk_score += 0.15
        if snp_data["SNP_10"][i] == 0:
            risk_score += 0.3
        prob_respond = np.clip(0.7 - risk_score, 0.1, 0.95)
        drug_response_prob[i] = prob_respond

    drug_response = np.random.binomial(1, drug_response_prob)

    df = pd.DataFrame({
        "Patient_ID": [f"P{str(i).zfill(4)}" for i in range(n_samples)],
        "Age": age,
        "Gender": gender,
        "Drug_Response": drug_response,
        "Response_Probability": np.round(drug_response_prob, 3),
    })

    for snp_col, snp_values in snp_data.items():
        df[snp_col] = snp_values

    df.loc[df["Age"] < 30, "Drug_Response"] = 0

    noise_idx = np.random.choice(n_samples, size=int(n_samples * 0.05), replace=False)
    df.loc[noise_idx, "Drug_Response"] = 1 - df.loc[noise_idx, "Drug_Response"]

    return df


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    genomics_data = generate_synthetic_genomics_data(n_samples=500, n_snps=20)
    print(f"تعداد رکوردها: {len(genomics_data)}")
    print(f"ستون‌ها: {genomics_data.columns.tolist()}")
    print("\nنمونه داده:")
    print(genomics_data.head(10))
    print(f"\nتوزیع پاسخ به دارو:\n{genomics_data['Drug_Response'].value_counts()}")

    output_path = "data/synthetic_genomics.csv"
    genomics_data.to_csv(output_path, index=False)
    print(f"\nذخیره شد در: {output_path}")
