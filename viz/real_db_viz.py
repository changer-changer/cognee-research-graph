"""Generate visualization from actual Kuzu graph database."""
import sys
sys.path.insert(0, '/home/cuizhixing/cognee-env/lib/python3.10/site-packages')
import kuzu
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

db = kuzu.Database('/home/cuizhixing/cognee-env/lib/python3.10/site-packages/cognee/.cognee_system/databases/cognee_graph_kuzu')
conn = kuzu.Connection(db)

# Query all nodes
result = conn.execute('MATCH (n:Node) RETURN n.id, n.type, n.name, n.properties')
nodes = []
while result.has_next():
    row = result.get_next()
    node_id, ntype, name, props = row
    nodes.append({
        'id': node_id,
        'type': ntype,
        'name': name or '(unnamed)',
        'props': props or '',
    })

# Query all edges
result = conn.execute('MATCH (a:Node)-[r]->(b:Node) RETURN a.id, r.relationship_name, b.id')
edges = []
while result.has_next():
    row = result.get_next()
    edges.append({'from': row[0], 'to': row[2], 'rel': row[1]})

# Build lookup
node_lookup = {n['id']: n for n in nodes}

# Deduplicate by name for display (show unique entities)
seen_names = set()
unique_nodes = []
for n in nodes:
    key = (n['type'], n['name'])
    if key not in seen_names:
        seen_names.add(key)
        unique_nodes.append(n)

# But we need to map original IDs to display IDs for edges
# For edges, use original nodes

# Categorize nodes
type_colors = {
    'Paper': ('#ffcdd2', '#e53935'),
    'Method': ('#bbdefb', '#1e88e5'),
    'Problem': ('#c8e6c9', '#43a047'),
    'Resource': ('#ffe0b2', '#fb8c00'),
    'Insight': ('#e1bee7', '#8e24aa'),
    'PaperRelations': ('#fff9c4', '#fbc02d'),
    'MethodRelations': ('#cfd8dc', '#546e7a'),
}

# Layout: circular by type
type_groups = {}
for n in nodes:
    t = n['type']
    if t not in type_groups:
        type_groups[t] = []
    type_groups[t].append(n)

positions = {}
angle_offset = 0
radius = 5
for t, group in type_groups.items():
    count = len(group)
    for i, n in enumerate(group):
        angle = angle_offset + (2 * np.pi * i / max(count, 1))
        # Stagger radius slightly to avoid overlap
        r = radius + (i % 3) * 0.8
        positions[n['id']] = (r * np.cos(angle), r * np.sin(angle))
    angle_offset += 2 * np.pi / len(type_groups)

fig, ax = plt.subplots(1, 1, figsize=(22, 16))
ax.set_xlim(-9, 9)
ax.set_ylim(-9, 9)
ax.axis('off')
ax.set_facecolor('#fafafa')
fig.patch.set_facecolor('#fafafa')

# Draw edges first (so they appear behind nodes)
for e in edges:
    src = node_lookup.get(e['from'])
    dst = node_lookup.get(e['to'])
    if not src or not dst:
        continue
    if src['id'] not in positions or dst['id'] not in positions:
        continue
    x1, y1 = positions[src['id']]
    x2, y2 = positions[dst['id']]

    # Skip test data edges for cleaner viz
    if src['name'] in ['A', 'B', 'Machine Translation'] or dst['name'] in ['A', 'B', 'Machine Translation']:
        continue

    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", color='#aaa', lw=0.8,
                               connectionstyle="arc3,rad=0.1"))
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    ax.text(mx, my, e['rel'], fontsize=6, ha='center', va='center',
            color='#666', style='italic',
            bbox=dict(boxstyle='round,pad=0.15', facecolor='white', edgecolor='none', alpha=0.8))

# Draw nodes
for n in nodes:
    if n['id'] not in positions:
        continue
    # Skip test data
    if n['name'] in ['A', 'B', 'Machine Translation', 'WMT-14', 'LoRA']:
        continue

    fc, ec = type_colors.get(n['type'], ('#eeeeee', '#999'))
    x, y = positions[n['id']]

    label = n['name'] if n['name'] != '(unnamed)' else n['type']
    # Shorten long labels
    if len(label) > 30:
        label = label[:27] + '...'

    w = max(1.8, len(label) * 0.18)
    h = 0.7

    box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                         boxstyle="round,pad=0.02,rounding_size=0.15",
                         facecolor=fc, edgecolor=ec, linewidth=1.5, zorder=3, alpha=0.95)
    ax.add_patch(box)

    fontsize = 7 if len(label) > 20 else 8
    weight = 'bold' if n['type'] == 'Paper' else 'normal'
    ax.text(x, y, label, fontsize=fontsize, ha='center', va='center',
            fontweight=weight, zorder=4, color='#222')

# Legend
legend_items = [
    ('Paper', type_colors['Paper'][0], type_colors['Paper'][1]),
    ('Method', type_colors['Method'][0], type_colors['Method'][1]),
    ('Problem', type_colors['Problem'][0], type_colors['Problem'][1]),
    ('Resource', type_colors['Resource'][0], type_colors['Resource'][1]),
    ('Insight', type_colors['Insight'][0], type_colors['Insight'][1]),
    ('PaperRelations', type_colors['PaperRelations'][0], type_colors['PaperRelations'][1]),
    ('MethodRelations', type_colors['MethodRelations'][0], type_colors['MethodRelations'][1]),
]
for i, (name, fc, ec) in enumerate(legend_items):
    x = -8.5 + (i % 4) * 4.5
    y = -8.5 if i < 4 else -7.8
    rect = plt.Rectangle((x - 0.25, y - 0.15), 0.5, 0.3, facecolor=fc, edgecolor=ec, linewidth=1.5)
    ax.add_patch(rect)
    ax.text(x + 0.4, y, name, fontsize=9, va='center')

# Title and stats
type_counts = {}
for n in nodes:
    t = n['type']
    type_counts[t] = type_counts.get(t, 0) + 1

stats_text = f"Nodes: {len(nodes)} | Edges: {len(edges)} | " + " | ".join([f"{k}: {v}" for k, v in sorted(type_counts.items())])
ax.text(0, 8.5, 'Cognee Graph Database - Actual Stored Data', fontsize=16, ha='center', fontweight='bold', color='#333')
ax.text(0, 8.0, stats_text, fontsize=10, ha='center', color='#666', style='italic')
ax.text(0, -8.0, 'Gray arrows = relationships  |  Filtered: test data (A, B, Machine Translation, WMT-14, LoRA)',
        fontsize=9, ha='center', color='#999', style='italic')

plt.tight_layout()
plt.savefig('/home/cuizhixing/research_graph/viz/real_database_graph.png', dpi=150, bbox_inches='tight',
            facecolor='#fafafa', edgecolor='none')
print("Saved: /home/cuizhixing/research_graph/viz/real_database_graph.png")

# Also save detailed text report
report = []
report.append("=" * 70)
report.append("COGNEE GRAPH DATABASE CONTENT REPORT")
report.append("=" * 70)
report.append(f"\nTotal Nodes: {len(nodes)}")
report.append(f"Total Edges: {len(edges)}")
report.append(f"\nNode Type Breakdown:")
for t, c in sorted(type_counts.items()):
    report.append(f"  {t}: {c}")

report.append(f"\n{'='*70}")
report.append("ALL NODES")
report.append(f"{'='*70}")
for n in sorted(nodes, key=lambda x: (x['type'], x['name'])):
    report.append(f"  [{n['type']}] {n['name']}")

report.append(f"\n{'='*70}")
report.append("ALL EDGES")
report.append(f"{'='*70}")
for e in edges:
    src = node_lookup.get(e['from'], {})
    dst = node_lookup.get(e['to'], {})
    src_name = src.get('name') or src.get('type', '?')
    dst_name = dst.get('name') or dst.get('type', '?')
    report.append(f"  {src_name} --{e['rel']}--> {dst_name}")

with open('/home/cuizhixing/research_graph/viz/db_content_report.txt', 'w') as f:
    f.write('\n'.join(report))
print("Saved: /home/cuizhixing/research_graph/viz/db_content_report.txt")
