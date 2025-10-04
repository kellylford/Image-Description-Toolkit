# GroundingDINO Model Download - How It Works

## 📦 Automatic Model Download

**You don't need to manually download the model!** GroundingDINO handles this automatically.

## 🔄 Download Process

### First Time Use
1. **Install package**: `pip install groundingdino-py torch torchvision`
2. **Select GroundingDINO provider** in ImageDescriber
3. **Process an image** - Click OK to start
4. **Automatic download begins**:
   - Model size: ~700MB
   - Source: Hugging Face Model Hub
   - Download location: `~/.cache/groundingdino/` (user's home directory)
   - Progress shown in console/terminal
   - Takes 2-10 minutes depending on internet speed

### After First Download
- **Model is cached** locally
- **No more downloads** needed
- **Instant startup** on subsequent uses
- Works **offline** once downloaded

## 📍 Model Cache Location

**Windows**: `C:\Users\<YourUsername>\.cache\groundingdino\`
**Linux/Mac**: `~/.cache/groundingdino/`

## 🎯 What You'll See

### During First Use:
```
Processing image...
Downloading GroundingDINO model...
Download progress: 0%...25%...50%...75%...100%
Model loaded successfully
Running detection...
```

### After First Use:
```
Processing image...
Model loaded from cache
Running detection...
```

## ❓ FAQ

**Q: Do I need to download the model manually?**  
A: No! It downloads automatically when you first use GroundingDINO.

**Q: Can I use it offline?**  
A: Yes, after the first download, everything works offline.

**Q: What if the download fails?**  
A: Check your internet connection and try again. The download will resume from where it left off.

**Q: Can I delete the model to save space?**  
A: Yes, delete the `~/.cache/groundingdino/` folder. It will re-download next time you use it.

**Q: Why is the first detection slow?**  
A: The model needs to download (~700MB). After that, detection is fast.

**Q: Do I need a GPU?**  
A: No, but GPU makes detection faster. CPU works fine, just slower.

## 🚀 Quick Start

1. **Install**:
   ```bash
   pip install groundingdino-py torch torchvision
   ```

2. **Use in ImageDescriber**:
   - Select image
   - Click "Process Image"
   - Choose "GroundingDINO" provider
   - Select detection mode (Automatic or Custom)
   - Click OK
   - **Wait for automatic download on first use** (2-10 minutes)
   - Enjoy unlimited object detection!

## 💡 Tips

- **First time**: Be patient during download
- **Use CPU-only PyTorch** if you don't have a GPU: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
- **Check console/terminal** for download progress
- **Restart ImageDescriber** if model download seems stuck
