"""شبیه‌سازی LD با Gaussian Copula — بدون وابستگی خارجی."""

from __future__ import annotations

from math import erf, sqrt

import numpy as np

from data.dev_fixtures import PGX_SNPS_ORDERED


_sqrt2 = sqrt(2.0)
_erf_vec = np.vectorize(erf, otypes=[float])


def _norm_cdf(x: np.ndarray) -> np.ndarray:
    """CDF نرمال استاندارد — برداری."""
    return 0.5 * (1.0 + _erf_vec(x / _sqrt2))


def build_ld_correlation_matrix(
    n_snps: int,
    *,
    block_size: int = 4,
    within_block_r: float = 0.65,
    distance_decay: float = 0.12,
    min_r: float = 0.05,
) -> np.ndarray:
    """
    ماتریس همبستگی با بلوک‌های LD:
    SNPهای مجاور در یک بلوک همبستگی بالاتر دارند (شبیه LD واقعی).
    """
    corr = np.eye(n_snps)
    for block_start in range(0, n_snps, block_size):
        block_end = min(block_start + block_size, n_snps)
        for i in range(block_start, block_end):
            for j in range(i + 1, block_end):
                r = within_block_r * (1.0 - distance_decay * (j - i))
                r = float(np.clip(r, min_r, 0.95))
                corr[i, j] = corr[j, i] = r

    # اطمینان از مثبت‌تعریف بودن برای Cholesky
    eig_min = float(np.linalg.eigvalsh(corr).min())
    if eig_min < 1e-6:
        corr += (1e-4 - eig_min) * np.eye(n_snps)
    return corr


def build_pgx_ld_matrix() -> tuple[np.ndarray, list[str], list[float]]:
    """ماتریس LD برای SNPهای PharmGKB شناخته‌شده."""
    rsids = [s["rsid"] for s in PGX_SNPS_ORDERED]
    mafs = [s["maf"] for s in PGX_SNPS_ORDERED]
    n = len(rsids)
    corr = np.eye(n)
    block_map = {s["rsid"]: s["ld_block"] for s in PGX_SNPS_ORDERED}

    for i in range(n):
        for j in range(i + 1, n):
            if block_map[rsids[i]] == block_map[rsids[j]]:
                dist = abs(i - j)
                r = 0.7 * (1.0 - 0.1 * dist)
                corr[i, j] = corr[j, i] = float(np.clip(r, 0.15, 0.9))
            else:
                corr[i, j] = corr[j, i] = 0.02

    eig_min = float(np.linalg.eigvalsh(corr).min())
    if eig_min < 1e-6:
        corr += (1e-4 - eig_min) * np.eye(n)
    return corr, rsids, mafs


def _uniform_to_genotype(u: np.ndarray, maf: float) -> np.ndarray:
    """تبدیل uniform [0,1] به ژنوتیپ {0,1,2} تحت HWE."""
    q0 = (1.0 - maf) ** 2
    q1 = q0 + 2.0 * maf * (1.0 - maf)
    return np.where(u <= q0, 0, np.where(u <= q1, 1, 2)).astype(int)


def simulate_genotypes_gaussian_copula(
    n_samples: int,
    mafs: list[float] | np.ndarray,
    correlation: np.ndarray,
    *,
    seed: int | None = 42,
) -> np.ndarray:
    """
    Gaussian Copula → uniform → ژنوتیپ گسسته.

    بازگشت: آرایه (n_samples, n_snps) با مقادیر 0/1/2
    """
    mafs_arr = np.asarray(mafs, dtype=float)
    n_snps = len(mafs_arr)
    if correlation.shape != (n_snps, n_snps):
        raise ValueError(f"ابعاد correlation باید ({n_snps}, {n_snps}) باشد")

    rng = np.random.default_rng(seed)
    chol = np.linalg.cholesky(correlation)
    z = rng.standard_normal((n_samples, n_snps)) @ chol.T
    u = _norm_cdf(z)

    genotypes = np.zeros((n_samples, n_snps), dtype=int)
    for j, maf in enumerate(mafs_arr):
        genotypes[:, j] = _uniform_to_genotype(u[:, j], float(maf))
    return genotypes


def pairwise_ld_r2(genotypes: np.ndarray) -> np.ndarray:
    """محاسبه r² بین جفت SNPها — برای اعتبارسنجی LD."""
    n_snps = genotypes.shape[1]
    r2 = np.eye(n_snps)
    for i in range(n_snps):
        for j in range(i + 1, n_snps):
            r = np.corrcoef(genotypes[:, i], genotypes[:, j])[0, 1]
            if np.isnan(r):
                r = 0.0
            r2[i, j] = r2[j, i] = r ** 2
    return r2
