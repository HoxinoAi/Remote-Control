from colorama import init, Fore
from time import sleep
import os
import random

init()

# 科技感装饰字符
tech_chars = ['░', '▒', '▓', '█', '■', '□', '▢', '▣', '▤', '▥', '▦', '▧', '▨', '▩', '▪', '▫']

anims = [
"""
██╗  ██╗
██║  ██║
███████║
██╔══██║
██║  ██║
╚═╝  ╚═╝
""",
"""
██╗  ██╗ ██████╗
██║  ██║██╔═══██╗
███████║██║   ██║
██╔══██║██║   ██║
██║  ██║╚██████╔╝
╚═╝  ╚═╝ ╚═════╝
""",
"""
██╗  ██╗ ██████╗ ██╗  ██╗
██║  ██║██╔═══██╗╚██╗██╔╝
███████║██║   ██║ ╚███╔╝
██╔══██║██║   ██║ ██╔██╗
██║  ██║╚██████╔╝██╔╝ ██╗
╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝
""",
"""
██╗  ██╗ ██████╗ ██╗  ██╗██╗███╗   ██╗ ██████╗
██║  ██║██╔═══██╗╚██╗██╔╝██║████╗  ██║██╔═══██╗
███████║██║   ██║ ╚███╔╝ ██║██╔██╗ ██║██║   ██║
██╔══██║██║   ██║ ██╔██╗ ██║██║╚██╗██║██║   ██║
██║  ██║╚██████╔╝██╔╝ ██╗██║██║ ╚████║╚██████╔╝
╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝
""",
"""
██╗  ██╗ ██████╗ ██╗  ██╗██╗███╗   ██╗ ██████╗ ██╗  ██╗ ██████╗  ██████╗ ██╗  ██╗
██║  ██║██╔═══██╗╚██╗██╔╝██║████╗  ██║██╔═══██╗██║  ██║██╔═══██╗██╔═══██╗██║ ██╔╝
███████║██║   ██║ ╚███╔╝ ██║██╔██╗ ██║██║   ██║███████║██║   ██║██║   ██║█████╔╝
██╔══██║██║   ██║ ██╔██╗ ██║██║╚██╗██║██║   ██║██╔══██║██║   ██║██║   ██║██╔═██╗
██║  ██║╚██████╔╝██╔╝ ██╗██║██║ ╚████║╚██████╔╝██║  ██║╚██████╔╝╚██████╔╝██║  ██╗
╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
"""
]

def add_tech_effect(text):
    """添加科技感装饰效果"""
    lines = text.split('\n')
    max_length = max(len(line) for line in lines)
    decorated_lines = []
    
    for line in lines:
        # 在每行左右添加随机科技字符
        left_decor = random.choice(tech_chars)
        right_decor = random.choice(tech_chars)
        padded_line = line.ljust(max_length)
        decorated_lines.append(f"{left_decor} {padded_line} {right_decor}")
    
    # 添加顶部和底部装饰
    width = max_length + 4
    top_bottom = ''.join(random.choice(tech_chars) for _ in range(width))
    
    return f"{top_bottom}\n" + '\n'.join(decorated_lines) + f"\n{top_bottom}"

def anim():
    for frame in anims:
        colored_text = ""
        frame_with_effects = add_tech_effect(frame)
        
        for char in frame_with_effects:
            if char == "█":
                colored_text += f"{Fore.CYAN}{char}"
            elif char in "╗╔":
                colored_text += f"{Fore.BLUE}{char}"
            elif char in "║═":
                colored_text += f"{Fore.LIGHTBLUE_EX}{char}"
            elif char in "╝╚":
                colored_text += f"{Fore.BLUE}{char}"
            elif char in tech_chars:
                colored_text += f"{Fore.GREEN}{char}"
            else:
                colored_text += char
        
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
            
        print(colored_text)
        sleep(0.3)  # 稍微加快动画速度
          