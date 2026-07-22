"""Generate exact LAR / lasso path data for the LAR concept page.

Writes lar-data.json next to this script.

Dataset A: N=100, p=6, correlated factor design (seed 16). v3 is a "bridge"
variable correlated with both factor groups; its true coefficient is negative
but it enters the path early with a positive coefficient (proxy effect), rises,
then crosses zero -> the lasso modification produces a drop event and the LAR
and lasso paths visibly diverge (ESL Fig 3.15 style).

Dataset B: N=50, p=2 (corr ~0.5) for the equiangular-geometry picture.

All paths are EXACT piecewise-linear LARS (Efron et al. 2004 / ESL Alg 3.2):
  gamma = min+_{j in inactive} { (C - c_j)/(A_A - a_j), (C + c_j)/(A_A + a_j) }
Lasso modification: if some active beta_j would cross zero at
  gamma_tilde_j = -beta_j / d_j  <  gamma,
truncate the step there, drop j, and recompute the direction.
"""
import json
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "lar-data.json")


# ----------------------------------------------------------------------------
# Core algorithm
# ----------------------------------------------------------------------------

def standardize(X):
    """ESL Alg 3.2 step 1: mean 0, unit L2 norm columns."""
    X = X - X.mean(axis=0)
    return X / np.linalg.norm(X, axis=0)


def lars(X, y, lasso=False, max_iter=500):
    """Exact LARS path; knots as list of dicts (beta, C, active, event)."""
    n, p = X.shape
    beta = np.zeros(p)
    mu = np.zeros(n)
    active = []
    c = X.T @ (y - mu)
    C = np.abs(c).max()
    next_add = int(np.argmax(np.abs(c)))
    # each knot's "event" says which variable joins/leaves AT that knot;
    # the joining variable moves during the following segment
    knots = [dict(beta=beta.copy(), C=C, active=[], event=f"add:{next_add}")]
    for _ in range(max_iter):
        c = X.T @ (y - mu)
        C = np.abs(c).max()
        if C < 1e-10:
            break
        if next_add is not None:
            active.append(next_add)
        s = np.sign(c[active])
        Xa = X[:, active] * s
        G = Xa.T @ Xa
        Ginv1 = np.linalg.solve(G, np.ones(len(active)))
        AA = 1.0 / np.sqrt(Ginv1.sum())          # A_A
        w = AA * Ginv1                            # w_A
        u = Xa @ w                                # equiangular unit vector u_A
        a = X.T @ u                               # a = X^T u_A
        inactive = [j for j in range(p) if j not in active]
        gamma = C / AA                            # full step -> joint OLS
        j_star = None
        for j in inactive:
            for val in ((C - c[j]) / (AA - a[j]), (C + c[j]) / (AA + a[j])):
                if 1e-12 < val < gamma - 1e-12:
                    gamma = val
                    j_star = j
        d = np.zeros(p)
        d[active] = s * w                         # direction in beta space
        dropped = None
        if lasso:
            g_drop, j_drop = np.inf, None
            for j in active:
                if abs(d[j]) > 1e-14:
                    gt = -beta[j] / d[j]          # gamma_tilde_j
                    if 1e-12 < gt < g_drop:
                        g_drop, j_drop = gt, j
            if j_drop is not None and g_drop < gamma - 1e-12:
                gamma, dropped, j_star = g_drop, j_drop, None
        beta = beta + gamma * d
        mu = mu + gamma * u
        if dropped is not None:
            beta[dropped] = 0.0                   # exact zero at the crossing
            active.remove(dropped)
            next_add = None                       # no add right after a drop
            ev = f"drop:{dropped}"
        else:
            next_add = j_star
            ev = f"add:{j_star}" if j_star is not None else "end"
        Cn = np.abs(X.T @ (y - mu)).max()
        knots.append(dict(beta=beta.copy(), C=Cn, active=list(active), event=ev))
        if dropped is None and j_star is None:
            break
    return knots


def arc_of(knots):
    """Cumulative L1 arc length along the piecewise-linear path."""
    arcs = [0.0]
    for k in range(1, len(knots)):
        arcs.append(arcs[-1] + np.abs(knots[k]["beta"] - knots[k - 1]["beta"]).sum())
    return arcs


def cd_lasso(X, y, lam, tol=1e-13, max_iter=400_000):
    """Coordinate descent for (1/2)||y - Xb||^2 + lam * ||b||_1 (unit-norm cols)."""
    p = X.shape[1]
    XtX = X.T @ X
    Xty = X.T @ y
    b = np.zeros(p)
    for _ in range(max_iter):
        delta = 0.0
        for j in range(p):
            rho = Xty[j] - XtX[j] @ b + XtX[j, j] * b[j]
            new = np.sign(rho) * max(abs(rho) - lam, 0.0) / XtX[j, j]
            delta = max(delta, abs(new - b[j]))
            b[j] = new
        if delta < tol:
            break
    return b


# ----------------------------------------------------------------------------
# Dataset A
# ----------------------------------------------------------------------------

SEED_A = 16
N_A, P_A = 100, 6
NAMES_A = [f"v{i+1}" for i in range(P_A)]
BETA_TRUE_A = np.array([6.0, -1.5, -1.6, 3.0, 0.0, 2.0])

rng = np.random.default_rng(SEED_A)
f1 = rng.standard_normal(N_A)
f2 = rng.standard_normal(N_A)
E = rng.standard_normal((N_A, P_A))
Xa = standardize(np.column_stack([
    f1 + 0.45 * E[:, 0],                      # v1: factor-1 group
    f1 + 0.45 * E[:, 1],                      # v2: factor-1 group (corr .85 w/ v1)
    0.6 * f1 + 0.6 * f2 + 0.6 * E[:, 2],      # v3: bridge between both groups
    f2 + 0.7 * E[:, 3],                       # v4: factor-2 group
    0.5 * f2 + 0.9 * E[:, 4],                 # v5: factor-2 group, weaker
    0.3 * f1 + E[:, 5],                       # v6: mostly independent
]))
ya = Xa @ BETA_TRUE_A + 0.75 * rng.standard_normal(N_A)
ya = ya - ya.mean()

knots_lar = lars(Xa, ya, lasso=False)
knots_lasso = lars(Xa, ya, lasso=True)
arcs_lar = arc_of(knots_lar)
arcs_lasso = arc_of(knots_lasso)
ols_a = np.linalg.lstsq(Xa, ya, rcond=None)[0]

# ----------------------------------------------------------------------------
# Self-checks
# ----------------------------------------------------------------------------
print("=" * 72)
print("SELF-CHECKS (dataset A)")
print("=" * 72)

def check_ties(knots, label):
    worst_tie, worst_inact = 0.0, -np.inf
    for k in knots:
        if not k["active"]:
            continue
        c = Xa.T @ (ya - Xa @ k["beta"])
        cabs = np.abs(c)
        tied = cabs[k["active"]]
        worst_tie = max(worst_tie, float(np.ptp(tied)))
        inactive = [j for j in range(P_A) if j not in k["active"]]
        if inactive:
            worst_inact = max(worst_inact, float(cabs[inactive].max() - tied.max()))
    assert worst_tie < 1e-8, f"{label}: active correlations not tied ({worst_tie})"
    assert worst_inact < 1e-8, f"{label}: inactive correlation exceeds tie ({worst_inact})"
    print(f"(a) {label}: max tie spread among active |c_j| at knots = {worst_tie:.3e}  (< 1e-8)")
    print(f"(b) {label}: max (inactive |c_j| - tied C) at knots     = {worst_inact:.3e}  (<= ~0)")

check_ties(knots_lar, "LAR  ")
check_ties(knots_lasso, "lasso")

end_diff_lar = np.abs(knots_lar[-1]["beta"] - ols_a).max()
end_diff_lasso = np.abs(knots_lasso[-1]["beta"] - ols_a).max()
assert end_diff_lar < 1e-8 and end_diff_lasso < 1e-8
print(f"(c) endpoint vs numpy lstsq OLS: LAR diff = {end_diff_lar:.3e}, "
      f"lasso diff = {end_diff_lasso:.3e}  (< 1e-8)")

drop_knots = [(i, k) for i, k in enumerate(knots_lasso) if k["event"].startswith("drop")]
assert len(drop_knots) >= 1, "no drop event on lasso path"
i_drop, k_drop = drop_knots[0]
j_drop = int(k_drop["event"].split(":")[1])
i_re = next(i for i in range(i_drop + 1, len(knots_lasso))
            if abs(knots_lasso[i]["beta"][j_drop]) > 1e-9)
print(f"(d) lasso drop events: {[k['event'] for _, k in drop_knots]} -> "
      f"{NAMES_A[j_drop]} dropped at arc {arcs_lasso[i_drop]:.3f} "
      f"(lambda = {k_drop['C']:.4f}), re-enters at arc {arcs_lasso[i_re - 1]:.3f} "
      f"with sign {np.sign(knots_lasso[i_re]['beta'][j_drop]):+.0f}")

# (e) cross-check against coordinate descent at 3 interior lambdas:
#     one mid-hump (before the drop), one inside the flat/dropped stretch,
#     one after re-entry.
Cs = [k["C"] for k in knots_lasso]
seg_choices = [max(1, i_drop - 2), i_drop, i_re - 1]
print("(e) coordinate-descent cross-check on lasso path:")
for seg in seg_choices:
    lam = 0.5 * (Cs[seg] + Cs[seg + 1])
    t = (Cs[seg] - lam) / (Cs[seg] - Cs[seg + 1])
    b_path = knots_lasso[seg]["beta"] + t * (knots_lasso[seg + 1]["beta"] - knots_lasso[seg]["beta"])
    b_cd = cd_lasso(Xa, ya, lam)
    diff = np.abs(b_path - b_cd).max()
    assert diff < 1e-4, f"CD mismatch at lambda={lam}: {diff}"
    print(f"    lambda = {lam:8.5f} (segment {seg}->{seg+1}): "
          f"max |beta_path - beta_cd| = {diff:.3e}  (< 1e-4)")

# ----------------------------------------------------------------------------
# Dense grids for dataset A (~200 points along L1 arc + exact knot locations)
# ----------------------------------------------------------------------------

def dense_block(knots, arcs, n_grid=200):
    arcs = np.asarray(arcs)
    B = np.array([k["beta"] for k in knots])              # (K, p)
    grid = np.union1d(np.linspace(0.0, arcs[-1], n_grid), arcs)
    betas = np.column_stack([np.interp(grid, arcs, B[:, j]) for j in range(B.shape[1])])
    corrs = (Xa.T @ (ya[:, None] - Xa @ betas.T)).T        # (G, p) signed
    return dict(
        arc=grid.tolist(),
        betas=[betas[:, j].tolist() for j in range(B.shape[1])],
        corrs=[corrs[:, j].tolist() for j in range(B.shape[1])],
        cmax=np.abs(corrs).max(axis=1).tolist(),
    )

dense_lar = dense_block(knots_lar, arcs_lar)
dense_lasso = dense_block(knots_lasso, arcs_lasso)


def knots_json(knots, arcs):
    return [dict(
        arc_l1=a,
        betas=k["beta"].tolist(),
        corr_abs=float(k["C"]),
        active=[NAMES_A[j] for j in k["active"]],
        event=k["event"] if ":" not in k["event"]
        else k["event"].split(":")[0] + ":" + NAMES_A[int(k["event"].split(":")[1])],
    ) for a, k in zip(arcs, knots)]


# ----------------------------------------------------------------------------
# Dataset B: p=2 geometry
# ----------------------------------------------------------------------------

SEED_B = 7
N_B = 50
rng_b = np.random.default_rng(SEED_B)
z1 = rng_b.standard_normal(N_B)
z2 = rng_b.standard_normal(N_B)
Xb = standardize(np.column_stack([z1, 0.5 * z1 + np.sqrt(1 - 0.25) * z2]))
BETA_TRUE_B = np.array([1.2, 0.7])
yb = Xb @ BETA_TRUE_B + 0.30 * rng_b.standard_normal(N_B)
yb = yb - yb.mean()

corr_b = float(Xb[:, 0] @ Xb[:, 1])            # unit-norm, mean-0 -> correlation
knots_b = lars(Xb, yb, lasso=False)
arcs_b = arc_of(knots_b)
ols_b = np.linalg.lstsq(Xb, yb, rcond=None)[0]
assert np.abs(knots_b[-1]["beta"] - ols_b).max() < 1e-8

# Orthonormal basis of span{x1, x2}; all geometry reported in these 2D coords.
e1 = Xb[:, 0]
x2_perp = Xb[:, 1] - (Xb[:, 1] @ e1) * e1
e2 = x2_perp / np.linalg.norm(x2_perp)
to2d = lambda v: [float(v @ e1), float(v @ e2)]

y_proj = (yb @ e1) * e1 + (yb @ e2) * e2       # projection of y on the fit plane

# First LAR step: mu moves along s1 * x_{j1}; second: along equiangular u2.
c0 = Xb.T @ yb
j_first = int(np.argmax(np.abs(c0)))
s_first = float(np.sign(c0[j_first]))
mu1 = Xb @ knots_b[1]["beta"]                  # fit vector at knot 1
c1 = Xb.T @ (yb - mu1)
s_b = np.sign(c1)
Xab = Xb * s_b
Gb = Xab.T @ Xab
Ginv1b = np.linalg.solve(Gb, np.ones(2))
u2 = Xab @ (Ginv1b / np.sqrt(Ginv1b.sum()))    # equiangular unit vector

# check u2 makes equal angles with the signed active predictors
angles = Xab.T @ u2
assert np.ptp(angles) < 1e-10

segments = []
mu_pts = [np.zeros(N_B)] + [Xb @ k["beta"] for k in knots_b[1:]]
for si in range(len(mu_pts) - 1):
    alpha = np.linspace(0.0, 1.0, 100)
    mus = np.outer(1 - alpha, mu_pts[si]) + np.outer(alpha, mu_pts[si + 1])
    coords = np.column_stack([mus @ e1, mus @ e2])
    segments.append(dict(
        from_knot=si, to_knot=si + 1,
        alpha=alpha.tolist(),
        mu_x=coords[:, 0].tolist(),
        mu_y=coords[:, 1].tolist(),
    ))

print("-" * 72)
print("Dataset B geometry")
print(f"    empirical corr(x1, x2) = {corr_b:.4f}")
print(f"    first variable entered: x{j_first+1} (sign {s_first:+.0f})")
for a, k in zip(arcs_b, knots_b):
    print(f"    knot arc={a:7.4f} C={k['C']:.4f} beta={np.round(k['beta'], 4)} ev={k['event']}")
print(f"    OLS beta = {np.round(ols_b, 4)}")
print(f"    y_proj 2D = {np.round(to2d(y_proj), 4)}, x2 2D = {np.round(to2d(Xb[:,1]), 4)}, "
      f"u2 2D = {np.round(to2d(u2), 4)}")

# ----------------------------------------------------------------------------
# df Monte Carlo (Viz 4): fixed X = dataset A design, sigma known.
# Separate RNG stream -> all dataset A/B values above are untouched.
# ----------------------------------------------------------------------------
from itertools import combinations

SIGMA_DF = 0.75
B_DF = 1000
N_BATCH = 10
rng_df = np.random.default_rng(1607)
MU_TRUE = Xa @ BETA_TRUE_A                              # fixed true mean (N_A,)
Y_REP = MU_TRUE[:, None] + SIGMA_DF * rng_df.standard_normal((N_A, B_DF))

# Hat matrices for every non-empty subset of the 6 columns (63 total)
subsets_by_k = {k: list(combinations(range(P_A), k)) for k in range(1, P_A + 1)}
hat = {}
for k, subs in subsets_by_k.items():
    for S in subs:
        Xs = Xa[:, S]
        hat[S] = Xs @ np.linalg.solve(Xs.T @ Xs, Xs.T)

fits_lar = np.zeros((P_A, N_A, B_DF))
fits_best = np.zeros((P_A, N_A, B_DF))
fits_fixed = np.zeros((P_A, N_A, B_DF))

# (c) prespecified nested subsets in fixed index order {v1}, {v1,v2}, ...
for k in range(1, P_A + 1):
    fits_fixed[k - 1] = hat[tuple(range(k))] @ Y_REP

# (b) best subset of size k: exhaustive by RSS, OLS refit
for k in range(1, P_A + 1):
    best_rss = np.full(B_DF, np.inf)
    for S in subsets_by_k[k]:
        HY = hat[S] @ Y_REP
        rss = ((Y_REP - HY) ** 2).sum(axis=0)
        better = rss < best_rss
        fits_best[k - 1][:, better] = HY[:, better]
        best_rss = np.minimum(best_rss, rss)

# (a) LAR stopped after k steps: fit vector at the k-th knot
for b in range(B_DF):
    kn = lars(Xa, Y_REP[:, b], lasso=False)
    for k in range(1, P_A + 1):
        fits_lar[k - 1][:, b] = Xa @ kn[min(k, len(kn) - 1)]["beta"]


def df_batches(fits_k):
    """df = (1/sigma^2) sum_i Cov_b(yhat_i, y_i); mean +/- SE over 10 batches."""
    bs = B_DF // N_BATCH
    vals = []
    for m in range(N_BATCH):
        sl = slice(m * bs, (m + 1) * bs)
        Yb, Fb = Y_REP[:, sl], fits_k[:, sl]
        cov = ((Fb - Fb.mean(axis=1, keepdims=True))
               * (Yb - Yb.mean(axis=1, keepdims=True))).sum(axis=1) / (bs - 1)
        vals.append(cov.sum() / SIGMA_DF ** 2)
    vals = np.array(vals)
    return float(vals.mean()), float(vals.std(ddof=1) / np.sqrt(N_BATCH))


df_lar, df_lar_se = zip(*(df_batches(fits_lar[k - 1]) for k in range(1, P_A + 1)))
df_best, df_best_se = zip(*(df_batches(fits_best[k - 1]) for k in range(1, P_A + 1)))
df_fixed, df_fixed_se = zip(*(df_batches(fits_fixed[k - 1]) for k in range(1, P_A + 1)))

print("-" * 72)
print(f"df Monte Carlo (B = {B_DF}, sigma = {SIGMA_DF}, {N_BATCH} batches)")
print(f"{'k':>3} {'LAR':>8} {'+/-':>6} {'best':>8} {'+/-':>6} {'fixed':>8} {'+/-':>6}")
for i, k in enumerate(range(1, P_A + 1)):
    print(f"{k:>3} {df_lar[i]:8.3f} {df_lar_se[i]:6.3f} "
          f"{df_best[i]:8.3f} {df_best_se[i]:6.3f} "
          f"{df_fixed[i]:8.3f} {df_fixed_se[i]:6.3f}")

for i, k in enumerate(range(1, P_A + 1)):
    assert abs(df_fixed[i] - k) < 3 * df_fixed_se[i], \
        f"fixed-subset df not within 3 SE of k={k}: {df_fixed[i]} +/- {df_fixed_se[i]}"
    assert abs(df_lar[i] - k) < 3 * df_lar_se[i], \
        f"LAR df not within 3 SE of k={k}: {df_lar[i]} +/- {df_lar_se[i]}"
for i, k in enumerate(range(1, 5)):
    assert df_best[i] > k, f"best-subset df not above k={k}: {df_best[i]}"
print("df_mc assertions passed: fixed ~ k, LAR ~ k (3 SE), best > k for k=1..4")

df_mc = {
    "k": list(range(1, P_A + 1)),
    "lar": list(df_lar), "lar_se": list(df_lar_se),
    "best": list(df_best), "best_se": list(df_best_se),
    "fixed": list(df_fixed), "fixed_se": list(df_fixed_se),
    "B": B_DF, "sigma": SIGMA_DF,
    "note": ("df_k = (1/sigma^2) sum_i Cov_b(yhat_i, y_i) across B replicate y draws "
             "(fixed X = dataset A design, true beta, sigma known); "
             "SE from 10 batches of 100 replicates"),
}

# ----------------------------------------------------------------------------
# JSON assembly
# ----------------------------------------------------------------------------

def r8(obj):
    """Round every float to 8 significant digits, recursively."""
    if isinstance(obj, float):
        return float(f"{obj:.8g}")
    if isinstance(obj, list):
        return [r8(v) for v in obj]
    if isinstance(obj, dict):
        return {k: r8(v) for k, v in obj.items()}
    return obj

data = {
    "meta": {
        "seed_A": SEED_A, "seed_B": SEED_B,
        "N_A": N_A, "p_A": P_A, "N_B": N_B, "p_B": 2,
        "standardization": "columns mean 0, unit L2 norm (ESL Alg 3.2 step 1); y centered",
        "corr_note": "corrs are inner products x_j' r (LARS 'correlations'); corr_abs = C = lambda",
    },
    "datasetA": {
        "names": NAMES_A,
        "true_beta": BETA_TRUE_A.tolist(),
        "ols_beta": ols_a.tolist(),
        "knots_lar": knots_json(knots_lar, arcs_lar),
        "knots_lasso": knots_json(knots_lasso, arcs_lasso),
        "dense_lar": dense_lar,
        "dense_lasso": dense_lasso,
        "drop": {
            "var": NAMES_A[j_drop],
            "arc_l1": arcs_lasso[i_drop],
            "lambda": float(k_drop["C"]),
            "reenter_arc_l1": arcs_lasso[i_re - 1],
        },
    },
    "datasetB": {
        "names": ["x1", "x2"],
        "corr_x1x2": corr_b,
        "true_beta": BETA_TRUE_B.tolist(),
        "ols_beta": ols_b.tolist(),
        "first_var": f"x{j_first+1}",
        "first_sign": s_first,
        "knots": [dict(
            arc_l1=a, betas=k["beta"].tolist(), corr_abs=float(k["C"]),
            active=[f"x{j+1}" for j in k["active"]],
        ) for a, k in zip(arcs_b, knots_b)],
        "coords": {
            "basis_note": "2D coords in orthonormal basis (e1 = x1, e2 = x2 orthogonalized)",
            "x1": to2d(Xb[:, 0]),
            "x2": to2d(Xb[:, 1]),
            "y_proj": to2d(y_proj),
            "u2": to2d(u2),
            "mu_knot1": to2d(mu1),
        },
        "segments": segments,
    },
    "df_mc": df_mc,
}

with open(OUT, "w") as fh:
    json.dump(r8(data), fh, separators=(",", ":"))

size = os.path.getsize(OUT)
print("-" * 72)
print(f"Wrote {OUT}")
print(f"JSON size: {size} bytes ({size/1024:.1f} KB)")
print(f"dense grid points: LAR={len(dense_lar['arc'])}, lasso={len(dense_lasso['arc'])}")
print("ALL SELF-CHECKS PASSED")
