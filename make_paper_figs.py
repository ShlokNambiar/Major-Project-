"""Paper figures for the 18-attack system: per-attack F1 and per-family mean F1.

Numbers are read from results/results_v18_final.json (ours = ensemble,
no neighbour attention = no_neighbour_ensemble) and results/results_v18.json
(rule_based.SSC_speed_check). Message-level labels throughout.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(ROOT, "results")
OUT = os.path.join(ROOT, "paper")

C_OURS = "#2a78d6"
C_NONB = "#eb6834"
C_RULE = "#8a8f98"

FAMILIES = [
    ("Position", ["ConstPos", "ConstPosOffset", "RandomPos", "RandomPosOffset"]),
    ("Speed", ["ConstSpeed", "ConstSpeedOffset", "RandomSpeed"]),
    ("Stop/replay/delay", ["EventualStop", "Disruptive", "DataReplay", "DelayedMessages"]),
    ("DoS", ["DoS", "DoSRandom", "DoSDisruptive"]),
    ("Sybil", ["GridSybil", "DataReplaySybil", "DoSRandomSybil", "DoSDisruptiveSybil"]),
]
ATTACKS = [a for _, al in FAMILIES for a in al]

plt.rcParams.update({
    "font.size": 7,
    "axes.labelsize": 7,
    "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5,
    "legend.fontsize": 6.5,
    "axes.linewidth": 0.5,
    "xtick.major.width": 0.5,
    "ytick.major.width": 0.5,
    "xtick.major.size": 2,
    "ytick.major.size": 0,
    "pdf.fonttype": 42,
    "font.family": "DejaVu Sans",
})


def load():
    fin = json.load(open(os.path.join(RES, "results_v18_final.json")))
    v18 = json.load(open(os.path.join(RES, "results_v18.json")))
    rule = v18["rule_based"]["SSC_speed_check"]["message"]["test"]

    def f1(d, a):
        x = d[a]
        return float(x["f1"] if isinstance(x, dict) else x)

    ours = {a: f1(fin["ensemble"]["message"], a) for a in ATTACKS}
    nonb = {a: f1(fin["no_neighbour_ensemble"]["message"], a) for a in ATTACKS}
    rb = {a: f1(rule, a) for a in ATTACKS}
    return ours, nonb, rb


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def fig_attacks(ours, nonb, rb):
    fig, ax = plt.subplots(figsize=(3.4, 3.1))
    h = 0.26
    ypos, y, fam_spans = [], 0.0, []
    for fam, al in FAMILIES:
        start = y
        for _ in al:
            ypos.append(y)
            y += 1
        fam_spans.append((fam, start, y - 1))
        y += 0.6  # gap between families
    ypos = np.array(ypos)
    series = [("Ours", ours, C_OURS), ("No neighbour attention", nonb, C_NONB),
              ("Speed-check rule", rb, C_RULE)]
    for i, (lab, d, c) in enumerate(series):
        ax.barh(ypos + (i - 1) * h, [d[a] for a in ATTACKS], height=h,
                color=c, label=lab, linewidth=0)
    # mark exact-zero rule bars so they read as 0, not as missing
    for a, yy in zip(ATTACKS, ypos):
        if rb[a] < 0.005:
            ax.text(0.018, yy + h, "0", va="center", ha="left", fontsize=6.5, color=C_RULE)
    ax.set_yticks(ypos)
    ax.set_yticklabels(ATTACKS)
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_xlabel("F1 (message labels)")
    ax.xaxis.grid(True, linewidth=0.3, color="#d0d3d8")
    ax.set_axisbelow(True)
    style(ax)
    ax.set_ylim(y - 0.6 - 0.5 + 0.2, -0.5 - 0.2)
    # family separators + labels (right edge, inside axis frame margin)
    for k, (fam, s, e) in enumerate(fam_spans):
        if k > 0:
            ax.axhline(s - 0.8, color="#9aa0a6", linewidth=0.4, linestyle=(0, (2, 2)),
                       xmin=-0.42, clip_on=False)
        lab = "Replay/delay" if fam.startswith("Stop") else fam
        ax.text(1.02, (s + e) / 2, lab, linespacing=1.0, transform=ax.get_yaxis_transform(),
                rotation=270, va="center", ha="left", fontsize=6.5, color="#555b63")
    ax.legend(loc="lower center", bbox_to_anchor=(0.42, 1.0), ncol=3, frameon=False,
              handlelength=1.0, columnspacing=0.8, handletextpad=0.4, borderaxespad=0.2)
    fig.subplots_adjust(left=0.30, right=0.92, top=0.94, bottom=0.125)
    fig.savefig(os.path.join(OUT, "fig_attacks18.pdf"))
    plt.close(fig)


def fig_families(ours, nonb, rb):
    names = [f for f, _ in FAMILIES]
    means = {lab: [float(np.mean([d[a] for a in al])) for _, al in FAMILIES]
             for lab, d in (("ours", ours), ("nonb", nonb), ("rule", rb))}
    fig, ax = plt.subplots(figsize=(3.4, 1.65))
    x = np.arange(len(names))
    w = 0.26
    bars = ax.bar(x - w, means["ours"], w, color=C_OURS, label="Ours", linewidth=0)
    ax.bar(x, means["nonb"], w, color=C_NONB, label="No neighbour attention", linewidth=0)
    ax.bar(x + w, means["rule"], w, color=C_RULE, label="Speed-check rule", linewidth=0)
    for b, v in zip(bars, means["ours"]):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.2f}", ha="center",
                va="bottom", fontsize=6.5, color=C_OURS)
    ax.set_xticks(x)
    ax.set_xticklabels(["Position", "Speed", "Stop/replay/\ndelay", "DoS", "Sybil"], fontsize=6.5)
    ax.set_ylim(0, 1.12)
    ax.set_yticks(np.linspace(0, 1, 6))
    ax.set_ylabel("Mean F1")
    ax.yaxis.grid(True, linewidth=0.3, color="#d0d3d8")
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=0)
    style(ax)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=3, frameon=False,
              handlelength=1.0, columnspacing=0.8, handletextpad=0.4, borderaxespad=0.2)
    fig.subplots_adjust(left=0.12, right=0.99, top=0.86, bottom=0.21)
    fig.savefig(os.path.join(OUT, "fig_families.pdf"))
    plt.close(fig)
    return names, means


def main():
    ours, nonb, rb = load()
    fig_attacks(ours, nonb, rb)
    names, means = fig_families(ours, nonb, rb)
    print("attack,ours,no_neighbour,speed_rule")
    for a in ATTACKS:
        print(f"{a},{ours[a]:.4f},{nonb[a]:.4f},{rb[a]:.4f}")
    print("family,ours,no_neighbour,speed_rule")
    for i, n in enumerate(names):
        print(f"{n},{means['ours'][i]:.4f},{means['nonb'][i]:.4f},{means['rule'][i]:.4f}")


if __name__ == "__main__":
    main()
