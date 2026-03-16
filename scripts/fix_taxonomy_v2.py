"""Fix taxonomy v2: remove conclusions category, fix bad concepts."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "textbooks.db"


def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # === 1. Reclassify "conclusions/generalization" concepts → principles/guarantees ===
    # These are all theoretical results about prediction, bias, variance, etc.
    generalization_to_guarantees = [
        106,  # bias-variance decomposition
        177,  # bias-variance tradeoff in model selection
        298,  # boundary bias in kernel methods
        86,   # curse of dimensionality
        299,  # curse of dimensionality in local regression
        88,   # empty space phenomenon
        283,  # estimation bias
        178,  # mean squared error decomposition
        282,  # model bias
        284,  # optimism
        516,  # rate-distortion tradeoff
        135,  # squared bias
        136,  # variance of prediction
    ]
    for cid in generalization_to_guarantees:
        cur.execute("UPDATE concepts SET new_category='principles', subcategory='guarantees' WHERE id=?", (cid,))

    # overfit boundary → assessment/diagnostics (evaluating fit behavior)
    cur.execute("UPDATE concepts SET new_category='assessment', subcategory='diagnostics' WHERE id=449")

    # === 2. Reclassify "conclusions/interpretation" concepts ===

    # → assessment/diagnostics (visualization/evaluation tools)
    interpretation_to_diagnostics = [
        407,  # hinton diagrams
        375,  # partial dependence plot
        389,  # partial dependence plots
        589,  # proximity plot
        388,  # relative importance of predictor variables
        301,  # trellis display
    ]
    for cid in interpretation_to_diagnostics:
        cur.execute("UPDATE concepts SET new_category='assessment', subcategory='diagnostics' WHERE id=?", (cid,))

    # → model/proxy (model components or approaches)
    interpretation_to_proxy = [
        486,  # association rules
        3,    # bias in machine learning (intercept term in model)
        565,  # blind source separation
        381,  # main effect (component of model)
        485,  # market basket analysis
        43,   # support vectors (define the SVM model)
    ]
    for cid in interpretation_to_proxy:
        cur.execute("UPDATE concepts SET new_category='model', subcategory='proxy' WHERE id=?", (cid,))

    # → implementation/representation
    cur.execute("UPDATE concepts SET new_category='implementation', subcategory='representation' WHERE id=60")  # factor loadings

    # → principles/guarantees (theoretical insights)
    interpretation_to_guarantees = [
        175,  # multiple regression coefficient interpretation
        593,  # random forest as adaptive nearest neighbors
    ]
    for cid in interpretation_to_guarantees:
        cur.execute("UPDATE concepts SET new_category='principles', subcategory='guarantees' WHERE id=?", (cid,))

    # → implementation/computation
    cur.execute("UPDATE concepts SET new_category='implementation', subcategory='computation' WHERE id=652")  # pre-conditioning for interpretability

    # === 3. Remove bad concept: model complexity ===
    cur.execute("DELETE FROM concepts WHERE id=107")
    cur.execute("DELETE FROM concept_relationships WHERE source_id=107 OR target_id=107")
    cur.execute("DELETE FROM concept_facts WHERE concept_id=107")
    print("Removed concept 107 (model complexity)")

    # === 4. Rename bad concepts ===
    cur.execute("UPDATE concepts SET name='linearity assumption' WHERE id=90")
    print("Renamed id 90: 'linear model assumption' → 'linearity assumption'")

    cur.execute("UPDATE concepts SET name='hold-out validation' WHERE id=128")
    print("Renamed id 128: 'training set validation' → 'hold-out validation'")

    # id 280 already covers "model selection", so remove the redundant 127
    cur.execute("DELETE FROM concepts WHERE id=127")
    cur.execute("DELETE FROM concept_relationships WHERE source_id=127 OR target_id=127")
    cur.execute("DELETE FROM concept_facts WHERE concept_id=127")
    print("Removed concept 127 (model selection criterion) — redundant with 280 (model selection)")

    conn.commit()

    # === Verify ===
    remaining = cur.execute("SELECT COUNT(*) FROM concepts WHERE new_category='conclusions'").fetchone()[0]
    print(f"\nConcepts still in 'conclusions': {remaining}")

    total = cur.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
    print(f"Total concepts: {total}")

    print("\nDistribution:")
    for row in cur.execute(
        "SELECT new_category, subcategory, COUNT(*) FROM concepts "
        "WHERE new_category IS NOT NULL GROUP BY new_category, subcategory ORDER BY new_category, subcategory"
    ):
        print(f"  {row[0]}/{row[1]}: {row[2]}")

    conn.close()


if __name__ == "__main__":
    main()
