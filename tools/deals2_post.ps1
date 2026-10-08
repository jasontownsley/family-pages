# Afternoon run: validate deals\data\<date>-b.json, build, commit and push.
param([string]$Date = (Get-Date -Format yyyy-MM-dd))
$file = "deals\data\$Date-b.json"

if (-not (Test-Path $file)) { throw "No $file written - no afternoon roundup today" }

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
