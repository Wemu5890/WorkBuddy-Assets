import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMessageBox, QWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QIcon, QColor, QFont, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize
from importer import import_pet_from_folder

# ================================
# 全局极暗风格样式表
# ================================
DARK_STYLESHEET = """
QWidget#MainContainer {
    background-color: #1a1a1c;
    border: 1px solid #333336;
    border-radius: 12px;
}
QLabel {
    color: #e0e0e0;
}
QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}
QListWidget::item {
    background-color: #232326;
    border-radius: 10px;
    margin-bottom: 10px;
    padding: 10px;
}
QListWidget::item:hover {
    background-color: #2a2a2e;
}
QListWidget::item:selected {
    background-color: #2a2a2e;
    border: 1px solid #3a68a3;
}
QPushButton#CloseBtn {
    background-color: transparent;
    color: #888;
    border: none;
    font-weight: bold;
    font-size: 16px;
}
QPushButton#CloseBtn:hover {
    color: #ff5555;
}
"""

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        
        title_label = QLabel("喔的Buddy")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4db8ff;")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseBtn")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.parent.close)
        layout.addWidget(close_btn)

        self.start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.start_pos is not None:
            delta = event.globalPosition().toPoint() - self.start_pos
            self.parent.move(self.parent.pos() + delta)
            self.start_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.start_pos = None

class PetCardWidget(QWidget):
    def __init__(self, assets_dir, pet_name, is_current=False):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        
        # 头像
        avatar = QLabel()
        avatar.setFixedSize(60, 60)
        avatar.setStyleSheet("background-color: transparent; border-radius: 10px;")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 随机抽取一张动作的图作为头像
        pet_dir = os.path.join(assets_dir, pet_name)
        if os.path.exists(pet_dir):
            actions = [d for d in os.listdir(pet_dir) if os.path.isdir(os.path.join(pet_dir, d))]
            if actions:
                import random
                import json
                random_action = random.choice(actions)
                action_dir = os.path.join(pet_dir, random_action)
                img_path = os.path.join(action_dir, "sprite.png")
                cfg_path = os.path.join(action_dir, "config.json")
                if os.path.exists(img_path) and os.path.exists(cfg_path):
                    try:
                        with open(cfg_path, 'r', encoding='utf-8') as f:
                            cfg = json.load(f)
                        fw, fh = cfg.get("frameWidth", 192), cfg.get("frameHeight", 208)
                        from PyQt6.QtGui import QPixmap
                        from PyQt6.QtCore import QRect
                        sheet = QPixmap(img_path)
                        frame = sheet.copy(QRect(0, 0, fw, fh))
                        scaled_frame = frame.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        avatar.setPixmap(scaled_frame)
                    except Exception as e:
                        avatar.setText("🐾")
                else:
                    avatar.setText("🐾")
            else:
                avatar.setText("🐾")
        else:
            avatar.setText("🐾")

        layout.addWidget(avatar)
        
        # 文本信息
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        name_label = QLabel(pet_name)
        name_label.setStyleSheet("font-size: 18px; font-weight: bold; padding-top: 5px;")
        text_layout.addWidget(name_label)
        
        status_text = "运行中 (Active)" if is_current else "已休眠 (Inactive)"
        status_color = "#4db8ff" if is_current else "#888"
        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"font-size: 13px; color: {status_color}; padding-bottom: 5px;")
        text_layout.addWidget(status_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()

class SettingsDialog(QDialog):
    character_changed = pyqtSignal(str)

    def __init__(self, assets_dir, current_character, parent=None):
        super().__init__(parent)
        self.assets_dir = assets_dir
        self.current_character = current_character
        
        # 无边框 + 保持最上层
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(700, 500)
        
        self.setAcceptDrops(True)
        
        self.init_ui()
        self.refresh_pet_list()

    def init_ui(self):
        # 核心主容器 (实现圆角和阴影)
        self.main_container = QWidget(self)
        self.main_container.setObjectName("MainContainer")
        self.main_container.setStyleSheet(DARK_STYLESHEET)
        
        # 添加外层发光阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.main_container.setGraphicsEffect(shadow)

        # 全局布局
        global_layout = QVBoxLayout(self)
        global_layout.setContentsMargins(10, 10, 10, 10) # 给阴影留出空间
        global_layout.addWidget(self.main_container)

        # 容器内部布局
        inner_layout = QVBoxLayout(self.main_container)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        
        # 自定义标题栏
        self.title_bar = CustomTitleBar(self)
        inner_layout.addWidget(self.title_bar)
        
        # 列表区域
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        inner_layout.addWidget(self.list_widget)
        
        # 底部提示
        self.drop_hint = QLabel("💡 将装着新宠物的文件夹直接拖入此窗口即可安装")
        self.drop_hint.setStyleSheet("color: #666; font-size: 13px; padding: 10px;")
        self.drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner_layout.addWidget(self.drop_hint)

    def refresh_pet_list(self):
        self.list_widget.clear()
        if not os.path.exists(self.assets_dir):
            return
            
        for folder in os.listdir(self.assets_dir):
            if os.path.isdir(os.path.join(self.assets_dir, folder)):
                # 创建列表项
                item = QListWidgetItem()
                item.setSizeHint(QSize(0, 95)) # 增加卡片高度，防止文字被截断
                self.list_widget.addItem(item)
                
                # 创建自定义 Widget
                is_current = (folder == self.current_character)
                card = PetCardWidget(self.assets_dir, folder, is_current)
                self.list_widget.setItemWidget(item, card)
                
                # 记录名字
                item.setData(Qt.ItemDataRole.UserRole, folder)
                if is_current:
                    item.setSelected(True)

    def on_item_clicked(self, item):
        pet_name = item.data(Qt.ItemDataRole.UserRole)
        if pet_name != self.current_character:
            self.current_character = pet_name
            self.character_changed.emit(pet_name)
            self.refresh_pet_list() # 刷新状态文字

    # ================= 拖拽安装逻辑 =================
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            # 边框发光提示
            self.main_container.setStyleSheet(DARK_STYLESHEET.replace(
                "border: 1px solid #333336;", 
                "border: 2px solid #4db8ff;"
            ))
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.main_container.setStyleSheet(DARK_STYLESHEET)

    def dropEvent(self, event):
        self.main_container.setStyleSheet(DARK_STYLESHEET)
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            folder_path = urls[0].toLocalFile()
            if os.path.isdir(folder_path):
                pet_name = os.path.basename(folder_path)
                count = import_pet_from_folder(folder_path, pet_name, self.assets_dir)
                if count > 0:
                    self.refresh_pet_list()
                    # 自动选中并切换
                    self.current_character = pet_name
                    self.character_changed.emit(pet_name)
                    self.refresh_pet_list()
                else:
                    QMessageBox.warning(self, "导入失败", "未在文件夹中找到动作图片（例如: 待机_6.png）。")
            else:
                QMessageBox.warning(self, "错误", "请拖拽一个文件夹！")
