# 批量 Windows OCR 引擎：pages/*.png → pages-md/pageNNNN.md
# 与 ocr_pdf.py 的 DeepSeek 管线同语义：断点续传（已存在非空 .md 跳过）
# 用法: powershell -ExecutionPolicy Bypass -File winocr.ps1 -PagesDir <dir> -OutDir <dir> [-Lang zh-Hans]
param(
    [Parameter(Mandatory=$true)][string]$PagesDir,
    [Parameter(Mandatory=$true)][string]$OutDir,
    [string]$Lang = "zh-Hans"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Storage.StorageFile, Windows.Foundation, ContentType = WindowsRuntime]

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

$langObj = [Windows.Globalization.Language, Windows.Foundation, ContentType = WindowsRuntime]::new($Lang)
$engine = if ([Windows.Media.Ocr.OcrEngine]::IsLanguageSupported($langObj)) {
    [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($langObj)
} else {
    [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
}
if (-not $engine) { Write-Error "OCR 引擎创建失败（缺少语言包: $Lang）"; exit 1 }

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }

$pngs = Get-ChildItem -Path $PagesDir -Filter "*.png" | Sort-Object Name
$ok = $skip = $fail = 0
foreach ($png in $pngs) {
    $mdPath = Join-Path $OutDir ($png.BaseName + ".md")
    if ((Test-Path $mdPath) -and ((Get-Item $mdPath).Length -gt 0)) { $skip++; continue }
    try {
        $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($png.FullName)) ([Windows.Storage.StorageFile])
        $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        # 清理: CJK 字符/中文标点之间的空格是引擎噪声; 全角句点归一
        $text = $result.Text -replace '．', '.'
        $text = $text -replace '([一-鿿，。：；、！？“”‘’（）《》])\s+(?=[一-鿿，。：；、！？“”‘’（）《》])', '$1'
        $text = $text -replace '\s*([《》])\s*', '$1'
        $text = $text -replace '(\d)\s*([.,])\s*(\d)', '$1$2$3'
        [IO.File]::WriteAllText($mdPath, $text, [Text.Encoding]::UTF8)
        $stream.Dispose()
        $ok++
    } catch {
        $fail++
        Write-Output ("FAIL {0}: {1}" -f $png.Name, $_.Exception.Message)
    }
}
Write-Output ("WINOCR-DONE ok={0} skip={1} fail={2} lang={3}" -f $ok, $skip, $fail, $engine.RecognizerLanguage.LanguageTag)
