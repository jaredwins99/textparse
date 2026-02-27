# Knowledge Graph Visualization Plan

## Status: Ready for Implementation

---

## Technology Decision: Cytoscape.js

**Winner: Cytoscape.js** over D3.js, vis.js, Sigma.js, and static HTML.

### Rationale

| Library | Pros | Cons | Verdict |
|---------|------|------|---------|
| **Cytoscape.js** | Purpose-built for network graphs. Compound nodes (clustering). Multiple layout algorithms built-in. Good performance at 600 nodes. Excellent selector/query API. | Slightly larger bundle (~500KB min) | **Best fit** |
| D3.js | Maximum flexibility | Enormous implementation effort for graph interactions. No built-in graph features. | Overkill |
| vis.js Network | Simple API, good defaults | Weaker clustering support. Less layout variety. Slower with 600+ nodes. | Runner-up |
| Sigma.js | WebGL, handles huge graphs | Designed for 10K+ node graphs. Fewer interaction features. Overkill for 681 nodes. | Wrong scale |
| Static HTML wiki | Simplest to build | No spatial overview of relationships. Loses the "graph" entirely. | Too limited |

Cytoscape.js wins because:
1. **Compound nodes** let us group concepts by chapter/category visually.
2. **Built-in layouts**: CoSE (Compound Spring Embedder) handles clustered graphs well. Also has concentric, breadthfirst, circle, grid.
3. **Filtering and querying**: `cy.$('[category = "method"]')` syntax makes interactive filtering trivial.
4. **600 nodes is comfortably in range** -- Cytoscape.js handles thousands of nodes in Canvas/WebGL mode.
5. **Layout extensions** like `cytoscape-cola`, `cytoscape-fcose` (faster CoSE) available via CDN.

---

## Data Shape (from actual DB analysis)

- **681 concepts** -- 559 connected, 122 isolated
- **580 relationships** -- types: `uses` (330), `contrasts_with` (85), `generalizes` (58), `special_case_of` (43), `example_of` (38), `prerequisite` (26)
- **Categories**: method (188), technique (150), metric (114), property (106), definition (56), algorithm (54), theorem (5), other (8)
- **All 681 have descriptions**. Only 66 have section_id (chapter info). Only 69 have paragraph links.
- **Degree distribution**: Most nodes have 1-2 edges. Hub nodes: lasso (34), ridge regression (15), local linear regression (11), support vector classifier (11).
- **615 concepts have no section_id** -- so chapter-based coloring requires either inferring chapter from paragraph links or using `category` as the primary color dimension.

### Color strategy decision

Since 90% of concepts lack section_id, **color by category** (method, technique, metric, property, definition, algorithm, theorem). This gives meaningful visual grouping. Provide a toggle to color by chapter for the 66 that have it (gray out the rest).

---

## Data Export: Python Script

### Script: `src/visualization/export_graph.py`

Reads SQLite, writes a single JSON file that the HTML page loads.

```python
"""Export knowledge graph from SQLite to JSON for Cytoscape.js visualization."""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "textbooks.db"
OUTPUT_PATH = Path(__file__).parent.parent.parent / "output" / "knowledge-graph" / "graph-data.js"


def export():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Concepts
    c.execute("""
        SELECT c.id, c.name, c.description, c.category, c.section_id,
               s.number as section_number, s.title as section_title
        FROM concepts c
        LEFT JOIN sections s ON c.section_id = s.id
    """)
    nodes = []
    for row in c.fetchall():
        section_num = row["section_number"] or ""
        chapter = section_num.split(".")[0] if section_num else ""
        nodes.append({
            "data": {
                "id": str(row["id"]),
                "name": row["name"],
                "description": row["description"] or "",
                "category": row["category"] or "other",
                "chapter": chapter,
                "section": f"{section_num} {row['section_title']}" if section_num else "",
            }
        })

    # Relationships
    c.execute("SELECT id, source_id, target_id, relationship_type FROM concept_relationships")
    edges = []
    for row in c.fetchall():
        edges.append({
            "data": {
                "id": f"e{row['id']}",
                "source": str(row["source_id"]),
                "target": str(row["target_id"]),
                "relationship_type": row["relationship_type"],
            }
        })

    conn.close()

    # Write as JS variable assignment (no CORS issues when opening file://)
    output = {
        "nodes": nodes,
        "edges": edges,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write("const GRAPH_DATA = ")
        json.dump(output, f, indent=None)  # compact for faster loading
        f.write(";")

    print(f"Exported {len(nodes)} nodes and {len(edges)} edges to {OUTPUT_PATH}")


if __name__ == "__main__":
    export()
```

**Key decision**: Output as `graph-data.js` with `const GRAPH_DATA = {...};` rather than pure JSON. This avoids CORS issues when opening `file://` paths in a browser. The HTML page loads it via a `<script>` tag.

---

## Layout and Interaction Design

### Layout: fCoSE (fast Compound Spring Embedder)

Use the `cytoscape-fcose` extension. It:
- Handles compound/clustered graphs
- Produces good results for networks of this size
- Supports constraints and alignment

**Fallback**: Built-in `cose` layout if fcose CDN fails.

### Handling 600+ Nodes

Strategy: **Search-first with progressive disclosure**.

1. **Initial view**: All 559 connected nodes rendered (122 isolated hidden by default). Zoomed out to show full graph. Nodes are small dots, labels hidden except for hubs (degree >= 5).
2. **Search bar**: Type to find concepts. Matched concept centers on screen, highlights its neighborhood (direct connections).
3. **Click a node**: Side panel opens with name, description, category, section, and list of connected concepts (clickable).
4. **Neighborhood expansion**: Click "Focus" to show only this node and its N-hop neighborhood, dimming everything else.
5. **Category filter**: Checkboxes to show/hide by category. Quick way to isolate all "methods" or all "definitions".
6. **Relationship type filter**: Checkboxes to show/hide edge types.
7. **Toggle isolated nodes**: Button to show/hide the 122 disconnected concepts.

### Visual Design

**Node styling**:
- Size: proportional to degree (min 15px, max 60px). Lasso gets the biggest node.
- Color by category:
  - `method`: #4C72B0 (blue)
  - `technique`: #55A868 (green)
  - `metric`: #C44E52 (red)
  - `property`: #8172B2 (purple)
  - `definition`: #CCB974 (gold)
  - `algorithm`: #64B5CD (cyan)
  - `theorem`: #DD8452 (orange)
  - other: #999999 (gray)
- Label: concept name, shown when zoomed in or when node has degree >= 5
- Shape: ellipse (default)

**Edge styling**:
- Color by relationship type:
  - `uses`: #AAAAAA (gray, most common, should be subtle)
  - `prerequisite`: #C44E52 (red, important directionality)
  - `generalizes`: #4C72B0 (blue)
  - `special_case_of`: #55A868 (green)
  - `example_of`: #CCB974 (gold)
  - `contrasts_with`: #8172B2 (purple, dashed line)
- Arrow: target arrow for directed relationships
- Width: 1px default, 3px when connected to selected node
- `contrasts_with` edges use dashed style (they're bidirectional conceptually)

**Interaction highlights**:
- Hovered node: enlarge slightly, show label
- Selected node: bright border, connected edges thicken, unconnected nodes dim to 20% opacity
- Search match: animated "pulse" effect

---

## HTML Structure

Single file: `output/knowledge-graph/index.html`

```
output/knowledge-graph/
    index.html          <-- main visualization
    graph-data.js       <-- exported data (generated by Python script)
```

### index.html rough structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ESL Knowledge Graph</title>
    <script src="https://unpkg.com/cytoscape@3.30.4/dist/cytoscape.min.js"></script>
    <script src="https://unpkg.com/cytoscape-fcose@2.2.0/cytoscape-fcose.js"></script>
    <style>
        /* Full-viewport layout with side panel */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; display: flex; height: 100vh; background: #1a1a2e; color: #e0e0e0; }
        #cy { flex: 1; }
        #sidebar { width: 350px; background: #16213e; overflow-y: auto; padding: 16px; border-left: 1px solid #0f3460; }
        #search-bar { position: absolute; top: 16px; left: 16px; z-index: 10; }
        #search-bar input { width: 300px; padding: 10px 14px; border-radius: 6px; border: 1px solid #0f3460; background: #16213e; color: #e0e0e0; font-size: 14px; }
        #controls { position: absolute; top: 16px; right: 366px; z-index: 10; display: flex; gap: 8px; flex-wrap: wrap; }
        .filter-group { background: #16213e; padding: 8px 12px; border-radius: 6px; border: 1px solid #0f3460; }
        .filter-group label { display: block; font-size: 12px; cursor: pointer; }
        .filter-group h4 { font-size: 11px; text-transform: uppercase; margin-bottom: 4px; color: #888; }
        #concept-detail { display: none; }
        #concept-detail.active { display: block; }
        #concept-detail h2 { font-size: 18px; margin-bottom: 8px; }
        #concept-detail .category-badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; margin-bottom: 12px; }
        #concept-detail .description { font-size: 14px; line-height: 1.5; margin-bottom: 16px; }
        #concept-detail .connections { font-size: 13px; }
        #concept-detail .connections li { cursor: pointer; padding: 4px 0; }
        #concept-detail .connections li:hover { color: #64B5CD; }
        #stats { font-size: 12px; color: #888; padding: 8px 0; border-bottom: 1px solid #0f3460; margin-bottom: 12px; }
        .legend { margin-top: 16px; }
        .legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; margin: 2px 0; }
        .legend-dot { width: 10px; height: 10px; border-radius: 50%; }
        button { background: #0f3460; color: #e0e0e0; border: 1px solid #1a1a6e; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; }
        button:hover { background: #1a1a6e; }
    </style>
</head>
<body>
    <div id="search-bar">
        <input type="text" id="search-input" placeholder="Search concepts..." autocomplete="off">
    </div>

    <div id="controls">
        <div class="filter-group" id="category-filters">
            <h4>Categories</h4>
            <!-- Generated by JS: checkboxes for each category -->
        </div>
        <div class="filter-group" id="edge-filters">
            <h4>Relationships</h4>
            <!-- Generated by JS: checkboxes for each relationship type -->
        </div>
        <div class="filter-group">
            <button id="btn-show-isolated">Show Isolated</button>
            <button id="btn-reset">Reset View</button>
            <button id="btn-fit">Fit All</button>
        </div>
    </div>

    <div id="cy"></div>

    <div id="sidebar">
        <div id="stats">
            <span id="node-count"></span> concepts, <span id="edge-count"></span> relationships
        </div>
        <div id="concept-detail">
            <h2 id="detail-name"></h2>
            <span class="category-badge" id="detail-category"></span>
            <p id="detail-section" style="font-size:12px;color:#888;margin-bottom:8px;"></p>
            <div class="description" id="detail-description"></div>
            <h3 style="font-size:14px;margin-bottom:8px;">Connections</h3>
            <ul class="connections" id="detail-connections"></ul>
            <button id="btn-focus" style="margin-top:12px;">Focus Neighborhood</button>
        </div>
        <div id="welcome-msg">
            <p style="color:#888;font-size:14px;margin-top:20px;">Click a concept node to see its details, or use the search bar to find a specific concept.</p>
        </div>
        <div class="legend" id="legend">
            <h4 style="font-size:11px;text-transform:uppercase;color:#888;margin-bottom:4px;">Node Colors (Category)</h4>
            <!-- Generated by JS -->
        </div>
    </div>

    <script src="graph-data.js"></script>
    <script>
        // Main application code -- see implementation steps below
    </script>
</body>
</html>
```

---

## Implementation Steps for Sisyphus

### Step 1: Create the data export script

**File**: `src/visualization/export_graph.py`

Write exactly the Python script shown above. Verify it runs:
```bash
python -m src.visualization.export_graph
```
Confirm `output/knowledge-graph/graph-data.js` is created and begins with `const GRAPH_DATA = {`.

### Step 2: Create the HTML file

**File**: `output/knowledge-graph/index.html`

Use the HTML structure above as the skeleton. The `<script>` section must implement the following in order:

#### 2a. Initialize Cytoscape

```javascript
// Register fcose layout
// cytoscape.use(cytoscapeFcose); -- fcose self-registers when loaded via script tag

const CATEGORY_COLORS = {
    method: '#4C72B0',
    technique: '#55A868',
    metric: '#C44E52',
    property: '#8172B2',
    definition: '#CCB974',
    algorithm: '#64B5CD',
    theorem: '#DD8452',
    other: '#999999'
};

const EDGE_COLORS = {
    uses: '#666666',
    prerequisite: '#C44E52',
    generalizes: '#4C72B0',
    special_case_of: '#55A868',
    example_of: '#CCB974',
    contrasts_with: '#8172B2'
};

// Compute degree for each node
const degreeMap = {};
GRAPH_DATA.edges.forEach(e => {
    degreeMap[e.data.source] = (degreeMap[e.data.source] || 0) + 1;
    degreeMap[e.data.target] = (degreeMap[e.data.target] || 0) + 1;
});

// Add degree to node data
GRAPH_DATA.nodes.forEach(n => {
    n.data.degree = degreeMap[n.data.id] || 0;
});

// Initially hide isolated nodes
const connectedElements = {
    nodes: GRAPH_DATA.nodes.filter(n => n.data.degree > 0),
    edges: GRAPH_DATA.edges
};

const cy = cytoscape({
    container: document.getElementById('cy'),
    elements: connectedElements,
    style: [
        {
            selector: 'node',
            style: {
                'label': 'data(name)',
                'text-valign': 'center',
                'font-size': '8px',
                'color': '#e0e0e0',
                'text-outline-color': '#1a1a2e',
                'text-outline-width': 1,
                'background-color': function(ele) {
                    return CATEGORY_COLORS[ele.data('category')] || CATEGORY_COLORS.other;
                },
                'width': function(ele) {
                    return Math.max(15, Math.min(60, 10 + ele.data('degree') * 3));
                },
                'height': function(ele) {
                    return Math.max(15, Math.min(60, 10 + ele.data('degree') * 3));
                },
                'text-opacity': function(ele) {
                    return ele.data('degree') >= 5 ? 1 : 0;
                },
                'border-width': 0,
            }
        },
        {
            selector: 'edge',
            style: {
                'width': 1,
                'line-color': function(ele) {
                    return EDGE_COLORS[ele.data('relationship_type')] || '#666';
                },
                'target-arrow-color': function(ele) {
                    return EDGE_COLORS[ele.data('relationship_type')] || '#666';
                },
                'target-arrow-shape': 'triangle',
                'arrow-scale': 0.8,
                'curve-style': 'bezier',
                'opacity': 0.4,
                'line-style': function(ele) {
                    return ele.data('relationship_type') === 'contrasts_with' ? 'dashed' : 'solid';
                }
            }
        },
        {
            selector: 'node:selected',
            style: {
                'border-width': 3,
                'border-color': '#ffffff',
                'text-opacity': 1,
                'font-size': '12px',
            }
        },
        {
            selector: '.dimmed',
            style: { 'opacity': 0.15 }
        },
        {
            selector: '.highlighted',
            style: {
                'opacity': 1,
                'text-opacity': 1,
                'font-size': '10px',
                'border-width': 2,
                'border-color': '#ffffff',
            }
        },
        {
            selector: 'edge.highlighted',
            style: { 'width': 3, 'opacity': 0.9 }
        },
        {
            selector: '.search-match',
            style: {
                'border-width': 4,
                'border-color': '#FFD700',
                'text-opacity': 1,
                'font-size': '14px',
                'z-index': 999,
            }
        }
    ],
    layout: {
        name: 'fcose',
        quality: 'default',
        randomize: true,
        animate: false,
        nodeDimensionsIncludeLabels: false,
        idealEdgeLength: 80,
        nodeRepulsion: 8000,
        edgeElasticity: 0.45,
        gravity: 0.25,
    },
    minZoom: 0.1,
    maxZoom: 5,
    wheelSensitivity: 0.3,
});
```

#### 2b. Search functionality

```javascript
const searchInput = document.getElementById('search-input');
let searchTimeout;

searchInput.addEventListener('input', function() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        const query = this.value.trim().toLowerCase();
        cy.elements().removeClass('search-match dimmed highlighted');

        if (query.length < 2) return;

        const matches = cy.nodes().filter(n =>
            n.data('name').toLowerCase().includes(query)
        );

        if (matches.length > 0) {
            cy.elements().addClass('dimmed');
            matches.removeClass('dimmed').addClass('search-match');
            matches.connectedEdges().removeClass('dimmed');
            matches.neighborhood().nodes().removeClass('dimmed');

            if (matches.length <= 5) {
                cy.animate({ fit: { eles: matches, padding: 80 }, duration: 500 });
            }
        }
    }, 300);
});

// Clear search on Escape
searchInput.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        this.value = '';
        cy.elements().removeClass('search-match dimmed highlighted');
    }
});
```

#### 2c. Node click -> detail panel

```javascript
cy.on('tap', 'node', function(evt) {
    const node = evt.target;
    const data = node.data();

    // Show detail panel
    document.getElementById('concept-detail').classList.add('active');
    document.getElementById('welcome-msg').style.display = 'none';
    document.getElementById('detail-name').textContent = data.name;

    const badge = document.getElementById('detail-category');
    badge.textContent = data.category;
    badge.style.backgroundColor = CATEGORY_COLORS[data.category] || CATEGORY_COLORS.other;

    document.getElementById('detail-section').textContent = data.section || '';
    document.getElementById('detail-description').textContent = data.description;

    // Build connections list
    const connList = document.getElementById('detail-connections');
    connList.innerHTML = '';
    node.connectedEdges().forEach(edge => {
        const otherNode = edge.source().id() === node.id() ? edge.target() : edge.source();
        const direction = edge.source().id() === node.id() ? '\u2192' : '\u2190';
        const li = document.createElement('li');
        li.textContent = `${direction} ${edge.data('relationship_type')}: ${otherNode.data('name')}`;
        li.addEventListener('click', () => {
            cy.getElementById(otherNode.id()).emit('tap');
            cy.animate({ center: { eles: otherNode }, duration: 300 });
        });
        connList.appendChild(li);
    });

    // Highlight neighborhood
    cy.elements().removeClass('highlighted dimmed search-match');
    cy.elements().addClass('dimmed');
    node.removeClass('dimmed');
    node.neighborhood().removeClass('dimmed').addClass('highlighted');
    node.connectedEdges().removeClass('dimmed').addClass('highlighted');

    // Store selected node for focus button
    cy._selectedNode = node;
});

// Click background to deselect
cy.on('tap', function(evt) {
    if (evt.target === cy) {
        cy.elements().removeClass('dimmed highlighted search-match');
        document.getElementById('concept-detail').classList.remove('active');
        document.getElementById('welcome-msg').style.display = 'block';
    }
});
```

#### 2d. Focus neighborhood button

```javascript
document.getElementById('btn-focus').addEventListener('click', function() {
    const node = cy._selectedNode;
    if (!node) return;
    const neighborhood = node.closedNeighborhood();
    cy.animate({ fit: { eles: neighborhood, padding: 60 }, duration: 500 });
});
```

#### 2e. Category and edge type filters

```javascript
// Generate category filter checkboxes
const catFilters = document.getElementById('category-filters');
const categories = [...new Set(GRAPH_DATA.nodes.map(n => n.data.category))].sort();
categories.forEach(cat => {
    const label = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = true;
    cb.value = cat;
    cb.addEventListener('change', applyFilters);
    label.appendChild(cb);
    label.appendChild(document.createTextNode(` ${cat}`));
    catFilters.appendChild(label);
});

// Generate edge filter checkboxes
const edgeFilters = document.getElementById('edge-filters');
const edgeTypes = [...new Set(GRAPH_DATA.edges.map(e => e.data.relationship_type))].sort();
edgeTypes.forEach(type => {
    const label = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = true;
    cb.value = type;
    cb.addEventListener('change', applyFilters);
    label.appendChild(cb);
    label.appendChild(document.createTextNode(` ${type}`));
    edgeFilters.appendChild(label);
});

function applyFilters() {
    const activeCats = new Set(
        [...catFilters.querySelectorAll('input:checked')].map(cb => cb.value)
    );
    const activeEdges = new Set(
        [...edgeFilters.querySelectorAll('input:checked')].map(cb => cb.value)
    );

    cy.batch(() => {
        cy.nodes().forEach(n => {
            if (activeCats.has(n.data('category'))) {
                n.style('display', 'element');
            } else {
                n.style('display', 'none');
            }
        });
        cy.edges().forEach(e => {
            if (activeEdges.has(e.data('relationship_type'))) {
                e.style('display', 'element');
            } else {
                e.style('display', 'none');
            }
        });
    });
}
```

#### 2f. Toolbar buttons

```javascript
let showingIsolated = false;
document.getElementById('btn-show-isolated').addEventListener('click', function() {
    showingIsolated = !showingIsolated;
    this.textContent = showingIsolated ? 'Hide Isolated' : 'Show Isolated';

    if (showingIsolated) {
        const isolatedNodes = GRAPH_DATA.nodes.filter(n => n.data.degree === 0);
        cy.add(isolatedNodes);
        // Place them in a grid at the periphery
        const isolated = cy.nodes().filter(n => n.data('degree') === 0);
        isolated.layout({ name: 'grid', boundingBox: { x1: -500, y1: -500, x2: -100, y2: 500 } }).run();
    } else {
        cy.nodes().filter(n => n.data('degree') === 0).remove();
    }
});

document.getElementById('btn-reset').addEventListener('click', function() {
    cy.elements().removeClass('dimmed highlighted search-match');
    searchInput.value = '';
    // Reset all filter checkboxes
    catFilters.querySelectorAll('input').forEach(cb => cb.checked = true);
    edgeFilters.querySelectorAll('input').forEach(cb => cb.checked = true);
    applyFilters();
    cy.fit(undefined, 30);
});

document.getElementById('btn-fit').addEventListener('click', function() {
    cy.animate({ fit: { padding: 30 }, duration: 500 });
});
```

#### 2g. Legend and stats

```javascript
document.getElementById('node-count').textContent = cy.nodes().length;
document.getElementById('edge-count').textContent = cy.edges().length;

const legend = document.getElementById('legend');
Object.entries(CATEGORY_COLORS).forEach(([cat, color]) => {
    const item = document.createElement('div');
    item.className = 'legend-item';
    item.innerHTML = `<span class="legend-dot" style="background:${color}"></span>${cat}`;
    legend.appendChild(item);
});
```

#### 2h. Zoom-dependent label visibility

```javascript
cy.on('zoom', function() {
    const zoom = cy.zoom();
    cy.batch(() => {
        cy.nodes().forEach(n => {
            if (n.hasClass('search-match') || n.hasClass('highlighted')) return;
            if (zoom > 1.5) {
                n.style('text-opacity', 1);
                n.style('font-size', '8px');
            } else if (zoom > 0.8) {
                n.style('text-opacity', n.data('degree') >= 3 ? 1 : 0);
            } else {
                n.style('text-opacity', n.data('degree') >= 5 ? 1 : 0);
            }
        });
    });
});
```

### Step 3: Test

1. Run `python src/visualization/export_graph.py` from the project root
2. Open `output/knowledge-graph/index.html` in Chrome/Firefox
3. Verify:
   - Graph renders with ~559 visible nodes
   - Nodes are colored by category
   - Clicking a node shows its description in the sidebar
   - Search finds concepts and highlights them
   - Category filter checkboxes show/hide node groups
   - Edge type checkboxes show/hide edge types
   - "Show Isolated" adds the 122 disconnected nodes
   - "Focus Neighborhood" zooms to a selected node's local network
   - Zoom in reveals labels progressively

---

## Final File Structure

```
textparse/
    src/visualization/
        export_graph.py          <-- NEW: SQLite -> JS export script
        renderer.py              <-- existing (untouched)
        __init__.py              <-- existing (untouched)
    output/knowledge-graph/
        index.html               <-- NEW: main visualization
        graph-data.js            <-- GENERATED: data file (not committed, .gitignore it)
```

### .gitignore addition

Add to `.gitignore`:
```
output/knowledge-graph/graph-data.js
```

The `index.html` should be committed. The `graph-data.js` is generated and should not be.

---

## CDN Dependencies

```
https://unpkg.com/cytoscape@3.30.4/dist/cytoscape.min.js
https://unpkg.com/cytoscape-fcose@2.2.0/cytoscape-fcose.js
```

No other dependencies. No build step. No npm. Just two CDN scripts and one local data file.

---

## Future Enhancements (not in scope for initial implementation)

- Export to PNG/SVG button
- Right-click context menu for "show all paths between two concepts"
- Hierarchical layout mode (chapters as layers)
- Time-based animation showing concepts introduced page by page
- Backfill section_id for the 615 concepts without it (prerequisite for chapter-based coloring)
