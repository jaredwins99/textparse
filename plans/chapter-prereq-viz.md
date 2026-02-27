# Chapter-Organized Prerequisite Navigation View

## Problem

Someone reading Chapter 14 of ESL needs to know: "What concepts from earlier chapters do I need to understand?" Currently the force-directed graph shows all 670 concepts in a hairball with no spatial relationship to the book's structure. This view solves that.

## Decision: New HTML Page, Not a Mode Toggle

**Build a new page** at `output/chapter-prereqs/index.html` that reuses the same `graph-data.js` export.

Rationale:
- The existing viz is a general-purpose explorer. This view has fundamentally different layout logic (fixed rectangular regions vs force-directed). Cramming both into one page creates a frankenstein with two layout engines and confusing mode-switching.
- Both pages share the same data file. No duplication of the export pipeline.
- The existing viz can link to this one and vice versa ("Switch to chapter view" / "Switch to graph view").
- Simpler for Sisyphus to implement: one clean HTML file with no conditionals around which mode is active.

## Data Export Changes

The current `export_graph.py` already includes `chapter` in each node's data (extracted from section number). **No changes needed to the export script.** The existing `graph-data.js` has everything required:
- `node.data.chapter` — string like "14"
- `node.data.section` — string like "14.3 Boosting Methods"
- `edge.data.relationship_type` — for filtering
- `edge.data.source` / `edge.data.target` — for graph traversal

## Layout Design

### Overall Structure

Horizontal scrollable canvas. Each chapter is a **column** (not a wide rectangle) to maximize vertical space usage on typical screens. Chapters are arranged left-to-right: Ch 1, Ch 2, ..., Ch 18.

```
┌──────┐  ┌──────┐  ┌──────┐       ┌──────┐
│ Ch 1 │  │ Ch 2 │  │ Ch 3 │  ...  │Ch 18 │
│      │  │      │  │      │       │      │
│  5   │  │  56  │  │  42  │       │  66  │
│nodes │  │nodes │  │nodes │       │nodes │
│      │  │      │  │      │       │      │
└──────┘  └──────┘  └──────┘       └──────┘
```

### Chapter Column Sizing

- **Fixed column width**: 200px per chapter
- **Column height**: Variable, proportional to concept count. Each concept node gets ~30px vertical space. Ch 14 (128 concepts) gets ~3840px; Ch 1 (5 concepts) gets ~150px.
- **Column gap**: 80px between columns (enough for edge routing clarity)
- **Total canvas**: ~18 columns x 280px = ~5040px wide. Scrollable.

### Within-Column Layout

Concepts within each chapter column use a **vertical stack**, sorted by section number then alphabetically within section. This gives a predictable, scannable order that maps to the book.

Each concept is rendered as a **small pill/badge** (160px wide, ~24px tall) with:
- Name text (truncated if > ~20 chars, full name on hover)
- Background color from category (same palette as existing viz)
- Left border accent (3px) colored by category

For Ch 14 (128 concepts), the column will be tall. This is fine — the canvas scrolls vertically too. Subsection headers within each column break up the wall of nodes:

```
┌── Chapter 14 ──────────┐
│ 14.1 Boosting Methods  │
│ ┌──────────────────┐   │
│ │ AdaBoost         │   │
│ ├──────────────────┤   │
│ │ boosting          │   │
│ └──────────────────┘   │
│ 14.2 Boosting Fits...  │
│ ┌──────────────────┐   │
│ │ additive model    │   │
│ ...                    │
└────────────────────────┘
```

### Edge Rendering

Cross-chapter edges are drawn as **SVG paths** (not Cytoscape — we're building this with plain HTML/CSS/SVG for the structured layout, not a graph library).

**Why not Cytoscape?** Cytoscape's strength is force-directed layout. For a fixed positional layout with rectangular containers, plain DOM + SVG gives full control and is simpler. Cytoscape would fight us on node positioning inside compound nodes.

Edge rendering rules:
1. **Default: only cross-chapter edges visible.** Within-chapter edges are hidden by default (they add clutter without helping the "what do I need from earlier chapters" use case). Toggle available to show them.
2. **Edge style by type:**
   - `prerequisite` / `uses` / `special_case_of` — solid line, opacity 0.6
   - `generalizes` — dashed
   - `contrasts_with` — dotted, lighter (0.3 opacity)
   - `example_of` — thin solid
3. **Edge color:** Matches the relationship type color from existing viz palette.
4. **Edge routing:** Simple bezier curves. Source point = right edge of source node pill. Target point = left edge of target node pill. Control points offset horizontally into the gap between columns. For edges spanning multiple chapters, the curve bows outward proportional to distance.
5. **Edge bundling (visual declutter):** Edges between the same pair of chapters share a "corridor" — a vertical band in the gap between those chapters. This naturally groups related cross-chapter connections.

### Handling Visual Complexity

With 151 cross-chapter edges, the view will be busy if all show at once. Mitigations:

1. **Default filter: only `prerequisite`, `uses`, and `special_case_of`** (330 + 26 + 43 = 399 total, but only ~100 cross-chapter). This matches the user's stated defaults.
2. **Edges hidden until interaction.** On page load, show chapter columns with nodes but **no edges**. Edges appear when a concept is clicked or hovered. This is the key insight — the view is primarily navigated by clicking, not by staring at a hairball.
3. **On hover over a concept:** Show only that concept's incoming edges from earlier chapters (faded) as a preview.
4. **On click:** Full prerequisite trace (see Interaction Design below).

## Interaction Design

### Click Flow: "What Do I Need?"

This is the core feature. When a user clicks a concept in Chapter 14:

1. **Immediate visual:** The clicked concept highlights (bold border, slight glow).
2. **Backward trace:** Walk backward through `prerequisite`, `uses`, and `special_case_of` edges recursively to find all transitive dependencies from earlier chapters. This is a BFS/DFS on the filtered graph.
3. **Highlight the dependency chain:**
   - All prerequisite concepts in earlier chapters get highlighted (colored border, full opacity).
   - Chapter columns that contain prerequisites get a subtle highlight on their header.
   - Edges in the chain are drawn and highlighted.
   - Non-participating concepts are dimmed (opacity 0.2).
4. **Sidebar panel** slides in from the right showing:
   - **Concept name and description** (from the clicked concept)
   - **"You need from earlier chapters"** — grouped by chapter:
     ```
     Chapter 2 (3 concepts):
       - linear regression
       - least squares
       - bias-variance tradeoff
     Chapter 3 (1 concept):
       - regularization
     Chapter 7 (2 concepts):
       - cross-validation
       - model selection
     ```
   - Each listed concept is clickable (navigates to it, re-runs the trace from that concept).
   - **"Direct dependencies only"** toggle — switches between showing only immediate edges vs the full transitive closure.

### Critical Path Feature

Beyond listing all prerequisites, compute and display the **minimum prerequisite set** — concepts that are themselves not prerequisites of other prerequisites already in the set. In graph terms: the "frontier" of the backward reachability set — nodes with no outgoing prerequisite edges to other nodes in the set.

This answers: "What are the foundational things I need, not the intermediate steps?"

Display this as a separate section in the sidebar:
```
Core prerequisites (start here):
  Ch 2: linear regression, least squares
  Ch 7: cross-validation

Full dependency chain (12 concepts across 4 chapters)
  [expand to see all]
```

### Filtering Controls

Top bar with:
- **Relationship type checkboxes:** prerequisite, uses, special_case_of, generalizes, contrasts_with, example_of. Default: first three checked.
- **Chapter range slider:** "Show chapters 1–18". Useful to zoom into e.g. chapters 5–10.
- **Search box:** Type to filter concepts. Matching concepts highlight across all chapters.
- **"Show within-chapter edges" toggle:** Off by default.

### Navigation Between Views

- Button in top-right: "Open Graph View" — links to `../knowledge-graph/index.html`
- The existing graph view gets a reciprocal "Open Chapter View" button linking back.

## Implementation Spec

### File Structure

```
output/chapter-prereqs/
  index.html      — Single-file app (HTML + CSS + JS inline)
  (uses ../knowledge-graph/graph-data.js via relative path)
```

Single file, same pattern as the existing viz. The `graph-data.js` is loaded via script tag with relative path.

### HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ESL Chapter Prerequisites</title>
    <!-- No external dependencies. Pure HTML/CSS/SVG/JS. -->
</head>
<body>
    <div id="toolbar">
        <div id="edge-filters"><!-- checkboxes --></div>
        <div id="chapter-range"><!-- range inputs --></div>
        <input id="search-input" placeholder="Search concepts...">
        <label><input type="checkbox" id="toggle-intra"> Show within-chapter edges</label>
        <a href="../knowledge-graph/index.html" id="link-graph-view">Open Graph View</a>
    </div>

    <div id="main-container">
        <div id="canvas-scroll">
            <svg id="edge-layer"><!-- all edges drawn here --></svg>
            <div id="chapters-row">
                <!-- Generated: one .chapter-column per chapter -->
            </div>
        </div>
        <div id="sidebar">
            <div id="concept-detail"><!-- populated on click --></div>
        </div>
    </div>
</body>
</html>
```

### CSS Key Points

```css
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #1a1a2e;
    color: #e0e0e0;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

#toolbar {
    height: 48px;
    background: #16213e;
    border-bottom: 1px solid #0f3460;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0 16px;
    flex-shrink: 0;
}

#main-container {
    flex: 1;
    display: flex;
    overflow: hidden;
}

#canvas-scroll {
    flex: 1;
    overflow: auto;
    position: relative;
}

#edge-layer {
    position: absolute;
    top: 0;
    left: 0;
    pointer-events: none;  /* clicks pass through to nodes below */
    z-index: 1;
}

#chapters-row {
    display: flex;
    gap: 80px;
    padding: 24px;
    position: relative;
    /* min-width set dynamically to contain all columns */
}

.chapter-column {
    width: 200px;
    flex-shrink: 0;
    background: rgba(15, 52, 96, 0.3);
    border: 1px solid #0f3460;
    border-radius: 8px;
    padding: 8px;
}

.chapter-header {
    font-size: 14px;
    font-weight: 600;
    padding: 8px;
    border-bottom: 1px solid #0f3460;
    margin-bottom: 8px;
    position: sticky;
    top: 0;
    background: rgba(22, 33, 62, 0.95);
    z-index: 2;
}

.section-header {
    font-size: 11px;
    color: #888;
    padding: 4px 8px;
    margin-top: 8px;
}

.concept-node {
    padding: 4px 8px;
    margin: 2px 0;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
    border-left: 3px solid transparent;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: opacity 0.2s, background 0.2s;
}

.concept-node:hover {
    background: rgba(255,255,255,0.1);
}

.concept-node.dimmed { opacity: 0.15; }
.concept-node.highlighted {
    opacity: 1;
    background: rgba(255,255,255,0.1);
    border-left-color: #FFD700;
    font-weight: 600;
}
.concept-node.selected {
    border-left-color: #fff;
    background: rgba(255,255,255,0.15);
    font-weight: 700;
}

.chapter-column.has-prereqs .chapter-header {
    background: rgba(100, 181, 205, 0.15);
}

#sidebar {
    width: 340px;
    flex-shrink: 0;
    background: #16213e;
    border-left: 1px solid #0f3460;
    overflow-y: auto;
    padding: 16px;
    transform: translateX(100%);
    transition: transform 0.2s;
}
#sidebar.open { transform: translateX(0); }
```

### JavaScript Architecture

The JS is structured as an IIFE with clear sections. No build step, no modules.

```javascript
(function() {
    "use strict";

    // ─── DATA PROCESSING ───────────────────────────────────

    // Build lookup structures from GRAPH_DATA
    var nodeById = {};          // id -> node data
    var nodesByChapter = {};    // chapter string -> [node data]
    var edgeIndex = {           // adjacency lists
        outgoing: {},           // source_id -> [edge data]
        incoming: {}            // target_id -> [edge data]
    };

    GRAPH_DATA.nodes.forEach(function(n) {
        var d = n.data;
        nodeById[d.id] = d;
        var ch = d.chapter || "0";
        if (!nodesByChapter[ch]) nodesByChapter[ch] = [];
        nodesByChapter[ch].push(d);
    });

    GRAPH_DATA.edges.forEach(function(e) {
        var d = e.data;
        if (!edgeIndex.outgoing[d.source]) edgeIndex.outgoing[d.source] = [];
        edgeIndex.outgoing[d.source].push(d);
        if (!edgeIndex.incoming[d.target]) edgeIndex.incoming[d.target] = [];
        edgeIndex.incoming[d.target].push(d);
    });

    // Sort chapters numerically
    var chapters = Object.keys(nodesByChapter).sort(function(a, b) {
        return parseInt(a) - parseInt(b);
    });

    // Sort concepts within each chapter by section number
    chapters.forEach(function(ch) {
        nodesByChapter[ch].sort(function(a, b) {
            return (a.section || "").localeCompare(b.section || "", undefined, {numeric: true})
                || a.name.localeCompare(b.name);
        });
    });

    // ─── DOM GENERATION ────────────────────────────────────

    var chaptersRow = document.getElementById('chapters-row');
    var nodeElements = {};  // concept id -> DOM element

    chapters.forEach(function(ch) {
        var col = document.createElement('div');
        col.className = 'chapter-column';
        col.dataset.chapter = ch;

        var header = document.createElement('div');
        header.className = 'chapter-header';
        header.textContent = 'Chapter ' + ch + ' (' + nodesByChapter[ch].length + ')';
        col.appendChild(header);

        // Group by section
        var currentSection = null;
        nodesByChapter[ch].forEach(function(concept) {
            var section = concept.section ? concept.section.split(' ').slice(0,1)[0] : '';
            if (section !== currentSection) {
                currentSection = section;
                if (section) {
                    var sh = document.createElement('div');
                    sh.className = 'section-header';
                    sh.textContent = concept.section;
                    col.appendChild(sh);
                }
            }

            var node = document.createElement('div');
            node.className = 'concept-node';
            node.dataset.id = concept.id;
            node.style.borderLeftColor = CATEGORY_COLORS[concept.category] || '#999';
            node.textContent = concept.name;
            node.title = concept.name + '\n' + (concept.description || '').substring(0, 200);
            col.appendChild(node);

            nodeElements[concept.id] = node;
        });

        chaptersRow.appendChild(col);
    });

    // ─── SVG EDGE LAYER ────────────────────────────────────

    var svgLayer = document.getElementById('edge-layer');

    function resizeSvg() {
        var rect = chaptersRow.getBoundingClientRect();
        svgLayer.setAttribute('width', chaptersRow.scrollWidth);
        svgLayer.setAttribute('height', chaptersRow.scrollHeight);
    }

    function getNodeCenter(id) {
        var el = nodeElements[id];
        if (!el) return null;
        // Position relative to chapters-row
        var rowRect = chaptersRow.getBoundingClientRect();
        var elRect = el.getBoundingClientRect();
        return {
            x: elRect.left - rowRect.left + elRect.width / 2,
            y: elRect.top - rowRect.top + elRect.height / 2,
            left: elRect.left - rowRect.left,
            right: elRect.right - rowRect.left,
            width: elRect.width
        };
    }

    function drawEdge(sourceId, targetId, relType, cssClass) {
        var from = getNodeCenter(sourceId);
        var to = getNodeCenter(targetId);
        if (!from || !to) return null;

        var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');

        // Source exits from right, target enters from left
        var x1 = from.right;
        var y1 = from.y;
        var x2 = to.left;
        var y2 = to.y;

        // Bezier control points: horizontal offset proportional to distance
        var dx = Math.abs(x2 - x1);
        var cpOffset = Math.max(40, dx * 0.3);

        var d = 'M ' + x1 + ' ' + y1
              + ' C ' + (x1 + cpOffset) + ' ' + y1
              + ', ' + (x2 - cpOffset) + ' ' + y2
              + ', ' + x2 + ' ' + y2;

        path.setAttribute('d', d);
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', EDGE_COLORS[relType] || '#666');
        path.setAttribute('stroke-width', '1.5');
        path.setAttribute('opacity', '0.6');
        if (cssClass) path.setAttribute('class', cssClass);

        // Dashed for certain types
        if (relType === 'generalizes') path.setAttribute('stroke-dasharray', '6,3');
        if (relType === 'contrasts_with') {
            path.setAttribute('stroke-dasharray', '3,3');
            path.setAttribute('opacity', '0.3');
        }

        svgLayer.appendChild(path);
        return path;
    }

    function clearEdges() {
        while (svgLayer.firstChild) svgLayer.removeChild(svgLayer.firstChild);
    }

    // ─── PREREQUISITE TRACE (BFS) ─────────────────────────

    // The key algorithm. Given a concept ID and a set of allowed
    // relationship types, walk BACKWARD through incoming edges to
    // find all transitive dependencies from earlier chapters.

    function tracePrerequisites(conceptId, allowedTypes) {
        var visited = {};
        var queue = [conceptId];
        visited[conceptId] = true;
        var result = {
            nodes: [],      // all prerequisite concept IDs (not including start)
            edges: [],      // {source, target, type} for each traversed edge
            byChapter: {},  // chapter -> [concept IDs]
            frontier: []    // "core prereqs" — no further prereqs in the set
        };

        var startChapter = nodeById[conceptId] ? nodeById[conceptId].chapter : null;

        while (queue.length > 0) {
            var current = queue.shift();
            var incoming = edgeIndex.incoming[current] || [];

            incoming.forEach(function(edge) {
                if (!allowedTypes[edge.relationship_type]) return;
                var sourceId = edge.source;
                if (visited[sourceId]) return;

                visited[sourceId] = true;
                result.nodes.push(sourceId);
                result.edges.push({
                    source: sourceId,
                    target: current,
                    type: edge.relationship_type
                });

                var sourceNode = nodeById[sourceId];
                if (sourceNode) {
                    var ch = sourceNode.chapter;
                    if (!result.byChapter[ch]) result.byChapter[ch] = [];
                    result.byChapter[ch].push(sourceId);
                }

                queue.push(sourceId);
            });
        }

        // Compute frontier: nodes in result that have no incoming
        // edges (within the result set) from the allowed types
        var resultSet = {};
        result.nodes.forEach(function(id) { resultSet[id] = true; });

        result.nodes.forEach(function(id) {
            var incoming = edgeIndex.incoming[id] || [];
            var hasPrereqInSet = incoming.some(function(edge) {
                return allowedTypes[edge.relationship_type] && resultSet[edge.source];
            });
            if (!hasPrereqInSet) {
                result.frontier.push(id);
            }
        });

        return result;
    }

    // ─── CLICK HANDLER ─────────────────────────────────────

    // Event delegation on chapters-row
    chaptersRow.addEventListener('click', function(evt) {
        var target = evt.target.closest('.concept-node');
        if (!target) {
            // Clicked empty space — clear selection
            clearSelection();
            return;
        }
        selectConcept(target.dataset.id);
    });

    function clearSelection() {
        Object.values(nodeElements).forEach(function(el) {
            el.classList.remove('dimmed', 'highlighted', 'selected');
        });
        document.querySelectorAll('.chapter-column').forEach(function(col) {
            col.classList.remove('has-prereqs');
        });
        clearEdges();
        document.getElementById('sidebar').classList.remove('open');
    }

    function selectConcept(conceptId) {
        clearEdges();

        // Get active relationship types from filter checkboxes
        var allowedTypes = getActiveEdgeTypes();

        var trace = tracePrerequisites(conceptId, allowedTypes);

        // Dim everything, highlight trace
        Object.values(nodeElements).forEach(function(el) {
            el.classList.add('dimmed');
            el.classList.remove('highlighted', 'selected');
        });

        // Highlight the selected node
        if (nodeElements[conceptId]) {
            nodeElements[conceptId].classList.remove('dimmed');
            nodeElements[conceptId].classList.add('selected');
        }

        // Highlight all prereqs
        trace.nodes.forEach(function(id) {
            if (nodeElements[id]) {
                nodeElements[id].classList.remove('dimmed');
                nodeElements[id].classList.add('highlighted');
            }
        });

        // Highlight chapter columns that have prereqs
        Object.keys(trace.byChapter).forEach(function(ch) {
            var col = document.querySelector('.chapter-column[data-chapter="' + ch + '"]');
            if (col) col.classList.add('has-prereqs');
        });

        // Draw edges
        resizeSvg();
        trace.edges.forEach(function(edge) {
            drawEdge(edge.source, edge.target, edge.type, 'trace-edge');
        });

        // Populate sidebar
        populateSidebar(conceptId, trace);
        document.getElementById('sidebar').classList.add('open');

        // Scroll the selected node into view
        if (nodeElements[conceptId]) {
            nodeElements[conceptId].scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
        }
    }

    // ─── SIDEBAR ───────────────────────────────────────────

    function populateSidebar(conceptId, trace) {
        var concept = nodeById[conceptId];
        var detail = document.getElementById('concept-detail');

        var html = '<h2>' + escHtml(concept.name) + '</h2>';
        html += '<span class="category-badge" style="background:'
             + (CATEGORY_COLORS[concept.category] || '#999') + '">'
             + escHtml(concept.category) + '</span>';
        html += '<p class="section-info">' + escHtml(concept.section || '') + '</p>';
        html += '<p class="description">' + escHtml(concept.description || '') + '</p>';

        // Core prerequisites (frontier)
        if (trace.frontier.length > 0) {
            html += '<div class="prereq-section">';
            html += '<h3>Core prerequisites (start here)</h3>';
            trace.frontier.sort(function(a, b) {
                return (nodeById[a].chapter || '0').localeCompare(nodeById[b].chapter || '0', undefined, {numeric: true});
            });
            trace.frontier.forEach(function(id) {
                var n = nodeById[id];
                html += '<div class="prereq-item clickable" data-id="' + id + '">'
                     + '<span class="ch-badge">Ch ' + n.chapter + '</span> '
                     + escHtml(n.name) + '</div>';
            });
            html += '</div>';
        }

        // Full chain by chapter
        var chapKeys = Object.keys(trace.byChapter).sort(function(a, b) {
            return parseInt(a) - parseInt(b);
        });

        if (chapKeys.length > 0) {
            html += '<div class="prereq-section">';
            html += '<h3>Full dependency chain (' + trace.nodes.length
                 + ' concepts across ' + chapKeys.length + ' chapters)</h3>';

            chapKeys.forEach(function(ch) {
                html += '<div class="chapter-group">';
                html += '<h4>Chapter ' + ch + ' (' + trace.byChapter[ch].length + ')</h4>';
                trace.byChapter[ch].forEach(function(id) {
                    var n = nodeById[id];
                    html += '<div class="prereq-item clickable" data-id="' + id + '">'
                         + escHtml(n.name) + '</div>';
                });
                html += '</div>';
            });
            html += '</div>';
        } else {
            html += '<p class="no-prereqs">No prerequisites found with current filters.</p>';
        }

        detail.innerHTML = html;

        // Attach click handlers to prerequisite items
        detail.querySelectorAll('.clickable').forEach(function(el) {
            el.addEventListener('click', function() {
                selectConcept(this.dataset.id);
            });
        });
    }

    function escHtml(s) {
        var div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    }

    // ─── FILTER CONTROLS ───────────────────────────────────

    var EDGE_TYPES = ['prerequisite', 'uses', 'special_case_of', 'generalizes', 'contrasts_with', 'example_of'];
    var DEFAULT_ON = { prerequisite: true, uses: true, special_case_of: true };

    function buildFilterControls() {
        var container = document.getElementById('edge-filters');
        EDGE_TYPES.forEach(function(type) {
            var label = document.createElement('label');
            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.value = type;
            cb.checked = !!DEFAULT_ON[type];
            label.appendChild(cb);
            label.appendChild(document.createTextNode(' ' + type.replace(/_/g, ' ')));
            container.appendChild(label);
        });
    }

    function getActiveEdgeTypes() {
        var types = {};
        document.querySelectorAll('#edge-filters input:checked').forEach(function(cb) {
            types[cb.value] = true;
        });
        return types;
    }

    buildFilterControls();

    // ─── SEARCH ────────────────────────────────────────────

    var searchInput = document.getElementById('search-input');
    var searchTimeout;

    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(function() {
            var query = searchInput.value.trim().toLowerCase();

            // Remove previous search highlights
            Object.values(nodeElements).forEach(function(el) {
                el.classList.remove('search-match', 'dimmed');
            });

            if (query.length < 2) return;

            var hasMatch = false;
            Object.keys(nodeElements).forEach(function(id) {
                var name = nodeById[id].name.toLowerCase();
                if (name.includes(query)) {
                    nodeElements[id].classList.add('search-match');
                    hasMatch = true;
                } else {
                    nodeElements[id].classList.add('dimmed');
                }
            });

            // Scroll first match into view
            if (hasMatch) {
                var first = document.querySelector('.concept-node.search-match');
                if (first) first.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
            }
        }, 300);
    });

})();
```

### Color Constants (shared with existing viz)

```javascript
var CATEGORY_COLORS = {
    method: '#4C72B0',
    technique: '#55A868',
    metric: '#C44E52',
    property: '#8172B2',
    definition: '#CCB974',
    algorithm: '#64B5CD',
    theorem: '#DD8452',
    other: '#999999'
};

var EDGE_COLORS = {
    uses: '#666666',
    prerequisite: '#C44E52',
    generalizes: '#4C72B0',
    special_case_of: '#55A868',
    example_of: '#CCB974',
    contrasts_with: '#8172B2'
};
```

## Implementation Checklist for Sisyphus

### Step 1: Create the HTML file
- Create `output/chapter-prereqs/index.html`
- Single file: all CSS in `<style>`, all JS in `<script>`
- Load `../knowledge-graph/graph-data.js` via `<script src>`
- No external dependencies (no Cytoscape, no CDN)

### Step 2: Build the chapter columns
- Parse `GRAPH_DATA.nodes`, group by `chapter` field
- Sort chapters numerically (1, 2, ..., 18)
- Within each chapter, sort by section then name
- Render as DOM elements with section subheaders
- Store element references in `nodeElements` map for edge drawing

### Step 3: Build the SVG edge layer
- Absolutely positioned SVG overlaying the chapters row
- `pointer-events: none` so clicks pass through
- Resize SVG dimensions to match `chaptersRow.scrollWidth/scrollHeight`
- Bezier curve drawing function using `getNodeCenter()` for coordinates

### Step 4: Implement the backward trace BFS
- `tracePrerequisites(conceptId, allowedTypes)` function
- Walks `edgeIndex.incoming` recursively
- Returns `{ nodes, edges, byChapter, frontier }`
- Frontier = nodes with no incoming prereqs within the result set

### Step 5: Implement click handler
- Dim all nodes, highlight trace, draw edges, populate sidebar
- Sidebar shows core prereqs + full chain grouped by chapter
- Prereq items are clickable (re-run trace from clicked concept)

### Step 6: Implement filters and search
- Edge type checkboxes (default: prerequisite, uses, special_case_of)
- Search input with debounced filtering
- When filters change and a concept is selected, re-run the trace

### Step 7: Add cross-link to existing viz
- Add "Open Graph View" link in toolbar
- Add "Open Chapter View" link in existing `index.html` toolbar

### What NOT to build (for now)
- No chapter range slider (add later if needed)
- No "show within-chapter edges" toggle (add later if needed)
- No hover preview of edges (click-only interaction first)
- No arrowheads on SVG edges (adds complexity, not needed for v1)
- No zoom/pan on the canvas (browser scroll is sufficient)

## Data Sizes & Performance

- 670 concepts as DOM elements: trivial for browsers
- 151 cross-chapter edges as SVG paths: trivial
- BFS on 670 nodes / 580 edges: instant, no optimization needed
- No layout computation (positions are determined by DOM flow)
- No external libraries to load

The entire page should load and render in under 100ms after `graph-data.js` is parsed.

## Edge Cases

- **Concepts with no section/chapter:** Group into a "Ch ?" column at the end. Currently all 670 have chapters, but guard against it.
- **Circular dependencies:** The BFS uses a visited set, so cycles won't cause infinite loops. Circular prereqs just mean both concepts appear in each other's traces.
- **Ch 14 height (128 concepts):** At 26px per concept + section headers, that's ~3500px. The canvas scrolls vertically. The column's section headers are sticky within the column.
- **Empty trace:** Show "No prerequisites found with current filters" in sidebar.
