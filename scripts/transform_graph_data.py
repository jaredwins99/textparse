#!/usr/bin/env python3
"""Transform graph-data.js: add tier fields to Ch3 nodes and fix casing for all concept names."""
import json

INPUT = '/home/godli/textparse/output/knowledge-graph/graph-data.js'

with open(INPUT) as f:
    content = f.read()

prefix = 'const GRAPH_DATA = '
json_str = content[len(prefix):]
json_str = json_str.rstrip().rstrip(';')
data = json.loads(json_str)

# ─── TIER MAPPING for Ch3 nodes ───
tier1_exact = {'lasso', 'ridge regression', 'multicollinearity', 'collinearity',
               'best subset selection', 'gauss-markov theorem'}
tier1_contains = ['bias-variance tradeoff', 'cross-validation', 'model selection']

tier2_exact = {'forward stepwise selection', 'backward stepwise selection',
               'principal components regression', 'partial least squares',
               'elastic net', 'orthogonal projection'}
tier2_contains = ['multiple regression', 'mse decomposition', 'mean squared error decomposition', 'svd']

tier3_contains = ['qr decomposition', 'gram-schmidt', 'least angle regression',
                  'forward stagewise regression', 'degrees of freedom', 'aic criterion',
                  'canonical correlation analysis', 'f-statistic', 'f statistic',
                  'variance-covariance matrix', 'reduced-rank regression', 'reduced rank regression']

tier4_contains = ['scad penalty', 'curds and whey', 'dantzig selector',
                  'grouped lasso', 'relaxed lasso', 'adaptive lasso',
                  'l2boost', 'homotopy algorithm', 'basis pursuit',
                  'l1 arc length', 'piecewise-linear solution path', 'piecewise linear solution path',
                  'soft thresholding', 'soft-thresholding',
                  'z-score', 'pathwise coordinate descent',
                  'incremental forward stagewise', 'infinitesimal forward stagewise',
                  'lar-lasso connection', 'lar lasso connection']


def get_tier(name_lower):
    """Determine tier for a Ch3 concept."""
    # Tier 4 first (more specific matches like "grouped lasso" before "lasso")
    for pat in tier4_contains:
        if pat in name_lower:
            return 4
    for pat in tier3_contains:
        if pat in name_lower:
            return 3
    if name_lower in tier2_exact:
        return 2
    for pat in tier2_contains:
        if pat in name_lower:
            return 2
    if name_lower in tier1_exact:
        return 1
    for pat in tier1_contains:
        if pat in name_lower:
            return 1
    return 3  # default for Ch3


# ─── TITLE CASE ───
ACRONYMS = {'QR', 'SVD', 'AIC', 'MSE', 'PLS', 'PCR', 'LAR', 'SCAD', 'LDA', 'FDA',
             'MARS', 'GEM', 'MM', 'SVM', 'KKT', 'RBF', 'HME', 'SOM', 'BH', 'SAM',
             'LVQ1', 'LVQ2', 'LVQ3', 'ARD', 'EM', 'MDS', 'ICA', 'NMF', 'ROC', 'PRIM', 'ANOVA'}

RENAMES = {
    'multicollinearity': 'Collinearity',
    'f-statistic for nested models': 'F Statistic',
    'z-score for regression coefficients': 'Z-Score Regression',
    'variance-covariance matrix of least squares estimates': 'Variance-Covariance Matrix',
    'multiple regression coefficient interpretation': 'Multiple Regression Interpretation',
    'mean squared error decomposition': 'MSE Decomposition',
    'bias-variance tradeoff in model selection': 'Bias-Variance Tradeoff',
    'degrees of freedom for adaptive fit': 'Degrees of Freedom',
    'gram-schmidt orthogonalization': 'Gram-Schmidt',
    'lar-lasso connection': 'LAR-Lasso Connection',
    'leaps and bounds procedure': 'Leaps and Bounds',
    'piecewise-linear solution path': 'Piecewise Linear Solution Path',
    'soft-thresholding operator': 'Soft Thresholding Operator',
    'reduced-rank regression': 'Reduced Rank Regression',
    'l2boost': 'L2Boost',
    'l1 arc length': 'L1 Arc Length',
    'aic criterion': 'AIC Criterion',
    'scad penalty': 'SCAD Penalty',
    'elastic net penalty': 'Elastic Net Penalty',
    'elastic net': 'Elastic Net',
    'elastic net for sparse pca': 'Elastic Net for Sparse PCA',
    'fda': 'FDA',
    'mars': 'MARS',
    'lasso': 'Lasso',
    'reduced-rank lda': 'Reduced-Rank LDA',
    'l1 regularized logistic regression': 'L1 Regularized Logistic Regression',
    'l1 normalized margin': 'L1 Normalized Margin',
    'svd': 'SVD',
    'scotlass': 'SCoTLASS',
    # Idempotent entries (already-renamed forms map to themselves)
    'collinearity': 'Collinearity',
    'f statistic': 'F Statistic',
    'z-score regression': 'Z-Score Regression',
    'variance-covariance matrix': 'Variance-Covariance Matrix',
    'multiple regression interpretation': 'Multiple Regression Interpretation',
    'mse decomposition': 'MSE Decomposition',
    'bias-variance tradeoff': 'Bias-Variance Tradeoff',
    'degrees of freedom': 'Degrees of Freedom',
    'gram-schmidt': 'Gram-Schmidt',
    'lar-lasso connection': 'LAR-Lasso Connection',
    'leaps and bounds': 'Leaps and Bounds',
    'piecewise linear solution path': 'Piecewise Linear Solution Path',
    'soft thresholding operator': 'Soft Thresholding Operator',
    'reduced rank regression': 'Reduced Rank Regression',
    'elastic net for sparse pca': 'Elastic Net for Sparse PCA',
    'reduced-rank lda': 'Reduced-Rank LDA',
}


SMALL_WORDS = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'from', 'if',
               'in', 'into', 'nor', 'of', 'on', 'or', 'so', 'the', 'to', 'up', 'vs', 'with'}


def title_word(word, is_first=False):
    """Title-case a single word, preserving acronyms."""
    wu = word.upper()
    if wu in ACRONYMS:
        return wu
    if len(word) >= 2 and word[0].lower() == 'l' and word[1].isdigit():
        return 'L' + word[1:]
    if word and (word[0] in '.(' or word[0].isdigit()):
        return word
    # Small words stay lowercase unless they're the first word
    if not is_first and word.lower() in SMALL_WORDS:
        return word.lower()
    return word.capitalize()


def title_case_name(name):
    """Convert a concept name to proper title case."""
    name_lower = name.lower()
    if name_lower in RENAMES:
        return RENAMES[name_lower]
    parts = name.split(' ')
    result = []
    for i, part in enumerate(parts):
        is_first = (i == 0)
        if '-' in part and not part.startswith('-'):
            hyp = part.split('-')
            result.append('-'.join(title_word(h, is_first=(is_first and j == 0)) for j, h in enumerate(hyp)))
        else:
            result.append(title_word(part, is_first=is_first))
    return ' '.join(result)


# ─── APPLY ───
ch3_tiers = {}
renamed = []
for node in data['nodes']:
    d = node['data']
    if d.get('isParent'):
        continue
    old_name = d['name']
    new_name = title_case_name(old_name)
    if old_name != new_name:
        renamed.append((old_name, new_name))
    d['name'] = new_name
    if d.get('parent') == 'ch-3':
        tier = get_tier(old_name.lower())
        d['tier'] = tier
        ch3_tiers[new_name] = tier

# ─── VERIFY ───
print("=== Ch3 Tier Assignments ===")
for tier_num in [1, 2, 3, 4]:
    names = sorted(n for n, t in ch3_tiers.items() if t == tier_num)
    print(f"\nTier {tier_num} ({len(names)} nodes):")
    for n in names:
        print(f"  {n}")

print(f"\n=== Renames ({len(renamed)} total) ===")
for old, new in renamed[:30]:
    print(f"  '{old}' -> '{new}'")
if len(renamed) > 30:
    print(f"  ... and {len(renamed) - 30} more")

# ─── WRITE ───
output = prefix + json.dumps(data, ensure_ascii=False, separators=(',', ':'))
with open(INPUT, 'w') as f:
    f.write(output)

print(f"\nDone. {len(ch3_tiers)} Ch3 nodes tiered. File written.")
