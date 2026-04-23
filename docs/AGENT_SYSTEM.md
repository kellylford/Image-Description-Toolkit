# IDT Copilot Agent System

**Location**: `.github/agents/`, `.github/prompts/`, `.github/hooks/`

This system enforces the pre/post verification protocol for every coding session on IDT. It exists because the codebase has grown large enough that undisciplined AI edits cause real production failures — most infamously a missing module-level `logger` that took 8 hours to trace down because wx silently swallows all event handler exceptions.

---

## What It Is

Three cooperating layers:

| Layer | File | Enforcement level |
|-------|------|-------------------|
| Coordinator agent | `.github/agents/idt-coding.agent.md` | Guidance (persona) |
| Pre-change prompt | `.github/prompts/pre-change.prompt.md` | On-demand checklist |
| Post-change prompt | `.github/prompts/post-change.prompt.md` | On-demand checklist |
| Hook guard | `.github/hooks/idt-session-guard.json` + `tools/idt_hook_guard.py` | Runtime enforcement |

---

## How to Use It

### Starting a coding session

Instead of opening default agent mode, open chat and select **IDT Coding Agent** from the agent picker (the `@` menu or agent selector in the chat input area).

The agent operates like regular agent mode — it has read, edit, search, and execute access — but it enforces checkpoints before and after any change.

### Before making any edit

Run the pre-change prompt from chat:
```
/pre-change rename get_date() in workflow.py
```

The prompt reads the actual code, finds every caller, checks PyInstaller compatibility, checks wx logger placement, and produces a written **PRE-CHANGE CHECKPOINT** block. If the verdict is BLOCKED, the agent will not proceed.

When the checkpoint passes, it writes `.idt_session/precheck_done` — the hook guard reads this to know it's safe to proceed.

### After making edits

Run the post-change prompt from chat:
```
/post-change imagedescriber_wx.py, ai_providers.py
```

The prompt runs `py_compile`, re-checks every caller, runs the code in dev mode, optionally builds the exe, reviews logs, and produces a **POST-CHANGE VERIFICATION** block. Only when OVERALL says VERIFIED can the task be declared complete.

When verification passes, it writes `.idt_session/verified`.

### The hook guard

The hook guard (`tools/idt_hook_guard.py`) runs automatically at two lifecycle events:

**PreToolUse** — fires before any file edit. If you try to edit a guarded core file without having run `/pre-change`, VS Code will show an `ask` confirmation dialog:
> "⚠️ IDT Guard: You're editing imagedescriber_wx.py without running /pre-change verification first."

You can confirm to proceed (for minor fixes), but the warning exists so you can't accidentally skip the checklist.

**Stop** — fires when the session ends. If guarded files were edited but `/post-change` wasn't completed, it injects a systemMessage reminder:
> "⚠️ IDT Guard: Core files were edited this session but /post-change verification was not completed."

This is a warning, not a hard block — the session can still end, but the reminder is explicit.

---

## Guarded Files

The hook guard raises the `ask` confirmation for these files:

| File | Why guarded |
|------|-------------|
| `imagedescriber_wx.py` | 6700+ lines; wx silent-failure risk; module-level logger |
| `workflow.py` | Core orchestrator; 2400+ lines; HIGH RISK rename target |
| `image_describer.py` | Multi-provider AI; frozen exe import paths |
| `idt_cli.py` | CLI entry point; argument parser conflict risk |
| `ai_providers.py` | Provider abstraction; import- and SDK-sensitive |
| `workers_wx.py` | Background thread workers; event handler silent-failure risk |
| `config_loader.py` | Path resolution; broken = nothing finds config files |

Adding a new guarded file: edit `GUARDED_FILES` in `tools/idt_hook_guard.py`.

---

## Session State

All state lives in `.idt_session/` (git-ignored):

| File | Written by | Meaning |
|------|------------|---------|
| `.idt_session/precheck_done` | `/pre-change` prompt or `--mark-precheck` | Pre-change checkpoint passed |
| `.idt_session/edits_made` | Hook guard PreToolUse | A guarded file was edited |
| `.idt_session/verified` | `/post-change` prompt or `--mark-verified` | Post-change verification passed |

Clear all flags to start a fresh task:
```bash
python tools/idt_hook_guard.py --reset
```

Write flags manually (e.g., if prompts aren't available):
```bash
python tools/idt_hook_guard.py --mark-precheck
python tools/idt_hook_guard.py --mark-verified
```

---

## Architecture Diagram

```
User: "fix the processing button"
        │
        ▼
[IDT Coding Agent]  ← .github/agents/idt-coding.agent.md
        │
        ├─ 1. Runs /pre-change ──────────────► [Pre-Change Prompt]
        │                                           │  reads code
        │                                           │  finds callers
        │                                           │  checks wx/PyInstaller
        │                                           │  writes PRE-CHANGE CHECKPOINT
        │                                           │  writes .idt_session/precheck_done
        │◄──────────────────────────────────────────┘
        │
        ├─ 2. Makes edits  ─────────────────► [Hook Guard: PreToolUse]
        │    (replace_string_in_file, etc.)        checks precheck_done
        │                                          asks user if missing
        │◄──────────────────────────────────────────┘
        │
        ├─ 3. Runs /post-change ─────────────► [Post-Change Prompt]
        │                                           │  py_compile
        │                                           │  caller re-verify
        │                                           │  dev mode test
        │                                           │  build exe (if needed)
        │                                           │  log review
        │                                           │  writes POST-CHANGE VERIFICATION
        │                                           │  writes .idt_session/verified
        │◄──────────────────────────────────────────┘
        │
        ├─ 4. Session ends ──────────────────► [Hook Guard: Stop]
        │                                          checks edits_made + verified
        │                                          injects reminder if not verified
        │◄──────────────────────────────────────────┘
        │
        ▼
   "Task complete" (with evidence)
```

---

## Why Each Piece Exists

### Why an agent instead of just instructions?

`copilot-instructions.md` is guidance — the model reads it but can de-prioritize it under pressure. An agent has explicit tool restrictions and the enforcement rules are its primary persona, not a footnote. The agent literally cannot deviate from the checkpoint protocol without explicitly announcing it.

### Why prompts instead of just checklist text?

Prompts are slash commands that run as mini-agents with their own tool access. `/pre-change` actually executes `grep_search` and `read_file` — it doesn't just nod and continue. The structured output format (CHECKPOINT block with field-by-field results) makes it impossible to fake.

### Why hooks?

Hooks are the only **deterministic** enforcement layer. Instructions and agents are guidance. Hooks run a real Python script and can return `ask` to require user confirmation before an edit lands. The Stop hook fires regardless of what the agent decides to say about being "done." You can't instruct your way past a hook.

### Why session state files?

The three components (agent, prompts, hooks) run in different contexts. The session files in `.idt_session/` are the only shared communication channel. When `/pre-change` writes `precheck_done`, the PreToolUse hook can read it milliseconds later without any in-memory coupling.

---

## Known Limitations

1. **Hooks require VS Code Copilot hook support** to be enabled in your settings. If the PreToolUse confirmation dialog never appears, hooks may not be active for your Copilot version. Check VS Code's Copilot settings for hook configuration.

2. **The `ask` confirmation can be bypassed** — clicking "Allow" skips pre-change for that edit. The system relies on discipline, not cryptographic enforcement. The point is to make skipping visible and intentional.

3. **The Stop warning is non-blocking** — you can end a session without running post-change. The warning is designed to be a reminder to the user, not a gate.

4. **Multi-file refactors**: If you run `/pre-change` once for a 5-file refactor and a later edit targets a different guarded file, the hook will still `ask`. Re-run `/pre-change` or use `--mark-precheck` to refresh the flag.

---

## Maintenance

- **Add a guarded file**: Add its filename to `GUARDED_FILES` in `tools/idt_hook_guard.py`
- **Change hook behavior**: Edit `tools/idt_hook_guard.py` — it's standard Python, no build needed
- **Update the checklist steps**: Edit `.github/prompts/pre-change.prompt.md` or `post-change.prompt.md`
- **Update agent persona**: Edit `.github/agents/idt-coding.agent.md`

The hook guard script itself is tested by:
```bash
python -m py_compile tools/idt_hook_guard.py
python tools/idt_hook_guard.py --reset
python tools/idt_hook_guard.py --mark-precheck
python tools/idt_hook_guard.py --mark-verified
```
