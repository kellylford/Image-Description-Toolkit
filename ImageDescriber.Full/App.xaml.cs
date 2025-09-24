using System.Windows;

namespace ImageDescriber.Full
{
    /// <summary>
    /// Interaction logic for App.xaml
    /// </summary>
    public partial class App : Application
    {
        protected override void OnStartup(StartupEventArgs e)
        {
            // Set application properties for accessibility
            Current.ShutdownMode = ShutdownMode.OnMainWindowClose;
            
            base.OnStartup(e);
        }
    }
}