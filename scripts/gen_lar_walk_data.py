"""Generate 3D response-space 'walk' data for the LAR concept page (ESL 3.4.4).

Everything is computed in span(x1,x2,x3) with an orthonormal basis, so the
scene is exactly 3D. Inner products x_j'(y - mu) equal x_j'(yhat - mu)
because the out-of-span residual component is orthogonal to every predictor,
so all correlations/ties/knots are exact. The drawn residual is the in-span
component (footnoted on the page).

Walkers, all from 0 to yhat (the OLS projection):
  - LAR        : piecewise linear, equiangular directions (Algorithm 3.2)
  - lasso      : LAR + drop rule 4a (Algorithm 3.2a)
  - stepwise   : greedy hops through intermediate projections
  - stagewise  : FS_eps crumbs (Algorithm 3.4 with fixed eps)
  - ridge      : mu(lambda) = X (G + lambda I)^-1 X' yhat, lambda inf -> 0

Counter-example data: at knot 1 (first tie), three candidate directions
(keep along x1 / switch to x2 / equiangular) with the resulting c1(t), c2(t)
showing that only the equiangular direction preserves the tie.

Self-checks are asserted; the script fails loudly rather than emitting bad data.
"""

import json
import numpy as np

OUT = "/tmp/claude-1000/-home-godli-textparse/f97dd12f-a8a2-4826-9fa7-519818afcaea/scratchpad/lar-walk-data.json"
TOL = 1e-9


# ---------------------------------------------------------------- LAR / lasso

def lar_path(X, yhat, lasso=False):
    """Exact LARS knots in the 3D representation. X columns unit-norm."""
    p = X.shape[1]
    beta = np.zeros(p)
    knots = [{"beta": beta.copy(), "event": "start"}]
    active, signs = [], {}
    for _ in range(40):
        c = X.T @ (yhat - X @ beta)
        C = np.max(np.abs(c))
        if C < 1e-12:
            break
        if not active:
            j = int(np.argmax(np.abs(c)))
            active = [j]
            signs = {j: np.sign(c[j])}
            knots[-1]["event"] = f"add:{j}"
        Xa = X[:, active]
        sa = np.array([signs[j] for j in active])
        # equiangular direction in coefficient space (signed LS on active set)
        Ga = Xa.T @ Xa
        w = np.linalg.solve(Ga, sa)
        A = 1.0 / np.sqrt(sa @ w)
        w = A * w                      # coefficient increments (signed)
        u = Xa @ w                     # unit fit direction, equal angle with all active
        a = X.T @ u
        # step length to next entry
        gammas = []
        for j in range(p):
            if j in active:
                continue
            for g in [(C - c[j]) / (A - a[j]), (C + c[j]) / (A + a[j])]:
                if g > TOL:
                    gammas.append((g, j))
        gamma, j_next = min(gammas) if gammas else (C / A, None)
        drop_j = None
        if lasso:
            # drop check: active beta hitting zero
            for idx, j in enumerate(active):
                d = w[idx]
                if abs(d) > TOL:
                    g = -beta[j] / d
                    if TOL < g < gamma - TOL:
                        gamma, drop_j = g, j
                        j_next = None
        new_beta = beta.copy()
        for idx, j in enumerate(active):
            new_beta[j] += gamma * w[idx]
        beta = new_beta
        if drop_j is not None:
            beta[drop_j] = 0.0
            active = [j for j in active if j != drop_j]
            del signs[drop_j]
            knots.append({"beta": beta.copy(), "event": f"drop:{drop_j}"})
        elif j_next is not None:
            active.append(j_next)
            c2 = X.T @ (yhat - X @ beta)
            signs[j_next] = np.sign(c2[j_next])
            knots.append({"beta": beta.copy(), "event": f"add:{j_next}"})
        else:
            knots.append({"beta": beta.copy(), "event": "end"})
            break
    return knots


def check_ties(X, yhat, knots):
    """At every knot the active-set |inner products| must be tied and maximal."""
    worst = 0.0
    for k in range(1, len(knots)):
        beta = knots[k]["beta"]
        c = np.abs(X.T @ (yhat - X @ beta))
        C = c.max()
        if C < 1e-10:
            continue
        nz_between = set()
        for kk in (k, k - 1):
            ev = knots[kk]["event"]
            if ev.startswith("add:"):
                nz_between.add(int(ev.split(":")[1]))
        act = [j for j in range(len(beta)) if abs(beta[j]) > TOL] + list(nz_between)
        tied = [j for j in set(act) if c[j] > 1e-10]
        if tied:
            worst = max(worst, float(np.max(np.abs(c[tied] - C))))
    return worst


# ------------------------------------------------------------- other walkers

def stepwise_path(X, yhat):
    """Greedy forward stepwise: full LS refit after each entry -> hop targets."""
    p = X.shape[1]
    active = []
    pts = [np.zeros(3)]
    order = []
    mu = np.zeros(3)
    for _ in range(p):
        c = X.T @ (yhat - mu)
        j = int(np.argmax(np.abs(c)))
        active.append(j)
        order.append(j)
        Xa = X[:, active]
        beta_a = np.linalg.lstsq(Xa, yhat, rcond=None)[0]
        mu = Xa @ beta_a
        pts.append(mu.copy())
    return np.array(pts), order


def stagewise_path(X, yhat, eps):
    """FS_eps: mu += eps * sign(c_j) * x_j for the most-correlated j.

    With a fixed step the walk cannot enter the ~eps-ball around yhat without
    oscillating, so stop once inside 1.2*eps of the target (ESL: FS_eps ends
    "when the correlations are all small" — the ball radius shrinks with eps).
    """
    mu = np.zeros(3)
    pts = [mu.copy()]
    for _ in range(2000):
        if np.linalg.norm(yhat - mu) < 1.2 * eps:
            break
        c = X.T @ (yhat - mu)
        j = int(np.argmax(np.abs(c)))
        mu = mu + eps * np.sign(c[j]) * X[:, j]
        pts.append(mu.copy())
    return np.array(pts)


def ridge_path(X, yhat, n=120):
    """mu(lambda) from lambda huge -> 0; smooth curve 0 -> yhat."""
    G = X.T @ X
    Xty = X.T @ yhat
    lams = np.concatenate([np.logspace(2.5, -3.5, n - 1), [0.0]])
    pts = [X @ np.linalg.solve(G + l * np.eye(3), Xty) for l in lams]
    return np.array(pts), lams


# ------------------------------------------------------------------- helpers

def densify(X, yhat, knots, per_seg=60):
    """Dense mu(t), inner products, |r|, arc pos along piecewise-linear path."""
    segs_mu, segs_c, segs_arc, segs_absr = [], [], [], []
    arc0 = 0.0
    for k in range(len(knots) - 1):
        b0, b1 = knots[k]["beta"], knots[k + 1]["beta"]
        seg_len = float(np.sum(np.abs(b1 - b0)))
        ts = np.linspace(0, 1, per_seg, endpoint=(k == len(knots) - 2))
        for t in ts:
            b = b0 + t * (b1 - b0)
            mu = X @ b
            r = yhat - mu
            segs_mu.append(mu)
            segs_c.append(X.T @ r)
            segs_absr.append(float(np.linalg.norm(r)))
            segs_arc.append(arc0 + t * seg_len)
        arc0 += seg_len
    return (np.array(segs_mu), np.array(segs_c),
            np.array(segs_arc), np.array(segs_absr), arc0)


def rnd(x, sig=7):
    if isinstance(x, np.ndarray):
        return [rnd(v, sig) for v in x.tolist()]
    if isinstance(x, (list, tuple)):
        return [rnd(v, sig) for v in x]
    if isinstance(x, float):
        return float(f"{x:.{sig}g}")
    return x


# ------------------------------------------------------------------- search

def build_scene(seed):
    rng = np.random.default_rng(seed)
    # Engineered for a lasso drop: x3 is a "bridge" variable, strongly
    # correlated with both x1 and x2 (which carry large positive OLS
    # coefficients), while x3's own OLS coefficient is small and negative.
    # Early in the path x3 proxies x1+x2 and enters positive; it must then
    # reverse toward its negative OLS value -> zero crossing -> drop rule.
    r12 = rng.uniform(0.15, 0.45)
    r13, r23 = rng.uniform(0.45, 0.68, 2)
    G = np.array([[1, r12, r13], [r12, 1, r23], [r13, r23, 1]])
    if np.min(np.linalg.eigvalsh(G)) < 0.12:
        return None
    L = np.linalg.cholesky(G)
    X = L.T                      # columns = coords of x1,x2,x3, X'X = G exactly
    beta_ols = np.array([rng.uniform(1.2, 2.5), rng.uniform(1.2, 2.5),
                         -rng.uniform(0.15, 0.6)])
    yhat = X @ beta_ols
    if np.linalg.norm(yhat) < 1.2:
        return None

    knots_lar = lar_path(X, yhat, lasso=False)
    if len(knots_lar) != 4:      # start + 2 more entries + end
        return None, "n_knots"
    order = [int(k["event"].split(":")[1]) for k in knots_lar[:-1] if k["event"].startswith("add")]
    if len(order) != 3:
        return None, "order_len"
    # relabel predictors so entry order becomes 0,1,2
    perm = np.array(order)
    X = X[:, perm]
    G = X.T @ X
    beta_ols = beta_ols[perm]
    knots_lar = lar_path(X, yhat, lasso=False)
    knots_lasso = lar_path(X, yhat, lasso=True)
    # need a genuine lasso drop
    if not any(k["event"].startswith("drop") for k in knots_lasso):
        return None, "no_drop"
    # well-spaced knots
    arcs = np.cumsum([0] + [np.sum(np.abs(knots_lar[i + 1]["beta"] - knots_lar[i]["beta"]))
                            for i in range(len(knots_lar) - 1)])
    total = arcs[-1]
    if np.min(np.diff(arcs)) < 0.15 * total:
        return None, "knot_spacing"
    # readable geometry: pairwise angles between predictors 40-82 deg
    angs = [np.degrees(np.arccos(abs(G[i, j]))) for i, j in [(0, 1), (0, 2), (1, 2)]]
    if min(angs) < 40 or max(angs) > 82:
        return None, "angles"
    return dict(G=G, X=X, beta_ols=beta_ols, yhat=yhat,
                knots_lar=knots_lar, knots_lasso=knots_lasso, seed=seed), "ok"


scene = None
from collections import Counter
reasons = Counter()
for seed in range(50000):
    res = build_scene(seed)
    if res is None or not isinstance(res, tuple):
        reasons["gram_or_norm"] += 1
        continue
    scene, why = res
    reasons[why] += 1
    if scene:
        break
print("search stats:", dict(reasons))
assert scene, "no scene found"
X, yhat, G = scene["X"], scene["yhat"], scene["G"]
knots_lar, knots_lasso = scene["knots_lar"], scene["knots_lasso"]
print(f"seed {scene['seed']}  corr: r12={G[0,1]:.3f} r13={G[0,2]:.3f} r23={G[1,2]:.3f}")
print("beta_ols:", np.round(scene["beta_ols"], 3), " |yhat|:", round(float(np.linalg.norm(yhat)), 3))
print("lar events:  ", [k["event"] for k in knots_lar])
print("lasso events:", [k["event"] for k in knots_lasso])

# ------------------------------------------------------------------- checks
tie_lar = check_ties(X, yhat, knots_lar)
tie_lasso = check_ties(X, yhat, knots_lasso)
end_lar = float(np.linalg.norm(X @ knots_lar[-1]["beta"] - yhat))
end_lasso = float(np.linalg.norm(X @ knots_lasso[-1]["beta"] - yhat))
assert tie_lar < 1e-8 and tie_lasso < 1e-8, (tie_lar, tie_lasso)
assert end_lar < 1e-8 and end_lasso < 1e-8, (end_lar, end_lasso)
print(f"tie spread: lar {tie_lar:.1e} lasso {tie_lasso:.1e}; endpoint err {end_lar:.1e}/{end_lasso:.1e}")

# stepwise
step_pts, step_order = stepwise_path(X, yhat)
assert np.linalg.norm(step_pts[-1] - yhat) < 1e-8
# stagewise
eps = 0.02 * float(np.linalg.norm(yhat))
stage_pts = stagewise_path(X, yhat, eps)
stage_end_err = float(np.linalg.norm(stage_pts[-1] - yhat))
assert stage_end_err < 2.0 * eps, stage_end_err
assert len(stage_pts) < 1000, len(stage_pts)
print(f"stepwise order {step_order}; stagewise pts {len(stage_pts)} end err {stage_end_err:.3f} (~eps-ball, eps={eps:.3f})")
# ridge
ridge_pts, lams = ridge_path(X, yhat)
assert np.linalg.norm(ridge_pts[-1] - yhat) < 1e-10

# dense walks
mu_lar, c_lar, arc_lar, absr_lar, total_lar = densify(X, yhat, knots_lar)
mu_las, c_las, arc_las, absr_las, total_las = densify(X, yhat, knots_lasso)

# angles theta_j(t) between in-span residual and each predictor (degrees)
def angles(c_arr, absr_arr):
    with np.errstate(invalid="ignore", divide="ignore"):
        cosv = np.abs(c_arr) / np.maximum(absr_arr[:, None], 1e-12)
    return np.degrees(np.arccos(np.clip(cosv, 0, 1)))

th_lar = angles(c_lar, absr_lar)

# ------------------------------------------------- counter-example at knot 1
b1 = knots_lar[1]["beta"]           # tie moment: x2 just caught up
mu1 = X @ b1
c1v = X.T @ (yhat - mu1)
s = np.sign(c1v[:2])
Ga = G[:2, :2]
w = np.linalg.solve(Ga, s)
A = 1.0 / np.sqrt(s @ w)
u_eq = X[:, :2] @ (A * w)           # equiangular (unit)
dirs = {
    "keep_x1": np.sign(c1v[0]) * X[:, 0],
    "switch_x2": np.sign(c1v[1]) * X[:, 1],
    "equiangular": u_eq,
}
ce = {}
T = np.linspace(0, 0.55 * float(np.linalg.norm(yhat - mu1)), 60)
for name, d in dirs.items():
    mus = mu1[None, :] + T[:, None] * d[None, :]
    cs = (yhat[None, :] - mus) @ X
    ce[name] = {"t": rnd(T), "mu": rnd(mus), "c1": rnd(np.abs(cs[:, 0])),
                "c2": rnd(np.abs(cs[:, 1])), "dir": rnd(d)}
gap_eq = float(np.max(np.abs(ce["equiangular"]["c1"][i] - ce["equiangular"]["c2"][i]) for i in range(len(T))) ) if False else \
         float(np.max(np.abs(np.array(ce["equiangular"]["c1"]) - np.array(ce["equiangular"]["c2"]))))
gap_x1 = float(np.max(np.abs(np.array(ce["keep_x1"]["c1"]) - np.array(ce["keep_x1"]["c2"]))))
assert gap_eq < 1e-7 and gap_x1 > 0.05, (gap_eq, gap_x1)
print(f"counter-example: equiangular tie gap {gap_eq:.1e}; keep-x1 splits to {gap_x1:.3f}")

# ------------------------------------------------------------------- output
data = {
    "meta": {
        "seed": scene["seed"],
        "note": ("3D coords = orthonormal basis of span(x1,x2,x3); inner products with the "
                 "in-span residual equal the true LARS inner products exactly (out-of-span "
                 "residual component is orthogonal to all predictors)."),
        "corr": {"r12": rnd(float(G[0, 1])), "r13": rnd(float(G[0, 2])), "r23": rnd(float(G[1, 2]))},
    },
    "scene": {
        "x": rnd(X.T),                       # rows = predictor unit vectors
        "yhat": rnd(yhat),
        "beta_ols": rnd(scene["beta_ols"]),
    },
    "lar": {
        "knots": [{"beta": rnd(k["beta"]), "event": k["event"],
                   "arc": rnd(float(np.sum([np.sum(np.abs(knots_lar[i+1]['beta']-knots_lar[i]['beta']))
                                            for i in range(j)])))}
                  for j, k in enumerate(knots_lar)],
        "mu": rnd(mu_lar), "c": rnd(c_lar), "arc": rnd(arc_lar),
        "absr": rnd(absr_lar), "theta": rnd(th_lar), "total_arc": rnd(total_lar),
    },
    "lasso": {
        "knots": [{"beta": rnd(k["beta"]), "event": k["event"]} for k in knots_lasso],
        "mu": rnd(mu_las), "arc": rnd(arc_las), "total_arc": rnd(total_las),
    },
    "stepwise": {"pts": rnd(step_pts), "order": step_order},
    "stagewise": {"pts": rnd(stage_pts), "eps": rnd(eps)},
    "ridge": {"pts": rnd(ridge_pts), "lambda": rnd(lams)},
    "counterexample": {"mu1": rnd(mu1), "beta1": rnd(b1), "C_at_tie": rnd(float(np.abs(c1v[0]))), **ce},
}
with open(OUT, "w") as f:
    json.dump(data, f, separators=(",", ":"))
import os
print("wrote", OUT, os.path.getsize(OUT), "bytes")
