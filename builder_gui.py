import os
import sys
import subprocess
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QLabel, QFileDialog, QTextEdit, QCheckBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# BASE_DIR: pasta onde o EXE (ou script) está — usada para SAÍDA de arquivos
# RESOURCE_DIR: pasta onde os arquivos internos do motor estão
#   - Quando EXE: sys._MEIPASS (pasta temp onde o PyInstaller extrai os recursos)
#   - Quando script: mesma pasta do .py
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)        # Pasta onde o .exe está
    RESOURCE_DIR = sys._MEIPASS                        # Pasta temp com spec, main.py, etc.
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = BASE_DIR

class BuildThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, app_name, html_path, icon_path, output_dir, make_installer):
        super().__init__()
        self.app_name = app_name
        self.html_path = html_path
        self.icon_path = icon_path
        self.output_dir = output_dir
        self.make_installer = make_installer

    def find_iscc(self):
        paths = [
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
            r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
            r"C:\Program Files\Inno Setup 5\ISCC.exe"
        ]
        for p in paths:
            if os.path.exists(p): return p
        return None

    def run(self):
        try:
            self.progress.emit(f"Iniciando build para: {self.app_name}...")
            self.progress.emit(f"Pasta de saida: {BASE_DIR}")
            self.progress.emit(f"Motor interno: {RESOURCE_DIR}")

            # Pasta assets DENTRO do diretório de recursos internos
            assets_path = os.path.join(RESOURCE_DIR, "assets")
            os.makedirs(assets_path, exist_ok=True)

            # Copiar recursos
            self.progress.emit("Preparando recursos...")
            shutil.copy(self.html_path, os.path.join(assets_path, "index.html"))
            shutil.copy(self.icon_path, os.path.join(assets_path, "favicon.ico"))

            # Configurar ambiente
            os.environ["APP_NAME"] = self.app_name
            spec_file = os.path.join(RESOURCE_DIR, "HeroJUVICKS.spec")
            iss_file  = os.path.join(RESOURCE_DIR, "installer.iss")
            
            # 1. Rodar PyInstaller
            self.progress.emit("Executando PyInstaller...")
            process = subprocess.Popen(
                ["pyinstaller", "--noconfirm", f"--workpath={os.path.join(BASE_DIR,'build')}",
                 f"--distpath={os.path.join(BASE_DIR,'dist')}", spec_file],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True,
                cwd=RESOURCE_DIR
            )
            for line in process.stdout:
                self.progress.emit(line.strip())
            process.wait()

            if process.returncode == 0:
                self.progress.emit("Executável gerado com sucesso!")
                
                # 2. Gerar Instalador se solicitado
                if self.make_installer:
                    iscc = self.find_iscc()
                    if iscc:
                        self.progress.emit("Iniciando Inno Setup...")
                        params = [
                            iscc,
                            f"/dMyAppName={self.app_name}",
                            f"/dMyAppExeName={self.app_name}.exe",
                            f"/dMyAppDataName={self.app_name}",
                            f"/dMyAppFolder={self.app_name}",
                            # Forma garantida de enviar colchetes duplos {{ID}} para o Inno Setup
                            "/dMyAppId={{HeroJUVICKS-" + self.app_name + "}}",
                            f"/dSourcePath={os.path.join(BASE_DIR, 'dist')}",
                            f"/dResourcePath={os.path.join(RESOURCE_DIR, 'assets')}",
                            f"/O{os.path.join(BASE_DIR,'dist_installer')}",
                            iss_file
                        ]
                        proc_inno = subprocess.Popen(params, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                        for line in proc_inno.stdout:
                            self.progress.emit(line.strip())
                        proc_inno.wait()
                    else:
                        self.progress.emit("AVISO: Inno Setup não encontrado. Pulando instalador.")

                # 3. Mover resultados para o destino final
                self.progress.emit("Organizando arquivos de saída...")
                
                # Voltamos para o modo PASTA (separada)
                dist_folder = os.path.join(BASE_DIR, "dist", self.app_name)
                final_dest_dir = os.path.join(self.output_dir, self.app_name)
                
                if os.path.exists(final_dest_dir):
                    shutil.rmtree(final_dest_dir)
                
                if os.path.exists(dist_folder):
                    shutil.copytree(dist_folder, final_dest_dir)
                    self.progress.emit(f"Pasta do sistema movida para: {final_dest_dir}")
                else:
                    self.progress.emit(f"AVISO: Pasta {dist_folder} não encontrada.")

                # Mover instalador se existir
                installer_src = os.path.join(BASE_DIR, "dist_installer")
                if os.path.exists(installer_src):
                    installer_dest = os.path.join(self.output_dir, "Instaladores")
                    os.makedirs(installer_dest, exist_ok=True)
                    for f in os.listdir(installer_src):
                        shutil.move(os.path.join(installer_src, f), os.path.join(installer_dest, f))
                    self.progress.emit(f"Instalador movido para: {installer_dest}")

                self.progress.emit(f"\n=== SUCESSO TOTAL! ===\nArquivos salvos em: {self.output_dir}")
                self.finished.emit(True)
            else:
                self.progress.emit("Erro na compilação do PyInstaller.")
                self.finished.emit(False)

        except Exception as e:
            self.progress.emit(f"ERRO CRÍTICO: {str(e)}")
            self.finished.emit(False)

class BuilderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hero JUVICKS - Studio Builder v1.2")
        self.resize(750, 650)
        self.initUI()

    def initUI(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.setStyleSheet("""
            QMainWindow { background-color: #0f0f12; }
            QLabel { color: #e8ff00; font-weight: bold; font-size: 12px; margin-top: 10px; }
            QLineEdit { background-color: #1c1c22; border: 1px solid #2a2a35; color: white; padding: 8px; border-radius: 5px; }
            QPushButton { background-color: #2a2a35; color: white; padding: 10px; border-radius: 5px; font-weight: bold; border: 1px solid #3a3a45; }
            QPushButton:hover { background-color: #e8ff00; color: black; }
            QCheckBox { color: white; font-weight: bold; margin: 10px 0; }
            QTextEdit { background-color: #000; color: #00e87a; font-family: 'Consolas', monospace; font-size: 11px; border: 1px solid #2a2a35; }
            #btnBuild { background-color: #00e87a; color: black; font-size: 14px; margin-top: 10px; }
            #btnBuild:disabled { background-color: #333; color: #777; }
        """)

        layout.addWidget(QLabel("NOME DO PROJETO"))
        self.txtName = QLineEdit()
        self.txtName.setPlaceholderText("Ex: SistemaVendas_ClienteA")
        layout.addWidget(self.txtName)

        layout.addWidget(QLabel("ARQUIVO HTML PRINCIPAL"))
        h1 = QHBoxLayout()
        self.txtHtml = QLineEdit()
        btnHtml = QPushButton("Selecionar HTML")
        btnHtml.clicked.connect(self.browseHtml)
        h1.addWidget(self.txtHtml); h1.addWidget(btnHtml)
        layout.addLayout(h1)

        layout.addWidget(QLabel("ÍCONE DO PROGRAMA (.ICO)"))
        h2 = QHBoxLayout()
        self.txtIcon = QLineEdit()
        btnIcon = QPushButton("Selecionar Ícone")
        btnIcon.clicked.connect(self.browseIcon)
        h2.addWidget(self.txtIcon); h2.addWidget(btnIcon)
        layout.addLayout(h2)

        layout.addWidget(QLabel("PASTA DE DESTINO (ONDE SALVAR O EXE)"))
        h3 = QHBoxLayout()
        self.txtOutput = QLineEdit()
        btnOutput = QPushButton("Selecionar Pasta")
        btnOutput.clicked.connect(self.browseOutput)
        h3.addWidget(self.txtOutput); h3.addWidget(btnOutput)
        layout.addLayout(h3)

        self.chkInstaller = QCheckBox("GERAR INSTALADOR PROFISSIONAL (.EXE DE SETUP)")
        self.chkInstaller.setChecked(True)
        layout.addWidget(self.chkInstaller)

        layout.addWidget(QLabel("LOG DE PROCESSAMENTO"))
        self.logArea = QTextEdit()
        self.logArea.setReadOnly(True)
        layout.addWidget(self.logArea)

        self.btnBuild = QPushButton("GERAR TUDO AGORA")
        self.btnBuild.setObjectName("btnBuild")
        self.btnBuild.clicked.connect(self.startBuild)
        layout.addWidget(self.btnBuild)

    def browseHtml(self):
        f, _ = QFileDialog.getOpenFileName(self, "Selecionar HTML", "", "HTML (*.html)")
        if f: self.txtHtml.setText(f)

    def browseIcon(self):
        f, _ = QFileDialog.getOpenFileName(self, "Selecionar Icone", "", "Icone (*.ico)")
        if f: self.txtIcon.setText(f)

    def browseOutput(self):
        f = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Saida")
        if f: self.txtOutput.setText(f)

    def startBuild(self):
        name = self.txtName.text().strip()
        html = self.txtHtml.text()
        icon = self.txtIcon.text()
        out = self.txtOutput.text()

        if not all([name, html, icon, out]):
            self.logArea.append("!!! ERRO: Preencha todos os campos antes de gerar.")
            return

        self.btnBuild.setEnabled(False)
        self.logArea.clear()
        
        self.thread = BuildThread(name, html, icon, out, self.chkInstaller.isChecked())
        self.thread.progress.connect(self.logArea.append)
        self.thread.finished.connect(self.onFinished)
        self.thread.start()

    def onFinished(self, success):
        self.btnBuild.setEnabled(True)
        if success:
            self.logArea.append("\n=== PROCESSO FINALIZADO! ===")
        else:
            self.logArea.append("\n=== OCORREU UM ERRO DURANTE O PROCESSO ===")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BuilderApp()
    window.show()
    sys.exit(app.exec_())
