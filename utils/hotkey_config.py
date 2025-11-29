# -*- coding: utf-8 -*-
"""
快捷键配置管理器
允许用户自定义快捷键设置
"""
import json
import os
from pathlib import Path
from utils.config_manager import get_config_manager

class HotkeyConfig:
    def __init__(self):
        self.config_manager = get_config_manager()
        self.config_file = self.config_manager.get_config_path('hotkey_config.json')
        self.default_config = {
            'copilot_key': 'ctrl+alt+f10',  # 默认使用一个不太可能冲突的组合
            'enable_copilot_interception': True,
            'other_shortcuts': {
                'open_app': ['ctrl+alt+n']  # 其他快捷键选项
            }
        }
        self.config = self.load_config()

    def load_config(self):
        """加载快捷键配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 确保配置包含所有必需的键
                for key, value in self.default_config.items():
                    if key not in config:
                        config[key] = value
                print(f"✅ 加载快捷键配置成功: {config}")
                return config
        except FileNotFoundError:
            # 配置文件不存在，创建默认配置
            print(f"⚠️ 快捷键配置文件不存在，将创建默认配置: {self.config_file}")
            self.save_config(self.default_config)
            return self.default_config
        except Exception as e:
            print(f"❌ 加载快捷键配置失败，使用默认配置: {e}")
            return self.default_config

    def save_config(self, config=None):
        """保存快捷键配置"""
        if config is None:
            config = self.config
        
        # 确保配置目录存在
        self.config_manager.ensure_config_directory()
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.config = config
            return True
        except Exception as e:
            print(f"保存快捷键配置失败: {e}")
            return False

    def get_copilot_key(self):
        """获取 Copilot 键配置"""
        return self.config.get('copilot_key', self.default_config['copilot_key'])

    def get_all_shortcuts(self):
        """获取所有快捷键配置"""
        shortcuts = {self.config.get('copilot_key', self.default_config['copilot_key']): 'open_app'}
        # 添加其他快捷键
        for action, keys in self.config.get('other_shortcuts', {}).items():
            for key in keys:
                shortcuts[key] = action
        return shortcuts

    def update_copilot_key(self, new_key):
        """更新 Copilot 键配置"""
        self.config['copilot_key'] = new_key
        return self.save_config()

# 创建全局实例
_hotkey_config = None

def get_hotkey_config():
    """获取快捷键配置实例"""
    global _hotkey_config
    if _hotkey_config is None:
        _hotkey_config = HotkeyConfig()
    return _hotkey_config