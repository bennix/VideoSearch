import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLineEdit, QListWidget, 
                           QLabel, QFileDialog, QStatusBar, QProgressBar,
                           QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import vlc
from video_processor import VideoProcessor
from translator import OllamaTranslator

class IndexingThread(QThread):
    def __init__(self, video_processor, rebuild=False):
        super().__init__()
        self.video_processor = video_processor
        self.rebuild = rebuild
        
    def run(self):
        try:
            if self.rebuild:
                self.video_processor.rebuild_index()
            else:
                self.video_processor.build_index()
        except Exception as e:
            print(f"Indexing error: {str(e)}")

class VideoSearchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Search")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize video processor and translator
        self.video_processor = VideoProcessor()
        self.video_processor.progress_updated.connect(self.update_progress)
        self.video_processor.indexing_finished.connect(self.indexing_finished)
        self.translator = OllamaTranslator()
        
        # Initialize indexing thread
        self.indexing_thread = None
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        
        # Left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Buttons for index management
        button_layout = QHBoxLayout()
        self.open_folder_btn = QPushButton("Open Folder")
        self.rebuild_index_btn = QPushButton("Rebuild Index")
        self.build_index_btn = QPushButton("Build Index")
        
        button_layout.addWidget(self.open_folder_btn)
        button_layout.addWidget(self.rebuild_index_btn)
        button_layout.addWidget(self.build_index_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # Word list
        self.word_list = QListWidget()
        self.word_list.itemClicked.connect(self.word_clicked)
        left_layout.addLayout(button_layout)
        left_layout.addWidget(self.progress_bar)
        left_layout.addWidget(QLabel("Word List (A-Z)"))
        left_layout.addWidget(self.word_list)
        
        # Right panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Search box
        search_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_btn = QPushButton("Search")
        search_layout.addWidget(self.search_box)
        search_layout.addWidget(self.search_btn)
        
        # Results area
        self.results_list = QListWidget()
        
        # Translation area
        translation_layout = QVBoxLayout()
        translation_label = QLabel("Translation")
        self.translation_text = QTextEdit()
        self.translation_text.setReadOnly(True)
        translation_layout.addWidget(translation_label)
        translation_layout.addWidget(self.translation_text)
        
        # Video player area
        self.video_frame = QWidget()
        self.video_frame.setMinimumHeight(360)
        self.video_frame.setStyleSheet("background-color: black;")
        
        right_layout.addLayout(search_layout)
        right_layout.addWidget(QLabel("Search Results"))
        right_layout.addWidget(self.results_list)
        right_layout.addLayout(translation_layout)
        right_layout.addWidget(QLabel("Video Player"))
        right_layout.addWidget(self.video_frame)
        
        # Add panels to main layout
        layout.addWidget(left_panel, 1)
        layout.addWidget(right_panel, 2)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Connect signals
        self.open_folder_btn.clicked.connect(self.open_folder)
        self.rebuild_index_btn.clicked.connect(lambda: self.start_indexing(True))
        self.build_index_btn.clicked.connect(lambda: self.start_indexing(False))
        self.search_btn.clicked.connect(self.search)
        self.results_list.itemClicked.connect(self.play_video_segment)
        
        # Initialize VLC player
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        if sys.platform == "darwin":  # for MacOS
            self.player.set_nsobject(int(self.video_frame.winId()))
        else:
            self.player.set_xwindow(self.video_frame.winId())
        
    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Video Folder")
        if folder:
            # Clear previous state
            if self.indexing_thread and self.indexing_thread.isRunning():
                self.indexing_thread.terminate()
                self.indexing_thread.wait()
            
            self.word_list.clear()
            self.results_list.clear()
            self.search_box.clear()
            
            # Set new folder
            self.video_processor.set_folder(folder)
            self.status_bar.showMessage(f"Selected folder: {folder}")
            
            # Try to load existing index
            if self.video_processor.load_index():
                self.update_word_list()
                self.status_bar.showMessage("Loaded existing index")
    
    def start_indexing(self, rebuild=False):
        if not hasattr(self.video_processor, 'folder') or not self.video_processor.folder:
            self.status_bar.showMessage("Please select a folder first")
            return
            
        # If there's an existing thread running, stop it
        if self.indexing_thread and self.indexing_thread.isRunning():
            self.indexing_thread.terminate()
            self.indexing_thread.wait()
        
        # Disable buttons during indexing
        self.open_folder_btn.setEnabled(False)
        self.rebuild_index_btn.setEnabled(False)
        self.build_index_btn.setEnabled(False)
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Clear previous results if rebuilding
        if rebuild:
            self.word_list.clear()
            self.results_list.clear()
            self.search_box.clear()
            self.video_processor.clear_index()
        
        # Create and start indexing thread
        self.indexing_thread = IndexingThread(self.video_processor, rebuild)
        self.indexing_thread.finished.connect(self.indexing_finished)
        self.indexing_thread.start()
        
        self.status_bar.showMessage("Starting indexing process...")
            
    def update_progress(self, message, progress):
        self.status_bar.showMessage(message)
        self.progress_bar.setValue(progress)
        QApplication.processEvents()
        
    def indexing_finished(self):
        # Re-enable buttons
        self.open_folder_btn.setEnabled(True)
        self.rebuild_index_btn.setEnabled(True)
        self.build_index_btn.setEnabled(True)
        
        # Update word list
        self.update_word_list()
        
        # Hide progress bar
        self.progress_bar.setVisible(False)
        
        self.status_bar.showMessage("Indexing completed!")
        
    def update_word_list(self):
        self.word_list.clear()
        words = self.video_processor.get_word_list()
        self.word_list.addItems(words)
        
    def word_clicked(self, item):
        """When a word is clicked, add it to the search box"""
        current_text = self.search_box.text()
        word = item.text()
        
        # If search box is empty, just set the word
        if not current_text:
            self.search_box.setText(word)
        else:
            # Add the word with a space separator
            self.search_box.setText(f"{current_text} {word}")
            
        # Optionally trigger the search
        self.search()
        
    def search(self):
        query = self.search_box.text()
        if query:
            results = self.video_processor.search(query)
            self.results_list.clear()
            for result in results:
                self.results_list.addItem(f"{result['text']} ({result['start']:.1f}s - {result['end']:.1f}s)")
                
    def play_video_segment(self, item):
        # Get the selected result index
        index = self.results_list.row(item)
        results = self.video_processor.last_search_results
        if results and index < len(results):
            result = results[index]
            
            # Get translation
            if self.translator.is_available():
                self.translation_text.setText("Translating...")
                translation = self.translator.translate(result['text'])
                if translation:
                    self.translation_text.setText(
                        f"Original:\n{result['text']}\n\n"
                        f"中文翻译:\n{translation}"
                    )
                else:
                    self.translation_text.setText(
                        f"Original:\n{result['text']}\n\n"
                        "翻译失败。可能的原因：\n"
                        "1. Ollama 服务未正确响应\n"
                        "2. 请求超时\n"
                        "3. 模型响应格式错误\n\n"
                        "请确保：\n"
                        "1. Ollama 服务正在运行 (ollama serve)\n"
                        "2. gemma:2b 模型已安装 (ollama pull gemma:2b)"
                    )
            else:
                self.translation_text.setText(
                    f"Original:\n{result['text']}\n\n"
                    "翻译服务（Ollama）未启动。\n"
                    "请运行以下命令：\n"
                    "1. ollama serve\n"
                    "2. ollama pull gemma:2b"
                )
            
            # Play video
            video_path = os.path.join(self.video_processor.folder, result['video'])
            
            # Create a new media and set it to the player
            media = self.instance.media_new(video_path)
            self.player.set_media(media)
            
            # Convert timestamps to milliseconds
            start_time = int(result['start'] * 1000)
            end_time = int(result['end'] * 1000)
            
            # Set up event manager to handle end time
            events = self.player.event_manager()
            events.event_attach(vlc.EventType.MediaPlayerTimeChanged, 
                              lambda event: self.check_video_time(end_time))
            
            # Play the video from the start timestamp
            self.player.play()
            self.player.set_time(start_time)
            
    def check_video_time(self, end_time):
        """Check if we've reached the end timestamp"""
        current_time = self.player.get_time()
        if current_time >= end_time:
            self.player.pause()
            # Detach the event listener to prevent memory leaks
            self.player.event_manager().event_detach(vlc.EventType.MediaPlayerTimeChanged)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VideoSearchApp()
    window.show()
    sys.exit(app.exec_())
