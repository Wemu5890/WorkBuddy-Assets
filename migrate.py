import os
import shutil
import json

src_dir = r'D:\A\WWWW\1'
base_asset_dir = r'D:\A\WWWW\assets\default'
os.makedirs(base_asset_dir, exist_ok=True)

mapping = {
    '待机.png': {'folder': 'idle', 'fps': 10, 'loop': True},
    '挥手.png': {'folder': 'wave', 'fps': 12, 'loop': False},
    '站立眨眼.png': {'folder': 'blink', 'fps': 15, 'loop': False},
    '低头.png': {'folder': 'look_down', 'fps': 10, 'loop': False},
    '警觉表情.png': {'folder': 'alert', 'fps': 12, 'loop': False},
    '眼神变化.png': {'folder': 'eyes_change', 'fps': 10, 'loop': False},
    '悬浮待机.png': {'folder': 'hover_idle', 'fps': 10, 'loop': True},
    '向左飞行.png': {'folder': 'fly_left', 'fps': 12, 'loop': True},
    '向右飞行.png': {'folder': 'fly_right', 'fps': 12, 'loop': True}
}

for zh_name, info in mapping.items():
    src_path = os.path.join(src_dir, zh_name)
    if os.path.exists(src_path):
        anim_dir = os.path.join(base_asset_dir, info['folder'])
        os.makedirs(anim_dir, exist_ok=True)
        
        # copy and rename
        dest_img = os.path.join(anim_dir, 'sprite.png')
        shutil.copy2(src_path, dest_img)
        
        # create config.json
        config = {
            'frameWidth': 192,
            'frameHeight': 208,
            'fps': info['fps'],
            'loop': info['loop']
        }
        with open(os.path.join(anim_dir, 'config.json'), 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
            
        print(f"Migrated {zh_name} to {info['folder']}/sprite.png")
    else:
        print(f"Warning: {zh_name} not found in {src_dir}")
