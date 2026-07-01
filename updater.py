import os
import json
import requests
import zipfile
import shutil
import tempfile
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QProgressBar

# ==========================================
# 自动更新配置区
# ==========================================
GITHUB_USERNAME = "Wemu5890"          # 您的 GitHub 用户名
GITHUB_REPO = "WorkBuddy-Assets"      # 您即将创建的仓库名

# 国内镜像加速节点，防止 Github Raw 和 Zip 下载超时
GH_PROXY = "https://ghproxy.net/"
# ==========================================

class UpdateCheckerThread(QThread):
    update_found = pyqtSignal(dict)
    
    def __init__(self, local_version_file):
        super().__init__()
        self.local_version_file = local_version_file
        
    def run(self):
        try:
            # 读取本地版本号
            local_version = "0.0.0"
            if os.path.exists(self.local_version_file):
                with open(self.local_version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    local_version = data.get("version", "0.0.0")
            
            # 使用国内镜像加速获取 GitHub 远端版本配置
            raw_url = f"{GH_PROXY}https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/version.json"
            response = requests.get(raw_url, timeout=10)
            if response.status_code == 200:
                remote_data = response.json()
                remote_version = remote_data.get("version", "0.0.0")
                
                # 如果云端版本高于本地，则触发更新弹窗
                if remote_version > local_version:
                    self.update_found.emit(remote_data)
        except Exception as e:
            print(f"OTA Check failed (Network or Config Error): {e}")


class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, zip_url, assets_dir, local_version_file, new_version_data):
        super().__init__()
        # 强制走加速通道
        if "github.com" in zip_url and not zip_url.startswith(GH_PROXY):
            self.zip_url = GH_PROXY + zip_url
        else:
            self.zip_url = zip_url
            
        self.assets_dir = assets_dir
        self.local_version_file = local_version_file
        self.new_version_data = new_version_data
        
    def run(self):
        temp_dir = tempfile.mkdtemp()
        try:
            # 1. 下载 ZIP
            response = requests.get(self.zip_url, stream=True, timeout=15)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            zip_path = os.path.join(temp_dir, "update.zip")
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            self.progress.emit(int(downloaded * 100 / total_size))
            
            self.progress.emit(100)
            
            # 2. 静默解压 ZIP
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                
            # 3. 智能覆盖到本地 assets 目录
            # 找到解压后的根目录 (GitHub zip 通常外面包了一层 folder)
            root_folders = [d for d in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, d))]
            if len(root_folders) == 1:
                source_assets = os.path.join(extract_dir, root_folders[0])
            else:
                source_assets = extract_dir
                
            for item in os.listdir(source_assets):
                s_path = os.path.join(source_assets, item)
                d_path = os.path.join(self.assets_dir, item)
                
                # 仅同步角色文件夹，忽略其他文件
                if os.path.isdir(s_path):
                    if os.path.exists(d_path):
                        shutil.rmtree(d_path)  # 清除旧角色文件
                    shutil.copytree(s_path, d_path)
                    
            # 4. 更新本地版本号
            with open(self.local_version_file, 'w', encoding='utf-8') as f:
                json.dump(self.new_version_data, f, indent=4, ensure_ascii=False)
                
            self.finished.emit(True, "更新成功！")
            
        except Exception as e:
            self.finished.emit(False, f"下载或解压失败: {str(e)}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class UpdateDialog(QDialog):
    def __init__(self, update_data, assets_dir, local_version_file, parent=None):
        super().__init__(parent)
        self.update_data = update_data
        self.assets_dir = assets_dir
        self.local_version_file = local_version_file
        
        self.setWindowTitle("发现新角色包！")
        self.setFixedSize(400, 200)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: #1e1e1e; color: #fff; border-radius: 10px; border: 1px solid #333;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel(f"🌟 新版本发现: {update_data.get('version')}")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4db8ff; border: none;")
        layout.addWidget(title)
        
        log = QLabel(update_data.get("changelog", "有新的小可爱加入了！"))
        log.setWordWrap(True)
        log.setStyleSheet("font-size: 14px; margin-top: 10px; color: #ccc; border: none;")
        layout.addWidget(log)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #444; border-radius: 5px; text-align: center; color: white; }
            QProgressBar::chunk { background-color: #4db8ff; border-radius: 5px; }
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("下次一定")
        self.btn_cancel.setStyleSheet("padding: 8px 15px; background-color: #333; border-radius: 5px;")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_update = QPushButton("立即更新")
        self.btn_update.setStyleSheet("padding: 8px 15px; background-color: #4db8ff; color: #000; font-weight: bold; border-radius: 5px;")
        self.btn_update.clicked.connect(self.start_update)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_update)
        
        layout.addLayout(btn_layout)
        
    def start_update(self):
        self.btn_update.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.show()
        
        # 获取 zip url，并自动补全 Github 标准 Archive URL 格式
        zip_url = self.update_data.get("assets_zip_url")
        if not zip_url:
            zip_url = f"https://github.com/{GITHUB_USERNAME}/{GITHUB_REPO}/archive/refs/heads/main.zip"
            
        self.downloader = DownloadThread(zip_url, self.assets_dir, self.local_version_file, self.update_data)
        self.downloader.progress.connect(self.progress_bar.setValue)
        self.downloader.finished.connect(self.on_finished)
        self.downloader.start()
        
    def on_finished(self, success, msg):
        if success:
            self.accept()
        else:
            self.progress_bar.hide()
            self.btn_update.setEnabled(True)
            self.btn_cancel.setEnabled(True)
            self.btn_update.setText("更新失败重试")
            print(f"OTA Error: {msg}")
