using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ImageDescriber.Full.Models;
using ImageDescriber.Full.Services;
using Microsoft.Extensions.Logging;
using Microsoft.Win32;

namespace ImageDescriber.Full.ViewModels
{
    public partial class MainViewModel : ObservableObject
    {
        private readonly AIProviderService _aiProviderService;
        private readonly IWorkspaceService _workspaceService;
        private readonly ILogger<MainViewModel> _logger;
        private CancellationTokenSource? _processingCancellationToken;

        [ObservableProperty]
        private ImageWorkspace _currentWorkspace;

        [ObservableProperty]
        private ImageItem? _selectedImageItem;

        [ObservableProperty]
        private ImageDescription? _selectedDescription;

        [ObservableProperty]
        private ObservableCollection<AIProviderInfo> _availableProviders;

        [ObservableProperty]
        private AIProviderInfo? _selectedProvider;

        [ObservableProperty]
        private ObservableCollection<string> _availableModels;

        [ObservableProperty]
        private string? _selectedModel;

        [ObservableProperty]
        private string _statusMessage;

        [ObservableProperty]
        private double _progressValue;

        [ObservableProperty]
        private string _progressText;

        [ObservableProperty]
        private bool _isProcessing;

        // UI binding properties - fixes data binding issues mentioned in issue
        public ObservableCollection<ImageItem> WorkspaceItems => 
            new ObservableCollection<ImageItem>(CurrentWorkspace.Items.Values);

        public string WorkspaceName => CurrentWorkspace.WorkspaceName;

        // Fix for SelectedProviderName vs SelectedProvider issue
        public string? SelectedProviderName => SelectedProvider?.DisplayName;

        public MainViewModel(AIProviderService aiProviderService, IWorkspaceService workspaceService, ILogger<MainViewModel> logger)
        {
            _aiProviderService = aiProviderService;
            _workspaceService = workspaceService;
            _logger = logger;
            _currentWorkspace = new ImageWorkspace();
            _availableProviders = new ObservableCollection<AIProviderInfo>();
            _availableModels = new ObservableCollection<string>();
            _statusMessage = "Ready";
            _progressText = "";

            InitializeAsync();
        }

        private async void InitializeAsync()
        {
            await LoadAvailableProvidersAsync();
        }

        private async Task LoadAvailableProvidersAsync()
        {
            try
            {
                StatusMessage = "Loading AI providers...";
                var providers = _aiProviderService.GetAvailableProviders();
                
                AvailableProviders.Clear();
                foreach (var provider in providers)
                {
                    AvailableProviders.Add(provider);
                }

                // Select first available provider
                SelectedProvider = AvailableProviders.FirstOrDefault(p => p.IsAvailable) 
                                 ?? AvailableProviders.FirstOrDefault();
                
                if (SelectedProvider != null)
                {
                    await RefreshModelsAsync();
                }

                StatusMessage = $"Loaded {providers.Count} AI providers";
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error loading available providers");
                StatusMessage = "Error loading AI providers";
            }
        }

        [RelayCommand]
        private async Task RefreshModels()
        {
            await RefreshModelsAsync();
        }

        private async Task RefreshModelsAsync()
        {
            if (SelectedProvider == null) return;

            try
            {
                StatusMessage = "Loading models...";
                var models = await _aiProviderService.GetAvailableModelsAsync(SelectedProvider.Value);
                
                AvailableModels.Clear();
                foreach (var model in models)
                {
                    AvailableModels.Add(model);
                }

                SelectedModel = AvailableModels.FirstOrDefault();
                StatusMessage = $"Loaded {models.Count} models for {SelectedProvider.DisplayName}";
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error refreshing models for provider {ProviderName}", SelectedProvider.DisplayName);
                StatusMessage = $"Error loading models: {ex.Message}";
                
                // Add fallback models to prevent empty list
                AvailableModels.Clear();
                AvailableModels.Add($"{SelectedProvider.DisplayName} (Error loading models)");
                SelectedModel = AvailableModels.FirstOrDefault();
            }
        }

        [RelayCommand]
        private async Task NewWorkspace()
        {
            if (CurrentWorkspace.IsModified)
            {
                var result = MessageBox.Show(
                    "Current workspace has unsaved changes. Save before creating new workspace?",
                    "Unsaved Changes", 
                    MessageBoxButton.YesNoCancel, 
                    MessageBoxImage.Question);

                if (result == MessageBoxResult.Yes)
                {
                    await SaveWorkspace();
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
            OnPropertyChanged(nameof(WorkspaceItems));
            OnPropertyChanged(nameof(WorkspaceName));
        }

        [RelayCommand]
        private async Task OpenWorkspace()
        {
            try
            {
                var openFileDialog = new OpenFileDialog
                {
                    Filter = "ImageDescriber Workspace (*.idw)|*.idw",
                    Title = "Open Workspace"
                };

                if (openFileDialog.ShowDialog() == true)
                {
                    // Fix for OpenWorkspaceCommand - use proper async LoadAsync method
                    await LoadWorkspaceAsync(openFileDialog.FileName);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error opening workspace");
                MessageBox.Show($"Error opening workspace: {ex.Message}", "Error", 
                               MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private async Task LoadWorkspaceAsync(string filePath)
        {
            try
            {
                StatusMessage = "Loading workspace...";
                ProgressText = "Loading workspace file...";
                ProgressValue = 25;
                
                // Use workspace service for proper loading
                CurrentWorkspace = await _workspaceService.LoadWorkspaceAsync(filePath);
                
                ProgressValue = 75;
                ProgressText = "Refreshing UI...";
                
                // Refresh UI after successful load
                OnPropertyChanged(nameof(WorkspaceItems));
                OnPropertyChanged(nameof(WorkspaceName));
                
                ProgressValue = 100;
                ProgressText = "Complete";
                StatusMessage = $"Loaded workspace: {Path.GetFileName(filePath)} ({CurrentWorkspace.Items.Count} items)";
                
                // Clear progress after delay
                await Task.Delay(2000);
                ProgressValue = 0;
                ProgressText = "";
            }
            catch (Exception ex)
            {
                ProgressValue = 0;
                ProgressText = "";
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
                var saveFileDialog = new SaveFileDialog
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
                MessageBox.Show($"Error saving workspace: {ex.Message}", "Error", 
                               MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private async Task SaveWorkspaceToFileAsync(string filePath)
        {
            try
            {
                StatusMessage = "Saving workspace...";
                ProgressText = "Saving workspace...";
                ProgressValue = 50;
                
                await _workspaceService.SaveWorkspaceAsync(CurrentWorkspace, filePath);
                
                ProgressValue = 100;
                ProgressText = "Saved";
                StatusMessage = $"Workspace saved: {Path.GetFileName(filePath)}";
                OnPropertyChanged(nameof(WorkspaceName));
                
                // Clear progress after delay
                await Task.Delay(1500);
                ProgressValue = 0;
                ProgressText = "";
            }
            catch (Exception ex)
            {
                ProgressValue = 0;
                ProgressText = "";
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
                // Using folder browser dialog would require additional NuGet package
                // For now, show a message - this addresses the directory loading issue
                var dialog = new OpenFileDialog
                {
                    Title = "Select any image in the directory you want to add",
                    Filter = "Image Files|*.jpg;*.jpeg;*.png;*.gif;*.bmp;*.tiff;*.webp;*.heic",
                    CheckFileExists = true
                };

                if (dialog.ShowDialog() == true)
                {
                    var directoryPath = Path.GetDirectoryName(dialog.FileName);
                    if (!string.IsNullOrEmpty(directoryPath))
                    {
                        await AddDirectoryToWorkspaceAsync(directoryPath);
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error adding directory");
                MessageBox.Show($"Error adding directory: {ex.Message}", "Error", 
                               MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private async Task AddDirectoryToWorkspaceAsync(string directoryPath)
        {
            try
            {
                StatusMessage = "Scanning directory...";
                ProgressText = "Finding images...";
                ProgressValue = 25;
                
                var imageItems = await _workspaceService.LoadDirectoryAsync(directoryPath);
                
                ProgressValue = 50;
                ProgressText = "Adding to workspace...";
                
                int addedCount = 0;
                foreach (var imageItem in imageItems)
                {
                    if (!CurrentWorkspace.Items.ContainsKey(imageItem.FilePath))
                    {
                        CurrentWorkspace.AddItem(imageItem);
                        addedCount++;
                    }
                }

                if (!CurrentWorkspace.DirectoryPaths.Contains(directoryPath))
                {
                    CurrentWorkspace.DirectoryPaths.Add(directoryPath);
                }

                ProgressValue = 100;
                ProgressText = "Complete";
                OnPropertyChanged(nameof(WorkspaceItems));
                
                StatusMessage = $"Added {addedCount} images from directory ({imageItems.Count} total found)";
                
                // Clear progress after delay
                await Task.Delay(2000);
                ProgressValue = 0;
                ProgressText = "";
            }
            catch (Exception ex)
            {
                ProgressValue = 0;
                ProgressText = "";
                _logger.LogError(ex, "Error adding directory to workspace");
                StatusMessage = $"Error adding directory: {ex.Message}";
                throw;
            }
        }

        [RelayCommand]
        private async Task ProcessSelected()
        {
            if (SelectedImageItem == null || SelectedProvider == null || string.IsNullOrEmpty(SelectedModel))
            {
                MessageBox.Show("Please select an image and configure AI provider/model.", 
                               "Configuration Required", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            await ProcessImageAsync(SelectedImageItem);
        }

        [RelayCommand]
        private async Task ProcessBatch()
        {
            var batchItems = CurrentWorkspace.Items.Values.Where(i => i.BatchMarked).ToList();
            if (batchItems.Count == 0)
            {
                MessageBox.Show("No items marked for batch processing.", 
                               "No Items Selected", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            if (SelectedProvider == null || string.IsNullOrEmpty(SelectedModel))
            {
                MessageBox.Show("Please configure AI provider and model before batch processing.", 
                               "Configuration Required", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            await ProcessBatchAsync(batchItems);
        }

        private async Task ProcessImageAsync(ImageItem imageItem)
        {
            if (SelectedProvider == null || string.IsNullOrEmpty(SelectedModel)) return;

            try
            {
                IsProcessing = true;
                ProgressValue = 0;
                ProgressText = $"Processing {imageItem.FileName}...";
                StatusMessage = "Processing image...";

                _processingCancellationToken = new CancellationTokenSource();

                ProgressValue = 25;
                ProgressText = "Generating description...";

                // Simple prompt - could be made configurable in AI Settings
                var prompt = "Describe this image in detail, including the main subjects, setting, colors, and any notable features or activities.";

                var description = await _aiProviderService.GenerateDescriptionAsync(
                    SelectedProvider.Value, SelectedModel, imageItem.FilePath, prompt);

                ProgressValue = 75;
                ProgressText = "Saving description...";

                var imageDescription = new ImageDescription(
                    description, SelectedModel, "detailed", "", SelectedProvider.DisplayName);

                imageItem.AddDescription(imageDescription);
                
                ProgressValue = 100;
                ProgressText = "Complete";
                StatusMessage = "Image processed successfully";

                // Auto-select the new description
                if (SelectedImageItem == imageItem)
                {
                    SelectedDescription = imageDescription;
                }
            }
            catch (OperationCanceledException)
            {
                StatusMessage = "Processing cancelled";
                ProgressText = "Cancelled";
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error processing image {ImagePath}", imageItem.FilePath);
                MessageBox.Show($"Error processing image: {ex.Message}", "Processing Error", 
                               MessageBoxButton.OK, MessageBoxImage.Error);
                StatusMessage = "Processing failed";
                ProgressText = "Failed";
            }
            finally
            {
                IsProcessing = false;
                // Clear progress after delay
                await Task.Delay(2000);
                ProgressValue = 0;
                ProgressText = "";
                _processingCancellationToken?.Dispose();
                _processingCancellationToken = null;
            }
        }

        private async Task ProcessBatchAsync(List<ImageItem> items)
        {
            if (SelectedProvider == null || string.IsNullOrEmpty(SelectedModel)) return;

            try
            {
                IsProcessing = true;
                _processingCancellationToken = new CancellationTokenSource();

                for (int i = 0; i < items.Count; i++)
                {
                    if (_processingCancellationToken.Token.IsCancellationRequested)
                        break;

                    var item = items[i];
                    var overallProgress = (double)i / items.Count * 100;
                    ProgressValue = overallProgress;
                    ProgressText = $"Processing {i + 1} of {items.Count}: {item.FileName}";
                    StatusMessage = $"Batch processing... ({i + 1}/{items.Count})";

                    // Process individual image
                    try
                    {
                        var prompt = "Describe this image in detail, including the main subjects, setting, colors, and any notable features or activities.";
                        var description = await _aiProviderService.GenerateDescriptionAsync(
                            SelectedProvider.Value, SelectedModel, item.FilePath, prompt);

                        var imageDescription = new ImageDescription(
                            description, SelectedModel, "detailed", "", SelectedProvider.DisplayName);
                        item.AddDescription(imageDescription);
                    }
                    catch (Exception ex)
                    {
                        _logger.LogError(ex, "Error processing image {ImagePath} in batch", item.FilePath);
                        // Continue with other images
                    }
                    
                    // Small delay between items to prevent overwhelming the API
                    if (i < items.Count - 1) // Don't delay after the last item
                    {
                        await Task.Delay(2000, _processingCancellationToken.Token);
                    }
                }

                ProgressValue = 100;
                ProgressText = "Batch complete";
                StatusMessage = $"Batch processing completed: {items.Count} items processed";
            }
            catch (OperationCanceledException)
            {
                StatusMessage = "Batch processing cancelled";
                ProgressText = "Cancelled";
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in batch processing");
                StatusMessage = "Batch processing failed";
                ProgressText = "Failed";
            }
            finally
            {
                IsProcessing = false;
                // Clear progress after delay
                await Task.Delay(3000);
                ProgressValue = 0;
                ProgressText = "";
                _processingCancellationToken?.Dispose();
                _processingCancellationToken = null;
            }
        }

        [RelayCommand]
        private void StopProcessing()
        {
            _processingCancellationToken?.Cancel();
            StatusMessage = "Stopping processing...";
            ProgressText = "Stopping...";
        }

        [RelayCommand]
        private void EditDescription()
        {
            if (SelectedDescription == null) return;
            
            // Simple edit dialog - could be enhanced with proper dialog
            var currentText = SelectedDescription.Text;
            var result = Microsoft.VisualBasic.Interaction.InputBox(
                "Edit description:", "Edit Description", currentText);
            
            if (!string.IsNullOrEmpty(result) && result != currentText)
            {
                SelectedDescription.Text = result;
                StatusMessage = "Description updated";
            }
        }

        [RelayCommand]
        private void DeleteDescription()
        {
            if (SelectedDescription == null || SelectedImageItem == null) return;
            
            var result = MessageBox.Show("Are you sure you want to delete this description?", 
                                        "Confirm Delete", MessageBoxButton.YesNo, MessageBoxImage.Question);
            
            if (result == MessageBoxResult.Yes)
            {
                SelectedImageItem.RemoveDescription(SelectedDescription.Id);
                SelectedDescription = SelectedImageItem.Descriptions.FirstOrDefault();
                StatusMessage = "Description deleted";
            }
        }

        [RelayCommand]
        private void CopyDescription()
        {
            if (SelectedDescription == null) return;
            
            try
            {
                Clipboard.SetText(SelectedDescription.Text);
                StatusMessage = "Description copied to clipboard";
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error copying to clipboard");
                StatusMessage = "Error copying to clipboard";
            }
        }

        [RelayCommand]
        private void ToggleBatchMark()
        {
            if (SelectedImageItem == null) return;
            
            SelectedImageItem.BatchMarked = !SelectedImageItem.BatchMarked;
            StatusMessage = SelectedImageItem.BatchMarked ? "Marked for batch processing" : "Unmarked from batch processing";
        }

        [RelayCommand]
        private void MarkAllBatch()
        {
            int markedCount = 0;
            foreach (var item in CurrentWorkspace.Items.Values)
            {
                if (!item.BatchMarked)
                {
                    item.BatchMarked = true;
                    markedCount++;
                }
            }
            StatusMessage = $"Marked {markedCount} items for batch processing";
        }

        [RelayCommand]
        private void ClearAllBatchMarks()
        {
            int unmarkedCount = 0;
            foreach (var item in CurrentWorkspace.Items.Values)
            {
                if (item.BatchMarked)
                {
                    item.BatchMarked = false;
                    unmarkedCount++;
                }
            }
            StatusMessage = $"Cleared {unmarkedCount} batch marks";
        }

        [RelayCommand]
        private void Exit()
        {
            if (CurrentWorkspace.IsModified)
            {
                var result = MessageBox.Show(
                    "Current workspace has unsaved changes. Save before exiting?",
                    "Unsaved Changes", 
                    MessageBoxButton.YesNoCancel, 
                    MessageBoxImage.Question);

                if (result == MessageBoxResult.Yes)
                {
                    SaveWorkspace().Wait();
                }
                else if (result == MessageBoxResult.Cancel)
                {
                    return;
                }
            }
            
            Application.Current.Shutdown();
        }

        [RelayCommand]
        private void About()
        {
            var version = System.Reflection.Assembly.GetExecutingAssembly().GetName().Version;
            MessageBox.Show($"ImageDescriber.Full v{version}\nProfessional WPF Edition\n\nAI-powered image description toolkit with support for:\n• OpenAI GPT-4 Vision\n• Ollama (Local Models)\n• Hugging Face Models\n\nBuilt with .NET 8 and WPF", 
                           "About ImageDescriber", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        // Additional command implementations for menu items
        [RelayCommand] 
        private void AddFiles() 
        {
            try
            {
                var openFileDialog = new OpenFileDialog
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
                    
                    OnPropertyChanged(nameof(WorkspaceItems));
                    StatusMessage = $"Added {addedCount} images to workspace";
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error adding files");
                MessageBox.Show($"Error adding files: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        
        [RelayCommand] 
        private void ShowAISettings() 
        {
            // This would open a settings dialog for API keys and provider configuration
            MessageBox.Show("AI Settings dialog will be implemented.\n\nFor now, configure API keys via:\n• Environment variables (OPENAI_API_KEY, HUGGINGFACE_API_KEY)\n• Configuration files\n• Provider-specific settings", 
                           "AI Settings", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        
        [RelayCommand] 
        private void ExtractVideoFrames() => MessageBox.Show("Extract Video Frames functionality will be implemented", "TODO");
        [RelayCommand] 
        private void ConvertHeic() => MessageBox.Show("Convert HEIC functionality will be implemented", "TODO");
        [RelayCommand] 
        private void ExportDescriptions() => MessageBox.Show("Export Descriptions functionality will be implemented", "TODO");
        [RelayCommand] 
        private void ShowUserGuide() => MessageBox.Show("User Guide functionality will be implemented", "TODO");

        // Property change notifications for UI binding fixes
        partial void OnSelectedProviderChanged(AIProviderInfo? value)
        {
            OnPropertyChanged(nameof(SelectedProviderName));
            if (value != null)
            {
                _ = RefreshModelsAsync();
            }
        }

        partial void OnCurrentWorkspaceChanged(ImageWorkspace value)
        {
            OnPropertyChanged(nameof(WorkspaceItems));
            OnPropertyChanged(nameof(WorkspaceName));
        }

        partial void OnSelectedImageItemChanged(ImageItem? value)
        {
            SelectedDescription = value?.Descriptions.FirstOrDefault();
        }
    }
}