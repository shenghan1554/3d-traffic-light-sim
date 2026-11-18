# -*- coding: utf-8 -*-
r"""3D 交通灯仿真 - 安装器 / 启动器（单 exe，内嵌全部资源 + 图形安装向导）

重新打包命令（仓库根目录执行）：
  python -m PyInstaller --onefile --name "交通灯仿真_安装包" --clean --noconfirm ^
    --icon "packaging/traffic_light.ico" ^
    --add-data "交通灯仿真.html;." --add-data "plc_gateway.exe;." ^
    --add-data "IO映射表.md;." --add-data "packaging/traffic_light.ico;." ^
    --add-data "packaging/logo.png;." --add-data "packaging/wizard.ps1;." packaging/setup_installer.py

参数：
  --check       自检内嵌资源（不弹窗）
  --launch      启动网关 + 网页（快捷方式调用）
  --uninstall   图形卸载向导
  无参数         图形安装向导
"""
import sys, os, shutil, subprocess, tempfile, webbrowser, socket

APP = "3D 交通灯仿真"

def res(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)

def run_wizard(mode, stage, ico):
    # PowerShell 5.1 需 UTF-8 BOM 才能正确读中文；把内嵌脚本转成带 BOM 的临时文件
    with open(res("wizard.ps1"), encoding="utf-8") as f:
        script = f.read()
    ps = os.path.join(stage, "wizard.ps1")
    with open(ps, "w", encoding="utf-8-sig") as f:
        f.write(script)
    args = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", ps, "-Mode", mode, "-Stage", stage, "-Ico", ico]
    try:
        subprocess.run(args, timeout=600)
    except Exception:
        pass

def prepare_stage(stage):
    shutil.copy2(sys.executable, os.path.join(stage, APP + ".exe"))
    shutil.copy2(res("logo.png"), os.path.join(stage, "logo.png"))

def do_install():
    stage = tempfile.mkdtemp(prefix="tls_install_")
    try:
        prepare_stage(stage)
        run_wizard("install", stage, res("traffic_light.ico"))
    finally:
        shutil.rmtree(stage, ignore_errors=True)

def do_uninstall():
    stage = tempfile.mkdtemp(prefix="tls_uninstall_")
    try:
        prepare_stage(stage)
        run_wizard("uninstall", stage, res("traffic_light.ico"))
    finally:
        shutil.rmtree(stage, ignore_errors=True)

def port_open(host, port, timeout=0.3):
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except Exception:
        return False

def ctypes_msg(text, title):
    import ctypes
    ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)

def do_launch():
    local = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    target = os.path.join(local, "Programs", APP)
    gw = os.path.join(target, "plc_gateway.exe")
    html = os.path.join(target, "交通灯仿真.html")
    if not os.path.isfile(gw) or not os.path.isfile(html):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\3D Traffic Light Sim") as k:
                target, _ = winreg.QueryValueEx(k, "InstallPath")
                gw = os.path.join(target, "plc_gateway.exe")
                html = os.path.join(target, "交通灯仿真.html")
        except Exception:
            pass
    if not os.path.isfile(gw) or not os.path.isfile(html):
        ctypes_msg("未找到安装文件，请先运行安装程序。", APP)
        return
    ip = "127.0.0.1"
    try:
        with open(os.path.join(target, "PLC地址.txt"), encoding="utf-8-sig") as f:
            v = f.readline().strip()
            if v:
                ip = v
    except Exception:
        pass
    if not port_open("127.0.0.1", 8765):
        try:
            subprocess.Popen([gw, "--ip", ip], cwd=target, creationflags=0x08000000)
        except Exception:
            pass
    webbrowser.open("file:///" + html.replace("\\", "/"))

def self_check():
    ok = True
    for name in ("交通灯仿真.html", "plc_gateway.exe", "IO映射表.md", "traffic_light.ico", "logo.png", "wizard.ps1"):
        p = res(name)
        exists = os.path.isfile(p)
        size = os.path.getsize(p) if exists else 0
        print(("[OK] " if exists else "[MISS] ") + name + "  %d bytes" % size)
        ok = ok and exists and size > 0
    print("SELFCHECK_" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--check" in args:
        sys.exit(self_check())
    elif "--launch" in args:
        do_launch()
    elif "--uninstall" in args:
        do_uninstall()
    else:
        do_install()
