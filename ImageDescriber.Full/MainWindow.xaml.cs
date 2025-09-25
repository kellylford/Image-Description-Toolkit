using System;
using System.Windows;
using ImageDescriber.Full;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace ImageDescriber.Full
{
    public partial class MainWindow : Window
    {
        public MainWindow()
        {
            InitializeComponent();
            
            // Set up dependency injection and ViewModel
            var services = new ServiceCollection();
            services.AddLogging(builder => builder.AddConsole());
            services.AddTransient<MainViewModel>();
            
            var serviceProvider = services.BuildServiceProvider();
            DataContext = serviceProvider.GetService<MainViewModel>();
            
            // Set window properties for accessibility
            Title = "ImageDescriber - Professional WPF Edition";
            
            // Focus management for accessibility
            Loaded += (s, e) => MoveFocus(new System.Windows.Input.TraversalRequest(System.Windows.Input.FocusNavigationDirection.First));
        }
    }
}