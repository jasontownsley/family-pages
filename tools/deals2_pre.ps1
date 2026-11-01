# Afternoon run (15:00): same research job as the morning, but writes deals\data\<date>-b.json
# with a seasonal theme that differs from the morning's. The prompt is made from deals_research_prompt.txt (or the short paused prompt while tools\amazon_paused.txt exists).
cmd /c "git pull --ff-only 2>&1" | Out-String
if ($LASTEXITCODE) { throw "git pull failed" }
python tools\build_deals.py 2>&1 | Out-String
if ($LASTEXITCODE) { throw "build_deals.py failed before research" }

if (Test-Path tools\amazon_paused.txt) {
    Copy-Item tools\deals_prompt.txt C:\Users\User\ClaudeJobs\deals2_prompt.txt -Force
    "Amazon roundups paused - afternoon run refreshes prices only"
    return
}
$base = Get-Content -Raw -Encoding UTF8 tools\deals_research_prompt.txt
$extra = @'
AFTERNOON RUN - this overrides STEP 1's theme choice:
  - This is the SECOND roundup today. This morning's roundup is listed by recent_deals.py (today's date, not marked afternoon). Pick a different theme and angle from it, with no product overlap.
  - Theme: the next upcoming UK occasion - Halloween until 31 October, Bonfire Night from 1 to 5 November, then Christmas (rotate the Christmas angles listed above), Black Friday week when it applies, and New Year from 21 December. If this morning already used that occasion, use the same occasion with a clearly different angle (e.g. decorations vs gifts vs kids vs hosting).
  - Add "slot": "b" to the JSON, next to "date".

'@
$prompt = $base.Replace("deals/data/{{DATE}}.json", "deals/data/{{DATE}}-b.json").Replace("STEP 1 - Pick today's theme.", $extra + "STEP 1 - Pick today's theme.")
$prompt = $prompt.Replace('"date": "{{DATE}}",', '"date": "{{DATE}}",' + "`n  `"slot`": `"b`",")
Set-Content -Path C:\Users\User\ClaudeJobs\deals2_prompt.txt -Value $prompt -Encoding UTF8
"Afternoon prompt ready"
