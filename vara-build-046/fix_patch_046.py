from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: fix_patch_046.py <patch-file>")

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
old = '''rep(\n    \'\'\'        int apps = installedApps();\n        int issues = auditIssueCount();\'\'\',\n    \'\'\'        AppRiskSummary risk = analyzeAppRisk();\n        int apps = risk.visible;\n        int issues = auditIssueCount();\'\'\',\n    \'report app risk analysis\',\n)'''
new = '''rep(\n    \'\'\'    private void renderReport() {\n        currentPage = "report";\n        basePage(); addTopBar(t("Security Report", "گزارش امنیتی"), true);\n\n        int apps = installedApps();\n        int issues = auditIssueCount();\'\'\',\n    \'\'\'    private void renderReport() {\n        currentPage = "report";\n        basePage(); addTopBar(t("Security Report", "گزارش امنیتی"), true);\n\n        AppRiskSummary risk = analyzeAppRisk();\n        int apps = risk.visible;\n        int issues = auditIssueCount();\'\'\',\n    \'report app risk analysis\',\n)'''
if s.count(old) != 1:
    raise SystemExit(f"fix failed: expected one target, found {s.count(old)}")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("VARA 0.4.6 patch anchor fixed")
