using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using Newtonsoft.Json;

namespace ImageDescriber.Full.Models
{
    public class ImageDescription
    {
        public string Id { get; set; } = "";
        public string Text { get; set; } = "";
        public string Model { get; set; } = "";
        public string PromptStyle { get; set; } = "";
        public string Created { get; set; } = "";
        public string CustomPrompt { get; set; } = "";
        public string Provider { get; set; } = "";

        public ImageDescription()
        {
            Created = DateTime.Now.ToString("O");
            Id = DateTimeOffset.Now.ToUnixTimeMilliseconds().ToString();
        }

        public ImageDescription(string text, string model = "", string promptStyle = "", 
                              string customPrompt = "", string provider = "")
            : this()
        {
            Text = text;
            Model = model;
            PromptStyle = promptStyle;
            CustomPrompt = customPrompt;
            Provider = provider;
        }

        public Dictionary<string, object> ToDictionary()
        {
            return new Dictionary<string, object>
            {
                ["id"] = Id,
                ["text"] = Text,
                ["model"] = Model,
                ["prompt_style"] = PromptStyle,
                ["created"] = Created,
                ["custom_prompt"] = CustomPrompt,
                ["provider"] = Provider
            };
        }

        public static ImageDescription FromDictionary(Dictionary<string, object> data)
        {
            var desc = new ImageDescription
            {
                Id = data.GetValueOrDefault("id", "")?.ToString() ?? "",
                Text = data.GetValueOrDefault("text", "")?.ToString() ?? "",
                Model = data.GetValueOrDefault("model", "")?.ToString() ?? "",
                PromptStyle = data.GetValueOrDefault("prompt_style", "")?.ToString() ?? "",
                Created = data.GetValueOrDefault("created", "")?.ToString() ?? "",
                CustomPrompt = data.GetValueOrDefault("custom_prompt", "")?.ToString() ?? "",
                Provider = data.GetValueOrDefault("provider", "")?.ToString() ?? ""
            };
            return desc;
        }
    }

    public class ImageItem : INotifyPropertyChanged
    {
        private bool _batchMarked;
        private string _displayName = "";

        public string FilePath { get; set; } = "";
        public string ItemType { get; set; } = "image"; // "image", "video", "extracted_frame"
        public List<ImageDescription> Descriptions { get; set; } = new();
        
        public bool BatchMarked 
        { 
            get => _batchMarked; 
            set 
            { 
                _batchMarked = value; 
                OnPropertyChanged(nameof(BatchMarked));
                OnPropertyChanged(nameof(StatusPrefix)); // For UI binding
            } 
        }

        public string? ParentVideo { get; set; }
        public List<string> ExtractedFrames { get; set; } = new();
        
        public string DisplayName 
        { 
            get => _displayName; 
            set 
            { 
                _displayName = value; 
                OnPropertyChanged(nameof(DisplayName));
            } 
        }

        // UI binding properties to fix data binding issues
        public string StatusPrefix => BatchMarked ? "[✓] " : "";
        public string FileName => System.IO.Path.GetFileName(FilePath);
        public bool HasDescriptions => Descriptions.Count > 0;
        public int DescriptionCount => Descriptions.Count;

        public ImageItem() { }

        public ImageItem(string filePath, string itemType = "image")
        {
            FilePath = filePath;
            ItemType = itemType;
        }

        public void AddDescription(ImageDescription description)
        {
            Descriptions.Add(description);
            OnPropertyChanged(nameof(Descriptions));
            OnPropertyChanged(nameof(HasDescriptions));
            OnPropertyChanged(nameof(DescriptionCount));
        }

        public void RemoveDescription(string descId)
        {
            Descriptions.RemoveAll(d => d.Id == descId);
            OnPropertyChanged(nameof(Descriptions));
            OnPropertyChanged(nameof(HasDescriptions));
            OnPropertyChanged(nameof(DescriptionCount));
        }

        public Dictionary<string, object> ToDictionary()
        {
            return new Dictionary<string, object>
            {
                ["file_path"] = FilePath,
                ["item_type"] = ItemType,
                ["descriptions"] = Descriptions.Select(d => d.ToDictionary()).ToList(),
                ["batch_marked"] = BatchMarked,
                ["parent_video"] = ParentVideo ?? "",
                ["extracted_frames"] = ExtractedFrames,
                ["display_name"] = DisplayName
            };
        }

        public static ImageItem FromDictionary(Dictionary<string, object> data)
        {
            var item = new ImageItem(
                data.GetValueOrDefault("file_path", "")?.ToString() ?? "",
                data.GetValueOrDefault("item_type", "image")?.ToString() ?? "image"
            );

            if (data.ContainsKey("descriptions") && data["descriptions"] is List<object> descriptions)
            {
                foreach (var desc in descriptions)
                {
                    if (desc is Dictionary<string, object> descDict)
                    {
                        item.Descriptions.Add(ImageDescription.FromDictionary(descDict));
                    }
                }
            }

            item.BatchMarked = Convert.ToBoolean(data.GetValueOrDefault("batch_marked", false));
            item.ParentVideo = data.GetValueOrDefault("parent_video", "")?.ToString();
            
            if (data.ContainsKey("extracted_frames") && data["extracted_frames"] is List<object> frames)
            {
                item.ExtractedFrames = frames.Select(f => f?.ToString() ?? "").ToList();
            }

            item.DisplayName = data.GetValueOrDefault("display_name", "")?.ToString() ?? "";
            return item;
        }

        public event PropertyChangedEventHandler? PropertyChanged;
        protected virtual void OnPropertyChanged(string propertyName)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }

    public class ImageWorkspace : INotifyPropertyChanged
    {
        private const string WORKSPACE_VERSION = "3.0";

        public string Version { get; set; } = WORKSPACE_VERSION;
        public string DirectoryPath { get; set; } = ""; // Backward compatibility
        public List<string> DirectoryPaths { get; set; } = new();
        public Dictionary<string, ImageItem> Items { get; set; } = new();
        public Dictionary<string, object> ChatSessions { get; set; } = new();
        public string WorkspacePath { get; set; } = "";
        public bool IsModified { get; private set; } = false;

        // UI binding properties
        public string WorkspaceName => string.IsNullOrEmpty(WorkspacePath) 
            ? "New Workspace" 
            : System.IO.Path.GetFileNameWithoutExtension(WorkspacePath);
        
        public List<ImageItem> WorkspaceItems => Items.Values.ToList();

        public ImageWorkspace() { }

        public void AddItem(ImageItem item)
        {
            Items[item.FilePath] = item;
            IsModified = true;
            OnPropertyChanged(nameof(Items));
            OnPropertyChanged(nameof(WorkspaceItems));
        }

        public void RemoveItem(string filePath)
        {
            Items.Remove(filePath);
            IsModified = true;
            OnPropertyChanged(nameof(Items));
            OnPropertyChanged(nameof(WorkspaceItems));
        }

        public Dictionary<string, object> ToDictionary()
        {
            return new Dictionary<string, object>
            {
                ["version"] = Version,
                ["directory_path"] = DirectoryPath,
                ["directory_paths"] = DirectoryPaths,
                ["items"] = Items.ToDictionary(kvp => kvp.Key, kvp => kvp.Value.ToDictionary()),
                ["chat_sessions"] = ChatSessions,
                ["workspace_path"] = WorkspacePath
            };
        }

        public static ImageWorkspace FromDictionary(Dictionary<string, object> data)
        {
            var workspace = new ImageWorkspace
            {
                Version = data.GetValueOrDefault("version", WORKSPACE_VERSION)?.ToString() ?? WORKSPACE_VERSION,
                DirectoryPath = data.GetValueOrDefault("directory_path", "")?.ToString() ?? "",
                WorkspacePath = data.GetValueOrDefault("workspace_path", "")?.ToString() ?? ""
            };

            if (data.ContainsKey("directory_paths") && data["directory_paths"] is List<object> paths)
            {
                workspace.DirectoryPaths = paths.Select(p => p?.ToString() ?? "").ToList();
            }

            if (data.ContainsKey("items") && data["items"] is Dictionary<string, object> items)
            {
                foreach (var kvp in items)
                {
                    if (kvp.Value is Dictionary<string, object> itemDict)
                    {
                        workspace.Items[kvp.Key] = ImageItem.FromDictionary(itemDict);
                    }
                }
            }

            if (data.ContainsKey("chat_sessions") && data["chat_sessions"] is Dictionary<string, object> sessions)
            {
                workspace.ChatSessions = sessions;
            }

            workspace.IsModified = false;
            return workspace;
        }

        public event PropertyChangedEventHandler? PropertyChanged;
        protected virtual void OnPropertyChanged(string propertyName)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }

    // AI Provider Information class for UI binding
    public class AIProviderInfo
    {
        public string DisplayName { get; set; } = "";
        public string Value { get; set; } = "";
        public string Description { get; set; } = "";
        public bool IsAvailable { get; set; } = false;

        public AIProviderInfo() { }

        public AIProviderInfo(string displayName, string value, string description = "", bool isAvailable = true)
        {
            DisplayName = displayName;
            Value = value;
            Description = description;
            IsAvailable = isAvailable;
        }

        public override string ToString() => DisplayName;
    }
}