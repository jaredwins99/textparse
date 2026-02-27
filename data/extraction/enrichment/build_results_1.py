#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build results_1.json with verbatim quotes from paragraph text."""

import sqlite3
import json

conn = sqlite3.connect('/home/godli/textparse/data/textbooks.db')
cur = conn.cursor()

# All paragraph IDs needed
para_ids = [
    98, 3402, 3404, 3406,
    3410, 3422, 3424, 3427,
    3605, 3610, 3777,
    3945, 3956,
    3964, 3965, 3966, 3967, 3968, 3969, 3970, 3971,
    3979, 3986, 3990, 3992,
    4173, 4175, 4189, 4194,
    4402, 4410, 4412,
    4422, 4424, 4426, 4449, 4453,
    23504, 23508, 23535, 23547, 23551, 23553, 23556, 23558,
    24021, 24022, 24769,
    25060, 25088, 25137,
    31728, 32105, 32122, 32124,
]

paras = {}
for pid in para_ids:
    cur.execute(
        'SELECT p.text, pg.page_number FROM paragraphs p '
        'JOIN pages pg ON p.page_id = pg.id WHERE p.id = ?', (pid,)
    )
    row = cur.fetchone()
    if row:
        paras[pid] = {'text': row[0], 'page': row[1]}

conn.close()


def mk(fact_text, fact_type, rank, pid):
    t = paras[pid]['text']
    assert fact_text in t, f"fact_text not in para {pid}: {repr(fact_text[:80])}"
    return {
        "fact_text": fact_text,
        "fact_type": fact_type,
        "importance_rank": rank,
        "paragraph_id": pid,
        "page_number": paras[pid]['page']
    }


def s(pid, start_phrase, end_phrase=None):
    """Slice text from start_phrase to end of end_phrase (or just start_phrase if no end)."""
    t = paras[pid]['text']
    si = t.find(start_phrase)
    assert si >= 0, f"start phrase not found in {pid}: {repr(start_phrase)}"
    if end_phrase is None:
        return t[si:si + len(start_phrase)]
    raw_ei = t.find(end_phrase, si)
    assert raw_ei >= 0, f"end phrase not found in {pid}: {repr(end_phrase)}"
    ei = raw_ei + len(end_phrase)
    return t[si:ei]


# ============================================================
# CONCEPT 1: supervised learning (id=1)
# ============================================================
supervised_learning_facts = [
    mk(
        s(3402, 'The ', 'called supervised learning.'),
        'definition', 1, 3402
    ),
    mk(
        s(3404, 'The outputs vary in nature among the examples.', 'In both of'),
        'definition', 2, 3404
    ),
    mk(
        s(3406, 'This distinction in output type has led to a naming convention',
          'qualitative outputs.'),
        'property', 3, 3406
    ),
    mk(
        s(98, 'measurements for a set of objects', 'A good learner is one that accurately predicts such\nan outcome.'),
        'definition', 4, 98
    ),
]

# ============================================================
# CONCEPT 2: loss function (id=73)
# ============================================================
loss_function_facts = [
    mk(
        s(3964, 'This theory requires a loss\nfunction L(Y, f(X))', '(Y \u2212f(X))2.'),
        'definition', 1, 3964
    ),
    mk(
        s(3965, 'EPE(f)\n=\nE(Y ', '(2.9)'),
        'formula', 2, 3965
    ),
    mk(
        s(3968, 'and we see that it su', 'minimize EPE pointwise:'),
        'property', 3, 3968
    ),
    mk(
        s(3964, 'This leads us to a criterion for choosing f,'),
        'definition', 4, 3964
    ),
]

# ============================================================
# CONCEPT 3: squared error loss (id=74)
# ============================================================
squared_error_loss_facts = [
    mk(
        s(3971, 'the conditional expectation, also known as the regression function.',
          'best is measured by average squared error.'),
        'definition', 1, 3971
    ),
    mk(
        s(3964, 'by far the most\ncommon and convenient is squared error loss: L(Y, f(X)) = (Y '),
        'formula', 2, 3964
    ),
    mk(
        s(3971, 'The nearest-neighbor methods attempt to directly implement this recipe\nusing the training data.'),
        'property', 3, 3971
    ),
]

# ============================================================
# CONCEPT 4: absolute error loss (id=75)
# ============================================================
absolute_error_loss_facts = [
    mk(
        s(3992, 'which is a di', 'hindered their widespread use.'),
        'definition', 1, 3992
    ),
    mk(
        s(3992, 'Other more\nresistant loss functions will be mentioned in later chapters'),
        'property', 2, 3992
    ),
]

# ============================================================
# CONCEPT 5: conditional median (id=77)
# ============================================================
conditional_median_facts = [
    mk(
        s(3992, 'which is a di', 'hindered their widespread use.'),
        'definition', 1, 3992
    ),
    mk(
        s(3992, 'Other more\nresistant loss functions will be mentioned in later chapters'),
        'property', 2, 3992
    ),
]

# ============================================================
# CONCEPT 6: least squares fitting (id=80)
# ============================================================
least_squares_fitting_facts = [
    mk(
        s(3410, 'In this section we develop two simple but powerful prediction methods:',
          'k-nearest-neighbor prediction rule.'),
        'definition', 1, 3410
    ),
    mk(
        s(3410, 'The linear model makes huge assumptions about structure',
          'but can be unstable.'),
        'comparison', 2, 3410
    ),
    mk(
        s(3422, 'RSS(', 'but may not be unique.'),
        'property', 3, 3422
    ),
    mk(
        s(3424, 'where X is an N ', 'XT (y '),
        'formula', 4, 3424
    ),
]

# ============================================================
# CONCEPT 7: fitted values (id=82)
# ============================================================
fitted_values_facts = [
    mk(
        s(3427, 'and the ', 'The entire '),
        'definition', 1, 3427
    ),
]

# ============================================================
# CONCEPT 8: k-nearest neighbor averaging (id=83)
# ============================================================
knn_avg_facts = [
    mk(
        s(3605, 'Nearest-neighbor methods use those observations in the training set T',
          'for '),
        'definition', 1, 3605
    ),
    mk(
        s(3610, 'where Nk(x) is the neighborhood of x de', 'Euclidean distance.'),
        'definition', 2, 3610
    ),
    mk(
        s(3610, 'So, in words, we ', 'average their responses.'),
        'property', 3, 3610
    ),
]

# ============================================================
# CONCEPT 9: k-nearest neighbor classifier (id=84)
# ============================================================
knn_classifier_facts = [
    mk(
        s(4173, 'Again we see that the k-nearest neighbor class',
          'and probabilities are\nestimated by training-sample proportions.'),
        'property', 1, 4173
    ),
    mk(
        s(3777, 'In Figure 2.2 we see that far fewer training observations are misclass',
          'none of the training data are misclass'),
        'example', 2, 3777
    ),
]

# ============================================================
# CONCEPT 10: nearest neighbor decision boundary (id=85)
# ============================================================
nn_decision_boundary_facts = [
    mk(
        s(3945, 'The linear decision boundary from least squares is very smooth',
          'high variance and low bias.'),
        'comparison', 1, 3945
    ),
    mk(
        s(3956, 'then generated a N(mk, I/5), thus leading to a mixture of Gaussian clus-\nters for each class.',
          'We compare the results for least\nsquares and those for k-nearest neighbors for a range of values of k.'),
        'example', 2, 3956
    ),
]

# ============================================================
# CONCEPT 11: curse of dimensionality (id=86)
# ============================================================
curse_dim_facts = [
    mk(
        s(4175, 'We have examined two learning techniques for prediction so far:',
          'less stable but apparently less biased clas'),
        'comparison', 1, 4175
    ),
    mk(
        s(4189, 'FIGURE 2.6. The curse of dimensionality is well illustrated by a subcubical',
          'to capture 10% of the data.'),
        'definition', 2, 4189
    ),
    mk(
        s(4194, 'For N = 500, p = 10 , d(p, N) ', 'closer to the boundary\nof the sample space than to any other data point.'),
        'property', 3, 4194
    ),
]

# ============================================================
# CONCEPT 12: sampling density (id=87)
# ============================================================
sampling_density_facts = [
    mk(
        s(4194, 'For N = 500, p = 10 , d(p, N) ', 'closer to the boundary\nof the sample space than to any other data point.'),
        'property', 1, 4194
    ),
    mk(
        s(4189, 'FIGURE 2.6. The curse of dimensionality is well illustrated by a subcubical',
          'to capture 10% of the data.'),
        'definition', 2, 4189
    ),
]

# ============================================================
# CONCEPT 13: empty space phenomenon (id=88)
# ============================================================
empty_space_facts = [
    mk(
        s(4194, 'For N = 500, p = 10 , d(p, N) ', 'closer to the boundary\nof the sample space than to any other data point.'),
        'property', 1, 4194
    ),
    mk(
        s(4175, 'We have examined two learning techniques for prediction so far:',
          'less stable but apparently less biased clas'),
        'comparison', 2, 4175
    ),
]

# ============================================================
# CONCEPT 14: structured regression model (id=89)
# ============================================================
structured_regression_facts = [
    mk(
        s(4402, 'We have seen that although nearest-neighbor and other local methods',
          'inappropriate even in low dimensions in'),
        'definition', 1, 4402
    ),
    mk(
        s(4410, 'caused by the multiplicity of solutions. There are in', 'the ambiguity has simply\nbeen transferred to the choice of constraint.'),
        'property', 2, 4410
    ),
    mk(
        s(4412, 'The variety of nonparametric regression techniques or learning methods',
          'nature of the restrictions\nimposed.'),
        'definition', 3, 4412
    ),
]

# ============================================================
# CONCEPT 15: additive model (id=91)
# ============================================================
additive_model_facts = [
    mk(
        s(3990, 'This retains the additivity of the linear model, but each coordinate function',
          'k-nearest neighbors to approximate univariate con-\nditional expectations'),
        'definition', 1, 3990
    ),
    mk(
        s(4422, 'The roughness penalty here controls large values of the second derivative',
          'any interpolating function will do,'),
        'property', 2, 4422
    ),
    mk(
        s(3986, 'Although the latter seems more palatable', 'far more '),
        'comparison', 3, 3986
    ),
]

# ============================================================
# CONCEPT 16: radial basis function (id=103)
# ============================================================
rbf_facts = [
    mk(
        s(4449, 'where each of the hm is a function of the input x,', 'the action of the parameters '),
        'definition', 1, 4449
    ),
    mk(
        s(4453, 'for example, the Gaussian kernel K', 'Radial basis functions have centroids '),
        'formula', 2, 4453
    ),
    mk(
        s(25060, 'where each basis element is indexed by a location or prototype parameter ',
          'A popular choice for D is the standard Gaussian\ndensity function.'),
        'definition', 3, 25060
    ),
    mk(
        s(25088, 'with a basis function hi located at every observation and coe',
          'that is, '),
        'property', 4, 25088
    ),
]

# ============================================================
# CONCEPT 17: wavelet basis (id=253)
# ============================================================
wavelet_basis_facts = [
    mk(
        s(23504, 'Wavelets typically use a complete orthonormal basis to represent func-\ntions',
          'toward a sparse represen-\ntation.'),
        'definition', 1, 23504
    ),
    mk(
        s(23508, 'Wavelet bases are generated by translations and dilations of a single scal-\ning function ',
          '(also known as the father).'),
        'definition', 2, 23508
    ),
    mk(
        s(23535, 'generated by the mother wavelet ', 'form\na basis for Wj.'),
        'formula', 3, 23535
    ),
    mk(
        s(23547, 'Wavelets are particularly useful when the data are measured on a uniform\nlattice',
          'We will focus on\nthe one-dimensional case'),
        'property', 4, 23547
    ),
]

# ============================================================
# CONCEPT 18: adaptive wavelet filtering (id=255)
# ============================================================
adaptive_wavelet_facts = [
    mk(
        s(23551, 'The least squares coe', 'transform '),
        'definition', 1, 23551
    ),
    mk(
        s(23553, 'A simple choice for ', 'standard deviation of the noise.'),
        'formula', 2, 23553
    ),
    mk(
        s(23556, 'The spline L2 penalty cause pure shrinkage, while the SURE L1\npenalty does shrinkage and selection.'),
        'comparison', 3, 23556
    ),
    mk(
        s(23558, 'More generally smoothing splines achieve compression of the original signal\nby imposing smoothness',
          'while wavelets impose sparsity.'),
        'comparison', 4, 23558
    ),
]

# ============================================================
# CONCEPT 19: kernel smoother (id=256)
# ============================================================
kernel_smoother_facts = [
    mk(
        s(4424, 'These methods can be thought of as explicitly providing estimates of the re-\ngression function',
          'and of the class of regular functions'),
        'definition', 1, 4424
    ),
    mk(
        s(4426, 'weights to points x in a region around x0',
          'the Gaussian\ndensity function'),
        'definition', 2, 4426
    ),
    mk(
        s(24021, 'The smoothing parameter ', 'constant within the window).'),
        'property', 3, 24021
    ),
    mk(
        s(24022, 'Metric window widths', 'Nearest-neighbor window widths exhibit the opposite'),
        'comparison', 4, 24022
    ),
    mk(
        s(24769, 'There is a natural bias', 'which is most explicit for local averages:'),
        'property', 5, 24769
    ),
    mk(
        s(25137, 'Kernel and local regression and density estimation are memory-based meth-\nods',
          'evaluation or prediction time.'),
        'property', 6, 25137
    ),
]

# ============================================================
# CONCEPT 20: penalization method (id=426)
# ============================================================
penalization_facts = [
    mk(
        s(32105, 'where the subscript ', 'It is easy to\nshow (Exercise 12.1) that the solution to (12.25),'),
        'definition', 1, 32105
    ),
    mk(
        s(32105, 'This has the form loss +\npenalty, which is a familiar paradigm in function estimation.'),
        'definition', 2, 32105
    ),
    mk(
        s(31728, 'The role of the parameter C is clearer in an enlarged feature space,',
          'lead to an over'),
        'property', 3, 31728
    ),
    mk(
        s(32122, 'All the loss-function in Table 12.1 except squared-error are so called'),
        'property', 4, 32122
    ),
    mk(
        s(32124, 'Here we describe SVMs in terms of function estimation in reproducing\nkernel Hilbert spaces',
          'This material is\ndiscussed in some detail in Section 5.8.'),
        'definition', 5, 32124
    ),
]

# ============================================================
# Assemble results
# ============================================================
results = [
    {"concept_id": 1, "concept_name": "supervised learning", "facts": supervised_learning_facts},
    {"concept_id": 73, "concept_name": "loss function", "facts": loss_function_facts},
    {"concept_id": 74, "concept_name": "squared error loss", "facts": squared_error_loss_facts},
    {"concept_id": 75, "concept_name": "absolute error loss", "facts": absolute_error_loss_facts},
    {"concept_id": 77, "concept_name": "conditional median", "facts": conditional_median_facts},
    {"concept_id": 80, "concept_name": "least squares fitting", "facts": least_squares_fitting_facts},
    {"concept_id": 82, "concept_name": "fitted values", "facts": fitted_values_facts},
    {"concept_id": 83, "concept_name": "k-nearest neighbor averaging", "facts": knn_avg_facts},
    {"concept_id": 84, "concept_name": "k-nearest neighbor classifier", "facts": knn_classifier_facts},
    {"concept_id": 85, "concept_name": "nearest neighbor decision boundary", "facts": nn_decision_boundary_facts},
    {"concept_id": 86, "concept_name": "curse of dimensionality", "facts": curse_dim_facts},
    {"concept_id": 87, "concept_name": "sampling density", "facts": sampling_density_facts},
    {"concept_id": 88, "concept_name": "empty space phenomenon", "facts": empty_space_facts},
    {"concept_id": 89, "concept_name": "structured regression model", "facts": structured_regression_facts},
    {"concept_id": 91, "concept_name": "additive model", "facts": additive_model_facts},
    {"concept_id": 103, "concept_name": "radial basis function", "facts": rbf_facts},
    {"concept_id": 253, "concept_name": "wavelet basis", "facts": wavelet_basis_facts},
    {"concept_id": 255, "concept_name": "adaptive wavelet filtering", "facts": adaptive_wavelet_facts},
    {"concept_id": 256, "concept_name": "kernel smoother", "facts": kernel_smoother_facts},
    {"concept_id": 426, "concept_name": "penalization method", "facts": penalization_facts},
]

out_path = '/home/godli/textparse/data/extraction/enrichment/results_1.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Written {len(results)} concepts to {out_path}")
for c in results:
    print(f"  concept_id={c['concept_id']:4d} ({c['concept_name']}): {len(c['facts'])} facts")
