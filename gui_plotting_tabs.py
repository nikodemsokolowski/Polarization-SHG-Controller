import customtkinter as ctk

# Import individual tab classes (will be created next)
from gui_live_spectrum_tab import LiveSpectrumTab
from gui_analysis_tab import AnalysisTab

class PlottingTabs(ctk.CTkTabview):
    """
    Tab view containing the different plotting and analysis tabs.
    """
    # Modify __init__ to accept app_instance
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.app = app_instance # Store app instance
        self.plotting_module = app_instance.plotting_module # Get plotting module from app

        # Add tabs
        self.add("Live Spectrum")
        self.add("Intensity Analysis")
        # self.add("Advanced Fit") # Example for future expansion

        # Create content for each tab
        # Pass plotting_module to LiveSpectrumTab
        self.live_spectrum_tab = LiveSpectrumTab(self.tab("Live Spectrum"), self.plotting_module)
        self.live_spectrum_tab.pack(expand=True, fill="both")

        # Pass the full app_instance to AnalysisTab
        self.analysis_tab = AnalysisTab(self.tab("Intensity Analysis"), self.app)
        self.analysis_tab.pack(expand=True, fill="both")

        # TODO: Create and pack content for other tabs if added
        # self.advanced_fit_tab = AdvancedFitTab(self.tab("Advanced Fit"), plotting_module)
        # self.advanced_fit_tab.pack(expand=True, fill="both")

        # Set default tab (optional)
        self.set("Live Spectrum")

# Example usage (for testing this frame independently)
if __name__ == "__main__":
    # Mock plotting module and tab contents for testing
    class MockPlottingModule:
        def setup_live_plot(self, ax): print("Setting up live plot")
        def setup_analysis_plot(self, ax): print("Setting up analysis plot")
        def update_live_plot(self, data): print(f"Updating live plot with: {data}")
        def update_analysis_plot(self, data): print(f"Updating analysis plot with: {data}")

    class MockLiveSpectrumTab(ctk.CTkFrame):
        def __init__(self, master, plotter):
            super().__init__(master, fg_color="darkgrey")
            ctk.CTkLabel(self, text="Live Spectrum Plot Area").pack(pady=20)
            print("Mock Live Spectrum Tab Initialized")

    class MockAnalysisTab(ctk.CTkFrame):
        def __init__(self, master, plotter):
            super().__init__(master, fg_color="grey")
            ctk.CTkLabel(self, text="Analysis Plot Area & Controls").pack(pady=20)
            print("Mock Analysis Tab Initialized")

    # Monkey patch the real classes with mocks for standalone test
    LiveSpectrumTab = MockLiveSpectrumTab
    AnalysisTab = MockAnalysisTab

    app = ctk.CTk()
    app.geometry("700x500")
    app.title("Plotting Tabs Test")

    # Mock app instance for testing
    class MockApp:
        plotting_module = MockPlottingModule()
        # Add other attributes AnalysisTab might need from app if testing standalone
        main_window = None # Placeholder
        def update_status_bar(self, msg, error=False): print(f"STATUS: {msg}")

    mock_app_instance = MockApp()
    tab_view = PlottingTabs(app, mock_app_instance) # Pass mock app instance
    tab_view.pack(expand=True, fill="both", padx=10, pady=10)

    app.mainloop()
