function Get-GitIgnorePatterns {
    param (
        [string]$RootPath
    )
    $GitIgnoreFile = Join-Path $RootPath ".gitignore"
    $Patterns = @()

    if (Test-Path $GitIgnoreFile) {
        Get-Content $GitIgnoreFile | ForEach-Object {
            $Line = $_.Trim()
            if ($Line -and -not $Line.StartsWith("#")) {
                $Patterns += $Line.TrimEnd('/')
            }
        }
    }
    return $Patterns
}

function Test-IsIgnored {
    param (
        [System.IO.FileSystemInfo]$Item,
        [string]$RootPath,
        [string[]]$Patterns,
        [System.Collections.Generic.HashSet[string]]$ExtraIgnored
    )

    $RelativePath = (Resolve-Path $Item.FullName -Relative).Replace('\', '/').TrimStart('./')
    $ItemName = $Item.Name

    if ($ExtraIgnored.Contains($ItemName)) {
        return $true
    }

    foreach ($Pattern in $Patterns) {
        $RegexPattern = '^' + [regex]::Escape($Pattern).Replace('\*', '.*').Replace('\?', '.') + '$'

        if ($RelativePath -match $RegexPattern -or 
            $ItemName -match $RegexPattern -or 
            $RelativePath.StartsWith($Pattern + "/")) {
            return $true
        }
    }

    return $false
}

function Show-Structure {
    param (
        [string]$CurrentPath,
        [string]$Prefix = "",
        [string[]]$Patterns = @(),
        [System.Collections.Generic.HashSet[string]]$ExtraIgnored = @()
    )

    $Items = Get-ChildItem -Path $CurrentPath | ForEach-Object { $_ } | Sort-Object { $_.Attributes.HasFlag([System.IO.FileAttributes]::Directory) }, Name

    $FilteredItems = @()
    foreach ($Item in $Items) {
        $IsDirectory = $Item.Attributes.HasFlag([System.IO.FileAttributes]::Directory)
        if ($IsDirectory -or $Item.Extension -eq ".py") {
            if (-not (Test-IsIgnored -Item $Item -RootPath $ProjectRoot -Patterns $Patterns -ExtraIgnored $ExtraIgnored)) {
                $FilteredItems += $Item
            }
        }
    }

    $Count = $FilteredItems.Count
    for ($i = 0; $i -lt $Count; $i++) {
        $Item = $FilteredItems[$i]
        $IsLast = ($i -eq ($Count - 1))
        $Connector = if ($IsLast) { "└── " } else { "├── " }

        Write-Output ($Prefix + $Connector + $Item.Name)

        if ($Item.Attributes.HasFlag([System.IO.FileAttributes]::Directory)) {
            $Extension = if ($IsLast) { "    " } else { "│   " }
            Show-Structure `
                -CurrentPath $Item.FullName `
                -Prefix ($Prefix + $Extension) `
                -Patterns $Patterns `
                -ExtraIgnored $ExtraIgnored
        }
    }
}

$InputPath = Read-Host "Project path (blank=current)"
if ([string]::IsNullOrWhiteSpace($InputPath)) {
    $ProjectRoot = (Get-Item ".").FullName
} else {
    $ProjectRoot = (Resolve-Path $InputPath).Path
}

$ExtraIgnored = [System.Collections.Generic.HashSet[string]]::new(
    [string[]]@(".git", ".idea", ".vscode", "__pycache__", ".pytest_cache", ".mypy_cache"),
    [System.StringComparer]::OrdinalIgnoreCase
)

$GitIgnorePatterns = Get-GitIgnorePatterns -RootPath $ProjectRoot

Write-Output (Split-Path $ProjectRoot -Leaf)

Show-Structure `
    -CurrentPath $ProjectRoot `
    -Patterns $GitIgnorePatterns `
    -ExtraIgnored $ExtraIgnored