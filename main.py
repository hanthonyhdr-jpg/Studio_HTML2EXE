import os
import sys
import json
import sqlite3
import threading
import psutil
import base64
import logging
from PyQt5.QtCore import QUrl, QObject, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEnginePage, QWebEngineProfile
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtGui import QIcon
import pystray
from PIL import Image

# Configuração de Logs para Debug
APP_DATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), "HeroJUVICKS")
os.makedirs(APP_DATA_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(APP_DATA_DIR, "system.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def resource_path(relative_path):
    """ Retorna o caminho absoluto para recursos, funcionando em Dev e no EXE """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

DB_PATH = os.path.join(APP_DATA_DIR, "presets.db")

class Database:
    @staticmethod
    def init():
        conn = sqlite3.connect(DB_PATH)
        conn.execute('CREATE TABLE IF NOT EXISTS presets (name TEXT PRIMARY KEY, data TEXT)')
        conn.commit()
        conn.close()

    @staticmethod
    def get_all():
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT name, data FROM presets").fetchall()
        conn.close()
        return {r[0]: json.loads(r[1]) for r in rows}

    @staticmethod
    def save(name, data):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT OR REPLACE INTO presets (name, data) VALUES (?, ?)", (name, data))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(name):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM presets WHERE name = ?", (name,))
        conn.commit()
        conn.close()

class SystemBridge(QObject):
    """ Ponte de comunicação entre o HTML e o Windows """
    def __init__(self, window):
        super().__init__()
        self.window = window

    @pyqtSlot(result=str)
    def get_presets(self):
        return json.dumps(Database.get_all())

    @pyqtSlot(str, str, result=bool)
    def save_preset(self, name, data_json):
        try:
            Database.save(name, data_json)
            return True
        except Exception as e:
            logging.error(f"Erro ao salvar preset: {e}")
            return False

    @pyqtSlot(str, result=bool)
    def delete_preset(self, name):
        try:
            Database.delete(name)
            return True
        except Exception as e:
            logging.error(f"Erro ao deletar preset: {e}")
            return False

    @pyqtSlot(str, str, str)
    def save_file(self, filename, content_b64, file_filter):
        """ Abre diálogo nativo do Windows para salvar arquivos """
        options = QFileDialog.Options()
        path, _ = QFileDialog.getSaveFileName(
            self.window, "Salvar Arquivo", filename, file_filter, options=options
        )
        if path:
            try:
                with open(path, "wb") as f:
                    f.write(base64.b64decode(content_b64))
                logging.info(f"Arquivo salvo: {path}")
                QMessageBox.information(self.window, "Sucesso", "Arquivo salvo com sucesso!")
            except Exception as e:
                logging.error(f"Erro ao gravar arquivo no disco: {e}")
                QMessageBox.critical(self.window, "Erro", f"Erro ao salvar: {e}")

class CustomPage(QWebEnginePage):
    """ Intercepta navegação para disparar o seletor de arquivos e exibe alertas do JS """
    file_select_requested = pyqtSignal()

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if url.scheme() == 'app' and 'selectfiles' in url.host():
            self.file_select_requested.emit()
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)

    def javaScriptAlert(self, securityOrigin, msg):
        QMessageBox.warning(self.view(), "Aviso", msg)

    def javaScriptConsoleMessage(self, level, msg, line, sourceID):
        logging.info(f"JS Console: {msg} (Line: {line})")

class HeroWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Pega o nome dinâmico para o título da janela
        app_name = os.environ.get('APP_NAME', 'Hero JUVICKS')
        self.setWindowTitle(f"{app_name} - v1.1")
        self.resize(1366, 850)
        self.tray_icon = None

        # Ícone
        icon_path = resource_path("assets/favicon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Browser Engine
        self.browser = QWebEngineView()
        
        # Persistent Storage para LocalStorage e cookies (para presets funcionarem como no HTML original)
        profile = QWebEngineProfile.defaultProfile()
        profile.setPersistentStoragePath(os.path.join(APP_DATA_DIR, "webstorage"))
        profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        profile.downloadRequested.connect(self.handle_download)
        
        self.page = CustomPage()
        self.browser.setPage(self.page)
        
        # Configurações de Segurança
        settings = self.page.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)

        # Bridge
        self.channel = QWebChannel()
        self.bridge = SystemBridge(self)
        self.channel.registerObject('pybridge', self.bridge)
        self.page.setWebChannel(self.channel)

        # Eventos
        self.page.file_select_requested.connect(self.handle_file_import)
        self.browser.loadFinished.connect(self.init_javascript_bridge)

        self.setCentralWidget(self.browser)
        
        # Carregar UI
        ui_path = resource_path("assets/index.html")
        self.browser.load(QUrl.fromLocalFile(os.path.abspath(ui_path)))

        self.setup_tray()

    def init_javascript_bridge(self, ok):
        if ok:
            # Injeta a configuração do QWebChannel no carregamento da página
            # Isso garante que a ponte se conecte mesmo se o código nativo falhar por temporização
            js_code = """
            if (typeof qt !== 'undefined' && qt.webChannelTransport) {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    if (channel.objects.pybridge) {
                        window.pybridge = channel.objects.pybridge;
                        console.log("Bridge connected from Python injection.");
                    }
                });
            } else {
                console.error("qt.webChannelTransport is not available in Python injection either.");
            }
            """
            self.page.runJavaScript(js_code)

    def handle_file_import(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar XMLs", "", "Arquivos XML (*.xml);;Todos (*)"
        )
        if files:
            result = []
            for f_path in files:
                try:
                    with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
                        result.append({'name': os.path.basename(f_path), 'content': f.read()})
                except Exception as e:
                    logging.error(f"Falha ao ler {f_path}: {e}")
            
            js_data = json.dumps(result, ensure_ascii=False)
            self.page.runJavaScript(f"receiveFiles({js_data});")

    def handle_download(self, download):
        options = QFileDialog.Options()
        suggested_name = download.suggestedFileName()
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Arquivo", suggested_name, "Todos os Arquivos (*)", options=options
        )
        if path:
            download.setPath(path)
            download.accept()
        else:
            download.cancel()

    def setup_tray(self):
        def on_open(icon, item):
            self.show()
            self.showNormal()
            self.activateWindow()
            self.raise_()

        def on_exit(icon, item):
            icon.stop()
            QApplication.quit()
            os._exit(0)

        icon_path = resource_path("assets/favicon.ico")
        image = Image.open(icon_path) if os.path.exists(icon_path) else Image.new('RGB', (64, 64), (255, 255, 255))
        
        menu = pystray.Menu(
            pystray.MenuItem("Abrir Sistema", on_open),
            pystray.MenuItem("Fechar Tudo", on_exit)
        )
        self.tray_icon = pystray.Icon("HeroJUVICKS", image, "Hero JUVICKS", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

if __name__ == "__main__":
    Database.init()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    
    window = HeroWindow()
    window.show()
    sys.exit(app.exec_())
