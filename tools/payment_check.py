"""Weekly Awin payment check, run on the server (Mondays 09:35) - no browser or laptop needed.

Awin's "Exposure Level" (payment risk 1-4) is only shown on its website, so this uses what the Awin API
does give for every merchant: average payment time (days to pay commission), approval rate and EPC.
  - joined, pending and watch-list merchants are checked
  - "slow payer": average payment time over SLOW_DAYS (merchant_health pauses joined merchants over
    PAUSE_DAYS, except the ones Jason keeps running on purpose)
  - results go to ClaudeJobs\\merchant_kpi.json, and a short report is emailed to Jason

  python tools/payment_check.py            check, save, email
  python tools/payment_check.py --dry-run  check and print, no email
"""
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import awin_status as aw
import merchant_health as mh

JOBS = Path(r"C:\Users\User\ClaudeJobs")
KPI = JOBS / "merchant_kpi.json"
SLOW_DAYS = 90        # flagged in the report
PAUSE_DAYS = 120      # merchant_health pauses joined merchants slower than this
LOW_APPROVAL = 80.0   # % of sales the merchant approves; lower means many commissions get declined
TO = ["jason_townsley@yahoo.com"]


def kpi(adv, relationship):
    url = (f"https://api.awin.com/publishers/{aw.PUBLISHER}/programmedetails?advertiserId={adv}"
           f"&relationship={relationship}")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {aw.token()}", "User-Agent": "DailyDealsUK/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        k = json.load(r).get("kpi", {})
    days = k.get("averagePaymentTime")
    return {"pay_days": int(days) if str(days or "").isdigit() else None,
            "approval": k.get("approvalPercentage"), "epc": k.get("epc")}


def flags(k):
    out = []
    if k.get("pay_days") is not None and k["pay_days"] > SLOW_DAYS:
        out.append(f"slow payer ({k['pay_days']} days on average)")
    if k.get("approval") is not None and k["approval"] < LOW_APPROVAL:
        out.append(f"low approval ({k['approval']:.0f}%)")
    return out


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
    state = json.loads(aw.STATE.read_text(encoding="utf-8")) if aw.STATE.exists() else {}
    who = {int(i): (v["name"], v["status"]) for i, v in state.items() if v.get("status") in ("joined", "pending")}
    for i, n in mh.WATCHLIST.items():
        who.setdefault(i, (n, "watch list"))
    old = json.loads(KPI.read_text(encoding="utf-8")).get("merchants", {}) if KPI.exists() else {}
    res = {}
    for adv, (name, status) in sorted(who.items(), key=lambda x: x[1][0].lower()):
        rel = {"joined": "joined", "pending": "pending"}.get(status, "notjoined")
        try:
            k = kpi(adv, rel)
        except (urllib.error.URLError, OSError, ValueError) as e:
            k = {"error": str(e)[:60]}
        res[str(adv)] = {"name": name, "status": status, **k, "flags": flags(k)}
        time.sleep(3.1)                                  # Awin API rate limit
    KPI.write_text(json.dumps({"checked": date.today().isoformat(), "merchants": res}, indent=1), encoding="utf-8")

    lines, changes = [], []
    for adv, r in res.items():
        was = old.get(adv, {}).get("flags", [])
        if bool(r["flags"]) != bool(was) and adv in old:
            changes.append(f"{r['name']}: " + ("now " + "; ".join(r["flags"]) if r["flags"] else "back to normal"))
        if r["flags"]:
            lines.append(f"{r['name']} ({r['status']}): " + "; ".join(r["flags"]))
    joined = [r for r in res.values() if r["status"] == "joined"]
    print(f"Payment check: {len(res)} merchants, {len(lines)} flagged")
    for ln in lines:
        print("  " + ln)
    for c in changes:
        print("  CHANGE " + c)
    if "--dry-run" in argv:
        return 0

    # merchant_health picks this up on the next deals run (07:00) to pause very slow payers
    import html
    def row(r):
        days = "-" if r.get("pay_days") is None else str(r["pay_days"])
        appr = "-" if r.get("approval") is None else f"{r['approval']:.0f}%"
        status = html.escape("; ".join(r["flags"])) or "OK"
        return f"<tr><td>{html.escape(r['name'])}</td><td>{days}</td><td>{appr}</td><td>{status}</td></tr>"
    rows = "".join(row(r) for r in joined)
    body = (f"<p>Weekly Awin payment check ({date.today():%a %d %b}).</p>"
            + (f"<p><b>Changes since last week:</b><br>{'<br>'.join(html.escape(c) for c in changes)}</p>" if changes else
               "<p>No changes since last week.</p>")
            + "<p><b>Joined merchants</b> (average days to pay commission, approval rate):</p>"
            f"<table border='1' cellpadding='4' style='border-collapse:collapse;font-size:13px'>"
            f"<tr><th>Merchant</th><th>Days to pay</th><th>Approval</th><th>Status</th></tr>{rows}</table>"
            + (f"<p><b>Flagged pending / watch-list merchants:</b><br>"
               + "<br>".join(html.escape(l) for l in lines if "(joined)" not in l) + "</p>"
               if any("(joined)" not in l for l in lines) else "")
            + f"<p style='color:#666;font-size:12px'>Slow payer = over {SLOW_DAYS} days; joined merchants over {PAUSE_DAYS} days "
              "are paused from new pins automatically (Candles Direct is kept running by choice).</p>")
    sys.path.insert(0, str(JOBS / "cctv"))
    from cctv_alerts import send
    send(f"Awin payment check ({date.today():%d %b}): " + (f"{len(changes)} change(s)" if changes else "no changes"),
         body, [], False, TO)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
