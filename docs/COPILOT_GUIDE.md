# Copilot+ PC NPU Hardware Setup Guide# Copilot+ PC NPU Hardware Setup Guide



## Overview## Overview



**Copilot+ PC** refers to Windows PCs with dedicated **NPU (Neural Processing Unit)** chips that provide hardware-accelerated AI processing. This guide shows you how to use the Copilot+ PC provider for local, hardware-accelerated image description.**Copilot+ PC** refers to Windows PCs with dedicated **NPU (Neural Processing Unit)** chips that provide hardware-accelerated AI processing. This guide shows you how to use the Copilot+ PC provider for local, hardware-accelerated image description.



⚠️ **IMPORTANT:** This is about **Copilot+ PC NPU hardware**, NOT GitHub Copilot API service.⚠️ **IMPORTANT:** This is about **Copilot+ PC NPU hardware**, NOT GitHub Copilot API service. 

- **Copilot+ PC** = Special Windows PCs with NPU chips for local AI acceleration  - **Copilot+ PC** = Special Windows PCs with NPU chips for local AI acceleration

- **GitHub Copilot** = Cloud-based AI coding assistant (different product, not related)- **GitHub Copilot** = Cloud-based AI coding assistant (different product, not supported here)



## Why Use Copilot+ PC NPU?## Why Use Copilot+ PC NPU?



✅ **Advantages:**✅ **Advantages:**

- **Hardware acceleration** - Dedicated NPU chip for fast AI inference- **Hardware acceleration** - Dedicated NPU chip for fast AI inference

- **Local processing** - All data stays on your PC, complete privacy- **Local processing** - All data stays on your PC, complete privacy

- **No API costs** - Free once you have the hardware  - **No API costs** - Free once you have the hardware

- **Fast** - NPU-optimized inference- **Fast** - NPU-accelerated inference (though currently uses CPU fallback)

- **Offline capable** - Works without internet connection- **Offline capable** - Works without internet connection

- **Windows 11 optimized** - Native DirectML support- **Windows 11 optimized** - Native DirectML support



❌ **Considerations:**❌ **Considerations:**

- Requires specific Copilot+ PC hardware (~$999-2000)- Requires specific Copilot+ PC hardware (~$999-2000)

- Windows 11 only (version 22H2 or later)- Windows 11 only (version 22H2 or later)

- Limited model selection (Florence-2 primarily)- Limited model selection (Florence-2 primarily)

- Currently uses CPU fallback (full NPU acceleration coming soon)- Currently uses CPU fallback (full NPU support coming)

- Not as powerful as high-end GPUs or cloud APIs- Not as powerful as high-end GPUs or cloud APIs



## Requirements## Requirements



### Hardware Requirements### Hardware Requirements



**You MUST have a Copilot+ PC with one of these NPU chips:****You MUST have a Copilot+ PC with one of these NPU chips:**



**Qualcomm Snapdragon:****Qualcomm Snapdragon:**

- Snapdragon X Elite- Snapdragon X Elite

- Snapdragon X Plus- Snapdragon X Plus



**Intel:****Intel:**

- Core Ultra (Series 2) processors with NPU- Core Ultra (Series 2) processors with NPU

- Lunar Lake generation- Lunar Lake generation



**AMD:****AMD:**

- Ryzen AI processors with NPU  - Ryzen AI processors with NPU

- Strix Point generation- Strix Point generation



**Common Copilot+ PC Devices:****Common Copilot+ PC Devices:**

- Microsoft Surface Laptop (7th Edition, Snapdragon)- Microsoft Surface Laptop (7th Edition, Snapdragon)

- Microsoft Surface Pro (11th Edition, Snapdragon)- Microsoft Surface Pro (11th Edition, Snapdragon)

- Dell XPS 13 (9345, Snapdragon)- Dell XPS 13 (9345, Snapdragon)

- HP EliteBook Ultra G1q- HP EliteBook Ultra G1q

- Lenovo ThinkPad T14s Gen 6- Lenovo ThinkPad T14s Gen 6

- Samsung Galaxy Book4 Edge- Samsung Galaxy Book4 Edge

- ASUS Vivobook S 15- ASUS Vivobook S 15



### Software Requirements### Software Requirements



1. **Windows 11** (version 22H2 or later, preferably 24H2)1. **Windows 11** (version 22H2 or later, preferably 24H2)

   - Earlier versions may not have NPU support   - Earlier versions may not have NPU support

   - Check your version: `winver`   - Check your version: `winver`



2. **Python 3.9+** with required packages2. **Python 3.9+** with required packages



3. **DirectML Runtime:**3. **DirectML Runtime:**

   ```bash   ```bash

   pip install onnxruntime-directml   pip install onnxruntime-directml

   ```   ```



4. **AI Model Dependencies:**4. **AI Model Dependencies:**

   ```bash   ```bash

   pip install transformers torch einops timm pillow   pip install transformers torch einops timm pillow

   ```   ```



## Installation## Installation



### Step 1: Verify Copilot+ PC Hardware### Step 1: Verify Copilot+ PC Hardware



Check if you have a Copilot+ PC:Check if you have a Copilot+ PC:



**Option 1: Check Device Specifications****Option 1: Check Device Specifications**

1. Open Settings → System → About1. Open Settings → System → About

2. Look for "Copilot+ PC" badge or NPU mention2. Look for "Copilot+ PC" badge or NPU mention

3. Check processor model (Snapdragon X, Core Ultra Series 2, or Ryzen AI)3. Check processor model (Snapdragon X, Core Ultra Series 2, or Ryzen AI)



**Option 2: Check NPU in Task Manager****Option 2: Check NPU in Task Manager**

1. Open Task Manager (Ctrl+Shift+Esc)1. Open Task Manager (Ctrl+Shift+Esc)

2. Go to Performance tab2. Go to Performance tab

3. Look for "NPU" in the list (if you have one)3. Look for "NPU" in the list (if you have one)



**Option 3: Run Detection Script****Option 3: Run Detection Script**

```bash```bash

python -c "from models.copilot_npu import is_npu_available, get_npu_info; print(f'NPU: {get_npu_info()}')"python -c "from models.copilot_npu import is_npu_available, get_npu_info; print(f'NPU: {get_npu_info()}')"

``````



### Step 2: Install Dependencies### Step 2: Install Dependencies



```bash```bash

# Install DirectML support# Install DirectML support

pip install onnxruntime-directmlpip install onnxruntime-directml



# Install AI model libraries  # Install AI model libraries

pip install transformers torch einops timm pillowpip install transformers torch einops timm pillow



# Verify installation# Verify installation

python -c "import onnxruntime; print('DirectML ready!')"python -c "import onnxruntime; print('DirectML ready!')"

``````



### Step 3: Download Florence-2 Model### Step 3: Download Florence-2 Model



The Florence-2 model will download automatically on first use (~463MB), or you can pre-download:The Florence-2 model will download automatically on first use (~463MB), or you can pre-download:



```bash```bash

python models/download_florence2.pypython models/download_florence2.py

``````



### Step 4: Test the Provider### Step 4: Test the Provider



```bash```bash

# Test with a single image# Test with a single image

python scripts/workflow.py "test.jpg" --steps describe --provider copilot --model florence2-basepython scripts/workflow.py "test.jpg" --steps describe --provider copilot --model florence2-base

``````



## Using the Batch File## Using the Batch File



### Quick Start### Quick Start



1. **Verify you have a Copilot+ PC**1. **Verify you have a Copilot+ PC**

   - Check Settings → System → About for "Copilot+ PC" badge   - Check Settings → System → About for "Copilot+ PC" badge

   - Or verify you have Snapdragon X / Core Ultra / Ryzen AI processor   - Or verify you have Snapdragon X / Core Ultra / Ryzen AI processor



2. **Install dependencies**2. **Install dependencies**

   ```bash   ```bash

   pip install onnxruntime-directml transformers torch   pip install onnxruntime-directml transformers torch

   ```   ```



3. **Edit the batch file**3. **Edit the batch file**

   - Open `run_copilot.bat` in text editor   - Open `run_copilot.bat` in text editor

   - Set `IMAGE_PATH` to your image or folder   - Set `IMAGE_PATH` to your image or folder

   - Example:   - Example:

     ```batch     ```batch

     set IMAGE_PATH=C:\Users\YourName\Pictures\photo.jpg     set IMAGE_PATH=C:\Users\YourName\Pictures\photo.jpg

     ```     ```



4. **Run the batch file**4. **Run the batch file**

   - Double-click `run_copilot.bat`   - Double-click `run_copilot.bat`

   - OR run from command prompt: `run_copilot.bat`   - OR run from command prompt: `run_copilot.bat`



5. **Find your results**5. **Find your results**

   - Look for `wf_copilot_florence2-base_narrative_*` folder   - Look for `wf_copilot_florence2-base_narrative_*` folder

   - Open `descriptions/image_descriptions.txt` to see results   - Open `descriptions/image_descriptions.txt` to see results



### Configuration Options### Configuration Options



Edit these settings in the batch file:Edit these settings in the batch file:



```batch```batch

REM Path to image or folderREM Path to image or folder

set IMAGE_PATH=C:\path\to\your\imagesset IMAGE_PATH=C:\path\to\your\images



REM Steps to runREM Steps to run

set STEPS=describeset STEPS=describe

REM Or: set STEPS=describe,htmlREM Or: set STEPS=describe,html



REM Model to use (NPU-optimized models)REM Model to use (NPU-optimized models)

set MODEL=florence2-baseset MODEL=florence2-base

REM Options: florence2-base, florence2-largeREM Options: florence2-base, florence2-large



REM Prompt styleREM Prompt style

set PROMPT_STYLE=narrativeset PROMPT_STYLE=narrative

REM Options: narrative, detailed, concise, technicalREM Options: narrative, detailed, concise, technical

``````



## Command-Line Usage## Command-Line Usage



### Single Image### Single Image



```bash```bash

python scripts/workflow.py "C:\path\to\image.jpg" --provider copilot --model florence2-base --prompt-style narrativepython scripts/workflow.py "C:\path\to\image.jpg" --provider copilot --model florence2-base --prompt-style narrative

``````



### Folder of Images### Folder of Images



```bash```bash

python scripts/workflow.py "C:\path\to\images" --provider copilot --model florence2-base --prompt-style narrativepython workflow.py "C:\path\to\images" --provider copilot --model gpt-4o --prompt-style narrative

``````



### Full Workflow### Full Workflow



```bash```bash

python scripts/workflow.py "C:\path\to\images" --steps describe,html --provider copilot --model florence2-large --prompt-style detailedpython workflow.py "C:\path\to\images" --steps extract,describe,html,viewer --provider copilot --model gpt-4o --prompt-style narrative

``````



## Available Models## Available Models



| Model | Size | Quality | Speed | Best For || Model | Provider | Quality | Speed | Best For |

|-------|------|---------|-------|----------||-------|----------|---------|-------|----------|

| **florence2-base** | 230MB | Good | Fast | General image description (recommended) || **gpt-4o** | OpenAI | Excellent | Fast | General image description (recommended) |

| **florence2-large** | 463MB | Better | Medium | Detailed analysis || **claude-3.5-sonnet** | Anthropic | Excellent | Fast | Detailed analysis, creative tasks |

| **o1-preview** | OpenAI | Highest | Slower | Complex reasoning, detailed analysis |

### Model Recommendations| **o1-mini** | OpenAI | Very Good | Medium | Balanced quality/speed |



**For general use**: `florence2-base`### Model Recommendations

- Smaller model, faster processing

- Good quality descriptions**For general use**: `gpt-4o`

- Best balance for most users- Fast and accurate

- Great for most image descriptions

**For detailed descriptions**: `florence2-large`  - Best balance of quality and speed

- Larger model, more detailed

- Better at complex scenes**For detailed analysis**: `claude-3.5-sonnet`

- Slower but more thorough- Excellent at nuanced descriptions

- Good for artistic/creative analysis

## Prompt Styles- Very thorough



| Style | Best For | Description Focus |**For complex scenes**: `o1-preview`

|-------|----------|-------------------|- Best reasoning capabilities

| **narrative** | General use | Balanced storytelling |- Slowest but most thoughtful

| **detailed** | Maximum info | Comprehensive analysis |- Use for important/complex images

| **concise** | Quick summaries | Essential details only |

| **technical** | Photography | Technical aspects |**For speed**: `o1-mini`

- Faster than o1-preview

## Troubleshooting- Still very capable

- Good for batches

### "Copilot+ PC NPU not available"

## Prompt Styles

**Cause**: Don't have Copilot+ PC hardware or NPU not detected

| Style | Best For | Description Length |

**Solutions**:|-------|----------|-------------------|

1. Verify you have a Copilot+ PC (see Hardware Requirements above)| **narrative** | General use | Medium - balanced |

2. Update Windows 11 to latest version (24H2 recommended)| **detailed** | Maximum info | Long - comprehensive |

3. Check device drivers are up to date| **concise** | Quick summaries | Short - essentials only |

4. If you don't have Copilot+ PC hardware, use alternative providers:| **artistic** | Art analysis | Medium - composition focus |

   - `run_onnx.bat` for local CPU/GPU inference| **technical** | Photography | Medium - technical details |

   - `run_ollama.bat` for local Ollama models| **colorful** | Color analysis | Medium - palette focus |

   - `run_openai_gpt4o.bat` for cloud API

## Troubleshooting

### "DirectML not available"

### "GitHub CLI not installed"

**Cause**: DirectML runtime not installed

**Cause**: GitHub CLI not installed or not in PATH

**Solutions**:

```bash**Solutions**:

# Install DirectML1. Install from https://cli.github.com

pip install onnxruntime-directml2. After install, restart terminal/command prompt

3. Verify: `gh --version`

# Verify installation

python -c "import onnxruntime; print('OK')"### "Not authenticated with GitHub CLI"

```

**Cause**: Not logged in to GitHub

### "Missing dependencies"

**Solutions**:

**Cause**: Required Python packages not installed```bash

# Login

**Solutions**:gh auth login

```bash

# Install all requirements# Follow prompts to authenticate

pip install transformers torch einops timm pillow onnxruntime-directml

# Verify

# Or use requirements file if availablegh auth status

pip install -r requirements.txt```

```

### "No active GitHub Copilot subscription"

### "Florence-2 model not found"

**Cause**: Copilot subscription not active or expired

**Cause**: Model not downloaded yet

**Solutions**:

**Solutions**:1. Check subscription at https://github.com/settings/copilot

```bash2. Subscribe or renew at https://github.com/features/copilot

# Download model manually3. Wait a few minutes for activation

python models/download_florence2.py4. Re-authenticate: `gh auth refresh`



# Or let it download automatically on first use (will take a few minutes)### "Rate limits exceeded"

```

**Cause**: Too many requests in short time

### Performance is slow

**Solutions**:

**Current Status**: Full NPU acceleration is coming in a future update. Currently uses CPU fallback which is still reasonably fast (~2-3 seconds per image).1. Wait a few minutes before retrying

2. Process images in smaller batches

**Tips for better performance**:3. Contact GitHub support if limits seem wrong

- Use `florence2-base` instead of `florence2-large`  

- Close other applications### "Network connectivity issues"

- Process images in batches rather than one-by-one

- Ensure Windows power mode is set to "Best Performance"**Cause**: Internet connection problems



## Cost & Pricing**Solutions**:

1. Check internet connection

### Hardware Cost2. Check firewall isn't blocking GitHub

3. Try: `gh auth refresh`

Copilot+ PCs typically cost **$999-2000** depending on configuration:4. Use VPN if GitHub is blocked in your region



| Device | Price Range | NPU Type |### Authentication Expired

|--------|-------------|----------|

| Microsoft Surface Laptop | $999-1,499 | Snapdragon X |**Cause**: GitHub CLI authentication token expired

| Microsoft Surface Pro | $1,099-1,699 | Snapdragon X |

| Dell XPS 13 | $1,299-1,799 | Snapdragon X |**Solutions**:

| HP EliteBook Ultra | $1,499-2,299 | Snapdragon X |```bash

| Lenovo ThinkPad T14s | $1,399-1,999 | Snapdragon X |# Refresh authentication

gh auth refresh

### Operating Cost

# Or re-login

- **Free** - Once you have the hardware, no API feesgh auth logout

- **Electricity** - Minimal (NPU is very power efficient)gh auth login

- **Models** - Free (Florence-2 is open source)```



## Comparison with Other Providers## Cost & Pricing



### Copilot+ PC vs ONNX### GitHub Copilot Individual



| Feature | Copilot+ PC | ONNX |- **$10/month** or **$100/year**

|---------|-------------|------|- Includes:

| **Hardware** | Needs Copilot+ PC | Any PC |  - Code completion in IDE

| **Acceleration** | NPU (coming) | CPU/GPU |  - Chat in IDE and GitHub

| **Cost** | Free (after hardware) | Free |  - CLI assistance

| **Privacy** | Fully local | Fully local |  - **Access to image description via API**

| **Model support** | Florence-2 | Florence-2, YOLO, etc. |  - 30-day free trial



**Recommendation**: Use ONNX provider unless you specifically have Copilot+ PC hardware.### GitHub Copilot Business



### Copilot+ PC vs Ollama- **$19/user/month**

- Everything in Individual plus:

| Feature | Copilot+ PC | Ollama |  - Organization management

|---------|-------------|--------|  - Policy controls

| **Hardware** | Needs Copilot+ PC | Any PC (better with GPU) |  - Usage analytics

| **Quality** | Good | Excellent |

| **Models** | Florence-2 | LLaVA, Moondream, etc. |### GitHub Copilot Enterprise

| **Privacy** | Fully local | Fully local |

- **$39/user/month**

**Recommendation**: Use Ollama for better quality descriptions on standard hardware.- Everything in Business plus:

  - Chat in GitHub.com

### Copilot+ PC vs Cloud APIs  - Custom models

  - Fine-tuning

| Feature | Copilot+ PC | OpenAI/HuggingFace |  - Priority support

|---------|-------------|---------------------|

| **Cost** | Free (after hardware) | Pay-per-use |### Cost Comparison

| **Privacy** | Fully local | Cloud processing |

| **Quality** | Good | Excellent || Provider | Cost per Month | Cost per 1,000 Images |

| **Speed** | Fast | Very Fast ||----------|----------------|----------------------|

| **Offline** | Yes | No || **Copilot Individual** | **$10** | **$0** (included) |

| **Copilot Business** | **$19/user** | **$0** (included) |

**Recommendation**: Use Copilot+ PC if you have the hardware and need privacy/offline capability.| OpenAI gpt-4o (direct) | Pay-as-you-go | ~$10-20 |

| OpenAI gpt-4o-mini | Pay-as-you-go | ~$1-2 |

## Security & Privacy| HuggingFace Pro | $9 | $0 (unlimited) |

| Ollama/ONNX | $0 | $0 (unlimited) |

### What Stays Local

**Value Proposition**: If you already have Copilot for coding, image description is included at no extra cost!

When using Copilot+ PC provider:

- All images processed locally on your PC## Comparison with Other Providers

- No data sent to cloud or internet

- Models run entirely on device### Copilot vs OpenAI Direct

- Complete privacy and data security

| Feature | Copilot | OpenAI Direct |

### Best Practices|---------|---------|---------------|

| **Pricing** | Flat $10-19/month | Pay per API call |

**DO:**| **Usage limits** | Generous (fair use) | Unlimited (pay-as-you-go) |

- ✅ Use for sensitive/confidential images| **Setup** | GitHub CLI auth | API key management |

- ✅ Process offline without internet  | **Models** | GPT-4o, Claude, o1 | GPT models only |

- ✅ Keep Windows and drivers updated| **Best for** | Developers with Copilot | High-volume production |

- ✅ Verify you're using `--provider copilot` (not cloud providers)

### Copilot vs HuggingFace

**DON'T:**

- ❌ Confuse with GitHub Copilot (different product)| Feature | Copilot | HuggingFace |

- ❌ Share your Copilot+ PC credentials|---------|---------|-------------|

- ❌ Run untrusted models or code| **Free tier** | No (requires subscription) | Yes (~1K/month) |

| **Quality** | Excellent (GPT-4o) | Very Good (Florence-2) |

## Example Workflows| **Speed** | Very Fast | Medium (cold starts) |

| **Models** | Premium (GPT, Claude, o1) | Many open source |

### Basic Image Description

### Copilot vs Ollama/ONNX

```batch

REM Edit run_copilot.bat| Feature | Copilot | Ollama/ONNX |

set IMAGE_PATH=C:\Photos\Vacation|---------|---------|-------------|

set MODEL=florence2-base| **Cost** | $10-19/month | Free |

set STEPS=describe| **Privacy** | Cloud | Fully local |

| **Quality** | Excellent | Good-Very Good |

REM Run| **Resources** | None needed | Requires RAM/GPU |

run_copilot.bat| **Setup** | GitHub CLI | Local installation |

```

## Advanced Usage

### Detailed Analysis with HTML

### Using Different Models

```bash

python scripts/workflow.py "C:\Projects\Photos" ^Compare results from different models:

    --steps describe,html ^

    --provider copilot ^```batch

    --model florence2-large ^REM GPT-4o - Fast and accurate

    --prompt-style detailedset MODEL=gpt-4o

```run_copilot.bat



### Batch ProcessingREM Claude - Detailed and creative

set MODEL=claude-3.5-sonnet

```bashrun_copilot.bat

# Process all images in a folder

python scripts/workflow.py "C:\Photos\Event2024" ^REM o1 - Complex reasoning

    --provider copilot ^set MODEL=o1-preview

    --model florence2-base ^run_copilot.bat

    --prompt-style narrative```

```

### Batch Processing

## Current Status & Future Updates

For large image collections:

### Current Implementation (v2.0)

```batch

✅ Florence-2 model support  REM Use fastest model for batches

✅ DirectML detection  set MODEL=o1-mini

✅ CPU fallback (working)  set IMAGE_PATH=C:\Photos\LargeBatch

⚠️ NPU acceleration (in development)set STEPS=describe

```

### Coming Soon

### High-Quality Analysis

🔄 Full NPU hardware acceleration  

🔄 Additional NPU-optimized models  For important images:

🔄 Performance improvements  

🔄 Better DirectML integration```batch

REM Use best model and detailed prompt

### Performance Notesset MODEL=o1-preview

set PROMPT_STYLE=detailed

Currently the provider uses **CPU inference** as a fallback while full NPU acceleration is being implemented. Performance is still good (~2-3 seconds per image) but will improve significantly once NPU acceleration is fully enabled.set IMAGE_PATH=C:\ImportantImage.jpg

```

## Getting Help

### Integration with Development

- **Copilot+ PC Info**: https://www.microsoft.com/en-us/windows/copilot-plus-pcs

- **DirectML Docs**: https://learn.microsoft.com/en-us/windows/ai/directml/If you're using Copilot for coding, you can also:

- **IDT Documentation**: See `docs/` folder- Ask Copilot Chat to help write image processing scripts

- **Issue Reports**: Check GitHub repository issues- Use Copilot to generate batch files

- Get code suggestions for automation

## Summary

## Security & Privacy

Copilot+ PC NPU provider enables **local, hardware-accelerated** image description:

### What GitHub Sees

1. ✅ Verify you have Copilot+ PC hardware (Snapdragon X / Core Ultra / Ryzen AI)

2. ✅ Install Windows 11 (22H2 or later)When using Copilot for image description:

3. ✅ Install dependencies: `pip install onnxruntime-directml transformers torch`- Images are sent to GitHub/OpenAI/Anthropic servers

4. ✅ Edit `run_copilot.bat` with your image path- Processed in the cloud (not stored permanently)

5. ✅ Run batch file- Subject to GitHub's privacy policy

6. ✅ Find results in `wf_copilot_*` folder- Not used to train models (per Copilot terms)



Perfect for users who:### Best Practices

- 💻 Have Copilot+ PC hardware with NPU

- 🔒 Need complete privacy (local processing)**DO:**

- 🌐 Want offline capability- ✅ Review GitHub's privacy policy

- ⚡ Want hardware-accelerated AI- ✅ Use for appropriate content only

- 💰 Prefer one-time hardware cost over recurring API fees- ✅ Consider data sensitivity

- ✅ Keep GitHub CLI authenticated securely

If you don't have Copilot+ PC hardware, consider these alternatives:

- **ONNX provider** (`run_onnx.bat`) - Local CPU/GPU, any PC**DON'T:**

- **Ollama provider** (`run_ollama.bat`) - Better quality, local models- ❌ Process sensitive/confidential images

- **OpenAI provider** (`run_openai_gpt4o.bat`) - Best quality, cloud API- ❌ Share authentication tokens

- ❌ Process copyrighted images without rights

Happy describing! 🖼️- ❌ Violate GitHub's terms of service


### For Sensitive Data

If you need to process sensitive images:
- Use local providers (Ollama/ONNX) instead
- Or use OpenAI with data processing agreement
- Or ensure compliance with your organization's policies

## Example Workflows

### Developer Using Copilot

If you already have Copilot for coding:

```batch
REM Use included access for image description
set MODEL=gpt-4o
set IMAGE_PATH=C:\ProjectScreenshots
set PROMPT_STYLE=technical
```

No extra cost - already included!

### Professional Photography

```batch
REM High-quality analysis for client work
set MODEL=claude-3.5-sonnet
set IMAGE_PATH=C:\ClientPhotos\Photoshoot
set STEPS=extract,describe,html,viewer
set PROMPT_STYLE=detailed
```

### Quick Batch Processing

```batch
REM Fast processing of many images
set MODEL=o1-mini
set IMAGE_PATH=C:\Photos\EventPhotos
set STEPS=describe
set PROMPT_STYLE=concise
```

## Getting Help

- **GitHub Copilot Docs**: https://docs.github.com/en/copilot
- **GitHub CLI Docs**: https://cli.github.com/manual/
- **Copilot Support**: https://support.github.com/
- **IDT Documentation**: See `docs/` folder

## Summary

GitHub Copilot provides **premium AI models** for image description:

1. ✅ Subscribe to GitHub Copilot ($10-19/month)
   - 30-day free trial available
2. ✅ Install GitHub CLI: https://cli.github.com
3. ✅ Authenticate: `gh auth login`
4. ✅ Edit `run_copilot.bat` with your image path
5. ✅ Run batch file
6. ✅ Find results in `wf_copilot_*` folder

Perfect for users who:
- 💼 Already have Copilot for development (no extra cost!)
- 🎯 Want access to premium models (GPT-4o, Claude, o1)
- ⚡ Need fast, reliable cloud processing
- 🔄 Want to switch between multiple models
- 📊 Process moderate volumes regularly

If you're already paying for Copilot, this is effectively **free image description** included with your subscription!

Happy describing! 🖼️
