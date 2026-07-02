$url = Resolve-Path "pitch-deck-fa.html"
$edge = "$env:PROGRAMFILES (x86)\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path $edge)) {
    $edge = "$env:LOCALAPPDATA\Microsoft\Edge SxS\Application\msedge.exe"
}
if (-not (Test-Path $edge)) {
    Write-Host "Edge not found. Use Chrome's Save as PDF manually."
    exit 1
}
& $edge --headless --print-to-pdf="pitch-deck.pdf" --print-to-pdf-no-header --window-size=1280,720 "file:///$url"
Write-Host "PDF saved: pitch-deck.pdf"
