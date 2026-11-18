param(
    [string]$Mode = "install",
    [string]$Stage = "",
    [string]$Ico = ""
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$APP = "3D 交通灯仿真"
$REG = "HKCU:\Software\3D Traffic Light Sim"
$DEF = Join-Path $env:LOCALAPPDATA ("Programs\" + $APP)

$formIcon = $null
$icoImage = $null
if ($Ico -and (Test-Path $Ico)) {
    try { $formIcon = [System.Drawing.Icon]::FromFile($Ico) } catch {}
}
# 窗口 logo 优先用 PNG（多尺寸 ICO 在 .NET Image 里可能加载失败）
$logoPng = Join-Path $Stage "logo.png"
if (Test-Path $logoPng) {
    try { $icoImage = [System.Drawing.Image]::FromFile($logoPng) } catch {}
} elseif ($Ico -and (Test-Path $Ico)) {
    try { $icoImage = [System.Drawing.Image]::FromFile($Ico) } catch {}
}

function Lbl($text, $x, $y, $w, $h, $size, $bold, $color) {
    $l = New-Object System.Windows.Forms.Label
    $l.Text = $text
    $l.Location = New-Object System.Drawing.Point($x, $y)
    $l.Size = New-Object System.Drawing.Size($w, $h)
    $fstyle = [System.Drawing.FontStyle]::Regular
    if ($bold) { $fstyle = [System.Drawing.FontStyle]::Bold }
    $l.Font = New-Object System.Drawing.Font("Microsoft YaHei", $size, $fstyle)
    if ($null -ne $color -and $color -ne '') {
        if ($color -match '^\d+,\d+,\d+$') {
            $p = $color.Split(',')
            $l.ForeColor = [System.Drawing.Color]::FromArgb([int]$p[0], [int]$p[1], [int]$p[2])
        } else {
            $l.ForeColor = [System.Drawing.Color]::FromName($color)
        }
    }
    return $l
}

# ---------- 主窗口 ----------
$form = New-Object System.Windows.Forms.Form
$form.Text = "$APP 安装向导"
$form.AutoScaleMode = [System.Windows.Forms.AutoScaleMode]::None
$form.ClientSize = New-Object System.Drawing.Size(680, 560)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.BackColor = "White"
if ($formIcon) { $form.Icon = $formIcon }

$banner = New-Object System.Windows.Forms.Panel
$banner.Location = New-Object System.Drawing.Point(0, 0)
$banner.Size = New-Object System.Drawing.Size(680, 88)
$banner.BackColor = [System.Drawing.Color]::FromArgb(28, 42, 60)
$form.Controls.Add($banner)

if ($icoImage) {
    $pic = New-Object System.Windows.Forms.PictureBox
    $pic.Image = $icoImage
    $pic.Location = New-Object System.Drawing.Point(18, 16)
    $pic.Size = New-Object System.Drawing.Size(56, 56)
    $pic.SizeMode = "StretchImage"
    $banner.Controls.Add($pic)
}
$banner.Controls.Add((Lbl "$APP" 90 16 480 30 17 $true "White"))
$banner.Controls.Add((Lbl "安装向导  ·  内置全部组件，无需其他环境" 90 50 520 24 10 $false "170,190,215"))

$body = New-Object System.Windows.Forms.Panel
$body.Location = New-Object System.Drawing.Point(0, 88)
$body.Size = New-Object System.Drawing.Size(680, 410)
$form.Controls.Add($body)

$bottom = New-Object System.Windows.Forms.Panel
$bottom.Location = New-Object System.Drawing.Point(0, 498)
$bottom.Size = New-Object System.Drawing.Size(680, 62)
$bottom.BackColor = [System.Drawing.Color]::FromArgb(244, 247, 250)
$form.Controls.Add($bottom)

$btnBack = New-Object System.Windows.Forms.Button
$btnBack.Text = "上一步"
$btnBack.Size = New-Object System.Drawing.Size(96, 36)
$btnBack.Location = New-Object System.Drawing.Point(380, 18)
$btnBack.FlatStyle = "Flat"
$bottom.Controls.Add($btnBack)

$btnNext = New-Object System.Windows.Forms.Button
$btnNext.Text = "下一步"
$btnNext.Size = New-Object System.Drawing.Size(110, 36)
$btnNext.Location = New-Object System.Drawing.Point(486, 18)
$btnNext.FlatStyle = "Flat"
$btnNext.BackColor = [System.Drawing.Color]::FromArgb(45, 110, 200)
$btnNext.ForeColor = "White"
$bottom.Controls.Add($btnNext)

$btnCancel = New-Object System.Windows.Forms.Button
$btnCancel.Text = "取消"
$btnCancel.Size = New-Object System.Drawing.Size(80, 36)
$btnCancel.Location = New-Object System.Drawing.Point(20, 18)
$btnCancel.FlatStyle = "Flat"
$bottom.Controls.Add($btnCancel)

# ---------- 步骤页：欢迎 ----------
$pgWelcome = New-Object System.Windows.Forms.Panel
$pgWelcome.Dock = "Fill"
$body.Controls.Add($pgWelcome)
$pgWelcome.Controls.Add((Lbl "欢迎使用 $APP 安装向导" 30 18 580 34 20 $true "30,44,62"))
$pgWelcome.Controls.Add((Lbl "本安装包已内置 3D 路口网页、PLC 网关和文档，" 30 70 580 26 12 $false $null))
$pgWelcome.Controls.Add((Lbl "目标电脑无需安装 Python 或任何依赖，Win10 / Win11 均可运行。" 30 98 580 26 12 $false $null))
$pgWelcome.Controls.Add((Lbl "安装完成后，双击桌面图标即可自动启动网关并打开 3D 路口。" 30 126 580 26 12 $false $null))
$box = New-Object System.Windows.Forms.GroupBox
$box.Text = "即将执行"
$box.Location = New-Object System.Drawing.Point(30, 170)
$box.Size = New-Object System.Drawing.Size(580, 100)
$pgWelcome.Controls.Add($box)
$box.Controls.Add((Lbl "1. 释放程序文件到安装目录" 20 26 540 22 11 $false $null))
$box.Controls.Add((Lbl "2. 创建桌面与开始菜单快捷方式" 20 52 540 22 11 $false $null))
$box.Controls.Add((Lbl "3. 生成 PLC 地址配置文件（默认 127.0.0.1）" 20 78 540 22 11 $false $null))

# ---------- 步骤页：路径 ----------
$pgPath = New-Object System.Windows.Forms.Panel
$pgPath.Dock = "Fill"
$body.Controls.Add($pgPath)
$pgPath.Controls.Add((Lbl "选择安装位置" 30 24 580 30 18 $true "30,44,62"))
$pgPath.Controls.Add((Lbl "程序将安装到以下文件夹，也可以点【浏览】自行选择：" 30 70 580 26 11 $false $null))
$txtPath = New-Object System.Windows.Forms.TextBox
$txtPath.Text = $DEF
$txtPath.Location = New-Object System.Drawing.Point(40, 124)
$txtPath.Size = New-Object System.Drawing.Size(470, 30)
$txtPath.Font = New-Object System.Drawing.Font("Microsoft YaHei", 11)
$pgPath.Controls.Add($txtPath)
$btnBrowse = New-Object System.Windows.Forms.Button
$btnBrowse.Text = "浏览..."
$btnBrowse.Size = New-Object System.Drawing.Size(90, 30)
$btnBrowse.Location = New-Object System.Drawing.Point(520, 124)
$btnBrowse.FlatStyle = "Flat"
$pgPath.Controls.Add($btnBrowse)
$pgPath.Controls.Add((Lbl "提示：无需管理员权限，安装到当前用户目录即可。" 40 180 580 24 11 $false "120,130,145"))

$dlg = New-Object System.Windows.Forms.FolderBrowserDialog
$dlg.Description = "选择安装文件夹"
$btnBrowse.Add_Click({
    $dlg.SelectedPath = $txtPath.Text
    if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $txtPath.Text = $dlg.SelectedPath
    }
})

# ---------- 步骤页：进度 ----------
$pgProgress = New-Object System.Windows.Forms.Panel
$pgProgress.Dock = "Fill"
$body.Controls.Add($pgProgress)
$lblStage = Lbl "正在安装，请稍候..." 40 60 580 30 16 $true "30,44,62"
$pgProgress.Controls.Add($lblStage)
$lblDetail = Lbl "准备文件..." 40 110 580 26 11 $false "100,110,125"
$pgProgress.Controls.Add($lblDetail)
$bar = New-Object System.Windows.Forms.ProgressBar
$bar.Location = New-Object System.Drawing.Point(40, 160)
$bar.Size = New-Object System.Drawing.Size(580, 24)
$bar.Style = "Continuous"
$pgProgress.Controls.Add($bar)
$lblPct = Lbl "0%" 40 196 580 24 11 $false "100,110,125"
$pgProgress.Controls.Add($lblPct)

# ---------- 步骤页：完成 ----------
$pgDone = New-Object System.Windows.Forms.Panel
$pgDone.Dock = "Fill"
$body.Controls.Add($pgDone)
$lblDoneTitle = Lbl "安装完成！" 40 60 580 34 22 $true "28,140,80"
$pgDone.Controls.Add($lblDoneTitle)
$lblDoneText = Lbl "" 40 115 580 90 12 $false $null
$pgDone.Controls.Add($lblDoneText)
$chkRun = New-Object System.Windows.Forms.CheckBox
$chkRun.Text = "立即启动 3D 交通灯仿真"
$chkRun.Checked = $true
$chkRun.Location = New-Object System.Drawing.Point(40, 220)
$chkRun.Size = New-Object System.Drawing.Size(400, 30)
$chkRun.Font = New-Object System.Drawing.Font("Microsoft YaHei", 11)
$pgDone.Controls.Add($chkRun)

function Show-Step($n) {
    $script:step = $n
    $pgWelcome.Visible = ($n -eq 0)
    $pgPath.Visible = ($n -eq 1)
    $pgProgress.Visible = ($n -eq 2)
    $pgDone.Visible = ($n -eq 3)
    $btnBack.Visible = ($n -eq 1 -or $n -eq 2)
    $btnCancel.Visible = ($n -ne 3)
    if ($Mode -eq "install") {
        if ($n -eq 0) { $btnNext.Text = "下一步" }
        if ($n -eq 1) { $btnNext.Text = "安装" }
        if ($n -eq 2) { $btnNext.Visible = $false }
        if ($n -eq 3) { $btnNext.Text = "完成"; $btnNext.Visible = $true }
    }
}

function Set-Prog($pct, $msg) {
    $bar.Value = $pct
    $lblPct.Text = "$pct%"
    $lblDetail.Text = $msg
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 150
}

function New-Shortcut($path, $target, $arguments, $workdir, $icon) {
    $ws = New-Object -ComObject WScript.Shell
    $sc = $ws.CreateShortcut($path)
    $sc.TargetPath = $target
    if ($arguments) { $sc.Arguments = $arguments }
    if ($workdir) { $sc.WorkingDirectory = $workdir }
    if ($icon) { $sc.IconLocation = "$icon,0" }
    $sc.Save()
}

function Do-Install {
    $target = $txtPath.Text.Trim().TrimEnd('\')
    if (-not $target) { [System.Windows.Forms.MessageBox]::Show("请选择安装目录"); return }
    try {
        $form.Cursor = "WaitCursor"
        Show-Step 2
        Set-Prog 6 "创建安装目录..."
        New-Item -ItemType Directory -Path $target -Force | Out-Null
        $exeDst = Join-Path $target ($APP + ".exe")
        $icoDst = Join-Path $target "app.ico"

        Set-Prog 18 "复制 3D 路口网页..."
        Copy-Item (Join-Path $Stage "交通灯仿真.html") (Join-Path $target "交通灯仿真.html") -Force
        Set-Prog 40 "复制 PLC 网关..."
        Copy-Item (Join-Path $Stage "plc_gateway.exe") (Join-Path $target "plc_gateway.exe") -Force
        Set-Prog 58 "复制 IO 映射表..."
        Copy-Item (Join-Path $Stage "IO映射表.md") (Join-Path $target "IO映射表.md") -Force
        Copy-Item $Ico $icoDst -Force
        Set-Prog 70 "生成启动程序..."
        $srcExe = Join-Path $Stage ($APP + ".exe")
        if (-not (Test-Path $srcExe)) { $srcExe = (Get-Command $MyInvocation.MyCommand.Source).Source }
        Copy-Item $srcExe $exeDst -Force

        Set-Prog 80 "写入 PLC 地址配置..."
        $cfg = Join-Path $target "PLC地址.txt"
        if (-not (Test-Path $cfg)) { Set-Content -Path $cfg -Value "127.0.0.1" -Encoding UTF8 }

        Set-Prog 88 "创建快捷方式..."
        $ws = New-Object -ComObject WScript.Shell
        $desktop = [Environment]::GetFolderPath("Desktop")
        $start = [Environment]::GetFolderPath("Programs")
        $folder = Join-Path $start $APP
        if (-not (Test-Path $folder)) { New-Item -ItemType Directory -Path $folder -Force | Out-Null }
        New-Shortcut (Join-Path $desktop "$APP.lnk") $exeDst "--launch" $target $exeDst
        New-Shortcut (Join-Path $folder "启动仿真.lnk") $exeDst "--launch" $target $exeDst
        New-Shortcut (Join-Path $folder "修改PLC地址.lnk") "notepad.exe" "`"$cfg`"" $target $icoDst
        New-Shortcut (Join-Path $folder "IO映射表.lnk") "notepad.exe" ("`"" + (Join-Path $target "IO映射表.md") + "`"") $target $icoDst
        New-Shortcut (Join-Path $folder "卸载.lnk") $exeDst "--uninstall" $target $icoDst

        Set-Prog 96 "写入安装信息..."
        if (-not (Test-Path $REG)) { New-Item -Path $REG -Force | Out-Null }
        Set-ItemProperty -Path $REG -Name "InstallPath" -Value $target -Force
        Set-ItemProperty -Path $REG -Name "DisplayName" -Value $APP -Force
        Set-ItemProperty -Path $REG -Name "UninstallString" -Value "`"$exeDst`" --uninstall" -Force

        Set-Prog 100 "完成"
        $lblDoneTitle.Text = "安装完成！"
        $lblDoneText.Text = "已安装到：$target`n`n桌面和开始菜单已创建快捷方式。`n换 PLC 时用「修改PLC地址」改 IP 即可。"
        $chkRun.Visible = $true
        Show-Step 3
    } catch {
        $lblDoneTitle.Text = "安装失败"
        $lblDoneTitle.ForeColor = [System.Drawing.Color]::FromArgb(200, 50, 50)
        $lblDoneText.Text = "错误：" + $_.Exception.Message
        $chkRun.Visible = $false
        Show-Step 3
    } finally {
        $form.Cursor = "Default"
    }
}

function Do-Uninstall {
    $target = $DEF
    if (Test-Path $REG) {
        $v = (Get-ItemProperty -Path $REG -Name "InstallPath" -ErrorAction SilentlyContinue).InstallPath
        if ($v) { $target = $v }
    }
    try {
        $form.Cursor = "WaitCursor"
        Show-Step 2
        Set-Prog 20 "关闭网关..."
        $p = Start-Process "taskkill" -ArgumentList "/F /IM plc_gateway.exe" -NoNewWindow -PassThru -Wait -ErrorAction SilentlyContinue | Out-Null
        Set-Prog 50 "删除快捷方式..."
        $ws = New-Object -ComObject WScript.Shell
        $desktop = [Environment]::GetFolderPath("Desktop")
        $start = [Environment]::GetFolderPath("Programs")
        $folder = Join-Path $start $APP
        @((Join-Path $desktop "$APP.lnk"),(Join-Path $folder "启动仿真.lnk"),(Join-Path $folder "修改PLC地址.lnk"),(Join-Path $folder "IO映射表.lnk"),(Join-Path $folder "卸载.lnk")) | ForEach-Object {
            if (Test-Path $_) { Remove-Item $_ -Force -ErrorAction SilentlyContinue }
        }
        if (Test-Path $folder) { Remove-Item $folder -Force -Recurse -ErrorAction SilentlyContinue }
        Set-Prog 75 "删除程序文件..."
        if (Test-Path $target) { Remove-Item $target -Force -Recurse -ErrorAction SilentlyContinue }
        Set-Prog 95 "清理安装信息..."
        if (Test-Path $REG) { Remove-Item $REG -Force -Recurse -ErrorAction SilentlyContinue }
        Set-Prog 100 "完成"
        $lblDoneTitle.Text = "已卸载"
        $lblDoneText.Text = "$APP 已从本机移除。"
        $chkRun.Visible = $false
        Show-Step 3
    } catch {
        $lblDoneTitle.Text = "卸载出错"
        $lblDoneText.Text = $_.Exception.Message
        $chkRun.Visible = $false
        Show-Step 3
    } finally {
        $form.Cursor = "Default"
    }
}

$script:uninstallDone = $false
$btnNext.Add_Click({
    if ($Mode -eq "uninstall") {
        if ($script:uninstallDone) { $form.Close(); return }
        Do-Uninstall
        $script:uninstallDone = $true
        $btnNext.Text = "关闭"
        return
    }
    if ($script:step -eq 0) { Show-Step 1 }
    elseif ($script:step -eq 1) { Do-Install }
    elseif ($script:step -eq 3) {
        if ($chkRun.Checked) {
            $v = (Get-ItemProperty -Path $REG -Name "InstallPath" -ErrorAction SilentlyContinue).InstallPath
            if ($v) {
                $exe = Join-Path $v ($APP + ".exe")
                if (Test-Path $exe) { Start-Process $exe -ArgumentList "--launch" }
            }
        }
        $form.Close()
    }
})
$btnBack.Add_Click({ if ($script:step -eq 1) { Show-Step 0 } })
$btnCancel.Add_Click({ $form.Close() })
$form.Add_FormClosing({ param($s, $e) if ($script:step -eq 2) { $e.Cancel = $true } })

if ($Mode -eq "uninstall") {
    $lblDoneTitle.Text = "卸载 $APP"
    $lblDoneTitle.ForeColor = [System.Drawing.Color]::FromArgb(30, 44, 62)
    $lblDoneText.Text = "点击下方【开始卸载】移除本程序及其快捷方式。"
    Show-Step 3
    $btnNext.Text = "开始卸载"
    $btnNext.Visible = $true
} else {
    Show-Step 0
}

[System.Windows.Forms.Application]::Run($form)
