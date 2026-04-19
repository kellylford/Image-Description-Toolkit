# AI Models Used in IDT NASA Dataset

This file describes the AI models used to generate image descriptions for the [NASA Image of the Day dataset](https://www.theideaplace.net/projects/NasaDescriptions.csv). All descriptions below are sourced from official documentation.

---

## Anthropic

### Claude Haiku 4.5
*"Our fastest model, a lightweight version of our most powerful AI, at a more affordable price."*

Claude Haiku 4.5 is Anthropic's most cost-efficient model, designed for high-volume, latency-sensitive applications. It matches Claude Sonnet 4's performance on coding, computer use, and agent tasks while running substantially faster.

**Provider:** Anthropic  
**More info:** [anthropic.com/claude/haiku](https://www.anthropic.com/claude/haiku)

---

### Claude Sonnet 4.6
*"Hybrid reasoning model with superior intelligence for agents, featuring a 1M context window."*

Claude Sonnet 4.6 delivers frontier performance across coding, agents, and professional workflows. It can operate as both a standard model and a hybrid reasoning model, with configurable extended thinking for complex tasks.

**Provider:** Anthropic  
**More info:** [anthropic.com/claude/sonnet](https://www.anthropic.com/claude/sonnet)

---

## Google DeepMind

### Gemma4 31b (cloud)
*"Open models built by Google DeepMind. Gemma 4 models are multimodal, handling text and image input and generating text output."*

Gemma 4 is a family of open models designed to deliver frontier-level performance at each size. The 31b dense model is designed for advanced reasoning, coding, and agentic workflows on consumer hardware. All Gemma 4 models support configurable thinking modes and a 256K context window.

**Provider:** Google DeepMind  
**More info:** [deepmind.google/models/gemma/gemma-4](https://deepmind.google/models/gemma/gemma-4/)

---

## Moonshot AI

### Kimi K2 / Kimi-K2.5 (cloud)
*"A state-of-the-art Mixture-of-Experts model with 32 billion activated parameters and 1 trillion total parameters. It achieves state-of-the-art performance in frontier knowledge, math, and coding among non-thinking models. But it goes further — meticulously optimized for agentic tasks, Kimi K2 does not just answer; it acts."*

Kimi K2 is an open-source MoE model from Moonshot AI, optimized for complex reasoning, tool use, and autonomous agentic tasks. The cloud variant runs via Ollama's hosted inference.

**Provider:** Moonshot AI  
**More info:** [moonshotai.github.io/Kimi-K2](https://moonshotai.github.io/Kimi-K2/)

---

## Moondream

### Moondream2
*"A tiny vision language model that kicks ass and runs anywhere."*

Moondream2 is a compact 1.8B parameter vision-language model designed to run efficiently on edge devices with minimal resources. Despite its small size, it delivers capable image understanding for tasks like captioning, object detection, and visual question answering.

**Provider:** M87 Labs (Moondream)  
**More info:** [moondream.ai](https://moondream.ai/)

---

## Alibaba / Qwen Team

### Qwen3-VL 235b (cloud)
*"The most powerful vision-language model in the Qwen model family to date."*

Qwen3-VL is Alibaba's flagship vision-language model, with improvements across text understanding, visual reasoning, spatial understanding, long-context comprehension (up to 256K tokens natively), and visual coding. The 235b cloud variant runs via Ollama's hosted inference.

**Provider:** Alibaba / Qwen Team  
**More info:** [ollama.com/library/qwen3-vl](https://ollama.com/library/qwen3-vl)

---

## OpenAI

### GPT-4.1 Mini
*"A significant leap in small model performance, even beating GPT‑4o in many benchmarks. It matches or exceeds GPT‑4o in intelligence evals while reducing latency by nearly half and reducing cost by 83%."*

GPT-4.1 Mini is OpenAI's mid-tier model in the GPT-4.1 family, offering strong vision, coding, and instruction-following capabilities at lower cost and latency than the full GPT-4.1. Supports a 1 million token context window.

**Provider:** OpenAI  
**More info:** [openai.com/index/gpt-4-1](https://openai.com/index/gpt-4-1/)

---

### GPT-4.1 Nano
*"Our fastest and cheapest model available. It delivers exceptional performance at a small size with its 1 million token context window… ideal for tasks like classification or autocompletion."*

GPT-4.1 Nano is OpenAI's smallest and most cost-efficient model, optimized for speed and low latency. Despite its compact size, it scores 80.1% on MMLU and supports the full 1 million token context window shared across the GPT-4.1 family.

**Provider:** OpenAI  
**More info:** [openai.com/index/gpt-4-1](https://openai.com/index/gpt-4-1/)

---

*Descriptions sourced from official model documentation. All models were accessed via their respective providers or via [Ollama](https://ollama.com/) cloud inference.*
