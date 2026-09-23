# Runs before Claude: get the latest repo and refresh deals/data/exclude.txt.
cmd /c "git pull --ff-only 2>&1" | Out-String
if ($LASTEXITCODE) { throw "git pull failed" }
python tools\build_deals.py 2>&1 | Out-String
if ($LASTEXITCODE) { throw "build_deals.py failed before research" }
