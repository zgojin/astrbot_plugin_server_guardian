import asyncio
import time
import psutil
import datetime
import os
from email.mime.text import MIMEText
from email.header import Header
import aiosmtplib

from astrbot.api.event import filter, AstrMessageEvent, PermissionType
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig, logger

@register("astrbot_plugin_server_guardian", "长安某", "AstrBot 服务监控", "1.0.0")
class OfflineAlarmPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.is_running = True
        self.alarm_status = {}
        
        if self.config.get("enable", True):
            asyncio.create_task(self.monitor_loop()) [cite: 38]

    @filter.command("status", alias={'状态', '占用', '服务器'}) [cite: 8]
    @filter.permission_type(PermissionType.ADMIN) [cite: 10]
    async def check_server_status(self, event: AstrMessageEvent):
        yield event.plain_result("正在采样系统数据...")
        try:
            report = await asyncio.to_thread(self._get_system_snapshot) [cite: 40]
            yield event.plain_result(report)
        except Exception as e:
            logger.error(f"查询失败: {e}", exc_info=True) [cite: 40]
            yield event.plain_result(f"查询失败: {e}")

    @filter.command("clean", alias={'清理', '清理内存'}) [cite: 8]
    @filter.permission_type(PermissionType.ADMIN) [cite: 10]
    async def clean_memory(self, event: AstrMessageEvent):
        try:
            mem_before = psutil.virtual_memory().available
            os.system("sync && echo 3 > /proc/sys/vm/drop_caches")
            await asyncio.sleep(1.5) 
            mem_after = psutil.virtual_memory().available
            released = mem_after - mem_before
            
            msg = [
                "**系统内存清理完成**",
                "---------------------------",
                f"释放空间: {self._fmt_bytes(max(0, released))}",
                f"当前可用: {self._fmt_bytes(mem_after)}",
                "\n*提示: 仅清理系统缓存。*"
            ]
            yield event.plain_result("\n".join(msg))
        except Exception as e:
            logger.error("清理内存失败", exc_info=True) [cite: 40]
            yield event.plain_result(f"清理失败: {e}")

    def _get_system_snapshot(self):
        cpu_count = psutil.cpu_count()
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = str(datetime.datetime.now() - boot_time).split('.')[0]
        
        procs_map = {}
        for p in psutil.process_iter(['pid', 'name', 'memory_percent']):
            try:
                p.cpu_percent(interval=None)
                procs_map[p.pid] = p
            except (psutil.NoSuchProcess, psutil.AccessDenied): continue
        
        time.sleep(1.0) 
        
        proc_stats = []
        for pid, p in procs_map.items():
            try:
                cpu_val = p.cpu_percent(interval=None)
                mem_val = p.info['memory_percent']
                if cpu_val > 0.1 or mem_val > 0.5:
                    proc_stats.append({"name": p.info['name'], "pid": pid, "cpu": cpu_val, "mem": mem_val})
            except: continue
        
        top_cpu = sorted(proc_stats, key=lambda x: x['cpu'], reverse=True)[:5]
        top_mem = sorted(proc_stats, key=lambda x: x['mem'], reverse=True)[:5]
        sys_cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()

        msg = [
            "**服务器资源实时监控**",
            f"运行时长: {uptime}",
            f"核心数量: {cpu_count} 核",
            f"系统总 CPU: {sys_cpu}%",
            f"系统总内存: {mem.percent}% ({self._fmt_bytes(mem.used)}/{self._fmt_bytes(mem.total)})",
            "---------------------------",
            "**CPU 占用排行 (单核%)**"
        ]
        for i, p in enumerate(top_cpu):
            msg.append(f"{i+1}. {p['name'][:15]} [{p['pid']}] : **{p['cpu']:.1f}%**")
        msg.append("\n**内存 占用排行 (%)**")
        for i, p in enumerate(top_mem):
            msg.append(f"{i+1}. {p['name'][:15]} [{p['pid']}] : **{p['mem']:.1f}%**")
        return "\n".join(msg)

    async def monitor_loop(self):
        logger.info("掉线报警监控已启动")
        while self.is_running:
            try:
                interval = self.config.get("check_interval", 60)
                await asyncio.sleep(interval)
                await self.check_adapters()
            except asyncio.CancelledError: break
            except Exception as e:
                logger.error(f"监控异常: {e}")
                await asyncio.sleep(10)

    async def check_adapters(self):
        platforms = self.context.platform_manager.get_insts() [cite: 39]
        if not platforms: return
        for platform in platforms:
            is_alive = True
            p_name = getattr(platform, "platform_name", type(platform).__name__)
            class_name = type(platform).__name__
            if "WebChat" in class_name or p_name == "webchat": continue

            if class_name == "AiocqhttpAdapter":
                try:
                    client = platform.get_client()
                    if not client: raise Exception("Client为空")
                    await asyncio.wait_for(client.api.call_action('get_status'), timeout=5)
                except Exception: is_alive = False
            else:
                if not getattr(platform, "client", None): is_alive = False

            if not is_alive:
                if not self.alarm_status.get(p_name, False):
                    if await self.trigger_alarm(p_name):
                        self.alarm_status[p_name] = True
            else:
                if self.alarm_status.get(p_name, False):
                    self.alarm_status[p_name] = False

    async def trigger_alarm(self, name: str):
        logger.error(f"检测到 {name} 掉线，发送报警邮件...")
        subject = f"【AstrBot报警】{name} 连接断开"
        content = f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n检测到适配器 [{name}] 连接断开，请检查服务状态。"
        return await self.send_email(subject, content)

    async def send_email(self, subject, content):
        host = self.config.get("smtp_host")
        port = self.config.get("smtp_port")
        user = self.config.get("smtp_user")
        pwd = self.config.get("smtp_pass")
        to = self.config.get("receiver_email")
        if not (host and user and pwd and to): return False
        
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['From'], msg['To'], msg['Subject'] = user, to, Header(subject, 'utf-8')
        try:
            await aiosmtplib.send(msg, hostname=host, port=port, username=user, password=pwd, use_tls=True)
            return True
        except Exception: return False

    def _fmt_bytes(self, num):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if abs(num) < 1024.0: return f"{num:.2f}{unit}"
            num /= 1024.0
        return f"{num:.2f}TB"

    async def terminate(self): [cite: 2]
        self.is_running = False
