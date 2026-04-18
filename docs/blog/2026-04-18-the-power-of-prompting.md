# The Power of Prompting

*[BYLINE PLACEHOLDER — options: "By Kelly Ford", "By [AI Author Name]", or note AI-assisted authorship here]*

---

Since writing about IDT 4.0 Beta 1 in February, things have moved quickly. A new beta is out, new models have been added, the prompt library has grown, and I found a perfect real-world dataset to put the whole system through its paces: NASA's Image of the Day collection. This post is about what I learned, what the data showed, and why the right prompt can make all the difference.

---

## What Has Changed Since Beta 1

The February post introduced IDT 4.0's two main tools — the `ImageDescriber` GUI and the `idt` command line — along with support for Ollama, OpenAI, and Claude models. Since then, 4.0.0Beta3 has shipped with a number of additions worth knowing about:

- **`idt describe`** — a friendlier alias for `idt workflow`. Same command, easier to remember.
- **`idt redescribe`** — re-runs AI description on a set of images you have already processed, skipping the video extraction and conversion steps. Useful for quickly testing a new model or prompt on the same images without starting from scratch.
- **`idt manage-models`** — install, remove, and list Ollama models directly from the IDT without leaving your terminal.
- **`idt guideme` now accepts URLs** — in addition to a folder path, you can paste a web page URL at the image folder prompt and IDT will download images from that page and continue the workflow automatically.
- **Downloaded images organized by source** — images downloaded from a URL are now placed in a subfolder named after the domain and page title, so you always know where a set of images came from.
- **Expanded prompt recognition** — accessibility, comparison, mood, and functional prompt styles are now correctly identified across all analysis tools.

The full list of prompts has also grown. IDT now ships with eleven built-in prompts, each designed to draw out a different aspect of an image:

1. **Narrative** — a straightforward scene description, grounding you in what is present
2. **Detailed** — everything Narrative gives you, plus more technical depth
3. **Concise** — a brief, single-sentence summary
4. **Colorful** — emphasis on color, tone, and visual atmosphere
5. **Technical** — image quality, composition, exposure, and photographic characteristics
6. **Artistic** — style, mood, and creative interpretation
7. **Simple** — plain-language description suitable for a general audience
8. **Accessibility** — structured for screen readers and assistive technology
9. **Comparison** — designed for comparing two versions of the same image
10. **Mood** — emotional tone and atmosphere
11. **Functional** — what the image is for, not just what it shows

You can edit any of these or add your own through the Tools menu in ImageDescriber or by editing `prompts.json` directly.

---

## When You Download Images, IDT Now Captures Alt Text Too

One feature that did not get much attention in the Beta 1 post: when IDT downloads images from a web page, it also captures the alt text that is already on those images. That data is stored alongside your downloaded images and is available for comparison when you run the analysis tools.

This turned out to be far more interesting than I expected once I chose my test dataset.

---

## The NASA Opportunity

On April 7, 2026, NASA launched the Artemis II mission — the first crewed Moon trip since the Apollo program. NASA's Image of the Day page had been building up to this for weeks with stunning photographs: the crew in training, the rocket being prepared, and then the mission itself: Earthrise from lunar orbit, the Milky Way seen from deep space, the crew capsule from a window looking back at a shrunken planet.

This was a natural fit for IDT. I used `idt workflow` to download 64 images directly from the NASA Image of the Day page and ran all eleven built-in prompts across multiple AI models. The dataset includes descriptions from Claude Haiku 4.5, Claude Sonnet 4.6, Ollama Gemma4 31b (cloud), Ollama Kimi-K2.5 (cloud), Ollama Moondream, Ollama Qwen3-VL 235b (cloud), GPT-4.1 Mini, and GPT-4.1 Nano — over 700 descriptions in total.

And because IDT captured the alt text from NASA's page during download, I had a built-in comparison baseline.

---

## NASA Does Alt Text Well

Before getting into what IDT produced, it is worth saying clearly: NASA already writes excellent alt text. This is not a critique. NASA's image descriptions are thoughtful, specific, and informative. They name people, identify locations, and include context that no AI can supply from an image alone.

Here is an example. The image is a photograph taken from inside the Orion spacecraft. An astronaut is silhouetted against a window, looking out at Earth floating in space.

**NASA's alt text:**
> NASA astronaut Reid Wiseman looks out of the Orion spacecraft's rectangular window at Earth. He is barely visible in the dimly lit cabin, but Earth is bright. The entirety of Earth cannot be seen; in this view, Earth's round shape is cut off. Earth itself looks like a bright blue ball with swirling white clouds all over it; at center is a brown and green landmass.

That is excellent alt text. It names the astronaut. It identifies the spacecraft. It describes what Earth looks like from that vantage point. An AI looking at the same image cannot do any of that.

Here is what Kimi-K2.5 produced for the same image with the Narrative prompt:

> The image shows the interior of a spacecraft. The left side of the frame is filled with solid black darkness. Within this darkness, the silhouette of a human head appears in left profile, positioned approximately one-third from the left edge. The person's forehead, nose, closed mouth, and chin are outlined by light entering from the right.

Good, accurate description of what is visible — but no name, no mission context, no spacecraft identification. The AI sees the scene; NASA's writer knows the story.

---

## Prompts Change What You Get

Here is where the Power of Prompting shows up. Take a different image: Earthset from the far side of the Moon — the Earth appearing as a crescent above the cratered lunar horizon.

**NASA's alt text:**
> Earthset From the Lunar Far Side

That is the title, essentially. It tells you what it is but nothing about what you are seeing.

Now watch what happens as IDT works through different prompts, using Kimi-K2.5 (cloud):

**Narrative prompt:**
> The image presents a view of space dominated by the curved bulk of the Moon occupying the lower two-thirds of the frame. The scene contains no human figures, clothing, or artificial objects.

A starting point, but sparse.

**Colorful prompt:**
> This image depicts Earth rising above the Moon's horizon, with the planet's partially illuminated disk displaying **navy** oceans and **ivory** cloud formations against the **charcoal** blackness of space, while the foreground shows the Moon's cratered, uneven surface in shades of **slate** and **charcoal** gray. The lighting originates from the right side of the frame, producing hard-edged shadows across the lunar terrain.

Now we have color, light direction, texture. A vivid picture is forming.

**Accessibility prompt (Gemma4 31b):**
> A wide-angle shot of Earth rising over the horizon of the Moon against a black void.

Concise. Functional. Ready for a screen reader.

**AI Alt Text prompt (Kimi-K2.5, 25/50/100 words):**

> *25 words:* A stunning view of Earth rising over the Moon's cratered horizon, with the blue planet visible as a crescent against the vast blackness of space.

> *50 words:* A dramatic photograph showing the heavily cratered surface of the Moon in the foreground, with planet Earth visible as a blue and white crescent rising above the lunar horizon. The stark contrast between the gray moonscape and vibrant Earth suspended in black void of space creates a breathtaking cosmic perspective.

> *100 words:* This awe-inspiring image captures the iconic "Earthrise" phenomenon, showing the rugged, crater-covered surface of the Moon dominating the foreground while the delicate blue and white crescent of Earth emerges above the lunar horizon. The photograph reveals the stark beauty of the moonscape's gray, pockmarked terrain, illuminated by sunlight, contrasting dramatically with the vibrant colors of our home planet suspended in the infinite blackness. This perspective, captured from lunar orbit, emphasizes the profound isolation of the Moon and the fragility of Earth, offering a humbling reminder of our planet's place in the cosmos.

Each prompt gives you something different. None replaces NASA's contextual knowledge. But together they build a much fuller picture than any single description could.

---

## Introducing the AI Alt Text Prompt (Experimental)

The eleven standard prompts are all about understanding an image in depth. But there is also a practical question: can AI generate usable alt text for web images?

I added a twelfth experimental prompt — `aialttext` — that asks the AI for three versions of website alt text at different lengths: 25 words, 50 words, and 100 words. The goal is to give whoever is publishing the image options to choose from depending on the context.

The results above show what Kimi-K2.5 produced for the Earthset image. Let me give one more example. Here is NASA's alt text for the Saturn image taken by the James Webb Space Telescope:

**NASA's alt text:**
> NASA Webb, Hubble Share Most Comprehensive View of Saturn to Date

**Kimi AI Alt Text — 25 words:**
> Infrared image of Saturn captured by Webb Telescope on November 29, 2024, showing bright glowing blue rings and three labeled moons: Janus, Dione, and Enceladus.

This is interesting. The AI correctly read the labels on the image — Webb infrared, the date, the moon names. NASA's alt text is a headline; the AI's version is descriptive. Neither is wrong. They serve different purposes.

But here is the point that matters most: **you should not publish AI-generated alt text without reviewing it first.**

Unless you would automatically publish an AI-generated image on your website, you should not publish AI-generated alt text without review. Alt text is not decoration. It is the description that a person using a screen reader gets instead of seeing the image. Getting it wrong — or getting it confidently wrong, as AI sometimes does — causes real harm.

The AI cannot name people it has not been trained on. It may misread or invent labels. It may describe what looks plausible instead of what is actually there. Domain knowledge matters enormously. NASA's writers know the astronauts by name, the spacecraft by model, the mission by number. AI does not.

Used as a starting point for a human editor, the AI alt text prompt can save time and surface details a writer might miss. Used as a replacement for human review, it introduces exactly the kind of accessibility failure that ruins the experience for the people who most need it.

---

## Follow-Up Questions and Chat

One more IDT capability worth highlighting, now that the NASA dataset illustrates it well. After any image has been described, IDT lets you ask follow-up questions — press F in the ImageDescriber GUI or use the CLI. You can switch to a different model for the follow-up if you want.

For example: after running the Narrative prompt on the Artemis II launch photograph, you might ask: *"How does this compare to a Saturn V launch in terms of visual scale?"* Or for the supernova remnant: *"What telescope instruments were used to capture the different wavelengths in this image?"* The AI does not always get these right, but the capability is there, and for scientific images especially, the follow-up question is often where the real value is.

IDT also has a freestanding chat mode (press C in ImageDescriber) for model-to-model conversation without any image attached.

---

## Data Completeness

In a few instances, data for a prompt and model are not complete. In the case of Moondream, some prompts — such as Technical — failed to return any response on multiple tries.

In the case of Claude, not all prompts were run due to the amount of data already gathered and the costs associated with Claude models. In addition, due to image sizing and the way IDT currently works, some images exceeded the size limit for Claude and were not described.

The AI Alt Text prompt was only run on Kimi-K2.5 and Gemma4 models for this dataset.

---

## The Data

You can obtain the full set of image descriptions and prompts used for this set of NASA images at the following locations.

- [CSV of all descriptions]([LINK PLACEHOLDER])
- [Markdown file of all prompts]([LINK PLACEHOLDER])

---

## Try It Yourself

IDT 4.0.0Beta3 is available for Windows and macOS (build from source). The Windows installer is at [theideaplace.net/projects](https://www.theideaplace.net/projects). Full documentation is in the [User Guide on GitHub](https://github.com/kellylford/Image-Description-Toolkit/blob/main/docs/USER_GUIDE_COMPLETE.md).

If you want to replicate the NASA experiment, try:

```
idt workflow https://www.nasa.gov/image-of-the-day/
```

That will download the current Image of the Day collection and describe the images using your configured model and prompt. From there, `idt combinedescriptions` will compile everything into a CSV you can explore in Excel or any spreadsheet tool.

Questions, issues, and pull requests are welcome at [github.com/kellylford/Image-Description-Toolkit](https://github.com/kellylford/Image-Description-Toolkit).

---

*This blog post was [written with / assisted by] AI. [AUTHOR NOTE: Fill in authorship disclosure as appropriate.]*
