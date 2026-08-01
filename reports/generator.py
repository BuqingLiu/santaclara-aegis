"""Compliance report pack generator.

Scans an outputs/<run>/ directory for scenario results and produces:
  compliance_report.pdf   multi-page PDF (cover, KPI table, per-scenario page)
  compliance_report.md    Markdown version from the DMV template
  metrics.xlsx            per-scenario KPI workbook

Usage:  python -m reports.generator outputs/20260729_1902
"""
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "reports" / "template" / "dmv_compliance_report.md"


# --------------------------------------------------------------------------- #
def load_run(run_dir: Path):
    results = []
    for summary in sorted(run_dir.glob("*/summary.json")):
        with open(summary, encoding="utf-8") as f:
            metrics = json.load(f)
        metrics["_dir"] = summary.parent
        results.append(metrics)
    return results


def _telemetry(scenario_dir: Path):
    path = scenario_dir / "telemetry.csv"
    if not path.exists():
        return None
    return pd.read_csv(path)


# --------------------------------------------------------------------------- #
def build_pdf(results, run_dir: Path):
    pdf_path = run_dir / "compliance_report.pdf"
    with PdfPages(pdf_path) as pdf:
        # ---- cover ------------------------------------------------------- #
        fig = plt.figure(figsize=(8.5, 11))
        fig.text(0.5, 0.78, "AV Safety Scenario\nCompliance Report",
                 ha="center", fontsize=26, weight="bold")
        fig.text(0.5, 0.66, "Santa Clara Tech Park / San Jose\n"
                            "El Camino Real x Lawrence Expressway Corridor",
                 ha="center", fontsize=13)
        fig.text(0.5, 0.56, "CARLA 0.9.x Deterministic Simulation Pipeline",
                 ha="center", fontsize=11, style="italic")
        passed = sum(1 for r in results if r["result"] == "PASS")
        review = sum(1 for r in results if r["result"] == "REVIEW")
        failed = sum(1 for r in results if r["result"] == "FAIL")
        fig.text(0.5, 0.44,
                 f"Scenarios executed: {len(results)}\n"
                 f"PASS: {passed}    REVIEW: {review}    FAIL: {failed}",
                 ha="center", fontsize=14)
        fig.text(0.5, 0.30, "Prepared in alignment with CA DMV Autonomous\n"
                            "Vehicle Program reporting expectations "
                            "(13 CCR 227-228)\nand NHTSA pre-crash typology.",
                 ha="center", fontsize=10)
        fig.text(0.5, 0.12, datetime.now().strftime("Generated %Y-%m-%d %H:%M"),
                 ha="center", fontsize=9, color="gray")
        pdf.savefig(fig)
        plt.close(fig)

        # ---- KPI summary table ------------------------------------------- #
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.axis("off")
        cols = ["Scenario", "Result", "minTTC(s)", "minGap(m)",
                "maxDecel(m/s2)", "HardBrakes", "Collisions"]
        cells = [[r["title"][:34], r["result"],
                  r["min_ttc_s"] if r["min_ttc_s"] is not None else "-",
                  r["min_gap_m"] if r["min_gap_m"] is not None else "-",
                  r["max_decel_mps2"], r["hard_brake_count"],
                  r["collision_count"]] for r in results]
        table = ax.table(cellText=cells, colLabels=cols, loc="center",
                         cellLoc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(8.5)
        table.scale(1.0, 1.55)
        for i, r in enumerate(results, start=1):
            color = {"PASS": "#d3f2d9", "REVIEW": "#fff3cd",
                     "FAIL": "#f8d7da"}[r["result"]]
            table[i, 1].set_facecolor(color)
        ax.set_title("Scenario KPI Summary", fontsize=15, weight="bold",
                     pad=24)
        pdf.savefig(fig)
        plt.close(fig)

        # ---- per-scenario pages ------------------------------------------ #
        for r in results:
            df = _telemetry(r["_dir"])
            fig = plt.figure(figsize=(11, 8.5))
            fig.suptitle(f"{r['title']}  [{r['result']}]",
                         fontsize=15, weight="bold")
            fig.text(0.5, 0.925, f"Reference: {r['dmv_ref']}",
                     ha="center", fontsize=9, color="gray")

            if df is not None and len(df):
                ax1 = fig.add_subplot(2, 2, 1)
                ax1.plot(df["sim_time_s"], df["ego_speed_mps"], lw=1.2)
                ax1.set_title("Ego speed (m/s)", fontsize=10)
                ax1.set_xlabel("t (s)", fontsize=8)
                ax1.grid(alpha=0.3)

                ax2 = fig.add_subplot(2, 2, 2)
                gap = pd.to_numeric(df["nearest_threat_gap_m"],
                                    errors="coerce")
                ax2.plot(df["sim_time_s"], gap, lw=1.2, color="darkorange")
                ax2.set_title("Nearest threat gap (m)", fontsize=10)
                ax2.set_xlabel("t (s)", fontsize=8)
                ax2.grid(alpha=0.3)

                ax3 = fig.add_subplot(2, 2, 3)
                ax3.plot(df["sim_time_s"], df["brake"], lw=1.0,
                         color="crimson", label="brake")
                ax3.plot(df["sim_time_s"], df["throttle"], lw=1.0,
                         color="seagreen", label="throttle")
                ax3.legend(fontsize=8)
                ax3.set_title("Control commands", fontsize=10)
                ax3.set_xlabel("t (s)", fontsize=8)
                ax3.grid(alpha=0.3)

                # evidence frame (mid-event camera capture)
                ax4 = fig.add_subplot(2, 2, 4)
                frames = sorted((r["_dir"] / "frames").glob("*.png"))
                if frames:
                    img = plt.imread(frames[min(len(frames) - 1,
                                                int(len(frames) * 0.6))])
                    ax4.imshow(img)
                    ax4.set_title("Chase-camera evidence frame", fontsize=10)
                ax4.axis("off")

            kpi = (f"minTTC {r['min_ttc_s']} s | minGap {r['min_gap_m']} m | "
                   f"maxDecel {r['max_decel_mps2']} m/s2 | "
                   f"hardBrakes {r['hard_brake_count']} | "
                   f"collisions {r['collision_count']} | "
                   f"events: {', '.join(r['events_triggered']) or 'none'}")
            fig.text(0.5, 0.03, kpi, ha="center", fontsize=8)
            pdf.savefig(fig)
            plt.close(fig)
    return pdf_path


# --------------------------------------------------------------------------- #
def build_xlsx(results, run_dir: Path):
    df = pd.DataFrame([{k: v for k, v in r.items()
                        if not k.startswith("_")} for r in results])
    df["events_triggered"] = df["events_triggered"].apply(
        lambda x: "; ".join(x))
    path = run_dir / "metrics.xlsx"
    df.to_excel(path, index=False, sheet_name="Scenario KPIs")
    return path


def build_markdown(results, run_dir: Path):
    template = TEMPLATE.read_text(encoding="utf-8")
    rows = "\n".join(
        f"| {r['title']} | {r['dmv_ref']} | {r['result']} | "
        f"{r['min_ttc_s'] if r['min_ttc_s'] is not None else '-'} | "
        f"{r['min_gap_m'] if r['min_gap_m'] is not None else '-'} | "
        f"{r['collision_count']} |" for r in results)
    passed = sum(1 for r in results if r["result"] == "PASS")
    text = (template
            .replace("{{DATE}}", datetime.now().strftime("%Y-%m-%d"))
            .replace("{{N_SCENARIOS}}", str(len(results)))
            .replace("{{N_PASS}}", str(passed))
            .replace("{{N_REVIEW}}", str(sum(1 for r in results
                                             if r["result"] == "REVIEW")))
            .replace("{{N_FAIL}}", str(sum(1 for r in results
                                           if r["result"] == "FAIL")))
            .replace("{{RESULTS_TABLE}}", rows))
    path = run_dir / "compliance_report.md"
    path.write_text(text, encoding="utf-8")
    return path


def generate(run_dir):
    run_dir = Path(run_dir)
    results = load_run(run_dir)
    if not results:
        print(f"No scenario results found under {run_dir}")
        return None
    pdf = build_pdf(results, run_dir)
    xlsx = build_xlsx(results, run_dir)
    md = build_markdown(results, run_dir)
    print(f"Report pack ready:\n  {pdf}\n  {xlsx}\n  {md}")
    return pdf


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "outputs"
    generate(target)
