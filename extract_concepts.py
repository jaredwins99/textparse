#!/usr/bin/env python3
"""
Extract concepts and relationships from batch_6.json
"""

import json
from typing import List, Dict, Set

# Load data
with open('/home/godli/textparse/data/extraction/batch_6.json', 'r') as f:
    batch = json.load(f)

with open('/home/godli/textparse/data/extraction/existing_concepts.json', 'r') as f:
    existing = json.load(f)

# Build set of existing concept names
existing_names = {c['name'].lower() for c in existing}

print(f"Loaded {len(batch['paragraphs'])} paragraphs")
print(f"Found {len(existing_names)} existing concepts to avoid")
print("\nExisting concepts include:")
for name in sorted(list(existing_names)[:20]):
    print(f"  - {name}")

# Print section info
print("\nSections in batch 6:")
for section in batch['sections']:
    print(f"  {section['number']}: {section['title']} (page {section['page_start']})")

# Print a sample of paragraphs
print("\nSample paragraphs:")
for p in batch['paragraphs'][:5]:
    print(f"\nParagraph {p['id']} (page {p['page']}):")
    print(f"  {p['text'][:200]}...")
