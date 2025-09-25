using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ImageDescriber.Full;
using Microsoft.Extensions.Logging;
using Microsoft.Win32;
using Newtonsoft.Json;

namespace ImageDescriber.Full
{
    public partial class MainViewModel : ObservableObject
    {
        private readonly ILogger<MainViewModel> _logger;

        [ObservableProperty]
        private ImageWorkspace _currentWorkspace;

        [ObservableProperty]
        private ImageItem? _selectedImageItem;

        [ObservableProperty]
        private ImageDescription? _selectedDescription;

        [ObservableProperty]
        private string _statusMessage;

        [ObservableProperty]
        private double _progressValue;

        [ObservableProperty]
        private string _progressText;

        [ObservableProperty]
        private bool _isProcessing;

        // Collections for UI binding - exactly matching Python Qt6 structure
        public ObservableCollection<ImageItem> WorkspaceImages { get; } = new();
        public ObservableCollection<ImageDescription> SelectedImageDescriptions { get; } = new();

        // Computed properties for UI display
        public string BatchInfo
        {
            get
            {
                var batchCount = WorkspaceImages.Count(i => i.BatchMarked);
                return $"Batch Queue: {batchCount} items";
            }
        }

        public MainViewModel(ILogger<MainViewModel> logger)
        {
            _logger = logger;
            _currentWorkspace = new ImageWorkspace();
            _statusMessage = "Ready - Model verification disabled by default";
            _progressText = "";
            
            // Subscribe to property changes to update UI
            PropertyChanged += OnPropertyChanged;
        }

        private void OnPropertyChanged(object? sender, PropertyChangedEventArgs e)
        {
            switch (e.PropertyName)
            {
                case nameof(SelectedImageItem):
                    UpdateSelectedImageDescriptions();
                    break;
                case nameof(CurrentWorkspace):
                    UpdateWorkspaceImages();
                    break;
            }
        }

        private void UpdateSelectedImageDescriptions()
        {
            SelectedImageDescriptions.Clear();
            if (SelectedImageItem != null)
            {
                foreach (var desc in SelectedImageItem.Descriptions)
                {
                    SelectedImageDescriptions.Add(desc);
                }
                SelectedDescription = SelectedImageDescriptions.FirstOrDefault();
            }
        }

        private void UpdateWorkspaceImages()
        {
            WorkspaceImages.Clear();
            foreach (var item in CurrentWorkspace.Items.Values)
            {
                WorkspaceImages.Add(item);
            }
            OnPropertyChanged(nameof(BatchInfo));
        }

        [RelayCommand]
        private void NewWorkspace()
        {
            if (CurrentWorkspace.IsModified)
            {
                var result = System.Windows.MessageBox.Show(
                    "Current workspace has unsaved changes. Save before creating new workspace?",
                    "Unsaved Changes", 
                    MessageBoxButton.YesNoCancel, 
                    MessageBoxImage.Question);

                if (result == MessageBoxResult.Yes)
                {
                    SaveWorkspace();
                }
                else if (result == MessageBoxResult.Cancel)
                {
                    return;
                }
            }

            CurrentWorkspace = new ImageWorkspace();
            SelectedImageItem = null;
            SelectedDescription = null;
            StatusMessage = "New workspace created";
            UpdateWorkspaceImages();
        }

        [RelayCommand]
        private async Task OpenWorkspace()
        {
            try
            {
                var openFileDialog = new Microsoft.Win32.OpenFileDialog
                {
                    Filter = "ImageDescriber Workspace (*.idw)|*.idw",
                    Title = "Open Workspace"
                };

                if (openFileDialog.ShowDialog() == true)
                {
                    await LoadWorkspaceAsync(openFileDialog.FileName);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error opening workspace");
                System.Windows.MessageBox.Show($"Error opening workspace: {ex.Message}", "Error", 
                               MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private async Task LoadWorkspaceAsync(string filePath)
        {
            try
            {
                StatusMessage = "Loading workspace...";
                
                if (!File.Exists(filePath))
                {
                    throw new FileNotFoundException($"Workspace file not found: {filePath}");
                }

                var json = await File.ReadAllTextAsync(filePath);
                var workspaceData = JsonConvert.DeserializeObject<Dictionary<string, object>>(json);
                
                if (workspaceData == null)
                {
                    throw new InvalidOperationException("Failed to deserialize workspace data");
                }

                // Create new workspace and load data
                var newWorkspace = new ImageWorkspace();
                
                if (workspaceData.ContainsKey("version"))
                    newWorkspace.Version = workspaceData["version"].ToString() ?? "3.0";
                
                if (workspaceData.ContainsKey("directory_path"))
                    newWorkspace.DirectoryPath = workspaceData["directory_path"].ToString() ?? "";
                
                if (workspaceData.ContainsKey("directory_paths") && workspaceData["directory_paths"] is Newtonsoft.Json.Linq.JArray pathsArray)
                {
                    newWorkspace.DirectoryPaths = pathsArray.ToObject<List<string>>() ?? new List<string>();
                }

                if (workspaceData.ContainsKey("items") && workspaceData["items"] is Newtonsoft.Json.Linq.JObject itemsObj)
                {
                    foreach (var kvp in itemsObj)
                    {
                        var itemData = kvp.Value?.ToObject<Dictionary<string, object>>();
                        if (itemData != null)
                        {
                            var imageItem = new ImageItem(kvp.Key);
                            
                            if (itemData.ContainsKey("descriptions") && itemData["descriptions"] is Newtonsoft.Json.Linq.JArray descriptionsArray)
                            {
                                foreach (var descObj in descriptionsArray)
                                {
                                    var descData = descObj.ToObject<Dictionary<string, object>>();
                                    if (descData != null)
                                    {
                                        var description = new ImageDescription(
                                            descData.GetValueOrDefault("text", "").ToString() ?? "",
                                            descData.GetValueOrDefault("model", "").ToString() ?? "",
                                            descData.GetValueOrDefault("prompt_style", "").ToString() ?? "",
                                            descData.GetValueOrDefault("custom_prompt", "").ToString() ?? "",
                                            descData.GetValueOrDefault("provider", "").ToString() ?? ""
                                        );
                                        description.Id = descData.GetValueOrDefault("id", "").ToString() ?? "";
                                        description.Created = descData.GetValueOrDefault("created", "").ToString() ?? "";
                                        imageItem.AddDescription(description);
                                    }
                                }
                            }
                            
                            newWorkspace.AddItem(imageItem);
                        }
                    }
                }

                newWorkspace.WorkspacePath = filePath;
                newWorkspace.IsModified = false;
                
                CurrentWorkspace = newWorkspace;
                StatusMessage = $"Loaded workspace: {Path.GetFileName(filePath)} ({CurrentWorkspace.Items.Count} items)";
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error loading workspace from {FilePath}", filePath);
                StatusMessage = $"Failed to load workspace: {ex.Message}";
                throw;
            }
        }

        [RelayCommand]
        private async Task SaveWorkspace()
        {
            if (string.IsNullOrEmpty(CurrentWorkspace.WorkspacePath))
            {
                await SaveWorkspaceAs();
            }
            else
            {
                await SaveWorkspaceToFileAsync(CurrentWorkspace.WorkspacePath);
            }
        }

        [RelayCommand]
        private async Task SaveWorkspaceAs()
        {
            try
            {
                var saveFileDialog = new Microsoft.Win32.SaveFileDialog
                {
                    Filter = "ImageDescriber Workspace (*.idw)|*.idw",
                    Title = "Save Workspace As",
                    DefaultExt = ".idw"
                };

                if (saveFileDialog.ShowDialog() == true)
                {
                    await SaveWorkspaceToFileAsync(saveFileDialog.FileName);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error saving workspace");
                System.Windows.MessageBox.Show($"Error saving workspace: {ex.Message}", "Error", 
                               MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private async Task SaveWorkspaceToFileAsync(string filePath)
        {
            try
            {
                StatusMessage = "Saving workspace...";
                
                // Convert workspace to dictionary format matching Python
                var data = new Dictionary<string, object>
                {
                    ["version"] = CurrentWorkspace.Version,
                    ["directory_path"] = CurrentWorkspace.DirectoryPath,
                    ["directory_paths"] = CurrentWorkspace.DirectoryPaths,
                    ["items"] = CurrentWorkspace.Items.ToDictionary(
                        kvp => kvp.Key,
                        kvp => new Dictionary<string, object>
                        {
                            ["file_path"] = kvp.Value.FilePath,
                            ["item_type"] = kvp.Value.ItemType,
                            ["descriptions"] = kvp.Value.Descriptions.Select(d => new Dictionary<string, object>
                            {
                                ["id"] = d.Id,
                                ["text"] = d.Text,
                                ["model"] = d.Model,
                                ["prompt_style"] = d.PromptStyle,
                                ["created"] = d.Created,
                                ["custom_prompt"] = d.CustomPrompt,
                                ["provider"] = d.Provider
                            }).ToList()
                        }
                    ),
                    ["created"] = CurrentWorkspace.Created,
                    ["modified"] = DateTime.Now.ToString("O")
                };
                
                var json = JsonConvert.SerializeObject(data, Formatting.Indented);
                await File.WriteAllTextAsync(filePath, json);
                
                CurrentWorkspace.WorkspacePath = filePath;
                CurrentWorkspace.IsModified = false;
                StatusMessage = $"Workspace saved: {Path.GetFileName(filePath)}";
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error saving workspace to {FilePath}", filePath);
                StatusMessage = $"Failed to save workspace: {ex.Message}";
                throw;
            }
        }

        [RelayCommand]
        private async Task AddDirectory()
        {
            try
            {
                // Use proper FolderBrowserDialog as requested
                using var dialog = new System.Windows.Forms.FolderBrowserDialog
                {
                    Description = "Select directory containing images",
                    ShowNewFolderButton = false
                };

                var result = dialog.ShowDialog();
                if (result == System.Windows.Forms.DialogResult.OK && !string.IsNullOrEmpty(dialog.SelectedPath))
                {
                    await AddDirectoryToWorkspaceAsync(dialog.SelectedPath);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error adding directory");
                System.Windows.MessageBox.Show($"Error adding directory: {ex.Message}", "Error", 
                               MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private async Task AddDirectoryToWorkspaceAsync(string directoryPath)
        {
            try
            {
                StatusMessage = "Scanning directory...";
                
                var supportedExtensions = new[] { ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic" };
                var imageFiles = Directory.GetFiles(directoryPath, "*.*", SearchOption.AllDirectories)
                    .Where(f => supportedExtensions.Contains(Path.GetExtension(f).ToLowerInvariant()))
                    .ToList();

                int addedCount = 0;
                foreach (var filePath in imageFiles)
                {
                    if (!CurrentWorkspace.Items.ContainsKey(filePath))
                    {
                        var imageItem = new ImageItem(filePath);
                        CurrentWorkspace.AddItem(imageItem);
                        addedCount++;
                    }
                }

                if (!CurrentWorkspace.DirectoryPaths.Contains(directoryPath))
                {
                    CurrentWorkspace.DirectoryPaths.Add(directoryPath);
                }

                UpdateWorkspaceImages();
                StatusMessage = $"Added {addedCount} images from directory ({imageFiles.Count} total found)";
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error adding directory to workspace");
                StatusMessage = $"Error adding directory: {ex.Message}";
                throw;
            }
        }

        [RelayCommand]
        private void AddFiles()
        {
            try
            {
                var openFileDialog = new Microsoft.Win32.OpenFileDialog
                {
                    Filter = "Image Files|*.jpg;*.jpeg;*.png;*.gif;*.bmp;*.tiff;*.webp;*.heic",
                    Title = "Add Images",
                    Multiselect = true
                };

                if (openFileDialog.ShowDialog() == true)
                {
                    int addedCount = 0;
                    foreach (var filePath in openFileDialog.FileNames)
                    {
                        if (!CurrentWorkspace.Items.ContainsKey(filePath))
                        {
                            var imageItem = new ImageItem(filePath);
                            CurrentWorkspace.AddItem(imageItem);
                            addedCount++;
                        }
                    }
                    
                    UpdateWorkspaceImages();
                    StatusMessage = $"Added {addedCount} images to workspace";
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error adding files");
                System.Windows.MessageBox.Show($"Error adding files: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        // Placeholder commands - these would be implemented with actual AI integration
        [RelayCommand] private void ProcessSelected() => StatusMessage = "Process Selected - To be implemented";
        [RelayCommand] private void ProcessBatch() => StatusMessage = "Process Batch - To be implemented";
        [RelayCommand] private void StopProcessing() => StatusMessage = "Stop Processing - To be implemented";
        [RelayCommand] private void CopyDescription() => StatusMessage = "Copy Description - To be implemented";
        [RelayCommand] private void EditDescription() => StatusMessage = "Edit Description - To be implemented";
        [RelayCommand] private void DeleteDescription() => StatusMessage = "Delete Description - To be implemented";

        [RelayCommand]
        private void Exit()
        {
            if (CurrentWorkspace.IsModified)
            {
                var result = System.Windows.MessageBox.Show(
                    "Current workspace has unsaved changes. Save before exiting?",
                    "Unsaved Changes", 
                    MessageBoxButton.YesNoCancel, 
                    MessageBoxImage.Question);

                if (result == MessageBoxResult.Yes)
                {
                    SaveWorkspace();
                }
                else if (result == MessageBoxResult.Cancel)
                {
                    return;
                }
            }
            
            System.Windows.Application.Current.Shutdown();
        }

        [RelayCommand]
        private void About()
        {
            var version = System.Reflection.Assembly.GetExecutingAssembly().GetName().Version;
            System.Windows.MessageBox.Show($"ImageDescriber v{version}\nProfessional WPF Edition\n\nAI-powered image description toolkit exactly matching the Python Qt6 ImageDescriber interface.", 
                           "About ImageDescriber", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }
}