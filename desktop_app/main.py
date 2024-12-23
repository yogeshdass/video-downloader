import sys
import time
from datetime import datetime
import yt_dlp
import os
from PyQt6.QtWidgets import (
    QApplication, 
    QMainWindow, 
    QLabel, 
    QVBoxLayout,
    QHBoxLayout, 
    QWidget, 
    QPushButton, 
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject

# Create a custom output stream to capture console output
class OutputStreamRedirector(QObject):
    text_written = pyqtSignal(str)

    def write(self, text):
        self.text_written.emit(str(text))
        # Uncomment the next line if you still want to see output in the console
        # sys.__stdout__.write(text)

    def flush(self):
        pass

class DownloadWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                # Extract the raw percentage and speed values
                percent = d.get('_percent_str', '').strip()
                speed = d.get('_speed_str', '').strip()
                
                # Remove ANSI color codes
                percent = percent.replace('[0;94m', '').replace('[0m', '')
                speed = speed.replace('[0;32m', '').replace('[0m', '')
                
                self.progress.emit(f"Downloading... {percent} at {speed}")
            except:
                self.progress.emit("Downloading...")
        elif d['status'] == 'finished':
            self.progress.emit("Download completed! Converting...")

    def run(self):
        try:
            self.progress.emit("Starting download...")
            
            ydl_opts = {
                'format': 'bestvideo[ext!=webm]+bestaudio[ext!=webm]/best[ext!=webm]',
                'progress_hooks': [self.progress_hook],
                'outtmpl': f'{self.save_path}/%(title)s.%(ext)s',
                'nocheckcertificate': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.progress.emit("Extracting video information...")
                info = ydl.extract_info(self.url, download=True)
                self.progress.emit(f"Successfully downloaded: {info['title']}")
                
        except Exception as e:
            self.progress.emit(f"Error: {str(e)}")
        finally:
            self.finished.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set up output redirection
        self.stdout_redirector = OutputStreamRedirector()
        self.stdout_redirector.text_written.connect(self.handle_stdout)
        sys.stdout = self.stdout_redirector
        
        # Rest of your initialization code...
        self.setWindowTitle("Наш Видео Загрузчик")
        self.setGeometry(100, 100, 800, 600)
        
        # Initialize save path
        self.last_save_path = os.path.join(os.path.expanduser("~"), "Downloads")

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main vertical layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Container for the form elements
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(20)
        
        # Create horizontal layout for Video link input
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add label and input field for Video link
        link_label = QLabel("Link name:")
        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("Enter Video URL here")
        self.link_input.setMaxLength(200)
        self.link_input.setMinimumWidth(400)
        
        input_layout.addWidget(link_label)
        input_layout.addWidget(self.link_input)
        
        # Add the input container to form layout
        form_layout.addWidget(input_container)
        
        # Create horizontal layout for save location
        save_location_container = QWidget()
        save_location_layout = QHBoxLayout(save_location_container)
        save_location_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add label and display field for save location
        save_location_label = QLabel("Save location:")
        self.save_location_display = QLineEdit(self.last_save_path)
        self.save_location_display.setReadOnly(True)
        self.save_location_display.setMinimumWidth(400)
        
        change_location_button = QPushButton("Browse")
        change_location_button.setFixedWidth(100)
        change_location_button.clicked.connect(self.change_save_location)
        
        save_location_layout.addWidget(save_location_label)
        save_location_layout.addWidget(self.save_location_display)
        save_location_layout.addWidget(change_location_button)
        
        form_layout.addWidget(save_location_container)
        
        # Create and add download button
        self.download_button = QPushButton("Download")
        self.download_button.setFixedWidth(200)
        self.download_button.clicked.connect(self.button_clicked)
        
        # Center align the button
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(self.download_button, alignment=Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(button_container)
        
        # Add multi-line text output
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(200)
        self.output_text.setPlaceholderText("Output will appear here...")
        self.output_text.setAcceptRichText(True)  # Enable rich text support
        form_layout.addWidget(self.output_text)
        
        # Add status label
        self.status_label = QLabel("Welcome! Enter a Video URL to download.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(self.status_label)
        
        # Add form container to main layout
        main_layout.addWidget(form_container, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Initialize download worker
        self.download_worker = None
        
        # Add some styling
        self.setStyleSheet("""
            QLabel {
                font-size: 14px;
            }
            QPushButton {
                padding: 8px;
                font-size: 14px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QLineEdit {
                padding: 8px;
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: black;
                color: white;
            }
            QLineEdit:read-only {
                background-color: black;
                color: #cccccc;
            }
            QTextEdit {
                padding: 8px;
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: black;
                font-family: monospace;
            }
        """)


    def handle_stdout(self, text):
        """Handle redirected stdout text"""
        current_time = datetime.now().strftime("%H:%M:%S")
        if "Error:" in text:
            self.output_text.append(f'<span style="color: #ff0000;">[{current_time}] {text.strip()}</span>')
        else:
            self.output_text.append(f'<span style="color: #00ff00;">[{current_time}] {text.strip()}</span>')
        # Scroll to the bottom
        self.output_text.verticalScrollBar().setValue(
            self.output_text.verticalScrollBar().maximum()
        )

    def change_save_location(self):
        """Open dialog to change save location"""
        new_path = QFileDialog.getExistingDirectory(
            self,
            "Select Save Location",
            self.last_save_path,
            QFileDialog.Option.ShowDirsOnly
        )
        if new_path:
            self.last_save_path = new_path
            self.save_location_display.setText(self.last_save_path)

    def update_output(self, message):
        """Update the output text area with a new message"""
        current_time = datetime.now().strftime("%H:%M:%S")
        if "Error:" in message:
            self.output_text.append(f'<span style="color: #ff0000;">[{current_time}] {message}</span>')
        else:
            self.output_text.append(f'<span style="color: #00ff00;">[{current_time}] {message}</span>')
        # Scroll to the bottom
        self.output_text.verticalScrollBar().setValue(
            self.output_text.verticalScrollBar().maximum()
        )

    def enable_interface(self, enabled=True):
        """Enable or disable the interface during download"""
        self.download_button.setEnabled(enabled)
        self.link_input.setEnabled(enabled)

    def download_finished(self):
        """Handle download completion"""
        self.enable_interface(True)
        self.status_label.setText("Download completed!")
        self.download_worker = None

    def button_clicked(self):
        link_text = self.link_input.text().strip()
        
        if not link_text:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please enter a Video URL before proceeding.",
                QMessageBox.StandardButton.Ok
            )
            return
            
        # Clear previous output
        self.output_text.clear()
        
        # Disable interface during download
        self.enable_interface(False)
        self.status_label.setText("Downloading...")
        
        # Create and start download worker
        self.download_worker = DownloadWorker(link_text, self.last_save_path)
        self.download_worker.progress.connect(self.update_output)
        self.download_worker.finished.connect(self.download_finished)
        self.download_worker.start()

    def closeEvent(self, event):
        """Restore stdout when closing the application"""
        sys.stdout = sys.__stdout__
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
