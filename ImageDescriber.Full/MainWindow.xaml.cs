using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
using System.IO;
using System.Collections.Generic;
using System.Linq;

namespace ImageDescriber.Full
{
    public partial class MainWindow : Window
    {
        private List<ImageItem> _images = new List<ImageItem>();
        private ImageItem? _selectedImage;
        private int _batchCount = 0;

        public MainWindow()
        {
            InitializeComponent();
            UpdateStatus("Ready");
            UpdateBatchInfo();
        }

        private void UpdateStatus(string message)
        {
            StatusText.Text = message;
        }

        private void UpdateBatchInfo()
        {
            BatchQueueText.Text = $"Batch Queue: {_batchCount}";
        }

        // Menu Handlers
        private void NewWorkspace_Click(object sender, RoutedEventArgs e)
        {
            _images.Clear();
            _selectedImage = null;
            ImagesList.Items.Clear();
            DescriptionsList.Items.Clear();
            DescriptionTextBox.Text = "";
            _batchCount = 0;
            UpdateStatus("New workspace created");
            UpdateBatchInfo();
        }

        private void OpenWorkspace_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFileDialog
            {
                Filter = "IDW Workspace Files (*.idw)|*.idw|All Files (*.*)|*.*",
                Title = "Open Workspace"
            };

            if (dialog.ShowDialog() == true)
            {
                UpdateStatus($"Opening workspace: {Path.GetFileName(dialog.FileName)}");
                // TODO: Implement IDW file loading
            }
        }

        private void SaveWorkspace_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new SaveFileDialog
            {
                Filter = "IDW Workspace Files (*.idw)|*.idw|All Files (*.*)|*.*",
                Title = "Save Workspace",
                DefaultExt = "idw"
            };

            if (dialog.ShowDialog() == true)
            {
                UpdateStatus($"Saving workspace: {Path.GetFileName(dialog.FileName)}");
                // TODO: Implement IDW file saving
            }
        }

        private void AddDirectory_Click(object sender, RoutedEventArgs e)
        {
            // Use WPF FolderBrowserDialog alternative
            var dialog = new OpenFileDialog
            {
                Title = "Select Directory (choose any file in the target directory)",
                Filter = "All Files (*.*)|*.*",
                Multiselect = false,
                CheckFileExists = false,
                CheckPathExists = true
            };

            if (dialog.ShowDialog() == true)
            {
                string selectedDirectory = Path.GetDirectoryName(dialog.FileName) ?? "";
                if (!string.IsNullOrEmpty(selectedDirectory))
                {
                    LoadImagesFromDirectory(selectedDirectory);
                }
            }
        }

        private void AddFiles_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFileDialog
            {
                Filter = "Image Files|*.jpg;*.jpeg;*.png;*.gif;*.bmp;*.tiff;*.webp|All Files (*.*)|*.*",
                Title = "Select Image Files",
                Multiselect = true
            };

            if (dialog.ShowDialog() == true)
            {
                foreach (string filename in dialog.FileNames)
                {
                    AddImageFile(filename);
                }
                RefreshImagesList();
                UpdateStatus($"Added {dialog.FileNames.Length} files");
            }
        }

        private void Exit_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }

        private void ProcessImages_Click(object sender, RoutedEventArgs e)
        {
            UpdateStatus("Image processing not yet implemented");
        }

        private void StopProcessing_Click(object sender, RoutedEventArgs e)
        {
            UpdateStatus("Processing stopped");
        }

        private void About_Click(object sender, RoutedEventArgs e)
        {
            MessageBox.Show("ImageDescriber WPF Edition\n\nProfessional AI-powered image description toolkit matching Python Qt6 ImageDescriber functionality.", 
                "About ImageDescriber", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        // Helper Methods
        private void LoadImagesFromDirectory(string directoryPath)
        {
            var imageExtensions = new[] { ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp" };
            var files = Directory.GetFiles(directoryPath, "*.*", SearchOption.AllDirectories)
                                 .Where(f => imageExtensions.Contains(Path.GetExtension(f).ToLower()))
                                 .ToArray();

            foreach (string file in files)
            {
                AddImageFile(file);
            }

            RefreshImagesList();
            UpdateStatus($"Loaded {files.Length} images from directory");
        }

        private void AddImageFile(string filePath)
        {
            var imageItem = new ImageItem
            {
                FilePath = filePath,
                FileName = Path.GetFileName(filePath),
                DescriptionCount = 0
            };

            _images.Add(imageItem);
        }

        private void RefreshImagesList()
        {
            ImagesList.Items.Clear();
            foreach (var image in _images)
            {
                var displayText = $"{image.FileName} ({image.DescriptionCount})";
                ImagesList.Items.Add(displayText);
            }
        }

        // Event Handlers
        private void ImagesList_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ImagesList.SelectedIndex >= 0 && ImagesList.SelectedIndex < _images.Count)
            {
                _selectedImage = _images[ImagesList.SelectedIndex];
                LoadDescriptionsForSelectedImage();
                UpdateStatus($"Selected: {_selectedImage.FileName}");
            }
        }

        private void DescriptionsList_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (DescriptionsList.SelectedItem is string selectedDescription)
            {
                DescriptionTextBox.Text = selectedDescription;
            }
        }

        private void LoadDescriptionsForSelectedImage()
        {
            DescriptionsList.Items.Clear();
            DescriptionTextBox.Text = "";
            
            if (_selectedImage != null)
            {
                // TODO: Load actual descriptions for this image
                // For now, show placeholder
                if (_selectedImage.DescriptionCount == 0)
                {
                    DescriptionsList.Items.Add("No descriptions yet - use Process menu to generate");
                }
            }
        }
    }

    // Simple data model
    public class ImageItem
    {
        public string FilePath { get; set; } = "";
        public string FileName { get; set; } = "";
        public int DescriptionCount { get; set; } = 0;
    }
}