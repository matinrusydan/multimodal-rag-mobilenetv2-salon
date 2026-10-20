# PDF-only adaptation of the user's existing build_tex.ps1 pipeline.
# Reference: C:\laragon\www\TUGAS Deep Learning\generate_docs\build_tex.ps1
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$compiler = (Get-Command pdflatex.exe -ErrorAction SilentlyContinue).Source
if (!$compiler) { $compiler = 'C:\Users\lilol\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe' }
if (!(Test-Path -LiteralPath $compiler)) { throw 'MiKTeX pdflatex tidak ditemukan.' }
$source = Join-Path $PSScriptRoot 'main.tex'
Push-Location -LiteralPath $PSScriptRoot
try {
    for ($pass = 1; $pass -le 2; $pass++) {
        & $compiler --disable-installer -interaction=nonstopmode -halt-on-error -file-line-error "-output-directory=$PSScriptRoot" $source
        if ($LASTEXITCODE -ne 0) { throw "Kompilasi LaTeX gagal pada putaran $pass. Lihat main.log." }
    }
    Write-Output ('PDF=' + (Join-Path $PSScriptRoot 'main.pdf'))
} finally {
    Pop-Location
}
