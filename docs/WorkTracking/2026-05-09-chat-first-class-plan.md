# Chat First-Class Experience — Feature Plan
**Date**: 2026-05-09  
**Author**: GitHub Copilot (Claude Sonnet 4.6)  
**Status**: Planning  

---

## Overview

This plan makes chat a first-class experience in ImageDescriber, on equal footing with image descriptions. The core architectural idea: a **chat session = an item in the workspace tree**, and each **message turn = a description entry** on that item. This reuses the existing tree, description pane, export, filter, rename, and search infrastructure without duplicating it.

---

## Current State (as-built)

- `ImageWorkspace.chat_sessions` — a parallel `Dict[str, dict]` that stores sessions, completely separate from `workspace.items` (images)
- `ChatWindow` — a modal `wx.Dialog`; sessions are saved into `chat_sessions` but **never appear in the tree**
- `on_chat()` — launches a provider/model picker, then opens `ChatWindow`; no workspace-save check
- `ChatProcessingWorker` — captures token usage metadata but does not store it on the message dict
- `refresh_image_list()` — only iterates `workspace.items`; chat sessions are invisible
- `export_descriptions_to_text/html` — only iterates `workspace.items`; chats are excluded from both exports today

---

## Target Architecture

### Chat item in the tree

A chat session becomes an `ImageItem` with `item_type="chat"` in `workspace.items`. Its `file_path` key is a synthetic URI `chat:<session_id>` (never touches the filesystem). Its `display_name` is the user-facing name. Each message turn is stored as an `ImageDescription`:

```
ImageItem(item_type="chat", display_name="Chat, Claude claude-opus-4-6 5/9/2026 2:30P")
  └─ ImageDescription(prompt_style="user_question",  text="What is in this photo?")
  └─ ImageDescription(prompt_style="ai_response",    text="The photo shows …", completion_tokens=312)
  └─ ImageDescription(prompt_style="user_question",  text="Where was it taken?")
  └─ ImageDescription(prompt_style="ai_response",    text="Based on the background …", completion_tokens=87)
```

The existing `chat_sessions` dict is **deprecated** and migrated forward on workspace load.

---

## Feature Breakdown

### Feature 1 — Workspace Save Prompt Before Chat

**Problem**: Starting a chat when the workspace has no file path shows a confusing error dialog.

**Solution**: Mirror the exact pattern used in batch processing (imagedescriber_wx.py lines 3220–3284):

1. In `on_chat()`, before opening `ChatDialog`, check if `self.workspace.file_path` is `None`.
2. If unsaved: show `wx.MessageDialog` — "Chat sessions are saved with the workspace. Save your workspace first?\n\n[Save Now] [Save to Default Location] [Cancel]"
3. "Save Now" → call `on_save_workspace_as()` → if user cancels save, abort chat launch.
4. "Save to Default Location" → auto-create an Untitled workspace in the default location and save silently, then proceed. User can rename later.
5. Cancel → abort.

**Files touched**: `imagedescriber_wx.py` → `on_chat()`

**Complexity**: Low. Pattern already exists.

---

### Feature 2 — Chat Session Persistence (Messages as Descriptions)

This is the load-bearing architectural change.

#### 2a. Data Model

**`data_models.py`**:
- `ImageDescription`: Add `prompt_style` values `"user_question"` and `"ai_response"` to the informal enum (no code change needed, just convention).
- `ImageDescription`: Add `token_usage: dict` field (stores `{prompt_tokens, completion_tokens, total_tokens}`) and persist via `to_dict()`/`from_dict()`.
- `ImageItem`: No change needed; `item_type="chat"` is already supported as an open string. Add class-level constant `ITEM_TYPE_CHAT = "chat"` for safety.
- `ImageWorkspace`:
  - Add `migrate_chat_sessions()` method: converts any entries in `chat_sessions` dict into `ImageItem`/`ImageDescription` objects in `items`.
  - Call `migrate_chat_sessions()` in `from_dict()` after loading.
  - Keep `chat_sessions` in serialization for one release cycle (write empty dict, ignore on load after migration).

#### 2b. Creating a Chat Item

In `on_chat()` (after workspace save confirmed):
1. Generate `session_id = f"chat_{int(time.time() * 1000)}"`.
2. Create `ImageItem(file_path=f"chat:{session_id}", item_type="chat")`.
3. Set `item.display_name = _format_chat_name(provider, model, datetime.now())` (see Feature 3).
4. `workspace.add_item(item)` → saves to `workspace.items`.
5. Open `ChatWindow` passing the `session_id` so it knows which item to update.

#### 2c. ChatWindow stores messages as descriptions

On `on_chat_complete()`, instead of appending to `session['messages']`, append two `ImageDescription` objects to the `ImageItem`:
```python
user_desc = ImageDescription(
    text=user_message,
    prompt_style="user_question",
    provider=provider,
    model=model,
    created=user_timestamp
)
ai_desc = ImageDescription(
    text=full_response,
    prompt_style="ai_response",
    provider=provider,
    model=model,
    created=ai_timestamp,
    completion_tokens=token_usage.get('completion_tokens', 0),
    metadata={'token_usage': token_usage}
)
chat_item.add_description(user_desc)
chat_item.add_description(ai_desc)
workspace.mark_modified()
workspace.save()
```

`ChatWindow._load_history()` reconstructs the conversation from descriptions instead of `session['messages']`.

#### 2d. Workspace Save Trigger

`workspace.save()` already exists (confirmed in codebase). Auto-save after each completed turn.

#### 2e. Tree Display for Chat Items

In `refresh_image_list()`:
- Add a "Chats" group or simply insert chat items alongside images.
- Decision: Insert chat items **after** all images/videos, in a separate tree section under a "Chats" parent node. This keeps the tree organized.
- Display label: use `item.display_name` (not `Path(item.file_path).name`).
- Icon: Use a distinct icon (speech bubble / chat icon if available in wx.ArtProvider; fallback to text marker).
- No thumbnail preview for chat items.

#### 2f. Selecting a Chat Item

`on_image_selected()` / `on_tree_selection_changed()`:
- Detect `item_type == "chat"`.
- In the description pane (`desc_list`): display messages with "You:" / "AI:" prefix.
- In the preview panel: show session metadata (provider, model, message count, start date).
- Double-click or Enter on a chat item in tree → reopen `ChatWindow` to resume the session.
- No image preview; no "Process" button active; no batch-mark checkbox.

**Files touched**: `imagedescriber_wx.py` → `refresh_image_list()`, `on_tree_selection_changed()`, `on_image_selected()`; `chat_window_wx.py` → `on_chat_complete()`, `_load_history()`

**Complexity**: High. This is the largest change.

---

### Feature 3 — Chat Naming and Rename

#### Default Name Format

Follow the project date/time standard (`M/D/YYYY H:MMP` — no leading zeros, A/P suffix):

```
Chat, Claude claude-opus-4-6 5/9/2026 2:30P
Chat, OpenAI gpt-4o 5/9/2026 10:15A
Chat, Ollama llava:latest 5/9/2026 3:00P
```

Implementation: `_format_chat_name(provider: str, model: str, dt: datetime) -> str`

```python
def _format_chat_name(provider: str, model: str, dt: datetime) -> str:
    time_str = dt.strftime("%-m/%-d/%Y %-I:%M").rstrip('0').rstrip(':')
    ampm = "A" if dt.hour < 12 else "P"
    return f"Chat, {provider.title()} {model} {time_str}{ampm}"
```
(Use `%#m/%#d` on Windows to suppress leading zeros.)

#### Rename Support

The existing `on_rename_item()` in `imagedescriber_wx.py` already updates `item.display_name`. It just needs to be enabled for `item_type == "chat"` items (currently it may early-exit for non-image types). No new mechanism needed — just ensure the rename path doesn't gate on item type.

**Files touched**: `imagedescriber_wx.py` → `on_rename_item()`, `on_chat()`

**Complexity**: Low.

---

### Feature 4 — View Menu "Chats Only" Filter

Add a new radio item to the View menu:

```
Filter: All Items              F5
Filter: Described Only
Filter: Undescribed Only
Filter: Videos Only
Filter: Chats Only             ← new
```

In `refresh_image_list()`, when `current_filter == "chats"`:
- Show only items where `item.item_type == "chat"`.
- Hide all images, videos, and frames.

Conversely, when `current_filter != "chats"` and `current_filter != "all"`:
- **Exclude** chat items from the list (chats don't have "described" / "undescribed" / "video" semantics).

The "All Items" filter (`"all"`) continues to show everything including chats.

**Files touched**: `imagedescriber_wx.py` → `_create_menus()`, `refresh_image_list()`, `on_set_filter()`

**Complexity**: Low-medium.

---

### Feature 5 — Export Behavior

#### Gallery Export (HTML with thumbnails)
Chat items must be **excluded**. In `on_export_html_gallery()` / `gallery_exporter.export_gallery()`:
- Filter out items where `item.item_type == "chat"` before passing to the exporter.
- If no non-chat items exist, show: "No images to export. Chat sessions are not included in gallery exports."

#### Description Export (Text / HTML)
Chat items must be **included**. In `export_descriptions_to_text()` and `export_descriptions_to_html()`:
- For `item_type == "chat"`, format as a conversation transcript section:
  ```
  Chat Session: Chat, Claude claude-opus-4-6 5/9/2026 2:30P
  Provider: Claude / claude-opus-4-6
  Messages: 6 turns
  
  You: What is in this photo?
  
  AI: The photo shows a coastal town…
     [Token usage: 312 completion, 1,847 prompt]
  
  You: Where was it taken?
  …
  ```
- Clearly delimit from image descriptions.
- Suppress the "File:" and "Path:" lines (no real file).

**Files touched**: `imagedescriber_wx.py` → `export_descriptions_to_text()`, `export_descriptions_to_html()`, `on_export_html_gallery()`; `gallery_exporter.py` (if filtering is done there).

**Complexity**: Medium.

---

### Feature 6 — HEIC Conversion for Chat Attachments

When a user attaches a `.heic` or `.HEIC` file in `on_attach_files()`:

1. Detect HEIC extension.
2. Call existing `ConvertImage.convert_heic_to_jpg(heic_path)` (from `scripts/ConvertImage.py`).
3. Save the converted JPG to a temp directory (`tempfile.mkdtemp()`).
4. Queue the JPG path (not the HEIC path) as the pending attachment.
5. Show a status message: "HEIC converted to JPEG for attachment."

The temp file lifecycle: delete on `ChatWindow` close or app exit. Use `atexit` or store in a class-level list for cleanup.

**Files touched**: `chat_window_wx.py` → `on_attach_files()`, `on_close()`

**Complexity**: Low-medium. Conversion logic already exists.

---

### Feature 7 — Clipboard Image Paste in Chat

When focus is in the `ChatWindow` (input field or anywhere in the window) and the user presses `Ctrl+V` (`Cmd+V` on macOS):

1. Check if clipboard contains a bitmap: `wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP))`.
2. If yes (and provider supports attachments): extract the bitmap, save to temp file as PNG.
3. Add the temp PNG as a pending attachment via `_add_pending_attachment(path, 'image/png')`.
4. Show feedback in status bar: "Image from clipboard added as attachment."
5. If clipboard has an image but provider does NOT support attachments: show `show_info()`: "Current provider does not support image attachments."
6. If clipboard does not have an image: fall through to default paste behavior (text paste in the input field).

Implementation detail: Intercept in `EVT_CHAR_HOOK` on `ChatWindow` or bind `Ctrl+V` at window level, checking if a text control currently has focus before deciding image vs. text paste.

**Files touched**: `chat_window_wx.py` → `_bind_events()`, new `on_paste_from_clipboard()`

**Complexity**: Medium. Platform differences (macOS clipboard access may need permission).

---

### Feature 8 — Token Usage Per Chat Message

#### Capturing tokens in the worker

`ChatProcessingWorker` already captures `last_usage` for image descriptions. For chat responses:
- After the API call, extract `usage` dict and post it with `ChatCompleteEvent`.
- Extend `ChatCompleteEvent` to include a `token_usage: dict` field.

#### Storing tokens on the message

In `on_chat_complete()`, store `token_usage` on the `ImageDescription.metadata` field (already exists) and in `ImageDescription.completion_tokens` (already exists as a field).

#### Displaying tokens in the ListBox

In `_load_history()` and `on_chat_complete()`, format the AI response line:
```
AI (2:30P) [↙ 312 tok]: The photo shows a coastal town…
```

Or more verbosely when hovered/selected:
```
AI (2:30P): The photo shows…
Token usage: 1,847 prompt + 312 completion = 2,159 total
```

In the description detail pane (when user selects a turn from `desc_list`), show token usage prominently in the metadata area.

**Files touched**: `workers_wx.py` → `ChatProcessingWorker`, `ChatCompleteEvent`; `chat_window_wx.py` → `on_chat_complete()`, `_load_history()`; `data_models.py` → `ImageDescription`

**Complexity**: Low-medium.

---

## Additional Implications (Beyond the 8 Requested Items)

### 9. Search (Ctrl+F) for Chat Content

`_matches_search()` currently searches `Path(file_path).stem` + description texts. For chat items:
- `Path("chat:abc123").stem` is not meaningful.
- Fix: use `item.display_name` as the primary search target for chat items (already a field).
- Message text (user questions + AI responses) is already in `item.descriptions`, so it's automatically included in the haystack.

### 10. Context Menu for Chat Items

Right-click in the tree on a chat item should show a context-specific menu:
- **Open Chat** (resume conversation) — primary action
- **Rename** — same as F2
- **Delete Session** — removes the item and all messages
- (NOT: Process, Batch Mark, Extract Frames, Convert HEIC, Copy Image)

Gate context menu items based on `item_type`.

### 11. Description Pane Formatting for Chat Turns

When a chat item is selected and the user clicks a message in `desc_list`:
- Label "You asked:" (for `prompt_style == "user_question"`) or "AI responded:" (for `"ai_response"`).
- Show timestamp, provider/model, token count.
- For AI responses: show edit button to manually correct/annotate the response.

### 12. Workspace Stats Dialog

`workspace_stats_dialog.py` should be updated to include:
- Total chat sessions
- Total chat messages (all turns across all sessions)
- Total tokens used across all chat sessions (if stored)

### 13. Session Resumption

Double-clicking a chat tree item or pressing Enter with it selected:
- Opens `ChatWindow` bound to that item's `file_path` key.
- `ChatWindow._load_history()` reconstructs conversation from `item.descriptions`.
- Conversation continues normally; new turns append more descriptions.

### 14. Migration Path for Existing Workspaces

On workspace load, `from_dict()` calls `migrate_chat_sessions()`:
```python
def migrate_chat_sessions(self):
    """Convert legacy chat_sessions dict entries to ImageItem objects."""
    for session_id, session in list(self.chat_sessions.items()):
        file_path = f"chat:{session_id}"
        if file_path in self.items:
            continue  # Already migrated
        item = ImageItem(file_path=file_path, item_type="chat")
        item.display_name = session.get('name', f"Chat {session_id}")
        for msg in session.get('messages', []):
            style = "user_question" if msg['role'] == 'user' else "ai_response"
            desc = ImageDescription(
                text=msg.get('content', ''),
                prompt_style=style,
                provider=session.get('provider', ''),
                model=session.get('model', ''),
                created=msg.get('timestamp', ''),
                metadata=msg.get('metadata', {})
            )
            item.add_description(desc)
        self.items[file_path] = item
    # Clear after migration (keep dict empty going forward)
    self.chat_sessions = {}
```

### 15. "Save chat before closing" Guard

When the user closes `ChatWindow` mid-turn (while `is_processing = True`):
- Warn: "AI is still responding. Wait for completion or close and lose the current response?"
- On normal close: ensure the workspace has been saved (call `workspace.save()`).

---

## Task Schedule

Tasks are ordered by dependency. Phases 1 and 2 are prerequisites for everything else.

### Phase 1 — Data Model & Foundation
**Agent**: IDT Coding Agent  
**Estimated work**: ~1 session

| # | Task | File(s) | Notes |
|---|------|---------|-------|
| 1.1 | Add `token_usage` field to `ImageDescription` | `data_models.py` | `to_dict`/`from_dict` |
| 1.2 | Add `ITEM_TYPE_CHAT = "chat"` constant to `ImageItem` | `data_models.py` | Symbolic constant |
| 1.3 | Implement `migrate_chat_sessions()` on `ImageWorkspace` | `data_models.py` | Called in `from_dict` |
| 1.4 | Call migration in `ImageWorkspace.from_dict()` | `data_models.py` | After loading items |
| 1.5 | Write unit tests for migration, new fields | `pytest_tests/` | New test file |

---

### Phase 2 — Tree Display for Chat Items
**Agent**: IDT Coding Agent  
**Prerequisite**: Phase 1  
**Estimated work**: ~1–2 sessions

| # | Task | File(s) | Notes |
|---|------|---------|-------|
| 2.1 | Update `refresh_image_list()` to add "Chats" parent node + children | `imagedescriber_wx.py` | Handle `item_type=="chat"` |
| 2.2 | Chat items show `display_name` not filename in tree | `imagedescriber_wx.py` | Guard `Path()` calls |
| 2.3 | Update `on_tree_selection_changed()` for chat items | `imagedescriber_wx.py` | No preview, show session info |
| 2.4 | Update `desc_list` to show "You:" / "AI:" prefixes for chat turns | `imagedescriber_wx.py` | Based on `prompt_style` |
| 2.5 | Double-click / Enter on chat item → resume `ChatWindow` | `imagedescriber_wx.py` | Call `_open_chat_window(item)` |
| 2.6 | Update `_matches_search()` for chat items | `imagedescriber_wx.py` | Use `display_name` |
| 2.7 | Guard `Path()` file operations against `chat:` URIs | `imagedescriber_wx.py` | `is_missing`, preview, mtime |

---

### Phase 3 — Chat Session Creation & Persistence
**Agent**: IDT Coding Agent  
**Prerequisite**: Phase 2  
**Estimated work**: ~1 session

| # | Task | File(s) | Notes |
|---|------|---------|-------|
| 3.1 | Workspace save prompt in `on_chat()` (Feature 1) | `imagedescriber_wx.py` | Mirror batch pattern |
| 3.2 | Create chat `ImageItem` in workspace on session start | `imagedescriber_wx.py` | `on_chat()` → `workspace.add_item()` |
| 3.3 | `_format_chat_name()` helper with date format standard | `imagedescriber_wx.py` | Cross-platform zero-stripping |
| 3.4 | Pass `chat_item` (not workspace) to `ChatWindow` | `chat_window_wx.py` | Change constructor signature |
| 3.5 | `on_chat_complete()` stores turns as `ImageDescription` | `chat_window_wx.py` | Replace session dict append |
| 3.6 | `_load_history()` reads from `item.descriptions` | `chat_window_wx.py` | Reconstruct from descriptions |
| 3.7 | `on_close()` guard — warn if mid-response | `chat_window_wx.py` | `is_processing` check |
| 3.8 | Refresh tree after `ChatWindow` closes | `imagedescriber_wx.py` | `on_chat()` post-modal |
| 3.9 | Write integration tests | `pytest_tests/` | Session create, persist, resume |

---

### Phase 4 — Chat Naming & Rename (Feature 3)
**Agent**: IDT Coding Agent  
**Prerequisite**: Phase 3  
**Estimated work**: ~0.5 sessions

| # | Task | File(s) | Notes |
|---|------|---------|-------|
| 4.1 | Enable rename for `item_type=="chat"` in `on_rename_item()` | `imagedescriber_wx.py` | Remove type gate if present |
| 4.2 | Verify renamed name persists after workspace save/load | `imagedescriber_wx.py` | Manual test |

---

### Phase 5 — View Menu Chats Filter (Feature 4)
**Agent**: IDT Coding Agent  
**Prerequisite**: Phase 2  
**Estimated work**: ~0.5 sessions

| # | Task | File(s) | Notes |
|---|------|---------|-------|
| 5.1 | Add "Filter: Chats Only" radio item to View menu | `imagedescriber_wx.py` | `_create_menus()` |
| 5.2 | Update `refresh_image_list()` for `current_filter=="chats"` | `imagedescriber_wx.py` | Show only `item_type=="chat"` |
| 5.3 | Hide chats from non-"all"/non-"chats" filter views | `imagedescriber_wx.py` | Consistency |

---

### Phase 6 — Export Integration (Feature 5)
**Agent**: IDT Coding Agent  
**Prerequisite**: Phase 3  
**Estimated work**: ~0.5 sessions

| # | Task | File(s) | Notes |
|---|------|---------|-------|
| 6.1 | Exclude chat items from gallery export | `imagedescriber_wx.py`, `gallery_exporter.py` | Filter before exporting |
| 6.2 | Include chat items in description text export | `imagedescriber_wx.py` | `export_descriptions_to_text()` |
| 6.3 | Include chat items in description HTML export | `imagedescriber_wx.py` | `export_descriptions_to_html()` |
| 6.4 | Format chat transcript nicely in both export formats | `imagedescriber_wx.py` | User/AI labeling |

---

### Phase 7 — Token Usage Display (Feature 8)
**Agent**: IDT Coding Agent  
**Prerequisite**: Phase 3  
**Estimated work**: ~0.5 sessions

| # | Task | File(s) | Notes |
|---|------|---------|-------|
| 7.1 | Extend `ChatCompleteEvent` with `token_usage` field | `workers_wx.py` | Post with event |
| 7.2 | Capture and post token usage from all providers in worker | `workers_wx.py` | Ollama, OpenAI, Claude |
| 7.3 | Store token usage in `ImageDescription.metadata` on complete | `chat_window_wx.py` | Already has field |
| 7.4 | Display token count in ListBox item label for AI turns | `chat_window_wx.py` | `on_chat_complete()`, `_load_history()` |
| 7.5 | Show detailed token breakdown in description detail pane | `imagedescriber_wx.py` | On AI turn selection |

---

### Phase 8 — HEIC Conversion for Attachments (Feature 6)
**Agent**: IDT Coding Agent  
**Prerequisite**: None (standalone)  
**Estimated work**: ~0.5 sessions

| # | Task | File(s) | Notes |
|---|------|---------|-------|
| 8.1 | Detect `.heic` extension in `on_attach_files()` | `chat_window_wx.py` | Case-insensitive |
| 8.2 | Convert via `ConvertImage` to temp JPG | `chat_window_wx.py` | Import pattern (try/except) |
| 8.3 | Clean up temp files on `ChatWindow.on_close()` | `chat_window_wx.py` | `self._temp_files` list |
| 8.4 | Add HEIC to the file picker wildcard | `chat_window_wx.py` | `get_attachment_wildcard()` needs update |

---

### Phase 9 — Clipboard Image Paste (Feature 7)
**Agent**: IDT Coding Agent  
**Prerequisite**: None (standalone)  
**Estimated work**: ~0.5 sessions

| # | Task | File(s) | Notes |
|---|------|---------|-------|
| 9.1 | Bind `EVT_CHAR_HOOK` on `ChatWindow` for Ctrl/Cmd+V | `chat_window_wx.py` | Only intercept when input has no text selection |
| 9.2 | Check clipboard for bitmap; save to temp PNG | `chat_window_wx.py` | `wx.TheClipboard`, `wx.BitmapDataObject` |
| 9.3 | Add temp PNG as pending attachment | `chat_window_wx.py` | Call `_refresh_attachment_panel()` |
| 9.4 | Inform user if provider doesn't support attachments | `chat_window_wx.py` | `show_info()` message |
| 9.5 | Clean up clipboard-sourced temp files on close | `chat_window_wx.py` | Part of `self._temp_files` cleanup |

---

### Phase 10 — Context Menu & Stats Polish
**Agent**: IDT Coding Agent  
**Prerequisite**: Phase 2, Phase 3  
**Estimated work**: ~0.5 sessions

| # | Task | File(s) | Notes |
|---|------|---------|-------|
| 10.1 | Context menu for chat items (Open, Rename, Delete) | `imagedescriber_wx.py` | `on_tree_right_click()` |
| 10.2 | Disable non-applicable menu items for chat items | `imagedescriber_wx.py` | Process, Batch Mark, etc. |
| 10.3 | Update `workspace_stats_dialog.py` with chat stats | `workspace_stats_dialog.py` | Session count, message count, tokens |

---

## Open Design Questions (Resolve Before Phase 1 Starts)

1. **Chat items in "All Items" filter**: Should chats appear intermixed with images in date order, or always at the bottom under a "Chats" parent node? **Recommendation**: Separate "Chats" parent node — keeps the image list clean, is easier to implement, and is clearly navigable.

2. **What happens to `ChatWindow` modality?** Currently `wx.Dialog` (modal). Making it modeless would allow simultaneous chat + image browsing. **Recommendation**: Defer modelessness — it's a larger UX change. Keep modal for now.

3. **Chat item `is_missing` behavior**: Chat items use synthetic URIs, so the "file missing" check should always return False. **Recommendation**: In the missing-file scan, skip items with `file_path.startswith("chat:")`.

4. **Multiple open chat windows**: Can the user open two chats simultaneously? **Recommendation**: Yes, since each creates a separate item. No limit enforced.

5. **Clipboard paste collision with text paste**: If focus is in the input `wx.TextCtrl`, Ctrl+V should still paste text normally. Only intercept at the window level when the clipboard contains an image AND input field is empty or provider supports attachments. **Recommendation**: Intercept at window level; check clipboard type first; if bitmap → image paste; else → let event propagate to text control.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `chat:` URI breaks `Path()` calls in 50+ places | High | High | Audit all `Path(item.file_path)` usages; add helper `is_chat_item(item)` guard |
| Migration corrupts existing workspaces | Medium | High | Test migration with real `.idw` files; keep backup pattern; migration is idempotent |
| `refresh_image_list()` performance regression | Medium | Medium | Chat items are light (no EXIF extraction); add early-out for `item_type=="chat"` |
| Clipboard access denied on macOS | Low | Low | Wrap in try/except; show friendly message |
| Token usage unavailable for Ollama | Low | Low | Ollama doesn't always return usage; treat 0 as "not available" |

---

## Testing Requirements

Per project standards, all code requires tests before claiming complete.

| Phase | Test Type | What to test |
|-------|-----------|-------------|
| 1 | Unit | `migrate_chat_sessions()`, `ImageDescription.token_usage` serialization |
| 2 | Integration | Tree builds correctly with chat items, search finds chat content |
| 3 | Integration | Session create → message send → workspace save → reload → session resumed |
| 6 | Unit | Gallery export excludes chats; description export includes chats |
| 7 | Unit | Token capture from all 3 providers |
| 8 | Unit | HEIC attachment conversion, temp file cleanup |
| 9 | Manual | Clipboard paste (cannot automate clipboard in headless tests) |

---

## Implementation Order Summary

```
Phase 1 (Data Model)        ← START HERE
    ↓
Phase 2 (Tree Display)
    ↓
Phase 3 (Session Creation & Persistence)
    ↓
Phase 4 (Naming/Rename) ─────────────────────────────────┐
Phase 5 (Filter)         ──────────────────────────────── │
Phase 6 (Export)         ──────────────────────────────── │ (all can run in parallel after Phase 3)
Phase 7 (Token Display)  ──────────────────────────────── │
Phase 10 (Context/Stats) ──────────────────────────────── ┘

Phase 8 (HEIC Attach)    ← Independent; can start any time
Phase 9 (Clipboard Paste) ← Independent; can start any time
```

Phases 8 and 9 are fully independent of the architectural phases and can be assigned to a parallel agent or tackled between the main phases.

---

## Files That Will Change

| File | Change Level | Why |
|------|-------------|-----|
| `data_models.py` | Medium | New fields, migration method |
| `imagedescriber_wx.py` | High | Tree, filter, export, context menu |
| `chat_window_wx.py` | High | Persistence, HEIC, clipboard, tokens |
| `workers_wx.py` | Low | Token event field |
| `workspace_stats_dialog.py` | Low | Chat counts |
| `pytest_tests/` | New files | Tests for above |
| `gallery_exporter.py` | Low | Exclude chat items |

---

*This plan will be kept current as work progresses. Mark phases complete when all tasks and tests are done.*
