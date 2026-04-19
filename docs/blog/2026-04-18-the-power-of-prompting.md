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

On April 1, 2026, NASA launched the Artemis II mission — the first crewed Moon trip since the Apollo program. NASA's Image of the Day page had been building up to this for weeks with stunning photographs: the crew in training, the rocket being prepared, and then the mission itself: Earthrise from lunar orbit, the Milky Way seen from deep space, the crew capsule from a window looking back at a shrunken planet.

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

## Kimi-K2.5 and Gemma4: Same Prompt, Different Voice

One of the things I wanted to know was whether two different models given the exact same alt text prompt would produce meaningfully different results — or whether the prompt would dominate and the model would not matter much.

The short answer: both models followed the three-length structure cleanly, but they have genuinely different voices. And the differences matter for publishing.

**Speed** is the most obvious difference — and it comes with a lesson. Kimi-K2.5 averaged 116 seconds per image for this run. Gemma4 averaged 14 seconds. For 64 images, Kimi took just over two hours; Gemma took about 15 minutes.

What makes that gap interesting is that Kimi is not normally a slow model. Across all the other prompts in this dataset, it averaged between 11 and 36 seconds per image. The aialttext run was a significant outlier. My hypothesis is that asking for three outputs of different lengths in a single prompt caused Kimi to generate substantially more text per image — and longer outputs simply take longer to produce. Gemma handled the same multi-part prompt without the same time cost.

The practical takeaway: any time you combine things in a prompt — multiple outputs, multiple formats, multiple lengths — it is worth running a small test batch first to understand how your model of choice responds before committing to 64 images. What works efficiently with one model may behave very differently with another.

**Formatting** differed in small but telling ways. Kimi labeled its sections `**25 words:**`, `**50 words:**`, `**100 words:**` — a clean, precise claim. Gemma used `**Short (approx. 25 words)**`, `**Medium (approx. 50 words)**`, `**Long (approx. 100 words)**`. Gemma's "approx." qualifier is more honest: neither model is actually hitting the word counts precisely, but Gemma at least acknowledges it.

Here is the same image — an astronaut silhouetted against a spacecraft window, with Earth filling the frame outside — described by both models.

**Kimi-K2.5:**

> *25 words:* Silhouette of an astronaut gazing at Earth through a spacecraft window, showing blue oceans, swirling white clouds, and the planet's curvature against the black space.

> *50 words:* Astronaut's silhouette visible against a spacecraft window, gazing at Earth suspended in the blackness of space. The planet displays vibrant blue oceans, swirling white cloud formations, and hints of landmasses. The curved horizon emphasizes Earth's spherical shape, creating a striking contrast between the dark interior and the illuminated planet beyond.

> *100 words:* The dark silhouette of an astronaut's profile is visible against a spacecraft window, gazing at the stunning view of Earth from orbit. The planet fills the window with vibrant blue oceans, swirling white cloud formations, and visible landmasses partially obscured by haze. The curvature of Earth is prominently displayed against the infinite blackness of space, creating a dramatic contrast between the illuminated planet and the dark void surrounding it. The spacecraft interior remains shadowed, emphasizing the isolation of space travel while highlighting the breathtaking beauty of our home planet. This perspective showcases Earth's fragility and the profound experience of orbital observation.

**Gemma4:**

> *Short (approx. 25 words):* Silhouette of an astronaut looking through a spacecraft window at a vibrant blue and white Earth against the deep black void of space.

> *Medium (approx. 50 words):* A dramatic silhouette of a person's profile, likely an astronaut, gazing through a rounded spacecraft portal. Outside the window, the Earth is visible as a brilliant blue marble with swirling white clouds and brown landmasses, contrasting sharply against the absolute darkness of the surrounding outer space.

> *Long (approx. 100 words):* A poignant, high-contrast photograph taken from inside a spacecraft. In the foreground, the dark silhouette of an astronaut's face is seen in profile, looking out through a curved observation window. The window frames a breathtaking view of planet Earth, showcasing deep blue oceans, intricate white cloud patterns, and the reddish-brown hues of a continent. The stark contrast between the pitch-black interior of the cabin and the luminous, glowing sphere of the planet emphasizes the isolation of space and the fragile beauty of Earth seen from a low-orbit perspective.

Neither names the astronaut (Reid Wiseman). Neither identifies the spacecraft (Orion). That knowledge has to come from the human editor. But as starting drafts, both are genuinely useful.

Kimi reads as more narrative and expansive. The 100-word version builds toward a conclusion — "the profound experience of orbital observation." Gemma is tighter and more visual — "the reddish-brown hues of a continent." Different writers will reach for one or the other depending on the context and tone of the publication.

There is also a case where model voice led to an actual error worth noting. For the Earthset image — Earth appearing above the lunar horizon, taken from the far side of the Moon — Kimi's 100-word version referred to it as the "Earthrise" phenomenon. Earthrise and Earthset are different events. Earthrise famously refers to the Apollo 8 photograph from lunar orbit. This image, taken by the Artemis II crew, shows Earthset from the lunar far side. Kimi reached for the famous reference but got it wrong. NASA's captured alt text — "Earthset From the Lunar Far Side" — was correct. Gemma described it accurately without using either term.

This is exactly why human review matters before publishing. The AI knew the image was significant. It chose a famous, evocative label. But the label was wrong. A human editor who knew the difference would catch it instantly. A human editor who did not might publish the error.

---

## Follow-Up Questions and Chat

One more IDT capability worth highlighting, now that the NASA dataset illustrates it well. After any image has been described, IDT lets you ask follow-up questions — press F in the ImageDescriber GUI or use the CLI. You can switch to a different model for the follow-up if you want.

For example: after running the Narrative prompt on the Artemis II launch photograph, you might ask: *"How does this compare to a Saturn V launch in terms of visual scale?"* Or for the supernova remnant: *"What telescope instruments were used to capture the different wavelengths in this image?"* The AI does not always get these right, but the capability is there, and for scientific images especially, the follow-up question is often where the real value is.

IDT also has a freestanding chat mode (press C in ImageDescriber) for model-to-model conversation without any image attached.

---

## The NASA Meatball

Some images are so iconic that AI models reference them by name without stopping to describe them — and the NASA meatball logo is the clearest example in this dataset.

The term "meatball" appeared in 61 descriptions across 12 images. In 11 of those images, the logo appeared as an incidental background element — on a wall at JPL, projected as a backdrop behind a rock sample display, on the tail of a T-38 jet, on the building behind the Artemis II crew. Across all of those background appearances, models named the logo 26 times and actually described what it looks like only 7 times. Most of those 7 were borderline — noting that the logo was "circular" or appeared on the wall. Almost no description explained what a viewer would actually see.

NASA's own alt-text set the tone. For the JPL auditorium selfie, NASA's caption reads: *"In the far background, there is a NASA 'meatball' insignia and the letters 'JPL' on the wall."* The name, nothing more. The AI models followed the same pattern. If you have never seen the NASA meatball and no one has ever described it to you, most of these descriptions left you exactly where you started.

The one exception: when the NASA logo itself was the image subject (a standalone logo PNG in the dataset), models gave rich, accurate descriptions across virtually every prompt. Gemma4's AI alt text treatment is a good example: *"The NASA insignia, known as the 'meatball' logo. It consists of a blue sphere representing a planet, containing the word 'NASA' in bold white text. A red V-shaped vector symbolizes aeronautics, while a white orbital ring and scattered white stars represent space exploration."* That's exactly what someone unfamiliar with the logo needs. The problem is that this only happened when the logo was the foreground subject — never when it appeared in the background.

**What the NASA meatball actually looks like:** A circular emblem on a deep blue field, with the word "NASA" in large bold white letters across the center. A red swoosh — sometimes described as a wing or chevron — cuts diagonally across the circle from lower-left to upper-right, representing aeronautics. A white curved orbital path arcs around the circle, suggesting a spacecraft in orbit. Small white stars are scattered through the blue field. The overall effect is dense but balanced: space, flight, and identity in one symbol.

**Followup questions help, but aren't foolproof.** When asked as a standalone followup — *"Please describe what the NASA meatball looks like to someone who has never seen it"* — GPT-4.1 Mini returned an accurate description on the first try: blue background, red wing-shaped vector, white stars, bold white NASA lettering. Claude Haiku's response, by contrast, described it as having *"a large red circle dominating the center"* as the main element — significantly wrong. The logo is primarily blue. Even when a model knows the name of an iconic image, its ability to accurately describe that image from memory alone varies.

**The prompt implication.** The accessibility and AI alt text prompts in IDT currently do not explicitly instruct models to describe iconic logos and emblems when they appear incidentally in an image. Adding language like *"when referencing iconic logos, insignia, or well-known symbols by name, include a brief visual description of what the symbol looks like"* may close this gap in a future prompt revision.

---

## Data Completeness

In a few instances, data for a prompt and model are not complete. In the case of Moondream, some prompts — such as Technical — failed to return any response on multiple tries.

In the case of Claude, not all prompts were run due to the amount of data already gathered and the costs associated with Claude models. In addition, due to image sizing and the way IDT currently works, some images exceeded the size limit for Claude and were not described.

The AI Alt Text prompt was only run on Kimi-K2.5 and Gemma4 models for this dataset.

---

## The Data

You can obtain the full set of image descriptions and prompts used for this set of NASA images at the following locations.

- [CSV of all descriptions](https://www.theideaplace.net/projects/NasaDescriptions.csv)
- [Markdown file of all prompts](https://www.theideaplace.net/projects/prompts.md) · [GitHub](https://github.com/kellylford/Image-Description-Toolkit/blob/v4.0.0Beta3/docs/archive/prompts.md)
- [AI models used in this dataset](https://www.theideaplace.net/projects/models.md)

The CSV includes descriptions from eight models across six providers: Claude Haiku 4.5, Claude Sonnet 4.6, Gemma4 31b, Kimi K2, Moondream, Qwen3-VL 235b, GPT-4.1 Mini, and GPT-4.1 Nano. For a brief description of each model and links to official documentation, see the models file above.

---

## Try It Yourself

The latest version of the Image Description Toolkit can be obtained from the [GitHub releases page](https://github.com/kellylford/Image-Description-Toolkit/releases/latest) or on the [project page at theideaplace.net](https://www.theideaplace.net/projects). Full documentation is in the [User Guide on GitHub](https://github.com/kellylford/Image-Description-Toolkit/blob/main/docs/USER_GUIDE_COMPLETE.md).

If you want to replicate the NASA experiment, try:

```
idt workflow https://www.nasa.gov/image-of-the-day/
```

That will download the current Image of the Day collection and describe the images using your configured model and prompt. From there, `idt combinedescriptions` will compile everything into a CSV you can explore in Excel or any spreadsheet tool.

Questions, issues, and pull requests are welcome at [github.com/kellylford/Image-Description-Toolkit](https://github.com/kellylford/Image-Description-Toolkit).

---

*This blog post was [written with / assisted by] AI. [AUTHOR NOTE: Fill in authorship disclosure as appropriate.]*
