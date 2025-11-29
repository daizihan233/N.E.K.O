import threading
import webbrowser
import sys
from pynput import keyboard
from config import MAIN_SERVER_PORT
from utils.hotkey_config import get_hotkey_config
from loguru import logger

class HotkeyHandler:
    def __init__(self):
        self.listener = None
        self.current_pressed_keys = set()
        self.last_pressed_time = 0  # 防止重复触发的时间戳
        self.action_executed = False  # 标记是否已经执行了操作
        self.hotkey_config = get_hotkey_config()
        
        # 解析配置的快捷键
        self.copilot_key_parts = set(self.hotkey_config.get_copilot_key().lower().split('+'))

    def on_press(self, key):
        """按键按下时的回调"""
        try:
            # 将按下的键添加到当前按键集合
            try:
                # 如果是特殊键（如 ctrl, alt, shift, win），使用其名称
                if hasattr(key, 'name'):
                    key_name = key.name.lower()
                    # 映射常见键名
                    if key_name == 'cmd' or key_name.startswith('win'):
                        key_name = 'ctrl'
                    elif key_name == 'alt_l':
                        key_name = 'alt'
                    elif key_name == 'ctrl_l':
                        key_name = 'ctrl'
                    elif key_name == 'shift_l':
                        key_name = 'shift'
                    self.current_pressed_keys.add(key_name)
                elif hasattr(key, 'char') and key.char:
                    # 如果是字符键，使用其字符表示
                    self.current_pressed_keys.add(key.char.lower())
                else:
                    # 如果是功能键（如F1-F24），使用其字符串表示
                    str_key = str(key).lower()
                    if str_key.startswith("'") and str_key.endswith("'"):
                        # 移除单引号，例如 'a' -> a
                        str_key = str_key[1:-1]
                    elif 'key.f' in str_key:
                        # 处理功能键，例如 'Key.f10' -> 'f10'
                        str_key = str_key.split('.')[-1]
                    elif str_key.startswith('<') and str_key.endswith('>'):
                        # 处理特殊键，例如 <255>
                        str_key = str_key[1:-1]
                    self.current_pressed_keys.add(str_key)
            except Exception as e:
                # 如果无法获取键名，使用字符串表示
                str_key = str(key).lower()
                if str_key.startswith("'") and str_key.endswith("'"):
                    str_key = str_key[1:-1]
                elif str_key.startswith('<') and str_key.endswith('>'):
                    str_key = str_key[1:-1]
                self.current_pressed_keys.add(str_key)

            # 调试日志 - 显示当前按下的所有键
            logger.debug(f"按键按下: {key}, 当前按键组合: {self.current_pressed_keys}, 期望组合: {self.copilot_key_parts}")

            # 检查是否匹配配置的快捷键
            if self.copilot_key_parts.issubset(self.current_pressed_keys):
                import time
                current_time = time.time()
                
                # 防止重复执行：如果上次执行时间距离现在不到1秒，则忽略
                if current_time - self.last_pressed_time < 1.0:
                    logger.debug("快捷键执行过于频繁，已忽略")
                    return
                
                logger.info(f"✅ 检测到配置的快捷键: {self.hotkey_config.get_copilot_key()}")
                
                # 更新最后执行时间
                self.last_pressed_time = current_time
                
                # 在新线程中打开应用，避免阻塞键盘监听
                try:
                    threading.Thread(target=self.open_neko_app, daemon=True).start()
                    logger.info("已启动线程打开 N.E.K.O 应用")
                except Exception as e:
                    logger.error(f"启动打开应用线程时出错: {e}")
                
        except Exception as e:
            logger.error(f"处理按键按下事件时出错: {e}")

    def on_release(self, key):
        """按键释放时的回调"""
        try:
            # 从当前按键集合中移除释放的键
            try:
                if hasattr(key, 'name'):
                    key_name = key.name.lower()
                    # 映射键名，与按下时保持一致
                    if key_name == 'cmd' or key_name.startswith('win'):
                        key_name = 'ctrl'
                    elif key_name == 'alt_l':
                        key_name = 'alt'
                    elif key_name == 'ctrl_l':
                        key_name = 'ctrl'
                    elif key_name == 'shift_l':
                        key_name = 'shift'
                    self.current_pressed_keys.discard(key_name)
                elif hasattr(key, 'char') and key.char:
                    self.current_pressed_keys.discard(key.char.lower())
                else:
                    str_key = str(key).lower()
                    if str_key.startswith("'") and str_key.endswith("'"):
                        str_key = str_key[1:-1]
                    elif 'key.f' in str_key:
                        # 处理功能键，例如 'Key.f10' -> 'f10'
                        str_key = str_key.split('.')[-1]
                    self.current_pressed_keys.discard(str_key)
            except Exception as e:
                str_key = str(key).lower()
                if str_key.startswith("'") and str_key.endswith("'"):
                    str_key = str_key[1:-1]
                self.current_pressed_keys.discard(str_key)
            
            # 调试日志
            logger.debug(f"按键释放: {key}, 剩余按键: {self.current_pressed_keys}")
        except Exception as e:
            logger.error(f"处理按键释放事件时出错: {e}")

    def reset_keys(self):
        """重置按键状态"""
        self.current_pressed_keys.clear()

    def open_neko_app(self):
        """通知前端应用获取焦点并打开文字对话框"""
        try:
            # 尝试直接调用主服务器的 WebSocket 广播功能，避免 HTTP 请求延迟
            import asyncio
            from main_server import broadcast_focus_request
            
            logger.info("正在直接发送 WebSocket 焦点请求到前端应用")
            
            # 由于 broadcast_focus_request 是异步函数，我们需要在事件循环中运行它
            # 检查当前线程是否已经有事件循环
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行（如在 FastAPI 应用中），创建任务
                    asyncio.create_task(broadcast_focus_request("focus_and_open_textbox"))
                else:
                    # 如果事件循环未运行，直接运行函数
                    loop.run_until_complete(broadcast_focus_request("focus_and_open_textbox"))
            except RuntimeError:
                # 如果没有事件循环（如在普通 Python 脚本中），创建一个新的
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(broadcast_focus_request("focus_and_open_textbox"))
                finally:
                    new_loop.close()
                
        except ImportError:
            logger.warning("无法导入主服务器广播函数，将使用HTTP请求方式")
            # 如果无法直接访问广播函数，则使用 HTTP 请求作为备选
            self._fallback_http_request()
        except Exception as e:
            logger.warning(f"直接发送 WebSocket 消息失败，将使用HTTP请求方式: {e}")
            logger.exception(e)  # 添加详细异常信息
            self._fallback_http_request()
    
    def _fallback_http_request(self):
        """备选的HTTP请求方法"""
        try:
            from config import MAIN_SERVER_PORT
            import requests
            url = f"http://localhost:{MAIN_SERVER_PORT}/api/focus-app"
            logger.info(f"正在发送HTTP焦点请求到: {url}")
            
            # 发送一个简单的请求给前端，通知它获取焦点
            # 使用更短的超时时间以提高响应速度
            response = requests.post(url, json={"action": "focus_and_open_textbox"}, timeout=1)
            logger.info(f"HTTP焦点请求响应: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("✅ 成功发送HTTP焦点请求到前端应用")
            else:
                logger.warning(f"⚠️ HTTP前端响应状态码: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            logger.warning("⚠️ 无法连接到主服务器")
        except Exception as e:
            logger.error(f"发送HTTP焦点请求失败: {e}")

    def start_listening(self):
        """开始监听快捷键"""
        if self.listener is None or not self.listener.is_alive():
            self.listener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release
            )
            self.listener.start()
            logger.info("快捷键监听器已启动")
            logger.info(f"当前配置的 Copilot 快捷键: {self.hotkey_config.get_copilot_key()}")
            logger.info("如需修改快捷键，请编辑 config/hotkey_config.json 文件")
            return self.listener
        else:
            logger.warning("快捷键监听器已在运行中")

    def stop_listening(self):
        """停止监听快捷键"""
        if self.listener:
            self.listener.stop()
            logger.info("快捷键监听器已停止")


# 全局实例
hotkey_handler = HotkeyHandler()

def start_hotkey_listener():
    """启动快捷键监听器的便捷函数"""
    return hotkey_handler.start_listening()

def stop_hotkey_listener():
    """停止快捷键监听器的便捷函数"""
    hotkey_handler.stop_listening()


def main():
    print("启动快捷键监听器...")
    hotkey_config = get_hotkey_config()
    print(f"当前配置的快捷键: {hotkey_config.get_copilot_key()}")
    print("如需修改快捷键，请编辑 config/hotkey_config.json 文件")
    print("按 Ctrl+C 退出")
    
    listener = start_hotkey_listener()
    
    try:
        # 保持程序运行
        if listener:
            listener.join()
    except KeyboardInterrupt:
        stop_hotkey_listener()
        print("\n已退出快捷键监听器")

if __name__ == "__main__":
    main()

