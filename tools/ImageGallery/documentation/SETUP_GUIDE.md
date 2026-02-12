# Image Gallery Setup & Deployment Guide

**How to deploy and host an IDT Image Gallery**

---

## For Gallery Creation

👉 **Want to create a new gallery?** See **[REPLICATION_GUIDE.md](REPLICATION_GUIDE.md)** for complete step-by-step instructions.

This document focuses on **deploying an existing gallery** to a web server.

---

## Quick Deploy

### Prerequisites
- Completed gallery directory containing:
  - `index.html`
  - `images/` (JPG files)
  - `descriptions/` (JSON files)

### Local Testing

```bash
cd /path/to/Image-Description-Toolkit/tools/ImageGallery/yourproject
python -m http.server 8082
```

Open browser to: `http://localhost:8082`

**Verify:**
- ✓ Gallery loads without errors
- ✓ All images display
- ✓ Descriptions load for all configurations
- ✓ Keyboard navigation works
- ✓ Alt text appears (check browser dev tools)

---

## Deployment Options

### Option 1: Simple Web Server

**Requirements:** Any HTTP server (Apache, Nginx, IIS, etc.)

**Steps:**
1. Copy entire gallery directory to web server
2. Ensure directory is publicly accessible
3. Done - no special configuration needed

**Files to copy:**
```
yourproject/
├── index.html
├── images/
│   └── *.jpg
└── descriptions/
    └── *.json
```

**Example (Linux/Apache):**
```bash
# Copy to web root
scp -r yourproject/ user@server:/var/www/html/gallery/

# Set permissions
ssh user@server "chmod -R 755 /var/www/html/gallery/"
```

**Example (Windows/IIS):**
```batch
# Copy to IIS wwwroot
xcopy /E /I yourproject C:\inetpub\wwwroot\gallery

# Gallery available at: http://yourserver/gallery/
```

---

### Option 2: GitHub Pages

**Best for:** Public galleries, demos, portfolios

**Steps:**

1. **Create repository or use existing**
   ```bash
   cd /path/to/Image-Description-Toolkit
   ```

2. **Create gh-pages branch**
   ```bash
   git checkout -b gh-pages
   ```

3. **Copy gallery to root** (or subdirectory)
   ```bash
   # Option A: Gallery in root
   cp -r tools/ImageGallery/yourproject/* .
   
   # Option B: Gallery in subdirectory
   mkdir -p gallery
   cp -r tools/ImageGallery/yourproject/* gallery/
   ```

4. **Commit and push**
   ```bash
   git add .
   git commit -m "Deploy gallery to GitHub Pages"
   git push origin gh-pages
   ```

5. **Enable GitHub Pages**
   - Go to repository Settings → Pages
   - Source: Deploy from branch
   - Branch: `gh-pages` → `/ (root)`
   - Save

6. **Access gallery**
   - URL: `https://username.github.io/repository/`
   - Or: `https://username.github.io/repository/gallery/` (if in subdirectory)

**Troubleshooting GitHub Pages:**
- If images don't load, check paths in `index.html` are relative
- Ensure `imagesBaseUrl: './images/'` (not absolute path)
- Check Actions tab for deployment errors

---

### Option 3: Netlify

**Best for:** Automatic deploys, custom domains, CDN

**Steps:**

1. **Create Netlify account** (free tier works)
   - Go to https://netlify.com
   - Sign up with GitHub/GitLab

2. **New site from Git**
   - Click "Add new site" → "Import existing project"
   - Connect to your repository
   - OR: Drag-and-drop gallery folder

3. **Configure build**
   - Build command: (leave empty - static site)
   - Publish directory: `tools/ImageGallery/yourproject/`
   - Or just upload the gallery directory

4. **Deploy**
   - Netlify auto-detects static site
   - Deploys in ~30 seconds
   - Provides URL: `random-name.netlify.app`

5. **Custom domain** (optional)
   - Settings → Domain management
   - Add custom domain
   - Update DNS records

**Netlify Features:**
- Automatic HTTPS
- CDN worldwide
- Preview deploys for branches
- Form handling (if added later)

---

### Option 4: Vercel

**Best for:** Similar to Netlify, different UI

**Steps:**

1. **Create Vercel account** (free tier)
   - https://vercel.com
   - Sign up with GitHub

2. **Import project**
   - Click "Add New" → "Project"
   - Import repository
   - OR: Use Vercel CLI

3. **Configure**
   - Framework Preset: Other
   - Root Directory: `tools/ImageGallery/yourproject/`
   - No build command needed

4. **Deploy**
   - Automatic deployment
   - URL: `project.vercel.app`

---

### Option 5: AWS S3 + CloudFront

**Best for:** Enterprise, high-traffic, full control

**Requirements:**
- AWS account
- AWS CLI installed

**Steps:**

1. **Create S3 bucket**
   ```bash
   aws s3 mb s3://your-gallery-bucket --region us-east-1
   ```

2. **Upload files**
   ```bash
   aws s3 sync yourproject/ s3://your-gallery-bucket/ \
     --acl public-read \
     --cache-control max-age=86400
   ```

3. **Enable static website hosting**
   ```bash
   aws s3 website s3://your-gallery-bucket/ \
     --index-document index.html
   ```

4. **Create CloudFront distribution** (optional, for CDN)
   - Go to CloudFront console
   - Create distribution
   - Origin: S3 bucket
   - Enable HTTPS

**URL:** `http://your-gallery-bucket.s3-website-us-east-1.amazonaws.com`

---

## Server Configuration

### MIME Types

Ensure your server sends correct MIME types:

| Extension | MIME Type |
|-----------|-----------|
| `.html` | `text/html` |
| `.json` | `application/json` |
| `.jpg` | `image/jpeg` |
| `.png` | `image/png` |
| `.css` | `text/css` |
| `.js` | `application/javascript` |

**Apache (.htaccess):**
```apache
AddType application/json .json
AddType image/jpeg .jpg .jpeg
AddType text/html .html
```

**Nginx (nginx.conf):**
```nginx
types {
    application/json json;
    image/jpeg jpg jpeg;
    text/html html;
}
```

### Caching Headers

**Recommended cache headers:**
```
index.html: no-cache (always check for updates)
*.json: max-age=3600 (1 hour)
*.jpg: max-age=86400 (24 hours)
```

**Apache:**
```apache
<Files "index.html">
    Header set Cache-Control "no-cache, must-revalidate"
</Files>
<FilesMatch "\.(json)$">
    Header set Cache-Control "max-age=3600"
</FilesMatch>
<FilesMatch "\.(jpg|jpeg|png|gif)$">
    Header set Cache-Control "max-age=86400"
</FilesMatch>
```

**Nginx:**
```nginx
location = /index.html {
    add_header Cache-Control "no-cache, must-revalidate";
}
location ~* \.(json)$ {
    add_header Cache-Control "max-age=3600";
}
location ~* \.(jpg|jpeg|png|gif)$ {
    add_header Cache-Control "max-age=86400";
}
```

### CORS Headers

**Only needed if gallery hosted on different domain than images:**

**Apache:**
```apache
Header set Access-Control-Allow-Origin "*"
```

**Nginx:**
```nginx
add_header Access-Control-Allow-Origin "*";
```

---

## Performance Optimization

### Image Optimization

**Before deployment:**
```bash
# Resize large images (max 1920px wide)
mogrify -resize "1920x>" images/*.jpg

# Compress (85% quality is good balance)
mogrify -quality 85 images/*.jpg

# Or use ImageMagick
for img in images/*.jpg; do
    convert "$img" -resize "1920x>" -quality 85 "$img"
done
```

**Recommended specs:**
- Max width: 1920px
- Quality: 85%
- Format: JPG (best compression for photos)
- Average size: 200KB - 1MB per image

### JSON Optimization

**Already optimized, but if needed:**
```bash
# Minify JSON (removes whitespace)
python -c "import json; d=json.load(open('file.json')); print(json.dumps(d, separators=(',',':')))" > file.min.json
```

**Trade-off:** Harder to debug, minimal size reduction (~10-15%)

### CDN Usage

**For high-traffic galleries:**

1. **Upload images to CDN** (Cloudflare, AWS CloudFront, etc.)
2. **Update imagesBaseUrl** in `index.html`:
   ```javascript
   const CONFIG = {
       imagesBaseUrl: 'https://cdn.example.com/gallery/images/',
       descriptionsBaseUrl: './descriptions/',
       workflowPattern: 'yourproject'
   };
   ```

**Benefits:**
- Faster load times worldwide
- Reduced origin server load
- Better for high traffic

---

## Custom Domain

### DNS Configuration

**For www.yourdomain.com:**

**A Record (GitHub Pages):**
```
Type: A
Name: @
Value: 185.199.108.153
```

**CNAME (Netlify/Vercel):**
```
Type: CNAME
Name: www
Value: your-site.netlify.app
```

### SSL/HTTPS

**GitHub Pages:** Automatic with custom domain (24 hours)

**Netlify/Vercel:** Automatic

**Custom server:** Use Let's Encrypt:
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d www.yourdomain.com
```

---

## Monitoring & Analytics

### Add Google Analytics

**Add to index.html before `</head>`:**
```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

### Server Logs

**Apache:**
```bash
tail -f /var/log/apache2/access.log | grep gallery
```

**Nginx:**
```bash
tail -f /var/log/nginx/access.log | grep gallery
```

---

## Maintenance

### Update Gallery Content

**Add new images:**
```bash
# 1. Add images to local images/ directory
cp new/*.jpg images/

# 2. Run workflows
c:/idt/idt.exe workflow images/ ...

# 3. Regenerate JSON
python generate_descriptions.py --descriptions-dir descriptions/ --output-dir descriptions/

# 4. Regenerate alt text
python generate_alt_text.py --jsondata-dir descriptions/

# 5. Redeploy (method depends on hosting)
```

**Remove configuration:**
```bash
# 1. Delete JSON file
rm descriptions/provider_model_prompt.json

# 2. Regenerate index
python generate_descriptions.py --descriptions-dir descriptions/ --output-dir descriptions/

# 3. Redeploy
```

### Backup

**Backup these files:**
```bash
# Create backup
tar -czf gallery-backup-$(date +%Y%m%d).tar.gz yourproject/

# Or with rsync
rsync -av yourproject/ /backup/gallery/
```

**What to backup:**
- All source images (originals)
- All JSON files
- index.html (if customized)
- Workflow output directories (optional, can regenerate)

---

## Troubleshooting

### Gallery loads but images broken

**Check:**
1. Images exist: `ls images/*.jpg`
2. Paths correct in index.html: `imagesBaseUrl: './images/'`
3. File permissions: `chmod 644 images/*.jpg`
4. MIME types configured (see Server Configuration)

### Descriptions don't load

**Check:**
1. JSON files exist: `ls descriptions/*.json`
2. Valid JSON: `python -m json.tool descriptions/file.json`
3. Paths correct: `descriptionsBaseUrl: './descriptions/'`
4. CORS not blocking (browser console)

### HTTPS mixed content warning

**Cause:** Gallery served over HTTPS but images/JSON over HTTP

**Fix:**
- Ensure all resources use HTTPS
- Or use relative paths (automatic)

### Slow loading

**Optimize:**
1. Compress images (see Performance Optimization)
2. Enable caching headers
3. Use CDN for images
4. Check server bandwidth

---

## Security Considerations

### Static Site Security

**Good news:** Static sites are inherently secure (no backend, no database)

**Still recommended:**
- Enable HTTPS (Let's Encrypt, Netlify/Vercel auto)
- Set security headers:
  ```
  X-Content-Type-Options: nosniff
  X-Frame-Options: SAMEORIGIN
  X-XSS-Protection: 1; mode=block
  ```
- Don't include sensitive data in JSON files
- Regular updates if adding dynamic features later

### Content Policy

**If allowing user uploads (future):**
- Scan images for inappropriate content
- Limit file sizes
- Validate file types
- Rate limiting on API if added

---

## Support

- **Architecture Questions:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Gallery Creation:** [REPLICATION_GUIDE.md](REPLICATION_GUIDE.md)
- **General Info:** [README.md](README.md)
- **Issues:** GitHub Issues

---

**Last Updated:** October 25, 2025
