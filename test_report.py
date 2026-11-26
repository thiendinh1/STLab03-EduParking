"""Chạy pytest rồi xuất Test Report: JUnit XML, CSV, Excel, HTML và biểu đồ PNG."""
import html
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def run_pytest(out, module, tests):
    """Bước 1: gọi pytest, sinh kết quả thô (XML), báo cáo HTML và số liệu coverage."""
    cmd = [sys.executable, "-m", "pytest", *tests, "-q", "--tb=line", "-p", "no:cacheprovider",
           f"--junitxml={out / 'junit.xml'}",
           f"--html={out / 'pytest_report.html'}", "--self-contained-html",
           f"--cov={module}", "--cov-branch", f"--cov-report=json:{out / 'coverage.json'}"]
    done = subprocess.run(cmd, capture_output=True, text=True)
    (out / "pytest_log.txt").write_text(done.stdout + done.stderr, encoding="utf-8")
    if done.returncode not in (0, 1):              # 0: pass hết, 1: có fail, khác: lỗi cấu hình
        raise RuntimeError(done.stdout + done.stderr)


def read_results(junit_file):
    """Bước 2: đọc junit.xml. Tên lớp -> REQ, tên hàm -> loại test."""
    rows = []
    for i, case in enumerate(ET.parse(junit_file).iter("testcase"), 1):
        bad = case.find("failure")
        err = case.find("error")
        skip = case.find("skipped")
        status = "FAIL" if bad is not None else "BLOCKED" if err is not None or skip is not None else "PASS"
        node = next((n for n in (bad, err, skip) if n is not None), None)
        cls = case.get("classname", "").split(".")[-1]
        req = re.match(r"TestReq(\d+)", cls)
        kind = re.match(r"test_(positive|negative|edge)_", case.get("name"))
        rows.append({
            "test_id": f"TC-{i:03d}",
            "requirement": f"REQ-{req.group(1)}" if req else "UNMAPPED",
            "type": kind.group(1) if kind else "other",
            "test_name": case.get("name"),
            "status": status,
            "time_s": float(case.get("time", 0)),
            "message": (node.get("message") or "").replace("\n", " ")[:160] if node is not None else "",
        })
    return pd.DataFrame(rows)


def build_report(name, module, tests, requirements, out_dir):
    """Bước 3: tổng hợp và xuất mọi định dạng. Trả về (bảng chi tiết, bảng tổng hợp, coverage)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    run_pytest(out, module, tests)
    df = read_results(out / "junit.xml")
    cov = json.loads((out / "coverage.json").read_text())["totals"]
    line = round(100 * cov["covered_lines"] / cov["num_statements"], 1)
    branch = round(100 * cov["covered_branches"] / cov["num_branches"], 1) if cov["num_branches"] else 100.0
    n = df["status"].value_counts().reindex(["PASS", "FAIL", "BLOCKED"], fill_value=0)
    summary = pd.DataFrame([{
        "executed": len(df), "pass": n["PASS"], "fail": n["FAIL"], "blocked": n["BLOCKED"],
        "pass_rate_%": round(100 * n["PASS"] / len(df), 1),
        "req_covered": f"{df['requirement'].isin(requirements).groupby(df['requirement']).any().sum()}/{len(requirements)}",
        "line_cov_%": line, "branch_cov_%": branch}])
    trace = (df.groupby(["requirement", "status"]).size().unstack(fill_value=0)
               .reindex(columns=["PASS", "FAIL", "BLOCKED"], fill_value=0)
               .reindex(list(requirements), fill_value=0))
    trace.columns.name = None
    trace.insert(0, "description", [requirements[r] for r in trace.index])
    trace["result"] = ["NOT TESTED" if a + b + c == 0 else "PASS" if b + c == 0 else "FAIL"
                       for a, b, c in trace[["PASS", "FAIL", "BLOCKED"]].values]
    trace = trace.reset_index().rename(columns={"index": "requirement"})

    df.to_csv(out / "test_execution.csv", index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(out / "test_report.xlsx", engine="openpyxl") as xls:
        for sheet, data in (("Summary", summary), ("Traceability", trace),
                            ("Execution", df), ("Failures", df[df.status != "PASS"])):
            data.to_excel(xls, index=False, sheet_name=sheet)
            for col in xls.sheets[sheet].columns:
                width = max(len(str(c.value or "")) for c in col)
                xls.sheets[sheet].column_dimensions[col[0].column_letter].width = min(width + 3, 60)
    draw_chart(trace, df, name, out / "chart.png")
    write_html(name, summary, trace, df, out / "dashboard.html")
    print(f"{name}: executed {len(df)} | PASS {n['PASS']} | FAIL {n['FAIL']} | BLOCKED {n['BLOCKED']}"
          f" | line {line}% | branch {branch}%")
    return df, summary, trace


def draw_chart(trace, df, name, file):
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4), gridspec_kw={"width_ratios": [2, 1]})
    a.bar(trace.requirement, trace.PASS, color="#16a34a", label="PASS")
    a.bar(trace.requirement, trace.FAIL + trace.BLOCKED, bottom=trace.PASS, color="#dc2626", label="FAIL/BLOCKED")
    a.tick_params(axis="x", rotation=45)
    a.set_ylabel("Test cases")
    a.set_title(name)
    a.legend()
    kinds = df.groupby("type").size()
    bars = b.barh(kinds.index, kinds.values, color="#2F75B5")
    b.bar_label(bars, padding=3)
    b.set_title("Test type")
    b.set_xlim(0, kinds.max() * 1.15)
    fig.tight_layout()
    fig.savefig(file, dpi=130)
    plt.close(fig)


def write_html(name, summary, trace, df, file):
    def cells(row, tag="td"):
        return "".join(f'<{tag} class="{v}">{html.escape(str(v))}</{tag}>' for v in row)

    def table(data):
        body = "".join(f"<tr>{cells(r)}</tr>" for r in data.values)
        return f"<table><tr>{cells(data.columns, 'th')}</tr>{body}</table>"

    cards = "".join(f'<div class="card"><b>{html.escape(str(v))}</b><span>{k}</span></div>'
                    for k, v in summary.iloc[0].items())
    file.write_text(f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{name}</title><style>
body{{font:14px Arial;margin:28px;color:#14233c}}h1{{color:#17385f;margin:0}}table{{border-collapse:collapse;width:100%;margin:8px 0 20px}}
td,th{{border:1px solid #cbd5e1;padding:6px 8px;text-align:left}}th{{background:#16385e;color:#fff}}
.card{{display:inline-block;background:#edf3f9;border-radius:10px;padding:10px 16px;margin:12px 8px 8px 0}}
.card b{{display:block;font-size:22px}}.PASS{{color:#15803d;font-weight:700}}.FAIL,.BLOCKED{{color:#b91c1c;font-weight:700}}
th.PASS,th.FAIL,th.BLOCKED{{color:#fff}}</style></head><body><h1>{name}</h1>
<div>Generated: {datetime.now():%d/%m/%Y %H:%M}</div>{cards}<h2>Requirement traceability</h2>{table(trace)}
<img src="chart.png" style="max-width:900px"><h2>Execution details</h2>{table(df)}</body></html>""", encoding="utf-8")
