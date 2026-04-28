"""Generate a static PNG visualization of the knowledge graph."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

# Graph data
nodes = [
    {"id": "paper", "label": "ChaosBench-Logic\n(Benchmark Paper)", "type": "Paper", "x": 0, "y": 0},
    {"id": "m1", "label": "Chain-of-Thought\n(baseline)", "type": "Method", "x": -4, "y": 3},
    {"id": "m2", "label": "Tool-Augmented\nReasoning (baseline)", "type": "Method", "x": -4, "y": -3},
    {"id": "p1", "label": "LLM Reasoning\nEvaluation", "type": "Problem", "x": 4, "y": 4},
    {"id": "p2", "label": "Domain-Specific\nMisconception", "type": "Problem", "x": 5, "y": 0},
    {"id": "p3", "label": "Scientific QA\n& Domain Reasoning", "type": "Problem", "x": 4, "y": -4},
    {"id": "r1", "label": "CHAOSBENCH-LOGIC\nBenchmark", "type": "Resource", "x": 0, "y": 5},
    {"id": "r2", "label": "BIG-Bench", "type": "Resource", "x": -3, "y": 6},
    {"id": "r3", "label": "SciBench", "type": "Resource", "x": 3, "y": 6},
    {"id": "i1", "label": "Dialogue coherence\ncollapses to 0", "type": "Insight", "x": -5, "y": -1},
    {"id": "i2", "label": "Local plausible\nmasks inconsistency", "type": "Insight", "x": 5, "y": -2},
    {"id": "i3", "label": "Temperature-zero\nreveals failures", "type": "Insight", "x": 0, "y": -6},
]

edges = [
    {"from": "paper", "to": "m1", "label": "uses", "style": "dashed", "color": "#999"},
    {"from": "paper", "to": "m2", "label": "uses", "style": "dashed", "color": "#999"},
    {"from": "paper", "to": "p1", "label": "addresses", "style": "solid", "color": "#43a047"},
    {"from": "paper", "to": "p2", "label": "addresses", "style": "solid", "color": "#43a047"},
    {"from": "paper", "to": "p3", "label": "addresses", "style": "solid", "color": "#43a047"},
    {"from": "paper", "to": "r1", "label": "proposes", "style": "solid", "color": "#e53935", "width": 2.5},
    {"from": "paper", "to": "r2", "label": "cites", "style": "solid", "color": "#fb8c00"},
    {"from": "paper", "to": "r3", "label": "cites", "style": "solid", "color": "#fb8c00"},
    {"from": "paper", "to": "i1", "label": "finds", "style": "solid", "color": "#8e24aa"},
    {"from": "paper", "to": "i2", "label": "finds", "style": "solid", "color": "#8e24aa"},
    {"from": "paper", "to": "i3", "label": "finds", "style": "solid", "color": "#8e24aa"},
    {"from": "r1", "to": "p1", "label": "evaluates", "style": "solid", "color": "#fb8c00"},
    {"from": "r1", "to": "p2", "label": "diagnoses", "style": "solid", "color": "#fb8c00"},
]

colors = {
    "Paper": "#ffcdd2",
    "Method": "#bbdefb",
    "Problem": "#c8e6c9",
    "Resource": "#ffe0b2",
    "Insight": "#e1bee7",
}
borders = {
    "Paper": "#e53935",
    "Method": "#1e88e5",
    "Problem": "#43a047",
    "Resource": "#fb8c00",
    "Insight": "#8e24aa",
}

fig, ax = plt.subplots(1, 1, figsize=(18, 14))
ax.set_xlim(-8, 8)
ax.set_ylim(-8, 8)
ax.axis('off')
ax.set_facecolor('#fafafa')
fig.patch.set_facecolor('#fafafa')

# Draw edges
for e in edges:
    src = next(n for n in nodes if n["id"] == e["from"])
    dst = next(n for n in nodes if n["id"] == e["to"])
    lw = e.get("width", 1.5)
    ls = '--' if e.get("style") == "dashed" else '-'
    ax.annotate("", xy=(dst["x"], dst["y"]), xytext=(src["x"], src["y"]),
                arrowprops=dict(arrowstyle="-|>", color=e["color"], lw=lw, ls=ls,
                               connectionstyle="arc3,rad=0.05"))
    # Edge label
    mx, my = (src["x"] + dst["x"]) / 2, (src["y"] + dst["y"]) / 2
    ax.text(mx, my, e["label"], fontsize=8, ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='none', alpha=0.85))

# Draw nodes
for n in nodes:
    c = colors[n["type"]]
    b = borders[n["type"]]
    box = FancyBboxPatch((n["x"] - 1.1, n["y"] - 0.55), 2.2, 1.1,
                         boxstyle="round,pad=0.05,rounding_size=0.2",
                         facecolor=c, edgecolor=b, linewidth=2, zorder=3)
    ax.add_patch(box)
    ax.text(n["x"], n["y"], n["label"], fontsize=9, ha='center', va='center',
            fontweight='bold' if n["type"] == "Paper" else 'normal', zorder=4)

# Legend
legend_items = [
    ("Paper", "#ffcdd2", "#e53935"),
    ("Method", "#bbdefb", "#1e88e5"),
    ("Problem", "#c8e6c9", "#43a047"),
    ("Resource", "#ffe0b2", "#fb8c00"),
    ("Insight", "#e1bee7", "#8e24aa"),
]
for i, (name, fc, ec) in enumerate(legend_items):
    x = -7.5 + i * 3.2
    y = -7.3
    rect = plt.Rectangle((x - 0.3, y - 0.2), 0.6, 0.4, facecolor=fc, edgecolor=ec, linewidth=1.5)
    ax.add_patch(rect)
    ax.text(x + 0.5, y, name, fontsize=10, va='center')

# Title
ax.text(0, 7.5, 'ChaosBench-Logic Knowledge Graph (Auto-Extracted)', fontsize=16, ha='center',
        fontweight='bold', color='#333')
ax.text(0, 7.0, 'Red = Error/Warning  |  Dashed = Baseline (not proposed)  |  Thick Red = Main Contribution',
        fontsize=10, ha='center', color='#666', style='italic')

plt.tight_layout()
plt.savefig('/home/cuizhixing/research_graph/viz/graph.png', dpi=150, bbox_inches='tight',
            facecolor='#fafafa', edgecolor='none')
print("Saved: /home/cuizhixing/research_graph/viz/graph.png")
