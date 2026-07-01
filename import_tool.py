import os
import shutil
import json
import re

# ====================================================
# 桌宠素材全自动导入工具
# 使用方法：将重命名好的图片（如“待机_6.png”）放在本目录下
# 运行此脚本，自动完成引擎所需的所有配置！
# ====================================================

# 配置路径
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SRC_DIR, 'assets', 'default')

# 动作中文到英文的映射字典及默认配置
ACTION_MAPPING = {
    '待机': {'folder': 'idle', 'fps': 6, 'loop': True},
    '悬浮待机': {'folder': 'hover_idle', 'fps': 8, 'loop': True},
    '向左飞行': {'folder': 'fly_left', 'fps': 10, 'loop': True},
    '向右飞行': {'folder': 'fly_right', 'fps': 10, 'loop': True},
    '挥手': {'folder': 'wave', 'fps': 8, 'loop': False},
    '眨眼': {'folder': 'blink', 'fps': 10, 'loop': False},
    '站立眨眼': {'folder': 'blink', 'fps': 10, 'loop': False},
    '低头': {'folder': 'look_down', 'fps': 8, 'loop': False},
    '警觉': {'folder': 'alert', 'fps': 8, 'loop': False},
    '警觉表情': {'folder': 'alert', 'fps': 8, 'loop': False},
    '眼神变化': {'folder': 'eyes_change', 'fps': 8, 'loop': False}
}

def import_assets():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    count = 0
    
    # 扫描当前目录下的所有 png 和 webp 文件
    for filename in os.listdir(SRC_DIR):
        if not (filename.endswith('.png') or filename.endswith('.webp')):
            continue
            
        folder_name = ""
        frames_count = 0
        fps = 8
        is_loop = False
        
        # 1. 尝试匹配全新规范: "Failed_失败的_8帧.png"
        new_match = re.match(r'^([A-Za-z0-9\s]+)_([^_]+)_(\d+)帧\.(png|webp)$', filename)
        
        # 2. 尝试匹配旧版规范: "待机_6.png"
        old_match = re.match(r'^([^\d_]+)_?(\d+)\.(png|webp)$', filename)
        
        if new_match:
            en_name = new_match.group(1).strip()
            zh_name = new_match.group(2).strip()
            frames_count = int(new_match.group(3))
            
            folder_name = en_name.lower().replace(' ', '_')
            
            # 智能推断循环状态与帧率
            loop_keywords = ['idle', 'run', 'fly', 'hover', 'wait', 'walk']
            is_loop = any(k in folder_name for k in loop_keywords)
            
            if 'run' in folder_name or 'fly' in folder_name:
                fps = 10
            elif 'idle' in folder_name or 'wait' in folder_name:
                fps = 6
            else:
                fps = 8
                
        elif old_match:
            zh_name = old_match.group(1)
            frames_count = int(old_match.group(2))
            
            if zh_name in ACTION_MAPPING:
                info = ACTION_MAPPING[zh_name]
                folder_name = info['folder']
                fps = info['fps']
                is_loop = info['loop']
            else:
                print(f"Warning: Unknown old action {filename}")
                continue
        else:
            continue
            
        target_dir = os.path.join(ASSETS_DIR, folder_name)
        os.makedirs(target_dir, exist_ok=True)
        
        # 移动并重命名为标准的 sprite.png
        src_path = os.path.join(SRC_DIR, filename)
        dest_path = os.path.join(target_dir, 'sprite.png')
        shutil.copy2(src_path, dest_path)
        
        # 生成带绝对帧数的 config.json
        config = {
            'frameWidth': 192,
            'frameHeight': 208,
            'fps': fps,
            'loop': is_loop,
            'frames': frames_count  # <-- 核心：将文件名上的帧数绝对锁定进配置！
        }
        
        with open(os.path.join(target_dir, 'config.json'), 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
            
        print(f"✅ 成功导入: {filename} -> {folder_name}/ (提取帧数: {frames_count})")
        count += 1
        
    print(f"\n🎉 导入完成！共处理了 {count} 个动作资源。请直接启动 main.py 即可生效。")

if __name__ == '__main__':
    import_assets()
