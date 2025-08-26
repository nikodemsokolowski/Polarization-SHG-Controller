import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# Configure Matplotlib for dark/light mode compatibility (optional)
# plt.style.use('seaborn-v0_8-darkgrid') # Example style

class LiveSpectrumTab(ctk.CTkFrame):
    """
    Tab displaying the live spectrum acquired from LightField.
    """
    def __init__(self, master, plotting_module):
        super().__init__(master, fg_color="transparent")
        self.plotting_module = plotting_module

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Matplotlib Figure and Canvas ---
        # Use a specific figure number or label if managing multiple plots elsewhere
        self.fig, self.ax = plt.subplots(figsize=(5, 4), dpi=100)
        # self.fig.patch.set_facecolor(self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])) # Match theme bg
        # self.ax.set_facecolor(self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])) # Match theme bg

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, padx=10, pady=(0, 5), sticky="nsew")

        # --- Matplotlib Toolbar ---
        self.toolbar_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.toolbar_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.toolbar_frame)
        self.toolbar.update()

        # --- Initial Plot Setup ---
        if self.plotting_module:
            self.plotting_module.setup_live_plot(self.ax) # Delegate setup
        else:
            # Default setup if no plotter provided
            self.ax.set_title("Live Spectrum")
            self.ax.set_xlabel("Wavelength (nm) or Pixels") # Placeholder
            self.ax.set_ylabel("Intensity (counts)")
            self.ax.grid(True)
            self.fig.tight_layout()

        self.canvas.draw()

        # Store plot line reference for updates
        self.live_plot_line = None



# Example usage (for testing this tab independently)
if __name__ == "__main__":
    # Mock plotting module for testing
    class MockPlottingModule:
        def setup_live_plot(self, ax):
            print("Setting up live plot via Mock")
            ax.set_title("Live Spectrum (Mock Setup)")
            ax.set_xlabel("Pixels")
            ax.set_ylabel("Intensity")
            ax.grid(True)
            ax.plot([1, 2, 3], [1, 4, 2], label="Initial Mock Data") # Add some data
            ax.legend()
            plt.gcf().tight_layout() # Use plt.gcf() to get current figure

    app = ctk.CTk()
    app.geometry("700x500")
    app.title("Live Spectrum Tab Test")

    mock_plotter = MockPlottingModule()
    tab_frame = LiveSpectrumTab(app, mock_plotter)
    tab_frame.pack(expand=True, fill="both", padx=10, pady=10)

    # Example of how plotting module might update later
    # def simulate_update():
    #     import numpy as np
    #     x = np.linspace(0, 10, 100)
    #     y = np.sin(x) + np.random.rand(100) * 0.2
    #     # In real app, plotting_module would call tab_frame.update_plot(x, y)
    #     print("Simulating plot update (manual for test)")
    #     if tab_frame.live_plot_line:
    #         tab_frame.live_plot_line.set_data(x,y)
    #         tab_frame.ax.relim()
    #         tab_frame.ax.autoscale_view()
    #         tab_frame.canvas.draw_idle()
    #
    # app.after(2000, simulate_update)


    app.mainloop()
