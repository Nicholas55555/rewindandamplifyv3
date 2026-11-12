# Export the V3 deck to PDF and slide previews with Microsoft PowerPoint, and confirm the videos are real media.
#
#   powershell -ExecutionPolicy Bypass -File finals-deck\finish_v3_deck.ps1
#
# Run this after build_v3_deck.py and before finish_v3_deck.py. It needs PowerPoint installed.
# It also reports whether PowerPoint opened the file cleanly, which the Python builder cannot know.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pptx = Join-Path $here 'Rewind_Amplify_Finals_V3.pptx'
$pdf = Join-Path $here 'Rewind_Amplify_Finals_V3.pdf'
$preview = Join-Path $here 'preview'
New-Item -ItemType Directory -Force $preview | Out-Null
Get-ChildItem $preview -Filter 'slide-*.png' | Remove-Item -Force

$app = New-Object -ComObject PowerPoint.Application
try {
  $deck = $app.Presentations.Open($pptx, $true, $false, $false)    # read-only, no window
  $videos = @()
  foreach ($i in 1..$deck.Slides.Count) {
    foreach ($shape in $deck.Slides.Item($i).Shapes) {
      if ($shape.Type -eq 16) {                                     # msoMedia
        if ($shape.MediaType -ne 3) { throw "Slide $i holds media that is not a movie" }
        if (-not $shape.MediaFormat.IsEmbedded) { throw "The video on slide $i is linked, not embedded" }
        $videos += [ordered]@{ slide = $i; name = $shape.Name; milliseconds = $shape.MediaFormat.Length }
      }
    }
  }
  $deck.SaveAs($pdf, 32)                                            # ppSaveAsPDF
  foreach ($i in 1..$deck.Slides.Count) {
    $deck.Slides.Item($i).Export((Join-Path $preview ('slide-{0:d2}.png' -f $i)), 'PNG', 1600, 900)
  }
  $report = [ordered]@{
    powerpoint_version = $app.Version
    opened_without_repair = $true
    slides = $deck.Slides.Count
    embedded_videos = $videos
  }
  $deck.Close()
  $json = $report | ConvertTo-Json -Depth 4
  [System.IO.File]::WriteAllText((Join-Path $preview 'powerpoint_report.json'), $json, (New-Object System.Text.UTF8Encoding($false)))
  $json
} finally {
  $app.Quit()
}
