$ErrorActionPreference='Stop'
$taskDir=Join-Path $PSScriptRoot 'initial_progress_14050719'
$source=Join-Path $taskDir 'گزارش اولیه اقدامات داشبورد انتقال آب ۱ تا ۱۹ مهر ۱۴۰۵.docx'
$pdf=Join-Path $taskDir 'word_render.pdf'
$word=$null
$document=$null
try {
  $word=New-Object -ComObject Word.Application
  $word.Visible=$false
  $word.DisplayAlerts=0
  $word.AutomationSecurity=3
  $document=$word.Documents.Open($source,$false,$false,$false)
  [void]$document.Fields.Update()
  if ($document.TablesOfContents.Count -gt 0) {
    $toc=$document.TablesOfContents.Item(1)
    $toc.Update()
    $toc.Range.Font.Name='B Nazanin'
    $toc.Range.Font.NameBi='B Nazanin'
    $toc.Range.Font.Size=11
    $toc.Range.Font.SizeBi=11
    $toc.Range.ParagraphFormat.ReadingOrder=0
    $toc.Range.ParagraphFormat.Alignment=0
    $toc.Range.ParagraphFormat.SpaceBefore=0
    $toc.Range.ParagraphFormat.SpaceAfter=2
    $toc.Range.ParagraphFormat.LineSpacingRule=4
    $toc.Range.ParagraphFormat.LineSpacing=18
  }
  $document.Repaginate()
  if ($document.TablesOfContents.Count -gt 0) { $document.TablesOfContents.Item(1).UpdatePageNumbers() }
  $document.Save()
  $document.ExportAsFixedFormat($pdf,17)
  Write-Output "Pages: $($document.ComputeStatistics(2))"
} finally {
  if ($document) { $document.Close(0); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($document) }
  if ($word) { $word.Quit(); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
}
