import requests
import json
from typing import Optional
import time

class OllamaTranslator:
    def __init__(self, model: str = "gemma:2b"):
        self.base_url = "http://localhost:11434/api/generate"
        self.model = model
        self.timeout = 30  # 设置超时时间
        
    def translate(self, text: str, target_lang: str = "Chinese") -> Optional[str]:
        """
        Translate text using Ollama API
        Args:
            text: Text to translate
            target_lang: Target language (default: Chinese)
        Returns:
            Translated text or None if translation fails
        """
        if not text.strip():
            return None
            
        try:
            prompt = f"""Please translate the following English text to {target_lang}. 
Only provide the direct translation without any explanations or additional text:
"{text.strip()}"
"""
            
            data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # 降低随机性
                    "top_p": 0.9
                }
            }
            
            response = requests.post(
                self.base_url, 
                json=data, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                translation = result.get('response', '').strip()
                
                # 清理翻译结果
                translation = translation.replace('"', '').strip()
                if translation.lower().startswith('translation:'):
                    translation = translation[11:].strip()
                    
                return translation if translation else None
            else:
                print(f"Translation API error: Status {response.status_code}")
                return None
                
        except requests.Timeout:
            print("Translation timeout")
            return None
        except requests.RequestException as e:
            print(f"Translation request error: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected translation error: {str(e)}")
            return None
            
    def is_available(self) -> bool:
        """Check if Ollama service is available"""
        try:
            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
