# Runs after Claude: validate today's data file, build the site, commit and push.
param([string]$Date = (Get-Date -Format yyyy-MM-dd))
$file = "deals\data\$Date.json"

if (-not (Test-Path $file)) { throw "No $file written - nothing published today" }

$check = python tools\build_deals.py --check $file 2>&1 | Out-String
if ($LASTEXITCODE) {
    # Move it out of the repo so a bad file never breaks later builds
    Move-Item $file "C:\Users\User\ClaudeJobs\rejected_$Date.json" -Force
    throw "Data file failed validation (moved to ClaudeJobs\rejected_$Date.json):`n$check"
}

python tools\build_deals.py 2>&1 | Out-String
if ($LASTEXITCODE) { throw "build_deals.py failed" }

git add deals 2>&1 | Out-String
git commit -m "Daily Deals UK: $Date roundup" 2>&1 | Out-String
git push 2>&1 | Out-String
if ($LASTEXITCODE) { throw "git push failed" }
"Published https://jasontownsley.github.io/family-pages/deals/$Date/"
