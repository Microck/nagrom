Get-ChildItem -Recurse -Filter *.mmd | ForEach-Object {
   $output = $_.FullName -replace '\.mmd$', '.png'
   Write-Host "$($_.Name) -> $([System.IO.Path]::GetFileName($output))"
   mmdc -i $_.FullName -o $output -t neutral -b transparent --scale 4
}