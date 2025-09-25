using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using Newtonsoft.Json;

namespace ImageDescriber.Full
{
    // Matches Python ImageDescription class exactly
    public class ImageDescription : INotifyPropertyChanged
    {
        public string Id { get; set; } = "";
        public string Text { get; set; } = "";
        public string Model { get; set; } = "";
        public string PromptStyle { get; set; } = "";
        public string Created { get; set; } = "";
        public string CustomPrompt { get; set; } = "";
        public string Provider { get; set; } = "";

        public event PropertyChangedEventHandler? PropertyChanged;

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
    }

    // Matches Python ImageItem class exactly  
    public class ImageItem : INotifyPropertyChanged
    {
        public string FilePath { get; set; } = "";
        public string ItemType { get; set; } = "image";
        public List<ImageDescription> Descriptions { get; set; } = new();
        public bool BatchMarked { get; set; } = false;

        public event PropertyChangedEventHandler? PropertyChanged;

        // UI Helper properties
        public string FileName => System.IO.Path.GetFileName(FilePath);
        public int DescriptionCount => Descriptions.Count;
        public string StatusPrefix => BatchMarked ? "✓ " : "";

        public ImageItem() { }

        public ImageItem(string filePath)
        {
            FilePath = filePath;
        }

        public void AddDescription(ImageDescription description)
        {
            Descriptions.Add(description);
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(DescriptionCount)));
        }

        public void RemoveDescription(string id)
        {
            var desc = Descriptions.FirstOrDefault(d => d.Id == id);
            if (desc != null)
            {
                Descriptions.Remove(desc);
                PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(DescriptionCount)));
            }
        }
    }

    // Matches Python ImageWorkspace class exactly
    public class ImageWorkspace : INotifyPropertyChanged
    {
        public string Version { get; set; } = "3.0";
        public string DirectoryPath { get; set; } = "";
        public List<string> DirectoryPaths { get; set; } = new();
        public Dictionary<string, ImageItem> Items { get; set; } = new();
        public string Created { get; set; } = DateTime.Now.ToString("O");
        public string Modified { get; set; } = DateTime.Now.ToString("O");
        public bool IsModified { get; set; } = false;
        public string? WorkspacePath { get; set; }

        public event PropertyChangedEventHandler? PropertyChanged;

        // UI Helper properties
        public string WorkspaceName => string.IsNullOrEmpty(WorkspacePath) ? "Untitled Workspace" : System.IO.Path.GetFileNameWithoutExtension(WorkspacePath);

        public void AddItem(ImageItem item)
        {
            Items[item.FilePath] = item;
            MarkModified();
        }

        public void RemoveItem(string filePath)
        {
            if (Items.ContainsKey(filePath))
            {
                Items.Remove(filePath);
                MarkModified();
            }
        }

        private void MarkModified()
        {
            Modified = DateTime.Now.ToString("O");
            IsModified = true;
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(IsModified)));
        }
    }

    // AI Provider info for dropdown binding
    public class AIProviderInfo
    {
        public string Name { get; set; } = "";
        public string DisplayName { get; set; } = "";
        public bool IsAvailable { get; set; } = false;
        
        public AIProviderInfo() { }
        
        public AIProviderInfo(string name, string displayName, bool isAvailable = true)
        {
            Name = name;
            DisplayName = displayName;
            IsAvailable = isAvailable;
        }
    }
}