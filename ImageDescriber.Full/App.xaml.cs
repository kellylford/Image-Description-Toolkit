using System;
using System.Windows;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using ImageDescriber.Full.Services;
using ImageDescriber.Full.ViewModels;

namespace ImageDescriber.Full
{
    public partial class App : Application
    {
        private IHost? _host;

        protected override async void OnStartup(StartupEventArgs e)
        {
            // Create host with dependency injection
            _host = Host.CreateDefaultBuilder()
                .ConfigureServices((context, services) =>
                {
                    // Register HTTP clients
                    services.AddHttpClient();

                    // Register AI Providers
                    services.AddSingleton<IAIProvider, OpenAIProvider>();
                    services.AddSingleton<IAIProvider, OllamaProvider>();
                    services.AddSingleton<IAIProvider, HuggingFaceProvider>();

                    // Register AI Provider Service
                    services.AddSingleton<AIProviderService>();

                    // Register Workspace Service
                    services.AddSingleton<IWorkspaceService, WorkspaceService>();

                    // Register ViewModels
                    services.AddTransient<MainViewModel>();

                    // Register Views
                    services.AddSingleton<MainWindow>();

                    // Logging
                    services.AddLogging(builder =>
                    {
                        builder.AddDebug();
                        builder.SetMinimumLevel(LogLevel.Information);
                    });
                })
                .Build();

            await _host.StartAsync();

            // Get main window and set up data context
            var mainWindow = _host.Services.GetRequiredService<MainWindow>();
            var mainViewModel = _host.Services.GetRequiredService<MainViewModel>();
            
            mainWindow.DataContext = mainViewModel;
            mainWindow.Show();

            base.OnStartup(e);
        }

        protected override async void OnExit(ExitEventArgs e)
        {
            if (_host != null)
            {
                await _host.StopAsync();
                _host.Dispose();
            }
            base.OnExit(e);
        }
    }
}