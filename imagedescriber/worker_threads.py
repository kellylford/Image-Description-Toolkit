"""
Worker threads for Image Describer

This module contains all the background processing worker threads
for AI processing, video frame extraction, file conversion, and chat processing.
"""

import sys
import os
import json
import time
import base64
import tempfile
from pathlib import Path
from typing import List, Dict, Optional

from PyQt6.QtCore import QThread, pyqtSignal

# Import our refactored modules
from ai_providers import get_available_providers, _ollama_provider, _openai_provider, _huggingface_provider

# Optional imports for video processing
try:
    import cv2
except ImportError:
    cv2 = None


class ProcessingWorker(QThread):
    """Worker thread for AI processing"""
    progress_updated = pyqtSignal(str, str)  # file_path, message
    processing_complete = pyqtSignal(str, str, str, str, str, str)  # file_path, description, provider, model, prompt_style, custom_prompt
    processing_failed = pyqtSignal(str, str)  # file_path, error
    
    def __init__(self, file_path: str, provider: str, model: str, prompt_style: str, custom_prompt: str = ""):
        super().__init__()
        self.file_path = file_path
        self.provider = provider
        self.model = model
        self.prompt_style = prompt_style
        self.custom_prompt = custom_prompt
        
    def run(self):
        try:
            # Load prompt configuration
            config = self.load_prompt_config()
            
            # Get the actual prompt text
            if self.custom_prompt:
                prompt_text = self.custom_prompt
            else:
                # Check for both prompt_variations (actual config) and prompts (converted format)
                prompt_data = config.get("prompt_variations", config.get("prompts", {}))
                if self.prompt_style in prompt_data:
                    if isinstance(prompt_data[self.prompt_style], dict):
                        prompt_text = prompt_data[self.prompt_style].get("text", "Describe this image.")
                    else:
                        prompt_text = prompt_data[self.prompt_style]
                else:
                    prompt_text = "Describe this image."
            
            # Emit progress
            self.progress_updated.emit(self.file_path, f"Processing with {self.provider} {self.model}...")
            
            # Process the image with selected provider
            description = self.process_with_ai(self.file_path, prompt_text)
            
            # Emit success
            self.processing_complete.emit(
                self.file_path, description, self.provider, self.model, self.prompt_style, self.custom_prompt
            )
            
        except Exception as e:
            self.processing_failed.emit(self.file_path, str(e))
    
    def load_prompt_config(self) -> dict:
        """Load prompt configuration from the scripts directory"""
        try:
            # Try to find the config file
            if getattr(sys, 'frozen', False):
                config_path = Path(sys._MEIPASS) / "scripts" / "image_describer_config.json"
            else:
                config_path = Path(__file__).parent.parent / "scripts" / "image_describer_config.json"
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Convert the config format to what we expect
                    if "prompt_variations" in config:
                        # Convert prompt_variations to our expected format
                        prompts = {}
                        for key, value in config["prompt_variations"].items():
                            prompts[key] = {"text": value}
                        config["prompts"] = prompts
                    return config
        except Exception as e:
            print(f"Failed to load config: {e}")
        
        # Return default config
        return {
            "prompts": {
                "detailed": {"text": "Provide a detailed description of this image."},
                "brief": {"text": "Briefly describe this image."},
                "creative": {"text": "Describe this image in a creative, engaging way."}
            }
        }
    
    def process_with_ai(self, image_path: str, prompt: str) -> str:
        """Process image with selected AI provider"""
        # Get available providers
        providers = get_available_providers()
        
        if self.provider not in providers:
            raise Exception(f"Provider '{self.provider}' not available")
        
        provider = providers[self.provider]
        
        try:
            # Check if it's a HEIC file and convert if needed
            path_obj = Path(image_path)
            if path_obj.suffix.lower() in ['.heic', '.heif']:
                # Convert HEIC to JPEG first
                converted_path = self.convert_heic_to_jpeg(image_path)
                if converted_path:
                    image_path = converted_path
                else:
                    raise Exception("Failed to convert HEIC file")
            
            print(f"Processing {path_obj.name} with {self.provider} {self.model}")
            
            # Process with the selected provider
            description = provider.describe_image(image_path, prompt, self.model)
            
            return description
                
        except Exception as e:
            print(f"AI processing error: {str(e)}")
            raise Exception(f"AI processing failed: {str(e)}")
    
    def convert_heic_to_jpeg(self, heic_path: str) -> str:
        """Convert HEIC file to JPEG"""
        try:
            from PIL import Image
            import pillow_heif
            
            # Register HEIF opener
            pillow_heif.register_heif_opener()
            
            # Open and convert
            image = Image.open(heic_path)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Create temporary JPEG file
            temp_dir = Path(tempfile.gettempdir())
            temp_path = temp_dir / f"temp_{int(time.time())}_{Path(heic_path).stem}.jpg"
            
            # Resize if too large
            max_dimension = 2048
            if max(image.size) > max_dimension:
                image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            
            image.save(temp_path, 'JPEG', quality=85, optimize=True)
            return str(temp_path)
            
        except Exception as e:
            print(f"HEIC conversion error: {e}")
            return None


class WorkflowProcessWorker(QThread):
    """Worker thread for running the proven workflow system"""
    progress_updated = pyqtSignal(str)
    workflow_complete = pyqtSignal(str, str)  # input_dir, output_dir
    workflow_failed = pyqtSignal(str)  # error
    
    def __init__(self, cmd, input_dir, output_dir):
        super().__init__()
        self.cmd = cmd
        self.input_dir = str(input_dir)
        self.output_dir = str(output_dir)
    
    def run(self):
        """Run the workflow command and monitor progress"""
        try:
            import subprocess
            
            # Start the workflow process
            self.progress_updated.emit("Starting workflow process...")
            
            process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True
            )
            
            # Monitor output for progress
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    if line:
                        # Emit progress updates
                        self.progress_updated.emit(f"Workflow: {line}")
            
            # Check if process completed successfully
            return_code = process.poll()
            if return_code == 0:
                self.workflow_complete.emit(self.input_dir, self.output_dir)
            else:
                self.workflow_failed.emit(f"Workflow process failed with code {return_code}")
                
        except Exception as e:
            self.workflow_failed.emit(f"Error running workflow: {str(e)}")


class ConversionWorker(QThread):
    """Worker thread for file conversions"""
    progress_updated = pyqtSignal(str, str)  # file_path, message
    conversion_complete = pyqtSignal(str, list)  # original_path, converted_paths
    conversion_failed = pyqtSignal(str, str)  # original_path, error
    
    def __init__(self, file_path: str, conversion_type: str):
        super().__init__()
        self.file_path = file_path
        self.conversion_type = conversion_type  # "heic" or "video"
        
    def run(self):
        try:
            if self.conversion_type == "heic":
                self.convert_heic()
            elif self.conversion_type == "video":
                self.extract_video_frames()
        except Exception as e:
            self.conversion_failed.emit(self.file_path, str(e))
    
    def convert_heic(self):
        """Convert HEIC image to JPEG"""
        try:
            from PIL import Image
            import pillow_heif
            
            self.progress_updated.emit(self.file_path, "Converting to JPG...")
            
            # Register HEIF opener
            pillow_heif.register_heif_opener()
            
            # Open and convert
            image = Image.open(self.file_path)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Save as JPEG
            output_path = str(Path(self.file_path).with_suffix('.jpg'))
            image.save(output_path, 'JPEG', quality=95)
            
            self.conversion_complete.emit(self.file_path, [output_path])
            
        except Exception as e:
            self.conversion_failed.emit(self.file_path, f"HEIC conversion failed: {str(e)}")
    
    def extract_video_frames(self):
        """Extract frames from video"""
        try:
            if not cv2:
                raise Exception("OpenCV (cv2) not available. Please install opencv-python.")
            
            self.progress_updated.emit(self.file_path, "Extracting video frames...")
            
            cap = cv2.VideoCapture(self.file_path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Extract frames at 1 frame per second
            extracted_paths = []
            frame_interval = max(1, int(fps))
            
            video_stem = Path(self.file_path).stem
            # Create frames in imagedescriptiontoolkit folder
            video_parent = Path(self.file_path).parent
            toolkit_dir = video_parent / "imagedescriptiontoolkit"
            video_dir = toolkit_dir / f"{video_stem}_frames"
            video_dir.mkdir(parents=True, exist_ok=True)
            
            frame_num = 0
            while frame_num < frame_count:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if ret:
                    frame_filename = f"{video_stem}_frame_{frame_num // frame_interval:04d}.jpg"
                    frame_path = video_dir / frame_filename
                    cv2.imwrite(str(frame_path), frame)
                    extracted_paths.append(str(frame_path))
                
                frame_num += frame_interval
            
            cap.release()
            self.conversion_complete.emit(self.file_path, extracted_paths)
            
        except Exception as e:
            self.conversion_failed.emit(self.file_path, f"Video frame extraction failed: {str(e)}")


class VideoProcessingWorker(QThread):
    """Worker thread for video processing with frame extraction and description"""
    
    progress_updated = pyqtSignal(str, str)  # message, details
    extraction_complete = pyqtSignal(str, list, dict)  # video_path, extracted_frames, processing_config  
    processing_failed = pyqtSignal(str, str)  # file_path, error_message
    
    def __init__(self, video_path: str, extraction_config: dict, processing_config: dict):
        super().__init__()
        self.video_path = video_path
        self.extraction_config = extraction_config
        self.processing_config = processing_config
    
    def run(self):
        """Extract frames from video and optionally process them"""
        try:
            self.progress_updated.emit("Extracting frames from video...", f"Processing: {Path(self.video_path).name}")
            
            # Extract frames based on configuration
            extracted_frames = self.extract_frames()
            
            if extracted_frames:
                self.progress_updated.emit(f"Extracted {len(extracted_frames)} frames", "Frame extraction complete")
                self.extraction_complete.emit(self.video_path, extracted_frames, self.processing_config)
            else:
                self.processing_failed.emit(self.video_path, "No frames were extracted from video")
                
        except Exception as e:
            self.processing_failed.emit(self.video_path, f"Video processing failed: {str(e)}")
    
    def extract_frames(self) -> list:
        """Extract frames from video based on configuration"""
        try:
            if not cv2:
                raise Exception("OpenCV (cv2) not available. Please install opencv-python.")
            
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                raise Exception("Could not open video file")
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Create output directory in imagedescriptiontoolkit folder
            video_path = Path(self.video_path)
            toolkit_dir = video_path.parent / "imagedescriptiontoolkit"
            video_dir = toolkit_dir / f"{video_path.stem}_frames"
            video_dir.mkdir(parents=True, exist_ok=True)
            
            extracted_paths = []
            
            # Extract based on mode
            if self.extraction_config["extraction_mode"] == "time_interval":
                extracted_paths = self.extract_by_time_interval(cap, fps, video_dir)
            else:
                extracted_paths = self.extract_by_scene_detection(cap, fps, video_dir)
            
            cap.release()
            return extracted_paths
            
        except Exception as e:
            raise Exception(f"Frame extraction failed: {str(e)}")
    
    def extract_by_time_interval(self, cap, fps: float, output_dir: Path) -> list:
        """Extract frames at regular time intervals"""
        interval_seconds = self.extraction_config["time_interval_seconds"]
        start_time = self.extraction_config["start_time_seconds"]
        end_time = self.extraction_config.get("end_time_seconds")
        max_frames = self.extraction_config.get("max_frames_per_video")
        
        frame_interval = int(fps * interval_seconds)
        start_frame = int(fps * start_time)
        
        extracted_paths = []
        frame_num = start_frame
        extract_count = 0
        
        video_stem = Path(self.video_path).stem
        
        while True:
            if max_frames and extract_count >= max_frames:
                break
                
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Check end time limit
            current_time = frame_num / fps
            if end_time and current_time > end_time:
                break
            
            # Save frame
            frame_filename = f"{video_stem}_frame_{extract_count:04d}.jpg"
            frame_path = output_dir / frame_filename
            cv2.imwrite(str(frame_path), frame)
            extracted_paths.append(str(frame_path))
            
            extract_count += 1
            frame_num += frame_interval
        
        return extracted_paths
    
    def extract_by_scene_detection(self, cap, fps: float, output_dir: Path) -> list:
        """Extract frames based on scene changes"""
        threshold = self.extraction_config["scene_change_threshold"] / 100.0
        min_duration = self.extraction_config["min_scene_duration_seconds"]
        max_frames = self.extraction_config.get("max_frames_per_video")
        
        extracted_paths = []
        prev_frame = None
        last_extract_frame = -1
        min_frame_gap = int(fps * min_duration)
        frame_num = 0
        extract_count = 0
        
        video_stem = Path(self.video_path).stem
        
        while True:
            if max_frames and extract_count >= max_frames:
                break
                
            ret, frame = cap.read()
            if not ret:
                break
            
            # Calculate difference from previous frame
            if prev_frame is not None:
                # Convert to grayscale for comparison
                gray_current = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray_prev = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                
                # Calculate mean squared difference
                diff = cv2.absdiff(gray_current, gray_prev)
                mean_diff = diff.mean() / 255.0
                
                # Check if scene change detected and minimum duration passed
                if (mean_diff > threshold and 
                    frame_num - last_extract_frame >= min_frame_gap):
                    
                    # Save frame
                    frame_filename = f"{video_stem}_scene_{extract_count:04d}.jpg"
                    frame_path = output_dir / frame_filename
                    cv2.imwrite(str(frame_path), frame)
                    extracted_paths.append(str(frame_path))
                    
                    last_extract_frame = frame_num
                    extract_count += 1
            
            prev_frame = frame.copy()
            frame_num += 1
        
        return extracted_paths


class ChatProcessingWorker(QThread):
    """Worker thread for processing chat messages with AI"""
    chat_response = pyqtSignal(str, str)  # chat_id, response
    chat_failed = pyqtSignal(str, str)    # chat_id, error
    
    def __init__(self, chat_session: dict, message: str):
        super().__init__()
        self.chat_session = chat_session
        self.message = message
        self._stop_requested = False
        
    def stop(self):
        """Request the worker to stop"""
        self._stop_requested = True
        
    def run(self):
        try:
            if self._stop_requested:
                return
                
            response = self.process_chat_with_ai(self.chat_session, self.message)
            
            if not self._stop_requested:
                self.chat_response.emit(self.chat_session['id'], response)
        except Exception as e:
            if not self._stop_requested:
                self.chat_failed.emit(self.chat_session['id'], str(e))
    
    def process_chat_with_ai(self, chat_session: dict, message: str) -> str:
        """Process chat message with AI provider"""
        provider = chat_session['provider']
        model = chat_session['model']
        
        # Build conversation context from chat history
        conversation_context = self.build_conversation_context(chat_session, message)
        
        if provider == "ollama":
            return self.process_with_ollama_chat(model, conversation_context)
        elif provider == "openai":
            return self.process_with_openai_chat(model, chat_session, message)
        elif provider == "huggingface":
            return self.process_with_huggingface_chat(model, conversation_context)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def build_conversation_context(self, chat_session: dict, current_message: str) -> str:
        """Build conversation context from chat history"""
        conversation = chat_session.get('conversation', [])
        
        # Get recent conversation history (limit to last 10 messages)
        recent_messages = conversation[-10:] if len(conversation) > 10 else conversation
        
        # Build context string
        context_parts = []
        
        # Add conversation history
        if recent_messages:
            context_parts.append("Previous conversation:")
            for msg in recent_messages:
                role = "User" if msg['type'] == 'user' else "Assistant"
                context_parts.append(f"{role}: {msg['content']}")
            context_parts.append("")
        
        # Add current message
        context_parts.append(f"User: {current_message}")
        context_parts.append("Assistant:")
        
        return "\n".join(context_parts)
    
    def process_with_ollama_chat(self, model: str, context: str) -> str:
        """Process chat with Ollama"""
        try:
            import ollama
            
            response = ollama.generate(
                model=model,
                prompt=context
            )
            
            if self._stop_requested:
                return "Processing stopped"
            
            if hasattr(response, 'response'):
                return response.response
            elif isinstance(response, dict) and 'response' in response:
                return response['response']
            else:
                return str(response)
                
        except Exception as e:
            raise Exception(f"Ollama processing failed: {str(e)}")
    
    def process_with_openai_chat(self, model: str, chat_session: dict, current_message: str) -> str:
        """Process chat with OpenAI"""
        try:
            if not _openai_provider.is_available():
                raise Exception("OpenAI is not available or API key not found")
            
            if self._stop_requested:
                return "Processing stopped"
            
            # Build OpenAI messages format
            messages = self.build_openai_messages(chat_session, current_message)
            
            # Use the provider's internal client
            import openai
            client = openai.OpenAI(api_key=_openai_provider.api_key)
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1000
            )
            
            if response.choices and response.choices[0].message:
                return response.choices[0].message.content
            else:
                raise Exception("Empty response from OpenAI")
            
        except Exception as e:
            raise Exception(f"OpenAI processing failed: {str(e)}")
    
    def build_openai_messages(self, chat_session: dict, current_message: str) -> list:
        """Build OpenAI-format messages array"""
        conversation = chat_session.get('conversation', [])
        
        # Get recent conversation history (limit to last 15 messages)
        recent_messages = conversation[-15:] if len(conversation) > 15 else conversation
        
        # Build OpenAI messages format
        messages = []
        
        # Add system message if this is the start of conversation
        if not recent_messages:
            messages.append({
                "role": "system",
                "content": "You are a helpful AI assistant. Please provide clear, accurate, and helpful responses to the user's questions."
            })
        
        # Add conversation history
        for msg in recent_messages:
            if msg['type'] == 'user':
                messages.append({"role": "user", "content": msg['content']})
            else:
                messages.append({"role": "assistant", "content": msg['content']})
        
        # Add current message
        messages.append({"role": "user", "content": current_message})
        
        return messages
    
    def process_with_huggingface_chat(self, model: str, context: str) -> str:
        """Process chat with HuggingFace"""
        try:
            if not _huggingface_provider.is_available():
                raise Exception("Hugging Face transformers is not available")
            
            if self._stop_requested:
                return "Processing stopped"
            
            # For now, return an informational message
            # In the future, this could be enhanced to use text generation models
            return f"Hugging Face chat mode not fully implemented yet. The selected model '{model}' is primarily designed for image processing. For text chat, consider using Ollama or OpenAI providers."
            
        except Exception as e:
            raise Exception(f"Hugging Face processing failed: {str(e)}")