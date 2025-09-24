using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using ImageDescriber.Full.Models;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;

namespace ImageDescriber.Full.Services
{
    public interface IWorkspaceService
    {
        Task<ImageWorkspace> LoadWorkspaceAsync(string filePath);
        Task SaveWorkspaceAsync(ImageWorkspace workspace, string filePath);
        Task<List<ImageItem>> LoadDirectoryAsync(string directoryPath);
        bool ValidateWorkspaceFile(string filePath);
    }

    public class WorkspaceService : IWorkspaceService
    {
        private readonly ILogger<WorkspaceService> _logger;
        private static readonly string[] SupportedImageExtensions = 
        {
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".heic"
        };

        public WorkspaceService(ILogger<WorkspaceService> logger)
        {
            _logger = logger;
        }

        public async Task<ImageWorkspace> LoadWorkspaceAsync(string filePath)
        {
            try
            {
                if (!File.Exists(filePath))
                {
                    throw new FileNotFoundException($"Workspace file not found: {filePath}");
                }

                _logger.LogInformation("Loading workspace from {FilePath}", filePath);

                var json = await File.ReadAllTextAsync(filePath);
                var data = JsonConvert.DeserializeObject<Dictionary<string, object>>(json);
                
                if (data == null)
                {
                    throw new InvalidOperationException("Failed to deserialize workspace data");
                }

                var workspace = ImageWorkspace.FromDictionary(data);
                workspace.WorkspacePath = filePath;

                // Validate file paths and update any that have moved
                await ValidateAndUpdateFilePathsAsync(workspace);

                _logger.LogInformation("Successfully loaded workspace with {ItemCount} items", workspace.Items.Count);
                return workspace;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error loading workspace from {FilePath}", filePath);
                throw;
            }
        }

        public async Task SaveWorkspaceAsync(ImageWorkspace workspace, string filePath)
        {
            try
            {
                _logger.LogInformation("Saving workspace to {FilePath}", filePath);

                workspace.WorkspacePath = filePath;
                var data = workspace.ToDictionary();
                var json = JsonConvert.SerializeObject(data, Formatting.Indented);
                
                // Create directory if it doesn't exist
                var directory = Path.GetDirectoryName(filePath);
                if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
                {
                    Directory.CreateDirectory(directory);
                }

                await File.WriteAllTextAsync(filePath, json);

                _logger.LogInformation("Successfully saved workspace");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error saving workspace to {FilePath}", filePath);
                throw;
            }
        }

        public async Task<List<ImageItem>> LoadDirectoryAsync(string directoryPath)
        {
            try
            {
                if (!Directory.Exists(directoryPath))
                {
                    throw new DirectoryNotFoundException($"Directory not found: {directoryPath}");
                }

                _logger.LogInformation("Loading images from directory {DirectoryPath}", directoryPath);

                var imageItems = new List<ImageItem>();
                var files = Directory.GetFiles(directoryPath, "*.*", SearchOption.AllDirectories);

                await Task.Run(() =>
                {
                    foreach (var filePath in files)
                    {
                        var extension = Path.GetExtension(filePath).ToLowerInvariant();
                        if (Array.Exists(SupportedImageExtensions, ext => ext == extension))
                        {
                            var imageItem = new ImageItem(filePath);
                            imageItems.Add(imageItem);
                        }
                    }
                });

                _logger.LogInformation("Found {ImageCount} images in directory", imageItems.Count);
                return imageItems;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error loading directory {DirectoryPath}", directoryPath);
                throw;
            }
        }

        public bool ValidateWorkspaceFile(string filePath)
        {
            try
            {
                if (!File.Exists(filePath))
                    return false;

                var json = File.ReadAllText(filePath);
                var data = JsonConvert.DeserializeObject<Dictionary<string, object>>(json);
                
                return data != null && data.ContainsKey("version");
            }
            catch
            {
                return false;
            }
        }

        private async Task ValidateAndUpdateFilePathsAsync(ImageWorkspace workspace)
        {
            var itemsToUpdate = new List<(string oldPath, string newPath)>();
            
            await Task.Run(() =>
            {
                foreach (var kvp in workspace.Items)
                {
                    var filePath = kvp.Value.FilePath;
                    if (!File.Exists(filePath))
                    {
                        // Try to find the file with same name in workspace directories
                        var fileName = Path.GetFileName(filePath);
                        foreach (var dir in workspace.DirectoryPaths)
                        {
                            var possiblePath = Path.Combine(dir, fileName);
                            if (File.Exists(possiblePath))
                            {
                                itemsToUpdate.Add((filePath, possiblePath));
                                break;
                            }
                        }
                    }
                }
            });

            // Update file paths
            foreach (var (oldPath, newPath) in itemsToUpdate)
            {
                if (workspace.Items.TryGetValue(oldPath, out var item))
                {
                    workspace.Items.Remove(oldPath);
                    item.FilePath = newPath;
                    workspace.Items[newPath] = item;
                    _logger.LogInformation("Updated file path from {OldPath} to {NewPath}", oldPath, newPath);
                }
            }
        }
    }
}