@echo off
REM Commit chat feature redesign changes

echo Staging files...
git add imagedescriber/chat_window_wx.py
git add imagedescriber/imagedescriber_wx.py  
git add imagedescriber/workers_wx.py
git add imagedescriber/data_models.py
git add docs/worktracking/2026-01-20-chat-with-ai-redesign.md

echo.
echo Current status:
git status

echo.
echo Creating commit...
git commit -m "feat: Redesign chat as 'Chat with AI' (general chat, no image required)" -m "- Remove image requirement from on_chat() entry point" -m "- Make ChatWindow accept Optional[ImageItem] for text-only mode" -m "- Update ChatProcessingWorker to skip image when None (all providers)" -m "- Update data models to support image_path = None in sessions" -m "- Add window title logic for text-only vs image chats" -m "- Update menu labels/comments to 'Chat with AI'" -m "" -m "BREAKING: None (backward compatible)" -m "TODO: Integrate chat sessions into image list UI" -m "TODO: Show messages in description list when chat selected"

echo.
echo Commit complete!
echo.
pause
