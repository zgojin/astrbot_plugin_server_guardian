# 🛡️ astrbot_plugin_server_guardian (服务器管家)

一个遵循标准命名风格的 AstrBot 高级监控插件。具备 **适配器掉线邮件报警**、**实时资源排行查询** 以及 **系统内存一键清理** 功能。

---

## ✨ 核心功能

* **掉线报警**：精准识别 OneBot (QQ) 等适配器状态，掉线后立即发送邮件，恢复后自动重置。
* **资源监控**：实时采样并显示宿主机 CPU 与 内存占用最高的进程排行（Top 5）。
* **内存清理**：穿透容器执行内核级 `drop_caches`，一键释放系统缓存（Buffer/Cache）。
* **上帝视角**：配合容器 `pid: host` 模式，实现对宿主机全量进程的监控。

---

## 📧 邮箱服务配置指南

插件需要 SMTP 服务来发送报警邮件。以下是常用平台的配置方法：

### 1. QQ 邮箱
* **SMTP 服务器**: `smtp.qq.com` | **端口**: `465` (需开启 TLS)
* **授权码获取**: 登录 [QQ邮箱网页版](https://mail.qq.com/) -> **设置** -> **账号** -> 下拉 找到 **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务** 开启并获取 **授权码**。

### 2. Gmail
* **SMTP 服务器**: `smtp.gmail.com` | **端口**: `465`
* **授权码获取**: 开启谷歌账号 **两步验证** -> 生成 **App Passwords**。

---

## 如果你是docker容器部署 内存监控以及清理可能无法正常使用或无法获取全部信息

由于涉及宿主机进程监控和内存清理，必须赋予容器 **PID 权限** 和 **特权模式**。

### 核心参数说明
* `--pid=host`: 允许容器读取宿主机的进程树（监控全机进程）。
* `--privileged`: 允许容器执行内核级清理指令（释放系统内存）。

### 一键部署代码 (Docker Run)
```bash
sudo docker run -itd \
  --privileged \
  --pid=host \
  -p 6185:6185 \
  -p 6199:6199 \
  -v /root/AstrBot:/AstrBot \
  -v /etc/localtime:/etc/localtime:ro \
  -v /etc/timezone:/etc/timezone:ro \
  --name astrbot \
  soulter/astrbot:latest
