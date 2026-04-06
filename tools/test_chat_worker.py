#!/usr/bin/env python3
"""
Simple test for ChatProcessingWorker

Tests that the worker can process a conversation with Ollama.
Run with: python test_chat_worker.py
"""

import sys
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

import wx
from imagedescriber.workers_wx import ChatProcessingWorker, EVT_CHAT_UPDATE, EVT_CHAT_COMPLETE, EVT_CHAT_ERROR


class TestFrame(wx.Frame):
    """Simple frame to test chat worker"""
    
    def __init__(self):
        super().__init__(None, title="Chat Worker Test")
        self.response_chunks = []
        self.completed = False
        self.error = None
        
        # Bind events
        self.Bind(EVT_CHAT_UPDATE, self.on_chat_update)
        self.Bind(EVT_CHAT_COMPLETE, self.on_chat_complete)
        self.Bind(EVT_CHAT_ERROR, self.on_chat_error)
        
        # Create UI
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.output_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(self.output_text, 1, wx.EXPAND | wx.ALL, 10)
        
        start_btn = wx.Button(panel, label="Start Test")
        start_btn.Bind(wx.EVT_BUTTON, self.on_start_test)
        sizer.Add(start_btn, 0, wx.ALL, 10)
        
        panel.SetSizer(sizer)
        self.SetSize(600, 400)
        
    def on_start_test(self, event):
        """Start the chat test"""
        # Find a test image (use any jpg in testimages)
        test_images = list(Path('testimages').glob('*.jpg'))
        if not test_images:
            self.output_text.SetValue("ERROR: No test images found in testimages/")
            return
        
        image_path = str(test_images[0])
        self.output_text.SetValue(f"Testing with image: {image_path}\n\n")
        
        # Create simple conversation
        messages = [
            {
                'role': 'user',
                'content': 'What is in this image? Please be brief.'
            }
        ]
        
        self.output_text.AppendText("Starting conversation with Ollama...\n\n")
        
        # Create and start worker
        worker = ChatProcessingWorker(
            parent_window=self,
            image_path=image_path,
            provider='ollama',
            model='llava:7b',  # Default Ollama vision model
            messages=messages
        )
        worker.start()
        
        self.output_text.AppendText("Worker started. Waiting for response...\n\n")
    
    def on_chat_update(self, event):
        """Handle streaming response chunks"""
        chunk = event.message_chunk
        self.response_chunks.append(chunk)
        self.output_text.AppendText(chunk)
    
    def on_chat_complete(self, event):
        """Handle completed response"""
        self.completed = True
        self.output_text.AppendText("\n\n" + "="*60 + "\n")
        self.output_text.AppendText("COMPLETE!\n")
        self.output_text.AppendText(f"Provider: {event.metadata.get('provider')}\n")
        self.output_text.AppendText(f"Model: {event.metadata.get('model')}\n")
        self.output_text.AppendText(f"Full response length: {len(event.full_response)} chars\n")
        self.output_text.AppendText(f"Chunks received: {len(self.response_chunks)}\n")
    
    def on_chat_error(self, event):
        """Handle error"""
        self.error = event.error
        self.output_text.AppendText("\n\n" + "="*60 + "\n")
        self.output_text.AppendText(f"ERROR: {event.error}\n")


def main():
    """Run the test"""
    app = wx.App()
    frame = TestFrame()
    frame.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()
