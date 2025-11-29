import webbrowser
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from main_helper import core as core, cross_server as cross_server
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from utils.preferences import load_user_preferences, update_model_preferences, validate_model_preferences, move_model_to_top
from utils.frontend_utils import find_models, find_model_config_file
from multiprocessing import Process, Queue, Event
import atexit
from config import MAIN_SERVER_PORT, MONITOR_SERVER_PORT
from utils.config_manager import get_config_manager
from utils.hotkey_handler import start_hotkey_listener
import sys
import os
import asyncio
import uuid

# 在 Windows 上使用多进程需要添加此检查
if __name__ == '__main__' or __package__:
    # 防止在导入时就启动多进程
    pass

# 确定 templates 目录位置（支持 PyInstaller/Nuitka 打包）
if getattr(sys, 'frozen', False):
    # 打包后运行
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller
        template_dir = sys._MEIPASS
    else:
        # Nuitka
        template_dir = os.path.dirname(os.path.abspath(__file__))
else:
    # 正常运行：当前目录
    template_dir = "./"

templates = Jinja2Templates(directory=template_dir)

# Configure logging with loguru
from loguru import logger

_config_manager = get_config_manager()

def cleanup():
    logger.info("Starting cleanup process")
    for k in sync_message_queue:
        while sync_message_queue[k] and not sync_message_queue[k].empty():
            sync_message_queue[k].get_nowait()
        sync_message_queue[k].close()
        sync_message_queue[k].join_thread()
    logger.info("Cleanup completed")
atexit.register(cleanup)
sync_message_queue = {}
sync_shutdown_event = {}
session_manager = {}
session_id = {}
sync_process = {}
# 每个角色的websocket操作锁，用于防止preserve/restore与cleanup()之间的竞争
websocket_locks = {}
# 全局活动WebSocket连接追踪器，用于广播消息到所有连接
active_websockets = set()  # 存储所有活跃的WebSocket连接
# Global variables for character data (will be updated on reload)
master_name = None
her_name = None
master_basic_config = None
lanlan_basic_config = None
name_mapping = None
lanlan_prompt = None
semantic_store = None
time_store = None
setting_store = None
recent_log = None
catgirl_names = []

async def initialize_character_data():
    """初始化或重新加载角色配置数据"""
    global master_name, her_name, master_basic_config, lanlan_basic_config
    global name_mapping, lanlan_prompt, semantic_store, time_store, setting_store, recent_log
    global catgirl_names, sync_message_queue, sync_shutdown_event, session_manager, session_id, sync_process, websocket_locks
    
    logger.info("正在加载角色配置...")
    
    # 清理无效的voice_id引用
    _config_manager.cleanup_invalid_voice_ids()
    
    # 加载最新的角色数据
    master_name, her_name, master_basic_config, lanlan_basic_config, name_mapping, lanlan_prompt, semantic_store, time_store, setting_store, recent_log = _config_manager.get_character_data()
    catgirl_names = list(lanlan_prompt.keys())
    
    # 为新增的角色初始化资源
    for k in catgirl_names:
        is_new_character = False
        if k not in sync_message_queue:
            sync_message_queue[k] = Queue()
            sync_shutdown_event[k] = Event()
            session_id[k] = None
            sync_process[k] = None
            logger.info(f"为角色 {k} 初始化新资源")
            is_new_character = True
        
        # 确保该角色有websocket锁
        if k not in websocket_locks:
            websocket_locks[k] = asyncio.Lock()
        
        # 更新或创建session manager（使用最新的prompt）
        # 使用锁保护websocket的preserve/restore操作，防止与cleanup()竞争
        async with websocket_locks[k]:
            # 如果已存在且已有websocket连接，保留websocket引用
            old_websocket = None
            if k in session_manager and session_manager[k].websocket:
                old_websocket = session_manager[k].websocket
                logger.info(f"保留 {k} 的现有WebSocket连接")
            
            session_manager[k] = core.LLMSessionManager(
                sync_message_queue[k],
                k,
                lanlan_prompt[k].replace('{LANLAN_NAME}', k).replace('{MASTER_NAME}', master_name)
            )
            
            # 将websocket锁存储到session manager中，供cleanup()使用
            session_manager[k].websocket_lock = websocket_locks[k]
            
            # 恢复websocket引用（如果存在）
            if old_websocket:
                session_manager[k].websocket = old_websocket
                logger.info(f"已恢复 {k} 的WebSocket连接")
        
        # 检查并启动同步连接器进程
        # 如果是新角色，或者进程不存在/已停止，需要启动进程
        if k not in sync_process:
            sync_process[k] = None
        
        need_start_process = False
        if is_new_character:
            # 新角色，需要启动进程
            need_start_process = True
        elif sync_process[k] is None:
            # 进程为None，需要启动
            need_start_process = True
        elif hasattr(sync_process[k], 'is_alive') and not sync_process[k].is_alive():
            # 进程已停止，需要重启
            need_start_process = True
            try:
                sync_process[k].join(timeout=0.1)
            except:
                pass
        
        if need_start_process:
            try:
                # 在线程池中启动进程以避免 Windows 上的多进程问题
                def create_and_start_process():
                    process = Process(
                        target=cross_server.sync_connector_process,
                        args=(sync_message_queue[k], sync_shutdown_event[k], k, f"ws://localhost:{MONITOR_SERVER_PORT}", {'bullet': False, 'monitor': True})
                    )
                    process.start()
                    return process
                
                # 获取当前事件循环以运行执行器任务
                current_loop = asyncio.get_event_loop()
                sync_process[k] = await current_loop.run_in_executor(None, create_and_start_process)
                logger.info(f"✅ 已为角色 {k} 启动同步连接器进程 (PID: {sync_process[k].pid})")
                await asyncio.sleep(0.2)
                if not sync_process[k].is_alive():
                    logger.error(f"❌ 同步连接器进程 {k} (PID: {sync_process[k].pid}) 启动后立即退出！退出码: {sync_process[k].exitcode}")
                else:
                    logger.info(f"✅ 同步连接器进程 {k} (PID: {sync_process[k].pid}) 正在运行")
            except Exception as e:
                logger.error(f"❌ 启动角色 {k} 的同步连接器进程失败: {e}", exc_info=True)
    
    # 清理已删除角色的资源
    removed_names = [k for k in session_manager.keys() if k not in catgirl_names]
    for k in removed_names:
        logger.info(f"清理已删除角色 {k} 的资源")
        
        # 先停止同步连接器进程
        if k in sync_process and sync_process[k] is not None:
            try:
                logger.info(f"正在停止已删除角色 {k} 的同步连接器进程...")
                if k in sync_shutdown_event:
                    sync_shutdown_event[k].set()
                sync_process[k].join(timeout=3)
                if sync_process[k].is_alive():
                    sync_process[k].terminate()
                    sync_process[k].join(timeout=1)
                    if sync_process[k].is_alive():
                        sync_process[k].kill()
                logger.info(f"✅ 已停止角色 {k} 的同步连接器进程")
            except Exception as e:
                logger.warning(f"停止角色 {k} 的同步连接器进程时出错: {e}")
        
        # 清理队列
        if k in sync_message_queue:
            try:
                while not sync_message_queue[k].empty():
                    sync_message_queue[k].get_nowait()
                sync_message_queue[k].close()
                sync_message_queue[k].join_thread()
            except:
                pass
            del sync_message_queue[k]
        
        # 清理其他资源
        if k in sync_shutdown_event:
            del sync_shutdown_event[k]
        if k in session_manager:
            del session_manager[k]
        if k in session_id:
            del session_id[k]
        if k in sync_process:
            del sync_process[k]
    
    logger.info(f"角色配置加载完成，当前角色: {catgirl_names}，主人: {master_name}")

# 初始化角色数据（使用asyncio.run在模块级别执行async函数）
import asyncio as _init_asyncio
try:
    _init_asyncio.get_event_loop()
except RuntimeError:
    _init_asyncio.set_event_loop(_init_asyncio.new_event_loop())
_init_asyncio.get_event_loop().run_until_complete(initialize_character_data())
lock = asyncio.Lock()

# --- FastAPI App Setup ---
app = FastAPI()

class CustomStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if path.endswith('.js'):
            response.headers['Content-Type'] = 'application/javascript'
        return response

# 确定 static 目录位置（支持 PyInstaller/Nuitka 打包）
if getattr(sys, 'frozen', False):
    # 打包后运行
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller
        static_dir = os.path.join(sys._MEIPASS, 'static')
    else:
        # Nuitka
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
else:
    # 正常运行：当前目录
    static_dir = 'static'

app.mount("/static", CustomStaticFiles(directory=static_dir), name="static")

# 挂载用户文档下的live2d目录
_config_manager.ensure_live2d_directory()
user_live2d_path = str(_config_manager.live2d_dir)
if os.path.exists(user_live2d_path):
    app.mount("/user_live2d", CustomStaticFiles(directory=user_live2d_path), name="user_live2d")
    logger.info(f"已挂载用户Live2D目录: {user_live2d_path}")

# 使用 FastAPI 的 app.state 来管理启动配置
def get_start_config():
    """从 app.state 获取启动配置"""
    if hasattr(app.state, 'start_config'):
        return app.state.start_config
    return {
        "browser_mode_enabled": False,
        "browser_page": "chara_manager",
        'server': None
    }

def set_start_config(config):
    """设置启动配置到 app.state"""
    app.state.start_config = config

@app.get("/", response_class=HTMLResponse)
async def get_default_index(request: Request):
    return templates.TemplateResponse("templates/index.html", {
        "request": request
    })


@app.get("/api/preferences")
async def get_preferences():
    """获取用户偏好设置"""
    preferences = load_user_preferences()
    return preferences

@app.post("/api/preferences")
async def save_preferences(request: Request):
    """保存用户偏好设置"""
    try:
        data = await request.json()
        if not data:
            return {"success": False, "error": "无效的数据"}
        
        # 验证偏好数据
        if not validate_model_preferences(data):
            return {"success": False, "error": "偏好数据格式无效"}
        
        # 更新偏好
        if update_model_preferences(data['model_path'], data['position'], data['scale']):
            return {"success": True, "message": "偏好设置已保存"}
        else:
            return {"success": False, "error": "保存失败"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/live2d/models")
async def get_live2d_models(simple: bool = False):
    """
    获取Live2D模型列表
    Args:
        simple: 如果为True，只返回模型名称列表；如果为False，返回完整的模型信息
    """
    try:
        models = find_models()
        
        if simple:
            # 只返回模型名称列表
            model_names = [model["name"] for model in models]
            return {"success": True, "models": model_names}
        else:
            # 返回完整的模型信息（保持向后兼容）
            return models
    except Exception as e:
        logger.error(f"获取Live2D模型列表失败: {e}")
        if simple:
            return {"success": False, "error": str(e)}
        else:
            return []

@app.get("/api/models")
async def get_models_legacy():
    """
    向后兼容的API端点，重定向到新的 /api/live2d/models
    """
    return await get_live2d_models(simple=False)

@app.post("/api/preferences/set-preferred")
async def set_preferred_model(request: Request):
    """设置首选模型"""
    try:
        data = await request.json()
        if not data or 'model_path' not in data:
            return {"success": False, "error": "无效的数据"}
        
        if move_model_to_top(data['model_path']):
            return {"success": True, "message": "首选模型已更新"}
        else:
            return {"success": False, "error": "模型不存在或更新失败"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/config/page_config")
async def get_page_config(lanlan_name: str = ""):
    """获取页面配置（lanlan_name 和 model_path）"""
    try:
        # 获取角色数据
        _, her_name, _, lanlan_basic_config, _, _, _, _, _, _ = _config_manager.get_character_data()
        
        # 如果提供了 lanlan_name 参数，使用它；否则使用当前角色
        target_name = lanlan_name if lanlan_name else her_name
        
        # 获取 live2d 字段
        live2d = lanlan_basic_config.get(target_name, {}).get('live2d', 'mao_pro')
        
        # 查找所有模型
        models = find_models()
        
        # 根据 live2d 字段查找对应的 model path
        model_path = next((m["path"] for m in models if m["name"] == live2d), find_model_config_file(live2d))
        
        return {
            "success": True,
            "lanlan_name": target_name,
            "model_path": model_path
        }
    except Exception as e:
        logger.error(f"获取页面配置失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "lanlan_name": "",
            "model_path": ""
        }

@app.get("/api/config/core_api")
async def get_core_config_api():
    """获取核心配置（API Key）"""
    try:
        # 尝试从core_config.json读取
        try:
            from utils.config_manager import get_config_manager
            config_manager = get_config_manager()
            core_config_path = str(config_manager.get_config_path('core_config.json'))
            with open(core_config_path, 'r', encoding='utf-8') as f:
                core_cfg = json.load(f)
                api_key = core_cfg.get('coreApi', '')
        except FileNotFoundError:
            # 如果文件不存在，返回当前配置中的CORE_API_KEY
            core_config = _config_manager.get_core_config()
            api_key = core_config['CORE_API_KEY']
        
        return {
            "api_key": api_key,
            "coreApi": core_cfg.get('coreApi', 'qwen'),
            "assistApi": core_cfg.get('assistApi', 'qwen'),
            "assistApiKeyQwen": core_cfg.get('assistApiKeyQwen', ''),
            "assistApiKeyOpenai": core_cfg.get('assistApiKeyOpenai', ''),
            "assistApiKeyGlm": core_cfg.get('assistApiKeyGlm', ''),
            "assistApiKeyStep": core_cfg.get('assistApiKeyStep', ''),
            "assistApiKeySilicon": core_cfg.get('assistApiKeySilicon', ''),
            "mcpToken": core_cfg.get('mcpToken', ''),  # 添加mcpToken字段
            "enableCustomApi": core_cfg.get('enableCustomApi', False),  # 添加enableCustomApi字段
            "success": True
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/config/api_providers")
async def get_api_providers_config():
    """获取API服务商配置（供前端使用）"""
    try:
        from utils.api_config_loader import (
            get_core_api_providers_for_frontend,
            get_assist_api_providers_for_frontend,
        )
        
        # 使用缓存加载配置（性能更好，配置更新后需要重启服务）
        core_providers = get_core_api_providers_for_frontend()
        assist_providers = get_assist_api_providers_for_frontend()
        
        return {
            "success": True,
            "core_api_providers": core_providers,
            "assist_api_providers": assist_providers,
        }
    except Exception as e:
        logger.error(f"获取API服务商配置失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "core_api_providers": [],
            "assist_api_providers": [],
        }


@app.post("/api/config/core_api")
async def update_core_config(request: Request):
    """更新核心配置（API Key）"""
    try:
        data = await request.json()
        if not data:
            return {"success": False, "error": "无效的数据"}
        
        # 检查是否启用了自定义API
        enable_custom_api = data.get('enableCustomApi', False)
        
        # 如果启用了自定义API，不需要强制检查核心API key
        if not enable_custom_api:
            # 检查是否为免费版配置
            is_free_version = data.get('coreApi') == 'free' or data.get('assistApi') == 'free'
            
            if 'coreApiKey' not in data:
                return {"success": False, "error": "缺少coreApiKey字段"}
            
            api_key = data['coreApiKey']
            if api_key is None:
                return {"success": False, "error": "API Key不能为null"}
            
            if not isinstance(api_key, str):
                return {"success": False, "error": "API Key必须是字符串类型"}
            
            api_key = api_key.strip()
            
            # 免费版允许使用 'free-access' 作为API key，不进行空值检查
            if not is_free_version and not api_key:
                return {"success": False, "error": "API Key不能为空"}
        
        # 保存到core_config.json
        from pathlib import Path
        from utils.config_manager import get_config_manager
        config_manager = get_config_manager()
        core_config_path = str(config_manager.get_config_path('core_config.json'))
        # 确保配置目录存在
        Path(core_config_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 构建配置对象
        core_cfg = {}
        
        # 只有在启用自定义API时，才允许不设置coreApiKey
        if enable_custom_api:
            # 启用自定义API时，coreApiKey是可选的
            if 'coreApiKey' in data:
                api_key = data['coreApiKey']
                if api_key is not None and isinstance(api_key, str):
                    core_cfg['coreApiKey'] = api_key.strip()
        else:
            # 未启用自定义API时，必须设置coreApiKey
            api_key = data.get('coreApiKey', '')
            if api_key is not None and isinstance(api_key, str):
                core_cfg['coreApiKey'] = api_key.strip()
        if 'coreApi' in data:
            core_cfg['coreApi'] = data['coreApi']
        if 'assistApi' in data:
            core_cfg['assistApi'] = data['assistApi']
        if 'assistApiKeyQwen' in data:
            core_cfg['assistApiKeyQwen'] = data['assistApiKeyQwen']
        if 'assistApiKeyOpenai' in data:
            core_cfg['assistApiKeyOpenai'] = data['assistApiKeyOpenai']
        if 'assistApiKeyGlm' in data:
            core_cfg['assistApiKeyGlm'] = data['assistApiKeyGlm']
        if 'assistApiKeyStep' in data:
            core_cfg['assistApiKeyStep'] = data['assistApiKeyStep']
        if 'assistApiKeySilicon' in data:
            core_cfg['assistApiKeySilicon'] = data['assistApiKeySilicon']
        if 'mcpToken' in data:
            core_cfg['mcpToken'] = data['mcpToken']
        if 'enableCustomApi' in data:
            core_cfg['enableCustomApi'] = data['enableCustomApi']
        
        # 添加用户自定义API配置
        if 'summaryModelProvider' in data:
            core_cfg['summaryModelProvider'] = data['summaryModelProvider']
        if 'summaryModelUrl' in data:
            core_cfg['summaryModelUrl'] = data['summaryModelUrl']
        if 'summaryModelApiKey' in data:
            core_cfg['summaryModelApiKey'] = data['summaryModelApiKey']
        if 'correctionModelProvider' in data:
            core_cfg['correctionModelProvider'] = data['correctionModelProvider']
        if 'correctionModelUrl' in data:
            core_cfg['correctionModelUrl'] = data['correctionModelUrl']
        if 'correctionModelApiKey' in data:
            core_cfg['correctionModelApiKey'] = data['correctionModelApiKey']
        if 'emotionModelProvider' in data:
            core_cfg['emotionModelProvider'] = data['emotionModelProvider']
        if 'emotionModelUrl' in data:
            core_cfg['emotionModelUrl'] = data['emotionModelUrl']
        if 'emotionModelApiKey' in data:
            core_cfg['emotionModelApiKey'] = data['emotionModelApiKey']
        if 'visionModelProvider' in data:
            core_cfg['visionModelProvider'] = data['visionModelProvider']
        if 'visionModelUrl' in data:
            core_cfg['visionModelUrl'] = data['visionModelUrl']
        if 'visionModelApiKey' in data:
            core_cfg['visionModelApiKey'] = data['emotionModelApiKey']
        if 'omniModelProvider' in data:
            core_cfg['omniModelProvider'] = data['omniModelProvider']
        if 'omniModelUrl' in data:
            core_cfg['omniModelUrl'] = data['omniModelUrl']
        if 'omniModelApiKey' in data:
            core_cfg['omniModelApiKey'] = data['omniModelApiKey']
        if 'ttsModelProvider' in data:
            core_cfg['ttsModelProvider'] = data['ttsModelProvider']
        if 'ttsModelUrl' in data:
            core_cfg['ttsModelUrl'] = data['ttsModelUrl']
        if 'ttsModelApiKey' in data:
            core_cfg['ttsModelApiKey'] = data['ttsModelApiKey']
        
        with open(core_config_path, 'w', encoding='utf-8') as f:
            json.dump(core_cfg, f, indent=2, ensure_ascii=False)
        
        # API配置更新后，需要先通知所有客户端，再关闭session，最后重新加载配置
        logger.info("API配置已更新，准备通知客户端并重置所有session...")
        
        # 1. 先通知所有连接的客户端即将刷新（WebSocket还连着）
        notification_count = 0
        for lanlan_name, mgr in session_manager.items():
            if mgr.is_active and mgr.websocket:
                try:
                    await mgr.websocket.send_text(json.dumps({
                        "type": "reload_page",
                        "message": "API配置已更新，页面即将刷新"
                    }))
                    notification_count += 1
                    logger.info(f"已通知 {lanlan_name} 的前端刷新页面")
                except Exception as e:
                    logger.warning(f"通知 {lanlan_name} 的WebSocket失败: {e}")
        
        logger.info(f"已通知 {notification_count} 个客户端")
        
        # 2. 立刻关闭所有活跃的session（这会断开所有WebSocket）
        sessions_ended = []
        for lanlan_name, mgr in session_manager.items():
            if mgr.is_active:
                try:
                    await mgr.end_session(by_server=True)
                    sessions_ended.append(lanlan_name)
                    logger.info(f"{lanlan_name} 的session已结束")
                except Exception as e:
                    logger.error(f"结束 {lanlan_name} 的session时出错: {e}")
        
        # 3. 重新加载配置并重建session manager
        logger.info("正在重新加载配置...")
        try:
            await initialize_character_data()
            logger.info("配置重新加载完成，新的API配置已生效")
        except Exception as reload_error:
            logger.error(f"重新加载配置失败: {reload_error}")
            return {"success": False, "error": f"配置已保存但重新加载失败: {str(reload_error)}"}
        
        logger.info(f"已通知 {notification_count} 个连接的客户端API配置已更新")
        return {"success": True, "message": "API Key已保存并重新加载配置", "sessions_ended": len(sessions_ended)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.on_event("startup")
async def startup_event():
    global sync_process
    logger.info("Starting sync connector processes")
    # 启动同步连接器进程（确保所有角色都有进程）
    for k in list(sync_message_queue.keys()):
        if k not in sync_process or sync_process[k] is None or (hasattr(sync_process.get(k), 'is_alive') and not sync_process[k].is_alive()):
            if k in sync_process and sync_process[k] is not None:
                # 清理已停止的进程
                try:
                    sync_process[k].join(timeout=0.1)
                except:
                    pass
            try:
                sync_process[k] = Process(
                    target=cross_server.sync_connector_process,
                    args=(sync_message_queue[k], sync_shutdown_event[k], k, f"ws://localhost:{MONITOR_SERVER_PORT}", {'bullet': False, 'monitor': True})
                )
                sync_process[k].start()
                logger.info(f"✅ 同步连接器进程已启动 (PID: {sync_process[k].pid}) for {k}")
                # 检查进程是否成功启动
                await asyncio.sleep(0.2)
                if not sync_process[k].is_alive():
                    logger.error(f"❌ 同步连接器进程 {k} (PID: {sync_process[k].pid}) 启动后立即退出！退出码: {sync_process[k].exitcode}")
                else:
                    logger.info(f"✅ 同步连接器进程 {k} (PID: {sync_process[k].pid}) 正在运行")
            except Exception as e:
                logger.error(f"❌ 启动角色 {k} 的同步连接器进程失败: {e}", exc_info=True)
    
    # 如果启用了浏览器模式，在服务器启动完成后打开浏览器
    current_config = get_start_config()
    print(f"启动配置: {current_config}")
    if current_config['browser_mode_enabled']:
        import threading
        
        def launch_browser_delayed():
            # 等待一小段时间确保服务器完全启动
            import time
            time.sleep(1)
            # 从 app.state 获取配置
            config = get_start_config()
            url = f"http://127.0.0.1:{MAIN_SERVER_PORT}/{config['browser_page']}"
            try:
                webbrowser.open(url)
                logger.info(f"服务器启动完成，已打开浏览器访问: {url}")
            except Exception as e:
                logger.error(f"打开浏览器失败: {e}")
        
        # 在独立线程中启动浏览器
        t = threading.Thread(target=launch_browser_delayed, daemon=True)
        t.start()

    # 启动快捷键监听器
    try:
        start_hotkey_listener()
        logger.info("快捷键监听器已启动")
    except Exception as e:
        logger.error(f"启动快捷键监听器失败: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("Shutting down sync connector processes")
    # 关闭同步服务器连接
    for k in sync_process:
        if sync_process[k] is not None:
            sync_shutdown_event[k].set()
            sync_process[k].join(timeout=3)  # 等待进程正常结束
            if sync_process[k].is_alive():
                sync_process[k].terminate()  # 如果超时，强制终止
    logger.info("同步连接器进程已停止")
    
    # 向memory_server发送关闭信号
    try:
        import requests
        from config import MEMORY_SERVER_PORT
        shutdown_url = f"http://localhost:{MEMORY_SERVER_PORT}/shutdown"
        response = requests.post(shutdown_url, timeout=2)
        if response.status_code == 200:
            logger.info("已向memory_server发送关闭信号")
        else:
            logger.warning(f"向memory_server发送关闭信号失败，状态码: {response.status_code}")
    except Exception as e:
        logger.warning(f"向memory_server发送关闭信号时出错: {e}")


@app.websocket("/ws/{lanlan_name}")
async def websocket_endpoint(websocket: WebSocket, lanlan_name: str):
    await websocket.accept()
    this_session_id = uuid.uuid4()
    async with lock:
        global session_id
        session_id[lanlan_name] = this_session_id
    logger.info(f"⭐websocketWebSocket accepted: {websocket.client}, new session id: {session_id[lanlan_name]}, lanlan_name: {lanlan_name}")
    
    # 立即设置websocket到session manager，以支持主动搭话
    # 注意：这里设置后，即使cleanup()被调用，websocket也会在start_session时重新设置
    if lanlan_name in session_manager:
        session_manager[lanlan_name].websocket = websocket
        logger.info(f"✅ 已设置 {lanlan_name} 的WebSocket连接")
    else:
        logger.error(f"❌ 错误：{lanlan_name} 不在session_manager中！当前session_manager: {list(session_manager.keys())}")
    
    # 将WebSocket添加到全局活跃连接集合，以便进行广播
    active_websockets.add(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            if session_id[lanlan_name] != this_session_id:
                await session_manager[lanlan_name].send_status(f"切换至另一个终端...")
                await websocket.close()
                break
            message = json.loads(data)
            action = message.get("action")
            # logger.debug(f"WebSocket received action: {action}") # Optional debug log

            if action == "start_session":
                session_manager[lanlan_name].active_session_is_idle = False
                input_type = message.get("input_type", "audio")
                if input_type in ['audio', 'screen', 'camera', 'text']:
                    # 传递input_mode参数，告知session manager使用何种模式
                    mode = 'text' if input_type == 'text' else 'audio'
                    asyncio.create_task(session_manager[lanlan_name].start_session(websocket, message.get("new_session", False), mode))
                else:
                    await session_manager[lanlan_name].send_status(f"Invalid input type: {input_type}")

            elif action == "stream_data":
                asyncio.create_task(session_manager[lanlan_name].stream_data(message))

            elif action == "end_session":
                session_manager[lanlan_name].active_session_is_idle = False
                asyncio.create_task(session_manager[lanlan_name].end_session())

            elif action == "pause_session":
                session_manager[lanlan_name].active_session_is_idle = True
                asyncio.create_task(session_manager[lanlan_name].end_session())

            elif action == "ping":
                # 心跳保活消息，回复pong
                await websocket.send_text(json.dumps({"type": "pong"}))
                # logger.debug(f"收到心跳ping，已回复pong")

            else:
                logger.warning(f"Unknown action received: {action}")
                await session_manager[lanlan_name].send_status(f"Unknown action: {action}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {websocket.client}, session id: {session_id[lanlan_name]}, lanlan_name: {lanlan_name}")
        if lanlan_name in session_manager:
            session_manager[lanlan_name].websocket = None
        # 从全局活跃连接集合中移除WebSocket
        if websocket in active_websockets:
            active_websockets.discard(websocket)
        # Clean up session ID
        async with lock:
            if lanlan_name in session_id and session_id[lanlan_name] == this_session_id:
                session_id[lanlan_name] = None
        # If the session was active, end it properly
        if lanlan_name in session_manager and session_manager[lanlan_name].is_active:
            try:
                await session_manager[lanlan_name].end_session(by_server=True)
            except Exception as e:
                logger.error(f"Error ending session for {lanlan_name}: {e}")

@app.post('/api/focus-app')
async def focus_app(request: Request):
    """供快捷键服务调用：通知前端应用获取焦点并打开文字对话框"""
    try:
        data = await request.json()
        action = data.get('action', '')
        
        if action == 'focus_and_open_textbox':
            # 向所有连接的客户端发送一个特殊消息，通知它们获取焦点
            # 使用列表推导式和批量处理来提高性能
            successful_sends = 0
            for lanlan_name, mgr in session_manager.items():
                if mgr.websocket:
                    try:
                        await mgr.websocket.send_text(json.dumps({
                            "type": "focus_request", 
                            "action": "focus_and_open_textbox"
                        }))
                        successful_sends += 1
                    except Exception as e:
                        logger.debug(f"发送焦点请求到 {lanlan_name} 失败: {e}")  # 改为debug级别避免过多日志
            return JSONResponse({"success": True, "message": f"Focus request sent to {successful_sends} clients"})
        else:
            return JSONResponse({"success": False, "error": "Invalid action"}, status_code=400)
    except Exception as e:
        logger.error(f"处理焦点请求时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post('/api/notify_task_result')
async def notify_task_result(request: Request):
    """供工具/任务服务回调：在下一次正常回复之后，插入一条任务完成提示。"""
    try:
        data = await request.json()
        # 如果未显式提供，则使用当前默认角色
        name = data.get('character_name', her_name)
        if name not in session_manager:
            return JSONResponse({"success": False, "error": f"Character {name} not found"}, status_code=404)
        session_manager[name].pending_task_result = data.get('result', '')
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"处理任务结果回调时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post('/api/notify_user_message')
async def notify_user_message(request: Request):
    """供外部服务调用：在下一次AI回复之后，插入一条用户消息记录。"""
    try:
        data = await request.json()
        # 如果未显式提供，则使用当前默认角色
        name = data.get('character_name', her_name)
        if name not in session_manager:
            return JSONResponse({"success": False, "error": f"Character {name} not found"}, status_code=404)
        session_manager[name].pending_user_message = data.get('message', '')
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"处理用户消息通知时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get('/api/characters')
async def get_characters():
    """获取所有角色列表"""
    try:
        return JSONResponse({"success": True, "characters": catgirl_names})
    except Exception as e:
        logger.error(f"获取角色列表时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get('/api/characters/{character_name}/config')
async def get_character_config(character_name: str):
    """获取特定角色的配置"""
    try:
        if character_name not in lanlan_prompt:
            return JSONResponse({"success": False, "error": f"Character {character_name} not found"}, status_code=404)
        config = lanlan_basic_config.get(character_name, {})
        config['prompt'] = lanlan_prompt[character_name]
        return JSONResponse({"success": True, "config": config})
    except Exception as e:
        logger.error(f"获取角色配置时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post('/api/characters/{character_name}/config')
async def update_character_config(character_name: str, request: Request):
    """更新特定角色的配置"""
    try:
        if character_name not in lanlan_prompt:
            return JSONResponse({"success": False, "error": f"Character {character_name} not found"}, status_code=404)
        data = await request.json()
        # 更新内存中的配置
        if character_name in lanlan_basic_config:
            lanlan_basic_config[character_name].update(data)
        else:
            lanlan_basic_config[character_name] = data
        # 保存到持久化存储
        _config_manager.update_character_config(character_name, data)
        # 通知客户端配置已更新（通过WebSocket发送reload_page消息）
        if character_name in session_manager and session_manager[character_name].websocket:
            try:
                await session_manager[character_name].websocket.send_text(json.dumps({
                    "type": "reload_page",
                    "message": f"角色 {character_name} 的配置已更新，页面即将刷新"
                }))
            except Exception as ws_error:
                logger.warning(f"通知 {character_name} 配置更新失败: {ws_error}")
        return JSONResponse({"success": True, "message": f"角色 {character_name} 配置已更新"})
    except Exception as e:
        logger.error(f"更新角色配置时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get('/api/characters/{character_name}/active')
async def is_character_active(character_name: str):
    """检查角色是否处于活跃状态"""
    try:
        if character_name not in session_manager:
            return JSONResponse({"success": False, "error": f"Character {character_name} not found"}, status_code=404)
        is_active = session_manager[character_name].is_active if hasattr(session_manager[character_name], 'is_active') else False
        return JSONResponse({"success": True, "active": is_active})
    except Exception as e:
        logger.error(f"检查角色活跃状态时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post('/api/characters/{character_name}/switch')
async def switch_character(character_name: str, request: Request):
    """切换到指定角色"""
    global her_name  # 在函数开始时声明全局变量
    try:
        if character_name not in lanlan_prompt:
            return JSONResponse({"success": False, "error": f"Character {character_name} not found"}, status_code=404)
        # 保存当前角色
        old_character = her_name
        # 更新全局变量
        her_name = character_name
        # 通知所有客户端角色已切换
        for name, mgr in session_manager.items():
            if mgr.websocket:
                try:
                    await mgr.websocket.send_text(json.dumps({
                        "type": "catgirl_switched",
                        "new_catgirl": character_name,
                        "old_catgirl": old_character
                    }))
                except Exception as ws_error:
                    logger.warning(f"通知 {name} 角色切换失败: {ws_error}")
        return JSONResponse({"success": True, "message": f"已切换到角色 {character_name}"})
    except Exception as e:
        logger.error(f"切换角色时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post('/api/memory/clear')
async def clear_memory(request: Request):
    """清除内存"""
    try:
        data = await request.json()
        character_name = data.get('character_name', her_name)
        if character_name not in session_manager:
            return JSONResponse({"success": False, "error": f"Character {character_name} not found"}, status_code=404)
        # 清除指定角色的内存
        session_manager[character_name].clear_memory()
        return JSONResponse({"success": True, "message": f"角色 {character_name} 的内存已清除"})
    except Exception as e:
        logger.error(f"清除内存时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get('/api/session/status')
async def get_session_status(character_name: str = None):
    """获取会话状态"""
    try:
        name = character_name or her_name
        if name not in session_manager:
            return JSONResponse({"success": False, "error": f"Character {name} not found"}, status_code=404)
        mgr = session_manager[name]
        status = {
            "active": mgr.is_active if hasattr(mgr, 'is_active') else False,
            "input_mode": mgr.input_mode if hasattr(mgr, 'input_mode') else None,
            "websocket_connected": mgr.websocket is not None
        }
        return JSONResponse({"success": True, "status": status})
    except Exception as e:
        logger.error(f"获取会话状态时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get('/api/characters/{character_name}/settings')
async def get_character_settings(character_name: str):
    """获取角色设置"""
    try:
        if character_name not in lanlan_basic_config:
            return JSONResponse({"success": False, "error": f"Character {character_name} not found"}, status_code=404)
        settings = lanlan_basic_config[character_name]
        return JSONResponse({"success": True, "settings": settings})
    except Exception as e:
        logger.error(f"获取角色设置时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post('/api/characters/{character_name}/settings')
async def update_character_settings(character_name: str, request: Request):
    """更新角色设置"""
    try:
        if character_name not in lanlan_basic_config:
            return JSONResponse({"success": False, "error": f"Character {character_name} not found"}, status_code=404)
        data = await request.json()
        # 更新内存中的设置
        for key, value in data.items():
            lanlan_basic_config[character_name][key] = value
        # 保存到持久化存储
        _config_manager.update_character_config(character_name, lanlan_basic_config[character_name])
        return JSONResponse({"success": True, "message": f"角色 {character_name} 设置已更新"})
    except Exception as e:
        logger.error(f"更新角色设置时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get('/api/characters/{character_name}/prompt')
async def get_character_prompt(character_name: str):
    """获取角色提示词"""
    try:
        if character_name not in lanlan_prompt:
            return JSONResponse({"success": False, "error": f"Character {character_name} not found"}, status_code=404)
        prompt = lanlan_prompt[character_name]
        return JSONResponse({"success": True, "prompt": prompt})
    except Exception as e:
        logger.error(f"获取角色提示词时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post('/api/characters/{character_name}/prompt')
async def update_character_prompt(character_name: str, request: Request):
    """更新角色提示词"""
    try:
        if character_name not in lanlan_prompt:
            return JSONResponse({"success": False, "error": f"Character {character_name} not found"}, status_code=404)
        data = await request.json()
        new_prompt = data.get('prompt', '')
        if not new_prompt:
            return JSONResponse({"success": False, "error": "Prompt cannot be empty"}, status_code=400)
        # 更新内存中的提示词
        lanlan_prompt[character_name] = new_prompt
        # 更新session manager中的提示词
        if character_name in session_manager:
            session_manager[character_name].update_system_prompt(new_prompt.replace('{LANLAN_NAME}', character_name).replace('{MASTER_NAME}', master_name))
        # 保存到持久化存储
        _config_manager.update_character_prompt(character_name, new_prompt)
        return JSONResponse({"success": True, "message": f"角色 {character_name} 提示词已更新"})
    except Exception as e:
        logger.error(f"更新角色提示词时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get('/api/settings/global')
async def get_global_settings():
    """获取全局设置"""
    try:
        settings = _config_manager.get_global_settings()
        return JSONResponse({"success": True, "settings": settings})
    except Exception as e:
        logger.error(f"获取全局设置时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post('/api/settings/global')
async def update_global_settings(request: Request):
    """更新全局设置"""
    try:
        data = await request.json()
        # 更新全局设置
        _config_manager.update_global_settings(data)
        return JSONResponse({"success": True, "message": "全局设置已更新"})
    except Exception as e:
        logger.error(f"更新全局设置时出错: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get('/api/health')
async def health_check():
    """健康检查端点"""
    return JSONResponse({"status": "healthy", "service": "main_server"})


@app.get('/api/version')
async def get_version():
    """获取版本信息"""
    try:
        import pkg_resources
        version = pkg_resources.get_distribution("n-e-k-o").version
        return JSONResponse({"version": version})
    except:
        return JSONResponse({"version": "unknown"})

# 添加全局函数，供 hotkey_handler 直接调用
async def broadcast_focus_request(action="focus_and_open_textbox"):
    """
    直接广播焦点请求到所有连接的客户端
    供 hotkey_handler 等模块直接调用，避免HTTP请求延迟
    """
    global session_manager, active_websockets
    logger.info("正在直接广播焦点请求到前端应用")
    logger.info(f"session_manager 中的角色: {list(session_manager.keys())}")
    logger.info(f"活跃的WebSocket连接数: {len(active_websockets)}")
    successful_sends = 0
    for lanlan_name, mgr in session_manager.items():
        try:
            await mgr.websocket.send_text(json.dumps({
                "type": "focus_request",
                "action": action
            }))
            successful_sends += 1
            logger.info(f"成功发送焦点请求到 {lanlan_name}")
        except Exception as e:
            logger.error(f"发送焦点请求到 {lanlan_name} 失败: {e}")  # 改为debug级别避免过多日志
    
    # 如果上面没有成功发送，尝试通过全局活跃连接集合发送
    if successful_sends == 0:
        logger.info("没有找到指定角色的WebSocket连接，将尝试通过全局活跃连接集合发送")
        for ws in active_websockets.copy():  # 使用副本以避免在迭代时修改集合
            try:
                await ws.send_text(json.dumps({
                    "type": "focus_request", 
                    "action": action
                }))
                successful_sends += 1
                logger.info(f"成功发送焦点请求到全局活跃连接")
            except Exception as e:
                logger.debug(f"发送焦点请求到全局活跃连接失败: {e}")
                # 如果连接失败，从活跃连接集合中移除
                active_websockets.discard(ws)
    
    logger.info(f"焦点请求已发送到 {successful_sends} 个客户端")
    return successful_sends

# 将函数添加到模块级别，以便其他模块可以导入
import sys
if __name__ != '__main__':
    sys.modules[__name__].broadcast_focus_request = broadcast_focus_request

if __name__ == "__main__":
    import argparse
    import uvicorn
    from utils.config_manager import get_config_manager
    import signal
    import os

    parser = argparse.ArgumentParser(description='N.E.K.O. Main Server')
    parser.add_argument('--port', type=int, default=MAIN_SERVER_PORT, help='Port to run the server on')
    parser.add_argument('--page', type=str, default='chara_manager', help='Default page to open in browser')
    parser.add_argument('--browser', action='store_true', help='Open browser after starting server')
    args = parser.parse_args()

    # Update MAIN_SERVER_PORT if specified in args
    MAIN_SERVER_PORT = args.port

    # Initialize config manager and set start config
    config_manager = get_config_manager()
    start_config = {
        "browser_mode_enabled": args.browser,
        "browser_page": args.page,
        'server': None
    }
    set_start_config(start_config)

    print(f"启动配置: {get_start_config()}")

    # 2) 定义服务器关闭回调
    def shutdown_server():
        logger.info("收到浏览器关闭信号，正在关闭服务器...")
        os.kill(os.getpid(), signal.SIGTERM)

    # 创建服务器实例
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=MAIN_SERVER_PORT, log_level="info"))
    
    # 4) 启动服务器（阻塞，直到 server.should_exit=True）
    logger.info("--- Starting FastAPI Server ---")
    logger.info(f"Access UI at: http://127.0.0.1:{MAIN_SERVER_PORT}/{args.page}")
    
    try:
        server.run()
    finally:
        logger.info("服务器已关闭")