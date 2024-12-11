import os
import json
import whisper
import jieba
import nltk
from moviepy.editor import VideoFileClip
from collections import defaultdict
from PyQt5.QtCore import QObject, pyqtSignal

class VideoProcessor(QObject):
    progress_updated = pyqtSignal(str, int)  # Signal for progress updates
    indexing_finished = pyqtSignal()  # Signal for completion

    def __init__(self):
        super().__init__()
        self.model = whisper.load_model("base")
        self.folder = None
        self.index = defaultdict(list)
        self.word_list = set()
        self.last_search_results = []  # Store last search results
        
        # Download required NLTK data
        nltk.download('punkt')
        nltk.download('words')
        
    def set_folder(self, folder_path):
        """Set the folder path containing videos"""
        self.folder = folder_path
        
    def extract_audio(self, video_path):
        """Extract audio from video file"""
        video = VideoFileClip(video_path)
        return video.audio
        
    def transcribe_video(self, video_path):
        """Transcribe video using Whisper"""
        result = self.model.transcribe(video_path, task="translate")
        return result["segments"]
        
    def process_words(self, text):
        """Process text to extract words in both English and Chinese"""
        # Process English words
        words = set(nltk.word_tokenize(text.lower()))
        # Only keep words that contain at least one letter
        english_words = {word for word in words if any(c.isalpha() for c in word)}
        
        # Process Chinese words
        chinese_words = set(jieba.cut(text))
        # Remove words that are only numbers or punctuation
        chinese_words = {word for word in chinese_words 
                        if any('\u4e00' <= c <= '\u9fff' for c in word)}
        
        return english_words.union(chinese_words)
        
    def build_index(self):
        """Build search index from videos in folder"""
        if not self.folder:
            return
            
        video_files = [f for f in os.listdir(self.folder) 
                      if f.endswith(('.mp4', '.avi', '.mov'))]
        total_files = len(video_files)
        
        for i, video_file in enumerate(video_files, 1):
            self.progress_updated.emit(f"Processing {video_file}...", int((i-1) * 100 / total_files))
            
            video_path = os.path.join(self.folder, video_file)
            try:
                segments = self.transcribe_video(video_path)
                
                for segment in segments:
                    text = segment["text"]
                    words = self.process_words(text)
                    self.word_list.update(words)
                    
                    for word in words:
                        self.index[word].append({
                            "video": video_file,
                            "text": text,
                            "start": segment["start"],
                            "end": segment["end"]
                        })
            except Exception as e:
                self.progress_updated.emit(f"Error processing {video_file}: {str(e)}", 
                                        int(i * 100 / total_files))
                continue
                
        # Save index
        self.save_index()
        self.progress_updated.emit("Indexing completed!", 100)
        self.indexing_finished.emit()
        
    def clear_index(self):
        """Clear the current index"""
        self.index.clear()
        self.word_list.clear()
        self.last_search_results.clear()
        
    def rebuild_index(self):
        """Clear and rebuild the search index"""
        self.clear_index()
        self.build_index()
        
    def save_index(self):
        """Save index to file"""
        if self.folder:
            index_path = os.path.join(self.folder, "video_index.json")
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "index": dict(self.index),
                    "words": list(self.word_list)
                }, f, ensure_ascii=False)
                
    def load_index(self):
        """Load index from file"""
        if self.folder:
            index_path = os.path.join(self.folder, "video_index.json")
            if os.path.exists(index_path):
                with open(index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.index = defaultdict(list, data["index"])
                    self.word_list = set(data["words"])
                    return True
        return False
                    
    def get_word_list(self):
        """Return sorted list of words"""
        return sorted(self.word_list)
        
    def search(self, query):
        """Search for query in index"""
        words = self.process_words(query)
        results = []
        
        for word in words:
            if word in self.index:
                results.extend(self.index[word])
                
        # Sort results by timestamp
        results.sort(key=lambda x: (x["video"], x["start"]))
        self.last_search_results = results
        return results
