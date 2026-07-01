import sys
import os
import psutil
import random
import time
import json
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QRect
from PyQt6.QtGui import QPixmap, QCursor, QAction, QColor
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QMenu

# ==========================================
# 配置区
if sys.platform == "darwin":
    TARGET_PROCESS_NAME = "WorkBuddy"
else:
    TARGET_PROCESS_NAME = "WorkBuddy.exe"
ASSETS_BASE_DIR = os.path.join(os.path.dirname(__file__), "assets")

DEFAULT_DISPLAY_SIZE = 110
FPS_CAP = 30

class DeskPet(QWidget):
    def __init__(self):
        super().__init__()
        self.current_size = DEFAULT_DISPLAY_SIZE
        self.current_character = "default"
        
        self.animations = {}
        
        self.idle_frame_idx = 0
        self.idle_time_accumulator = 0.0
        
        self.active_action = None
        self.action_frame_idx = 0         
        self.action_time_accumulator = 0.0
        
        self.is_dragging = False
        self.drag_direction = "hover_idle"
        self.drag_position = None
        
        # --- 新增：互动与 AFK 状态系统 ---
        self.last_interaction_time = time.time()
        self.first_click_time = 0
        self.click_count = 0
        self.press_time = 0
        self.press_start_pos = None
        self.is_holding = False
        self.afk_stage = 0  # 0: 正常, 1: 5分钟(waving), 2: 8分钟(failed)
        
        self.last_update_time = time.time()
        
        self.init_ui()
        self.load_assets()
        
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self.render_frame)
        
        self.ambient_timer = QTimer(self)
        self.ambient_timer.timeout.connect(self.roll_ambient_behavior)
        
        self.afk_timer = QTimer(self)
        self.afk_timer.timeout.connect(self.check_afk_status)
        
        # 延迟 3 秒检查网络 OTA 更新
        QTimer.singleShot(3000, self.check_ota_update)

    def check_ota_update(self):
        from updater import UpdateCheckerThread
        self.version_file = os.path.join(ASSETS_BASE_DIR, "version.json")
        self.checker = UpdateCheckerThread(self.version_file)
        self.checker.update_found.connect(self.show_update_dialog)
        self.checker.start()
        
    def show_update_dialog(self, update_data):
        from updater import UpdateDialog
        if hasattr(self, 'update_dialog') and self.update_dialog.isVisible():
            return
        self.update_dialog = UpdateDialog(update_data, ASSETS_BASE_DIR, self.version_file)
        if self.update_dialog.exec():
            print("OTA 更新成功，正在重载资产...")
            self.switch_character(self.current_character)

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.base_x = screen_geometry.width() - self.current_size - 50
        self.base_y = screen_geometry.height() - self.current_size - 50
        self.setGeometry(self.base_x, self.base_y, self.current_size, self.current_size)
        
        self.label = QLabel(self)
        self.label.setGeometry(0, 0, self.current_size, self.current_size)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def switch_character(self, character_name):
        self.current_character = character_name
        self.animations.clear()
        self.active_action = None
        self.idle_frame_idx = 0
        self.load_assets()

    def safe_get_action(self, action_names, default="idle"):
        """安全回退：按优先级尝试寻找动画"""
        if isinstance(action_names, str):
            action_names = [action_names]
        for act in action_names:
            if act in self.animations:
                return act
        return default

    def load_assets(self):
        char_dir = os.path.join(ASSETS_BASE_DIR, self.current_character)
        
        if not os.path.exists(char_dir):
            if os.path.exists(ASSETS_BASE_DIR):
                for folder in os.listdir(ASSETS_BASE_DIR):
                    if os.path.isdir(os.path.join(ASSETS_BASE_DIR, folder)):
                        self.current_character = folder
                        char_dir = os.path.join(ASSETS_BASE_DIR, self.current_character)
                        print(f"角色不存在，自动降级切换至: {self.current_character}")
                        break
                        
        if not os.path.exists(char_dir):
            print(f"Error: 找不到角色目录 {char_dir}，且没有其他备用角色！")
            return
            
        for action_name in os.listdir(char_dir):
            action_dir = os.path.join(char_dir, action_name)
            if not os.path.isdir(action_dir): continue
                
            json_path = os.path.join(action_dir, "config.json")
            img_path = os.path.join(action_dir, "sprite.png")
            
            if os.path.exists(json_path) and os.path.exists(img_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                sprite_sheet = QPixmap(img_path)
                frame_w = config.get("frameWidth", 192)
                frame_h = config.get("frameHeight", 208)
                
                calc_frames = sprite_sheet.width() // frame_w
                total_frames = config.get("frames", calc_frames)
                
                frames = []
                for i in range(total_frames):
                    rect = QRect(i * frame_w, 0, frame_w, frame_h)
                    frames.append(sprite_sheet.copy(rect))
                    
                self.animations[action_name] = {
                    "frames": frames,
                    "config": config,
                    "total_frames": total_frames
                }

    def start_engine(self):
        if not self.animations:
            return
        self.last_update_time = time.time()
        self.render_timer.start(1000 // FPS_CAP)
        self.afk_timer.start(1000)
        self.schedule_next_ambient()

    def schedule_next_ambient(self):
        next_ms = random.randint(6000, 18000)
        self.ambient_timer.start(next_ms)

    def check_afk_status(self):
        if self.is_dragging or self.is_holding:
            return
            
        elapsed = time.time() - self.last_interaction_time
        if elapsed > 8 * 60:
            if self.afk_stage != 2:
                self.afk_stage = 2
                self.trigger_action(self.safe_get_action(["failed", "look_down"]))
        elif elapsed > 5 * 60:
            if self.afk_stage != 1:
                self.afk_stage = 1
                self.trigger_action(self.safe_get_action(["waving", "wave", "alert"]))

    def roll_ambient_behavior(self):
        # 如果正在挂机、拖拽、或正在播放动作，则跳过随机
        if self.is_dragging or self.active_action is not None or self.afk_stage > 0:
            self.schedule_next_ambient()
            return

        pool = [
            ("blink", 40),
            ("eyes_change", 20),
            ("alert", 15),
            ("waving", 15),
            ("wave", 15),
            ("look_down", 10)
        ]
        
        pool = [item for item in pool if item[0] in self.animations]
        if not pool:
            self.schedule_next_ambient()
            return
            
        total = sum(weight for name, weight in pool)
        r = random.uniform(0, total)
        upto = 0
        chosen_anim = pool[0][0]
        
        for name, weight in pool:
            if upto + weight >= r:
                chosen_anim = name
                break
            upto += weight
            
        self.trigger_action(chosen_anim)
        self.schedule_next_ambient()

    def trigger_action(self, anim_name):
        if anim_name in self.animations:
            self.active_action = anim_name
            self.action_frame_idx = 0
            self.action_time_accumulator = 0.0

    def render_frame(self):
        now = time.time()
        dt = now - self.last_update_time
        self.last_update_time = now
        
        # Layer 1: 底层呼吸
        if "idle" in self.animations:
            idle_anim = self.animations["idle"]
            idle_fps = idle_anim["config"].get("fps", 6)
            self.idle_time_accumulator += dt
            if self.idle_time_accumulator >= (1.0 / idle_fps):
                self.idle_frame_idx = (self.idle_frame_idx + 1) % idle_anim["total_frames"]
                self.idle_time_accumulator -= (1.0 / idle_fps)
                
        current_anim_name = "idle"
        current_frame_idx = self.idle_frame_idx

        # Layer 2: 拖拽覆盖 (含长按原地跑)
        if self.is_dragging or self.is_holding:
            if self.drag_direction in self.animations:
                current_anim_name = self.drag_direction
                drag_anim = self.animations[self.drag_direction]
                current_frame_idx = self.idle_frame_idx % drag_anim["total_frames"]

        # Layer 3: 插入层 (动作/AFK)
        elif self.active_action is not None:
            current_anim_name = self.active_action
            action_anim = self.animations[self.active_action]
            action_fps = action_anim["config"].get("fps", 8)
            
            current_frame_idx = self.action_frame_idx
            
            self.action_time_accumulator += dt
            if self.action_time_accumulator >= (1.0 / action_fps):
                self.action_frame_idx += 1
                self.action_time_accumulator -= (1.0 / action_fps)
                
                # 动作播放完毕
                if self.action_frame_idx >= action_anim["total_frames"]:
                    # 如果在 AFK 阶段，强制无限循环
                    if self.afk_stage > 0:
                        self.action_frame_idx = 0
                    else:
                        self.active_action = None
                        current_anim_name = "idle"
                        current_frame_idx = self.idle_frame_idx
                else:
                    current_frame_idx = self.action_frame_idx

        # 执行渲染
        if current_anim_name in self.animations:
            anim_data = self.animations[current_anim_name]
            safe_idx = current_frame_idx % anim_data["total_frames"]
            frame_pixmap = anim_data["frames"][safe_idx]
            scaled_pixmap = frame_pixmap.scaled(
                self.current_size, self.current_size, 
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.label.setPixmap(scaled_pixmap)

    # ---------------- 交互事件 ----------------
    def interact(self):
        self.last_interaction_time = time.time()
        self.afk_stage = 0

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.interact()
            self.is_holding = True
            self.is_dragging = False
            self.press_time = time.time()
            self.press_start_pos = event.globalPosition().toPoint()
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            
            # 长按不移时播放 running
            self.drag_direction = self.safe_get_action(["running", "run", "hover_idle", "idle"])
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.interact()
            new_pos = event.globalPosition().toPoint() - self.drag_position
            
            # 判断是否从 holding 变成了 dragging
            if self.is_holding:
                dist_x = abs(event.globalPosition().toPoint().x() - self.press_start_pos.x())
                dist_y = abs(event.globalPosition().toPoint().y() - self.press_start_pos.y())
                if dist_x > 5 or dist_y > 5:
                    self.is_holding = False
                    self.is_dragging = True
            
            if self.is_dragging:
                delta_x = new_pos.x() - self.pos().x()
                delta_y = new_pos.y() - self.pos().y()
                
                if abs(delta_y) > abs(delta_x) + 2:
                    # 上下拖拽 -> 跳跃
                    self.drag_direction = self.safe_get_action(["jumping", "jump", "hover_idle"])
                elif delta_x > 2:
                    # 向右移动 -> 播放向右跑
                    self.drag_direction = self.safe_get_action(["run_right", "fly_right", "hover_idle"])
                elif delta_x < -2:
                    # 向左移动 -> 播放向左跑
                    self.drag_direction = self.safe_get_action(["run_left", "fly_left", "hover_idle"])
                
                self.move(new_pos)
            event.accept()

    def handle_click_logic(self):
        current_time = time.time()
        if current_time - self.first_click_time > 60:
            self.click_count = 1
            self.first_click_time = current_time
        else:
            self.click_count += 1
            
        if self.click_count == 1:
            self.trigger_action(self.safe_get_action(["review", "alert", "wave"]))
        elif self.click_count <= 8:
            exclude = {"idle", "hover_idle", "review", "failed"}
            pool = [a for a in self.animations.keys() if a not in exclude]
            if not pool: pool = list(self.animations.keys())
            self.trigger_action(random.choice(pool))
        else:
            self.trigger_action(self.safe_get_action(["failed", "look_down"]))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.interact()
            
            # 判断是否是短点击
            if self.is_holding and (time.time() - self.press_time < 0.3):
                self.handle_click_logic()
                
            self.is_holding = False
            self.is_dragging = False
            self.drag_position = None
            event.accept()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        # Mac 触控板滚动非常平滑且数值小但频率极高，因此要做平滑和阈值处理
        step = 20 if sys.platform != "darwin" else 5
        
        if delta > 0: self.current_size += step
        elif delta < 0: self.current_size -= step
        
        self.current_size = max(50, min(self.current_size, 800))
        self.setFixedSize(self.current_size, self.current_size)
        self.label.setGeometry(0, 0, self.current_size, self.current_size)
        event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        settings_action = QAction("设置 (Buddy)", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)
        menu.addSeparator()
        exit_action = QAction("退出Buddy", self)
        exit_action.triggered.connect(self.quit_app)
        menu.addAction(exit_action)
        menu.exec(QCursor.pos())

    def quit_app(self):
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == TARGET_PROCESS_NAME:
                    proc.kill()
        except Exception as e:
            print(f"Error closing {TARGET_PROCESS_NAME}: {e}")
        QApplication.quit()

    def open_settings(self):
        from settings_ui import SettingsDialog
        if hasattr(self, 'settings_dialog') and self.settings_dialog.isVisible():
            self.settings_dialog.activateWindow()
            return
        self.settings_dialog = SettingsDialog(ASSETS_BASE_DIR, self.current_character, self)
        self.settings_dialog.character_changed.connect(self.switch_character)
        self.settings_dialog.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pet = DeskPet()
    pet.show()
    pet.start_engine()
    sys.exit(app.exec())
