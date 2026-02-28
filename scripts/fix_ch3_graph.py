#!/usr/bin/env python3
"""Fix three issues with Ch3 knowledge graph:
1. Add missing concepts (Least Squares, Design Matrix, Elastic Net, SVD, Cholesky)
2. Change Ridge Regression and Lasso categories to 'estimation'
3. Write back valid JS
"""
import json

INPUT = '/home/godli/textparse/output/knowledge-graph/graph-data.js'

with open(INPUT) as f:
    content = f.read()

prefix = 'const GRAPH_DATA = '
json_str = content[len(prefix):]
json_str = json_str.rstrip().rstrip(';')
data = json.loads(json_str)

# ─── Issue 3: Change Ridge Regression and Lasso categories ───
changed = []
for node in data['nodes']:
    d = node['data']
    name_lower = (d.get('name') or '').lower()
    if name_lower == 'ridge regression' and d.get('category') != 'estimation':
        old_cat = d['category']
        d['category'] = 'estimation'
        changed.append(f"  Ridge Regression: {old_cat} -> estimation")
    elif name_lower == 'lasso' and d.get('parent') == 'ch-3' and d.get('category') != 'estimation':
        old_cat = d['category']
        d['category'] = 'estimation'
        changed.append(f"  Lasso: {old_cat} -> estimation")

print("=== Issue 3: Category changes ===")
for c in changed:
    print(c)

# ─── Issue 1: Add missing concepts ───
new_concepts = [
    {
        "data": {
            "id": "700",
            "name": "Least Squares",
            "description": "The foundational estimation method — minimizes average squared lack of fit. Linear in the parameters, not necessarily in the covariates.",
            "category": "estimation",
            "subcategory": "objective",
            "chapter": "3",
            "section": "3.2 Linear Regression Models and Least Squares",
            "parent": "ch-3",
            "tier": 1
        }
    },
    {
        "data": {
            "id": "701",
            "name": "Design Matrix",
            "description": "The N×p matrix X encoding all observations and features. The regression problem is a linear algebra problem in this matrix.",
            "category": "math",
            "subcategory": "algebra",
            "chapter": "3",
            "section": "3.2 Linear Regression Models and Least Squares",
            "parent": "ch-3",
            "tier": 3
        }
    },
    {
        "data": {
            "id": "702",
            "name": "Elastic Net",
            "description": "Combines L1 and L2 penalties. Key property: shrinks groups of correlated variables together rather than arbitrarily selecting one.",
            "category": "estimation",
            "subcategory": "optimization",
            "chapter": "3",
            "section": "3.4 Shrinkage Methods",
            "parent": "ch-3",
            "tier": 2
        }
    },
    {
        "data": {
            "id": "703",
            "name": "SVD",
            "description": "Singular Value Decomposition — decomposes the design matrix to reveal the directions of maximum variance and how ridge shrinkage operates along them.",
            "category": "math",
            "subcategory": "algebra",
            "chapter": "3",
            "section": "3.4 Shrinkage Methods",
            "parent": "ch-3",
            "tier": 2
        }
    },
    {
        "data": {
            "id": "704",
            "name": "Cholesky Decomposition",
            "description": "Computational building block for solving normal equations efficiently.",
            "category": "math",
            "subcategory": "computation",
            "chapter": "3",
            "section": "3.9 Computational Considerations",
            "parent": "ch-3",
            "tier": 4
        }
    }
]

# Check for duplicates before adding
existing_names = {(n['data'].get('name') or '').lower() for n in data['nodes']}
existing_ids = {n['data']['id'] for n in data['nodes']}

added = []
for concept in new_concepts:
    name = concept['data']['name']
    cid = concept['data']['id']
    name_lower = name.lower()

    if name_lower in existing_names:
        print(f"  SKIP (already exists): {name}")
        continue
    if cid in existing_ids:
        print(f"  SKIP (ID conflict): {cid}")
        continue

    data['nodes'].append(concept)
    added.append(name)

print(f"\n=== Issue 1: Added {len(added)} new concepts ===")
for name in added:
    print(f"  + {name}")

# ─── Verify ───
ch3_nodes = [n for n in data['nodes'] if n['data'].get('parent') == 'ch-3']
print(f"\nTotal Ch3 nodes now: {len(ch3_nodes)}")
print(f"Total nodes now: {len(data['nodes'])}")

# ─── Write ───
output = prefix + json.dumps(data, ensure_ascii=False, separators=(',', ':'))
with open(INPUT, 'w') as f:
    f.write(output)

# Verify it's valid
with open(INPUT) as f:
    verify = f.read()
verify_json = verify[len(prefix):].rstrip().rstrip(';')
json.loads(verify_json)  # Will throw if invalid
print("\nFile written and verified as valid JS/JSON.")
