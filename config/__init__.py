# -*- coding: utf-8 -*-
"""Configuration constants exposed by the config package."""

from copy import deepcopy
import logging

from config.prompts_chara import lanlan_prompt

logger = logging.getLogger(__name__)

# 应用程序名称配置
APP_NAME = "N.E.K.O"

# 服务器端口配置
MAIN_SERVER_PORT = 48911
MEMORY_SERVER_PORT = 48912
MONITOR_SERVER_PORT = 48913
COMMENTER_SERVER_PORT = 48914
TOOL_SERVER_PORT = 48915

# MCP Router配置
MCP_ROUTER_URL = 'http://localhost:3283'

# API 和模型配置的默认值
DEFAULT_CORE_API_KEY = ''
DEFAULT_AUDIO_API_KEY = ''
DEFAULT_OPENROUTER_API_KEY = ''
DEFAULT_MCP_ROUTER_API_KEY = 'Copy from MCP Router if needed'
DEFAULT_CORE_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
DEFAULT_CORE_MODEL = "qwen3-omni-flash-realtime"
DEFAULT_OPENROUTER_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 用户自定义模型配置的默认 Provider/URL/API_KEY（空字符串表示使用全局配置）
DEFAULT_SUMMARY_MODEL_PROVIDER = ""
DEFAULT_SUMMARY_MODEL_URL = ""
DEFAULT_SUMMARY_MODEL_API_KEY = ""
DEFAULT_CORRECTION_MODEL_PROVIDER = ""
DEFAULT_CORRECTION_MODEL_URL = ""
DEFAULT_CORRECTION_MODEL_API_KEY = ""
DEFAULT_EMOTION_MODEL_PROVIDER = ""
DEFAULT_EMOTION_MODEL_URL = ""
DEFAULT_EMOTION_MODEL_API_KEY = ""
DEFAULT_VISION_MODEL_PROVIDER = ""
DEFAULT_VISION_MODEL_URL = ""
DEFAULT_VISION_MODEL_API_KEY = ""
DEFAULT_OMNI_MODEL_PROVIDER = ""
DEFAULT_OMNI_MODEL_URL = ""
DEFAULT_OMNI_MODEL_API_KEY = ""
DEFAULT_TTS_MODEL_PROVIDER = ""
DEFAULT_TTS_MODEL_URL = ""
DEFAULT_TTS_MODEL_API_KEY = ""
DEFAULT_COMPUTER_USE_MODEL = ""  # 空字符串表示使用 assistApi 对应的视觉模型
DEFAULT_COMPUTER_USE_MODEL_URL = ""  # 空字符串表示使用 assistApi 对应的 URL
DEFAULT_COMPUTER_USE_MODEL_API_KEY = ""  # 空字符串表示使用 assistApi 对应的 API Key
DEFAULT_COMPUTER_USE_GROUND_MODEL = ""  # 空字符串表示使用 assistApi 对应的视觉模型
DEFAULT_COMPUTER_USE_GROUND_URL = ""  # 空字符串表示使用 assistApi 对应的 URL
DEFAULT_COMPUTER_USE_GROUND_API_KEY = ""  # 空字符串表示使用 assistApi 对应的 API Key

# 模型配置常量（默认值）
# 注：以下5个直接被导入使用的变量保留原名以保持向后兼容性
DEFAULT_ROUTER_MODEL = ROUTER_MODEL = 'openai/gpt-4.1'
DEFAULT_SETTING_PROPOSER_MODEL = SETTING_PROPOSER_MODEL = "qwen-max"
DEFAULT_SETTING_VERIFIER_MODEL = SETTING_VERIFIER_MODEL = "qwen-max"
DEFAULT_SEMANTIC_MODEL = SEMANTIC_MODEL = 'text-embedding-v4'
DEFAULT_RERANKER_MODEL = RERANKER_MODEL = 'qwen-plus'

# 其他模型配置（仅通过 config_manager 动态获取）
DEFAULT_SUMMARY_MODEL = "qwen-plus"
DEFAULT_CORRECTION_MODEL = 'qwen-max'
DEFAULT_EMOTION_MODEL = 'qwen-turbo'
DEFAULT_VISION_MODEL = "qwen3-vl-plus-2025-09-23"

# 用户自定义模型配置（可选，暂未使用）
DEFAULT_OMNI_MODEL = ""  # 全模态模型(语音+文字+图片)
DEFAULT_TTS_MODEL = ""   # TTS模型(Native TTS)


CONFIG_FILES = [
    'characters.json',
    'core_config.json',
    'user_preferences.json',
    'voice_storage.json',
    'workshop_config.json',
]

DEFAULT_MASTER_TEMPLATE = {
    "档案名": "哥哥",
    "性别": "男",
    "昵称": "哥哥",
}

DEFAULT_LANLAN_TEMPLATE = {
    "test": {
        "性别": "女",
        "年龄": 15,
        "昵称": "T酱, 小T",
        "live2d": "mao_pro",
        "voice_id": "",
        "system_prompt": lanlan_prompt,
    }
}

DEFAULT_CHARACTERS_CONFIG = {
    "主人": deepcopy(DEFAULT_MASTER_TEMPLATE),
    "猫娘": deepcopy(DEFAULT_LANLAN_TEMPLATE),
    "当前猫娘": next(iter(DEFAULT_LANLAN_TEMPLATE.keys()), "")
}

DEFAULT_CORE_CONFIG = {
    "coreApiKey": "",
    "coreApi": "qwen",
    "assistApi": "qwen",
    "assistApiKeyQwen": "",
    "assistApiKeyOpenai": "",
    "assistApiKeyGlm": "",
    "assistApiKeyStep": "",
    "assistApiKeySilicon": "",
    "mcpToken": "",
}

DEFAULT_USER_PREFERENCES = []

DEFAULT_VOICE_STORAGE = {}

# 默认API配置（供 utils.api_config_loader 作为回退选项使用）
DEFAULT_CORE_API_PROFILES = {
    'free': {
        'CORE_URL': "ws://47.100.209.206:9805",
        'CORE_MODEL': "free-model",
        'CORE_API_KEY': "free-access",
        'IS_FREE_VERSION': True,
    },
    'qwen': {
        'CORE_URL': "wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
        'CORE_MODEL': "qwen3-omni-flash-realtime",
    },
    'glm': {
        'CORE_URL': "wss://open.bigmodel.cn/api/paas/v4/realtime",
        'CORE_MODEL': "glm-realtime-air",
    },
    'openai': {
        'CORE_URL': "wss://api.openai.com/v1/realtime",
        'CORE_MODEL': "gpt-realtime",
    },
    'step': {
        'CORE_URL': "wss://api.stepfun.com/v1/realtime",
        'CORE_MODEL': "step-audio-2",
    },
}

DEFAULT_ASSIST_API_PROFILES = {
    'free': {
        'OPENROUTER_URL': "http://47.100.209.206:9807/v1",
        'SUMMARY_MODEL': "free-model",
        'CORRECTION_MODEL': "free-model",
        'EMOTION_MODEL': "free-model",
        'VISION_MODEL': "free-vision-model",
        'AUDIO_API_KEY': "free-access",
        'OPENROUTER_API_KEY': "free-access",
        'IS_FREE_VERSION': True,
        # Computer Use 不支持 free 版本
        'COMPUTER_USE_MODEL': "",
        'COMPUTER_USE_MODEL_URL': "",
        'COMPUTER_USE_GROUND_MODEL': "",
        'COMPUTER_USE_GROUND_URL': "",
    },
    'qwen': {
        'OPENROUTER_URL': "https://dashscope.aliyuncs.com/compatible-mode/v1",
        'SUMMARY_MODEL': "qwen3-next-80b-a3b-instruct",
        'CORRECTION_MODEL': "qwen3-235b-a22b-instruct-2507",
        'EMOTION_MODEL': "qwen-flash-2025-07-28",
        'VISION_MODEL': "qwen3-vl-plus-2025-09-23",
        # Qwen VL 模型支持 Computer Use
        'COMPUTER_USE_MODEL': "qwen3-vl-235b-a22b-instruct",
        'COMPUTER_USE_MODEL_URL': "https://dashscope.aliyuncs.com/compatible-mode/v1",
        'COMPUTER_USE_GROUND_MODEL': "qwen3-vl-30b-a3b-instruct",
        'COMPUTER_USE_GROUND_URL': "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    'openai': {
        'OPENROUTER_URL': "https://api.openai.com/v1",
        'SUMMARY_MODEL': "gpt-4.1-mini",
        'CORRECTION_MODEL': "gpt-5-chat-latest",
        'EMOTION_MODEL': "gpt-4.1-nano",
        'VISION_MODEL': "gpt-5-chat-latest",
        # OpenAI 使用 GPT-4o 进行 Computer Use
        'COMPUTER_USE_MODEL': "gpt-5-chat-latest",
        'COMPUTER_USE_MODEL_URL': "https://api.openai.com/v1",
        'COMPUTER_USE_GROUND_MODEL': "gpt-5-chat-latest",
        'COMPUTER_USE_GROUND_URL': "https://api.openai.com/v1",
    },
    'glm': {
        'OPENROUTER_URL': "https://open.bigmodel.cn/api/paas/v4",
        'SUMMARY_MODEL': "glm-4.5-flash",
        'CORRECTION_MODEL': "glm-4.5-air",
        'EMOTION_MODEL': "glm-4.5-flash",
        'VISION_MODEL': "glm-4v-plus-0111",
        # 智谱 GLM-4.5V 支持 Grounding
        'COMPUTER_USE_MODEL': "glm-4.5v",
        'COMPUTER_USE_MODEL_URL': "https://open.bigmodel.cn/api/paas/v4",
        'COMPUTER_USE_GROUND_MODEL': "glm-4.5v",
        'COMPUTER_USE_GROUND_URL': "https://open.bigmodel.cn/api/paas/v4",
    },
    'step': {
        'OPENROUTER_URL': "https://api.stepfun.com/v1",
        'SUMMARY_MODEL': "step-2-mini",
        'CORRECTION_MODEL': "step-2-mini",
        'EMOTION_MODEL': "step-2-mini",
        'VISION_MODEL': "step-1o-turbo-vision",
        # 阶跃星辰视觉模型
        'COMPUTER_USE_MODEL': "step-1o-turbo-vision",
        'COMPUTER_USE_MODEL_URL': "https://api.stepfun.com/v1",
        'COMPUTER_USE_GROUND_MODEL': "step-1o-turbo-vision",
        'COMPUTER_USE_GROUND_URL': "https://api.stepfun.com/v1",
    },
    'silicon': {
        'OPENROUTER_URL': "https://api.siliconflow.cn/v1",
        'SUMMARY_MODEL': "Qwen/Qwen3-Next-80B-A3B-Instruct",
        'CORRECTION_MODEL': "deepseek-ai/DeepSeek-V3.2-Exp",
        'EMOTION_MODEL': "inclusionAI/Ling-mini-2.0",
        'VISION_MODEL': "Qwen/Qwen3-VL-235B-A22B-Instruct",
        # 硅基流动使用 Qwen VL 模型
        'COMPUTER_USE_MODEL': "Qwen/Qwen3-VL-235B-A22B-Instruct",
        'COMPUTER_USE_MODEL_URL': "https://api.siliconflow.cn/v1",
        'COMPUTER_USE_GROUND_MODEL': "Qwen/Qwen3-VL-30B-A3B-Instruct",
        'COMPUTER_USE_GROUND_URL': "https://api.siliconflow.cn/v1",
    },
}

DEFAULT_ASSIST_API_KEY_FIELDS = {
    'qwen': 'ASSIST_API_KEY_QWEN',
    'openai': 'ASSIST_API_KEY_OPENAI',
    'glm': 'ASSIST_API_KEY_GLM',
    'step': 'ASSIST_API_KEY_STEP',
    'silicon': 'ASSIST_API_KEY_SILICON',
}

DEFAULT_CONFIG_DATA = {
    'characters.json': DEFAULT_CHARACTERS_CONFIG,
    'core_config.json': DEFAULT_CORE_CONFIG,
    'user_preferences.json': DEFAULT_USER_PREFERENCES,
    'voice_storage.json': DEFAULT_VOICE_STORAGE,
}


TIME_ORIGINAL_TABLE_NAME = "time_indexed_original"
TIME_COMPRESSED_TABLE_NAME = "time_indexed_compressed"

MODELS_WITH_EXTRA_BODY = ["qwen-flash-2025-07-28", "qwen3-vl-plus-2025-09-23"]


def get_api_providers_config():
    """获取API提供商配置"""
    import json
    import os
    from pathlib import Path
    
    # 尝试从api_providers.json加载配置
    config_file = Path(__file__).parent / "api_providers.json"
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"API提供商配置文件不存在: {config_file}，使用默认配置。")
        # 返回默认配置
        return {
            "core_api_providers": {
                "free": {
                    "key": "free",
                    "name": "免费版（猫娘专属福利）",
                    "description": "完全免费，无需API Key，但不支持自定义语音、Agent模式和视频对话",
                    "core_url": "ws://47.100.209.206:9805",
                    "core_model": "free-model",
                    "core_api_key": "free-access",
                    "is_free_version": True
                },
                "qwen": {
                    "key": "qwen",
                    "name": "Qwen-Omni（阿里）",
                    "description": "有免费额度，功能全面",
                    "core_url": "wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
                    "core_model": "qwen3-omni-flash-realtime"
                },
                "openai": {
                    "key": "openai",
                    "name": "GPT-Realtime（OpenAI）",
                    "description": "智能水平最高，但需要翻墙且价格昂贵",
                    "core_url": "wss://api.openai.com/v1/realtime",
                    "core_model": "gpt-realtime"
                },
                "glm": {
                    "key": "glm",
                    "name": "GLM-realtime（智谱）",
                    "description": "有免费额度，但需充值1元，内置联网搜索功能",
                    "core_url": "wss://open.bigmodel.cn/api/paas/v4/realtime",
                    "core_model": "glm-realtime-air"
                },
                "step": {
                    "key": "step",
                    "name": "Step-2（阶跃星辰）",
                    "description": "完全免费，但不支持视频",
                    "core_url": "wss://api.stepfun.com/v1/realtime",
                    "core_model": "step-audio-2"
                }
            },
            "assist_api_providers": {
                "free": {
                    "key": "free",
                    "name": "免费版（猫娘专属福利）",
                    "description": "完全免费，无需API Key，但不支持自定义语音",
                    "openrouter_url": "http://47.100.209.206:9807/v1",
                    "summary_model": "free-model",
                    "correction_model": "free-model",
                    "emotion_model": "free-model",
                    "vision_model": "free-vision-model",
                    "audio_api_key": "free-access",
                    "openrouter_api_key": "free-access",
                    "is_free_version": True
                },
                "qwen": {
                    "key": "qwen",
                    "name": "阿里（推荐）",
                    "description": "推荐选择，支持自定义语音",
                    "openrouter_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "summary_model": "qwen3-next-80b-a3b-instruct",
                    "correction_model": "qwen3-235b-a22b-instruct-2507",
                    "emotion_model": "qwen-flash-2025-07-28",
                    "vision_model": "qwen3-vl-plus-2025-09-23"
                },
                "openai": {
                    "key": "openai",
                    "name": "OpenAI",
                    "description": "记忆管理能力强",
                    "openrouter_url": "https://api.openai.com/v1",
                    "summary_model": "gpt-4.1-mini",
                    "correction_model": "gpt-5-chat-latest",
                    "emotion_model": "gpt-4.1-nano",
                    "vision_model": "gpt-5-chat-latest"
                },
                "glm": {
                    "key": "glm",
                    "name": "智谱",
                    "description": "支持Agent模式",
                    "openrouter_url": "https://open.bigmodel.cn/api/paas/v4",
                    "summary_model": "glm-4.5-flash",
                    "correction_model": "glm-4.5-air",
                    "emotion_model": "glm-4.5-flash",
                    "vision_model": "glm-4v-plus-0111"
                },
                "step": {
                    "key": "step",
                    "name": "阶跃星辰",
                    "description": "价格相对便宜",
                    "openrouter_url": "https://api.stepfun.com/v1",
                    "summary_model": "step-2-mini",
                    "correction_model": "step-2-mini",
                    "emotion_model": "step-2-mini",
                    "vision_model": "step-1o-turbo-vision"
                },
                "silicon": {
                    "key": "silicon",
                    "name": "硅基流动",
                    "description": "性价比高，功能少，只作为辅助API使用",
                    "openrouter_url": "https://api.siliconflow.cn/v1",
                    "summary_model": "Qwen/Qwen3-Next-80B-A3B-Instruct",
                    "correction_model": "deepseek-ai/DeepSeek-V3.2-Exp",
                    "emotion_model": "inclusionAI/Ling-mini-2.0",
                    "vision_model": "Qwen/Qwen3-VL-235B-A22B-Instruct"
                }
            },
            "default_models": {
                "router_model": "openai/gpt-4.1",
                "summary_model": "qwen-plus",
                "setting_proposer_model": "qwen-max",
                "setting_verifier_model": "qwen-max",
                "semantic_model": "text-embedding-v4",
                "reranker_model": "qwen-plus",
                "correction_model": "qwen-max",
                "emotion_model": "qwen-turbo",
                "vision_model": "qwen3-vl-plus-2025-09-23",
                "core_model": "qwen3-omni-flash-realtime",
                "core_url": "wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
                "openrouter_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
            },
            "assist_api_key_fields": {
                "qwen": "ASSIST_API_KEY_QWEN",
                "openai": "ASSIST_API_KEY_OPENAI",
                "glm": "ASSIST_API_KEY_GLM",
                "step": "ASSIST_API_KEY_STEP",
                "silicon": "ASSIST_API_KEY_SILICON"
            }
        }


__all__ = [
    'APP_NAME',
    'CONFIG_FILES',
    'DEFAULT_MASTER_TEMPLATE',
    'DEFAULT_LANLAN_TEMPLATE',
    'DEFAULT_CHARACTERS_CONFIG',
    'DEFAULT_CORE_CONFIG',
    'DEFAULT_USER_PREFERENCES',
    'DEFAULT_VOICE_STORAGE',
    'DEFAULT_CONFIG_DATA',
    'DEFAULT_CORE_API_PROFILES',
    'DEFAULT_ASSIST_API_PROFILES',
    'DEFAULT_ASSIST_API_KEY_FIELDS',
    'TIME_ORIGINAL_TABLE_NAME',
    'TIME_COMPRESSED_TABLE_NAME',
    'MODELS_WITH_EXTRA_BODY',
    'get_api_providers_config',
    'MAIN_SERVER_PORT',
    'MEMORY_SERVER_PORT',
    'MONITOR_SERVER_PORT',
    'COMMENTER_SERVER_PORT',
    'TOOL_SERVER_PORT',
    'MCP_ROUTER_URL',
    # API 和模型配置的默认值
    'DEFAULT_CORE_API_KEY',
    'DEFAULT_AUDIO_API_KEY',
    'DEFAULT_OPENROUTER_API_KEY',
    'DEFAULT_MCP_ROUTER_API_KEY',
    'DEFAULT_CORE_URL',
    'DEFAULT_CORE_MODEL',
    'DEFAULT_OPENROUTER_URL',
    # 直接被导入使用的5个模型配置（导出 DEFAULT_ 和无前缀版本）
    'DEFAULT_ROUTER_MODEL',
    'ROUTER_MODEL',
    'DEFAULT_SETTING_PROPOSER_MODEL',
    'SETTING_PROPOSER_MODEL',
    'DEFAULT_SETTING_VERIFIER_MODEL',
    'SETTING_VERIFIER_MODEL',
    'DEFAULT_SEMANTIC_MODEL',
    'SEMANTIC_MODEL',
    'DEFAULT_RERANKER_MODEL',
    'RERANKER_MODEL',
    # 其他模型配置（仅导出 DEFAULT_ 版本）
    'DEFAULT_SUMMARY_MODEL',
    'DEFAULT_CORRECTION_MODEL',
    'DEFAULT_EMOTION_MODEL',
    'DEFAULT_VISION_MODEL',
    'DEFAULT_OMNI_MODEL',
    'DEFAULT_TTS_MODEL',
    # 用户自定义模型配置的 Provider/URL/API_KEY
    'DEFAULT_SUMMARY_MODEL_PROVIDER',
    'DEFAULT_SUMMARY_MODEL_URL',
    'DEFAULT_SUMMARY_MODEL_API_KEY',
    'DEFAULT_CORRECTION_MODEL_PROVIDER',
    'DEFAULT_CORRECTION_MODEL_URL',
    'DEFAULT_CORRECTION_MODEL_API_KEY',
    'DEFAULT_EMOTION_MODEL_PROVIDER',
    'DEFAULT_EMOTION_MODEL_URL',
    'DEFAULT_EMOTION_MODEL_API_KEY',
    'DEFAULT_VISION_MODEL_PROVIDER',
    'DEFAULT_VISION_MODEL_URL',
    'DEFAULT_VISION_MODEL_API_KEY',
    'DEFAULT_OMNI_MODEL_PROVIDER',
    'DEFAULT_OMNI_MODEL_URL',
    'DEFAULT_OMNI_MODEL_API_KEY',
    'DEFAULT_TTS_MODEL_PROVIDER',
    'DEFAULT_TTS_MODEL_URL',
    'DEFAULT_TTS_MODEL_API_KEY',
    'DEFAULT_COMPUTER_USE_MODEL',
    'DEFAULT_COMPUTER_USE_MODEL_URL',
    'DEFAULT_COMPUTER_USE_MODEL_API_KEY',
    'DEFAULT_COMPUTER_USE_GROUND_MODEL',
    'DEFAULT_COMPUTER_USE_GROUND_URL',
    'DEFAULT_COMPUTER_USE_GROUND_API_KEY',
]

