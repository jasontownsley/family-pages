# Runs after Claude: validate today's data file, build the site, commit and push.
param([string]$Date = (Get-Date -Format yyyy-MM-dd))
$file = "deals\data\$Date.json"

# Awin programme statuses (API token in ClaudeJobs, not the repo); shows newly approved merchants in the log
python tools\awin_status.py 2>&1 | Out-String

# Candles Direct picks (Awin feed) don't depend on the Amazon research, so they go out either way
python tools\candles.py --pick $Date 2>&1 | Out-String
$candlesOk = -not $LASTEXITCODE
# Christmas gift picks from the other Awin merchants (own board)
python tools\gifts.py --pick $Date 2>&1 | Out-String
if ($LASTEXITCODE) { $candlesOk = $false }

if (-not (Test-Path $file)) {
    if ($candlesOk) {
        cmd /c "git add deals 2>&1" | Out-String
        git commit -q -m "Daily Deals UK: $Date candles only" | Out-String
        cmd /c "git push 2>&1" | Out-String
    }
    throw "No $file written - no roundup today (candles published: $candlesOk)"
}

$check = python tools\build_deals.py --check $file 2>&1 | Out-String
if ($LASTEXITCODE) {
    # Move it out of the repo so a bad file never breaks later builds
    Move-Item $file "C:\Users\User\ClaudeJobs\rejected_$Date.json" -Force
    throw "Data file failed validation (moved to ClaudeJobs\rejected_$Date.json):`n$check"
}

python tools\build_deals.py 2>&1 | Out-String
if ($LASTEXITCODE) { throw "build_deals.py failed" }

cmd /c "git add deals 2>&1" | Out-String
git commit -q -m "Daily Deals UK: $Date roundup and candles" | Out-String
cmd /c "git push 2>&1" | Out-String
if ($LASTEXITCODE) { throw "git push failed" }
"Published https://dailydealsuk.co.uk/deals/$Date/"
