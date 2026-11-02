# Afternoon run: validate deals\data\<date>-b.json, build, commit and push.
param([string]$Date = (Get-Date -Format yyyy-MM-dd))
$file = "deals\data\$Date-b.json"

# Afternoon Awin picks: 2 more candles and the afternoon share of the gift pins (busy season: more pins)
python tools\awin_status.py 2>&1 | Out-String
python tools\merchant_health.py 2>&1 | Out-String
python tools\candles.py --pick $Date 2 --afternoon 2>&1 | Out-String
python tools\gifts.py --pick $Date --afternoon 2>&1 | Out-String
# Second price check of the day (savings and stock), done even when there is no afternoon roundup
python tools\prices.py --quick 2>&1 | Out-String
# Live voucher codes and offers from our Awin merchants (homepage, gift guide, eSIM guide, /vouchers/)
python tools\vouchers.py 2>&1 | Out-String
python tools\collages.py --make $Date --afternoon 2>&1 | Out-String

if (-not (Test-Path $file)) {
    python tools\build_deals.py 2>&1 | Out-String
    cmd /c "git add deals sitemap.xml robots.txt 2>&1" | Out-String
    git commit -q -m "Daily Deals UK: $Date afternoon Awin picks" | Out-String
    cmd /c "git push 2>&1" | Out-String
    if ($LASTEXITCODE) { throw "git push failed" }
    if (Test-Path tools\amazon_paused.txt) { "Amazon roundups paused - prices refreshed"; return }
    throw "No $file written - no afternoon roundup today (prices refreshed)"
}

$check = python tools\build_deals.py --check $file 2>&1 | Out-String
if ($LASTEXITCODE) {
    Move-Item $file "C:\Users\User\ClaudeJobs\rejected_$Date-b.json" -Force
    throw "Data file failed validation (moved to ClaudeJobs\rejected_$Date-b.json):`n$check"
}

python tools\build_deals.py 2>&1 | Out-String
if ($LASTEXITCODE) { throw "build_deals.py failed" }

cmd /c "git add deals sitemap.xml robots.txt 2>&1" | Out-String
git commit -q -m "Daily Deals UK: $Date afternoon roundup" | Out-String
cmd /c "git push 2>&1" | Out-String
if ($LASTEXITCODE) { throw "git push failed" }
"Published https://dailydealsuk.co.uk/deals/$Date-b/"
