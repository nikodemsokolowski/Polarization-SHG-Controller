import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
import logging

class AnalysisTab(ctk.CTkFrame):
    """
    Tab for displaying polarization-dependent intensity analysis (max intensity vs. angle),
    loading data, and fitting.
    """
    # Modify __init__ to accept the main app instance
    def __init__(self, master, app_instance):
        super().__init__(master, fg_color="transparent")
        self.app = app_instance # Store the application instance
        self.plotting_module = app_instance.plotting_module # Get plotting module

        self.grid_rowconfigure(0, weight=1) # Plot area expands vertically
        self.grid_columnconfigure(0, weight=1) # Plot area expands horizontally
        self.grid_columnconfigure(1, weight=0) # Controls column fixed width

        # --- Plot Frame ---
        self.plot_frame = ctk.CTkFrame(self)
        self.plot_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        self.plot_frame.grid_rowconfigure(0, weight=1)
        self.plot_frame.grid_columnconfigure(0, weight=1)

        # --- Matplotlib Figure and Canvas ---
        self.fig, self.ax = plt.subplots(figsize=(5, 4), dpi=100)
        # TODO: Consider applying theme colors to plot background later if desired

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # --- Matplotlib Toolbar ---
        self.toolbar_frame = ctk.CTkFrame(self.plot_frame, fg_color="transparent")
        self.toolbar_frame.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="sew")
        try:
            # Wrap toolbar creation in try-except as it can sometimes cause issues on init
            self.toolbar = NavigationToolbar2Tk(self.canvas, self.toolbar_frame)
            self.toolbar.update()
        except Exception as e:
            logging.error(f"Failed to create Matplotlib toolbar: {e}")
            ctk.CTkLabel(self.toolbar_frame, text="Toolbar failed to load.").pack()


        # --- Initial Plot Setup ---
        # Delegate setup to plotting_module, which now handles analysis plot setup
        self.plotting_module.setup_analysis_plot(self.ax)
        self.ax.set_ylabel("Max Intensity (a.u.)") # Update label
        self.canvas.draw()

        # --- Controls Frame ---
        self.controls_frame = ctk.CTkFrame(self, width=200) # Adjust width as needed
        self.controls_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="ns")
        self.controls_frame.grid_propagate(False) # Prevent frame resizing

        # --- Data Controls ---
        self.data_label = ctk.CTkLabel(self.controls_frame, text="Data", font=ctk.CTkFont(weight="bold"))
        self.data_label.pack(padx=10, pady=(10, 5), anchor="nw")

        self.load_button = ctk.CTkButton(self.controls_frame, text="Load Data (.csv)", command=self.load_data)
        self.load_button.pack(padx=10, pady=5, fill="x")

        self.clear_button = ctk.CTkButton(self.controls_frame, text="Clear Plot", command=self.clear_plot)
        self.clear_button.pack(padx=10, pady=5, fill="x")

        self.save_button = ctk.CTkButton(self.controls_frame, text="Save Plotted Data", command=self.save_data)
        self.save_button.pack(padx=10, pady=5, fill="x")

        # --- Fitting Controls ---
        self.fitting_label = ctk.CTkLabel(self.controls_frame, text="Fitting", font=ctk.CTkFont(weight="bold"))
        self.fitting_label.pack(padx=10, pady=(15, 5), anchor="nw")

        self.fit_button = ctk.CTkButton(self.controls_frame, text="Fit Data", command=self.fit_data)
        self.fit_button.pack(padx=10, pady=5, fill="x")

        # Fit Function: I = y0 + A * sin^2(2*(3*theta + 3*theta0)) - Updated Label
        self.fit_func_label = ctk.CTkLabel(self.controls_frame, text="Fit Func: y₀ + A⋅sin²(2⋅(3θ + 3θ₀))", font=ctk.CTkFont(size=10))
        self.fit_func_label.pack(padx=10, pady=(0, 5), anchor="w")

        # Parameter Controls Frame
        self.params_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.params_frame.pack(padx=5, pady=0, fill="x")
        self.params_frame.grid_columnconfigure(1, weight=1) # Entry expands

        # y0 (Offset)
        self.y0_label = ctk.CTkLabel(self.params_frame, text="y₀:")
        self.y0_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.y0_entry = ctk.CTkEntry(self.params_frame, placeholder_text="Guess/Value", width=60)
        self.y0_entry.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        self.fix_y0_var = tk.BooleanVar(value=False)
        self.fix_y0_check = ctk.CTkCheckBox(self.params_frame, text="Fix", variable=self.fix_y0_var, width=10)
        self.fix_y0_check.grid(row=0, column=2, padx=5, pady=2, sticky="e")

        # A (Amplitude)
        self.A_label = ctk.CTkLabel(self.params_frame, text="A:")
        self.A_label.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.A_entry = ctk.CTkEntry(self.params_frame, placeholder_text="Guess/Value", width=60)
        self.A_entry.grid(row=1, column=1, padx=2, pady=2, sticky="ew")
        self.fix_A_var = tk.BooleanVar(value=False)
        self.fix_A_check = ctk.CTkCheckBox(self.params_frame, text="Fix", variable=self.fix_A_var, width=10)
        self.fix_A_check.grid(row=1, column=2, padx=5, pady=2, sticky="e")

        # theta0 (Phase Offset in degrees)
        self.theta0_label = ctk.CTkLabel(self.params_frame, text="θ₀ (°):")
        self.theta0_label.grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.theta0_entry = ctk.CTkEntry(self.params_frame, placeholder_text="Guess/Value", width=60)
        self.theta0_entry.grid(row=2, column=1, padx=2, pady=2, sticky="ew")
        self.fix_theta0_var = tk.BooleanVar(value=False)
        self.fix_theta0_check = ctk.CTkCheckBox(self.params_frame, text="Fix", variable=self.fix_theta0_var, width=10)
        self.fix_theta0_check.grid(row=2, column=2, padx=5, pady=2, sticky="e")

        # --- Fit Results Display ---
        self.results_label = ctk.CTkLabel(self.controls_frame, text="Fit Results", font=ctk.CTkFont(weight="bold"))
        self.results_label.pack(padx=10, pady=(15, 5), anchor="nw")

        self.fit_results_textbox = ctk.CTkTextbox(self.controls_frame, height=100, state="disabled", wrap="word")
        self.fit_results_textbox.pack(padx=10, pady=(0, 10), fill="x", expand=False)


    # --- Control Callbacks ---

    def load_data(self):
        """Callback for the Load Data button."""
        logging.info("Load Data button clicked.")
        # Get wavelength range from Scan Params Frame
        try:
            # Access ScanParamsFrame through the app instance and main window reference
            scan_params_frame = self.app.main_window.scan_params_frame
            min_str = scan_params_frame.wavelength_min_entry.get()
            max_str = scan_params_frame.wavelength_max_entry.get()
            if not min_str or not max_str:
                self.update_status("Please set wavelength range in Scan Parameters first.", error=True)
                return
            wvl_min = float(min_str)
            wvl_max = float(max_str)
            if wvl_min >= wvl_max or wvl_min < 0:
                raise ValueError("Invalid range (Min >= Max or negative)")
        except AttributeError:
            self.update_status("Error accessing Scan Parameters frame.", error=True)
            logging.error("Could not find main_window or scan_params_frame reference in app instance.")
            return
        except ValueError as e:
            self.update_status(f"Invalid wavelength range in Scan Parameters: {e}", error=True)
            return
        except Exception as e:
            self.update_status(f"Error reading wavelength range: {e}", error=True)
            logging.exception("Error getting wavelength range from scan params frame:")
            return

        filepaths = filedialog.askopenfilenames(
            title="Select CSV Data Files",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not filepaths:
            logging.info("No files selected for loading.")
            return

        self.update_status(f"Loading {len(filepaths)} file(s)...")
        # Run loading in plotting module
        success, message = self.plotting_module.load_analysis_data(list(filepaths), wvl_min, wvl_max)
        self.update_status(message, error=not success)
        # Clear previous fit results if new data is loaded
        self.fit_results_textbox.configure(state="normal")
        self.fit_results_textbox.delete("1.0", tk.END)
        self.fit_results_textbox.configure(state="disabled")


    def clear_plot(self):
        """Callback for the Clear Plot button."""
        logging.info("Clear Plot button clicked.")
        self.plotting_module.clear_analysis_data()
        # Clear fit results display
        self.fit_results_textbox.configure(state="normal")
        self.fit_results_textbox.delete("1.0", tk.END)
        self.fit_results_textbox.configure(state="disabled")
        self.update_status("Analysis plot cleared.")


    def fit_data(self):
        """Callback for the Fit Data button."""
        logging.info("Fit Data button clicked.")

        # Define the fit function (accepts degrees, converts internally) - Updated Function
        # I = y0 + A * sin^2(3*theta_deg + 3*theta0_deg)
        def fit_func(theta_deg, y0, A, theta0_deg):
            theta_rad = np.radians(3.0 * theta_deg + 3.0 * theta0_deg) # Changed here
            return y0 + A * (np.sin(2 * theta_rad)**2)

        param_names = ['y₀', 'A', 'θ₀']
        entries = [self.y0_entry, self.A_entry, self.theta0_entry]
        fix_vars = [self.fix_y0_var, self.fix_A_var, self.fix_theta0_var]

        p0 = []
        fixed_mask = []
        bounds_min = [-np.inf, 0, -360] # Sensible defaults: A>=0
        bounds_max = [np.inf, np.inf, 360]

        # Get parameters, initial guesses, and fixed status from GUI
        try:
            for i, entry in enumerate(entries):
                val_str = entry.get()
                if not val_str:
                    raise ValueError(f"Please provide an initial guess or fixed value for {param_names[i]}.")
                val = float(val_str)
                p0.append(val)
                is_fixed = fix_vars[i].get()
                fixed_mask.append(is_fixed)
                if is_fixed:
                    # If fixed, set bounds tightly around the value
                    bounds_min[i] = val - 1e-9
                    bounds_max[i] = val + 1e-9
            bounds = (bounds_min, bounds_max)
        except ValueError as e:
            self.update_status(f"Invalid fit parameter input: {e}", error=True)
            logging.warning(f"Fit parameter validation failed: {e}")
            return

        self.update_status("Fitting data...")
        # Call the fitting method in the plotting module
        fit_params, fit_errors, message = self.plotting_module.fit_intensity_data(
            fit_func,
            p0,
            bounds,
            fixed_params_mask=fixed_mask,
            param_names=param_names
        )

        # Display results
        self.fit_results_textbox.configure(state="normal")
        self.fit_results_textbox.delete("1.0", tk.END)
        if fit_params and fit_errors:
            results_text = f"{message}\nParameters:\n"
            for name in param_names:
                val = fit_params.get(name, np.nan)
                err = fit_errors.get(name, np.nan)
                results_text += f"  {name} = {val:.4f} ± {err:.4f}\n"
            self.fit_results_textbox.insert("1.0", results_text)
            self.update_status("Fit successful.")
        else:
            self.fit_results_textbox.insert("1.0", message) # Display error message
            self.update_status("Fit failed.", error=True)

        self.fit_results_textbox.configure(state="disabled")


    def update_status(self, message: str, error: bool = False):
        """Updates the main status bar via the app instance."""
        if hasattr(self.app, 'update_status_bar'):
            self.app.update_status_bar(message, error)
        else:
            # Fallback if method not found (shouldn't happen in real app)
            print(f"Status Update (AnalysisTab): {message}" + (" (Error)" if error else ""))


    def save_data(self):
        """Callback for the Save Plotted Data button."""
        logging.info("Save Data button clicked.")

        angles = self.plotting_module.angle_data
        intensities = self.plotting_module.intensity_data

        if not angles or not intensities or len(angles) != len(intensities):
            self.update_status("No data available to save.", error=True)
            logging.warning("Save data called but no valid data found in plotting module.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Save Intensity vs Angle Data",
            defaultextension=".txt",
            initialfile="intensity_vs_angle.txt",
            filetypes=[("Text files", "*.txt"), ("Data files", "*.dat"), ("All files", "*.*")]
        )

        if not filepath:
            logging.info("Save data cancelled by user.")
            return

        try:
            # Combine data into a 2-column array
            data_to_save = np.column_stack((angles, intensities))
            # Save using numpy, tab-delimited, specific format
            np.savetxt(filepath, data_to_save, delimiter='\t', fmt='%.4f')
            self.update_status(f"Data saved successfully to {filepath}")
            logging.info(f"Analysis data saved to: {filepath}")
        except Exception as e:
            self.update_status(f"Error saving data: {e}", error=True)
            logging.exception(f"Failed to save analysis data to {filepath}:")


# Example usage (for testing this tab independently)
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Mock plotting module for testing
    class MockPlottingModule:
        def __init__(self):
            self.angle_data = []
            self.intensity_data = []
        def setup_analysis_plot(self, ax):
            print("Mock Setup Analysis Plot")
            self.ax = ax
            self.points, = ax.plot([], [], 'bo', ms=5)
            self.line, = ax.plot([], [], 'r-')
            ax.set_xlabel("Angle (°)")
            ax.set_ylabel("Max Intensity")
            ax.grid(True)
            ax.figure.tight_layout()
        def clear_analysis_data(self):
            print("Mock Clear Analysis Data")
            self.angle_data = []
            self.intensity_data = []
            self.update_analysis_plot()
        def load_analysis_data(self, filepaths, wvl_min, wvl_max):
            print(f"Mock Load Analysis Data: {len(filepaths)} files, Range=[{wvl_min}, {wvl_max}]")
            # Simulate loading some data
            self.angle_data = np.linspace(0, 360, 15)
            self.intensity_data = 0.5 + 0.5 * np.sin(np.radians(3 * self.angle_data + 30))**2 + np.random.rand(15)*0.1
            self.update_analysis_plot()
            return True, f"Mock loaded {len(filepaths)} files."
        def fit_intensity_data(self, fit_func, p0, bounds, fixed_params_mask, param_names):
            print(f"Mock Fit: p0={p0}, bounds={bounds}, fixed={fixed_params_mask}")
            if len(self.angle_data) < 3: return None, None, "Mock Fit Error: Not enough data"
            try:
                # Simulate a successful fit
                popt = [p0[0]*0.9, p0[1]*1.1, p0[2]-5] # Slightly adjusted params
                perr = [0.01, 0.02, 1.0]
                fit_params = {name: val for name, val in zip(param_names, popt)}
                fit_errors = {name: err for name, err in zip(param_names, perr)}

                # Generate fake fit curve
                fit_angles = np.linspace(min(self.angle_data), max(self.angle_data), 100)
                fit_curve = fit_func(fit_angles, *popt)
                self.update_analysis_plot(fit_curve=fit_curve, fit_angles=fit_angles)
                return fit_params, fit_errors, "Mock Fit Successful"
            except Exception as e:
                return None, None, f"Mock Fit Error: {e}"
        def update_analysis_plot(self, fit_curve=None, fit_angles=None):
            print("Mock Update Analysis Plot")
            self.points.set_data(self.angle_data, self.intensity_data)
            if fit_curve is not None and fit_angles is not None:
                self.line.set_data(fit_angles, fit_curve)
            else:
                self.line.set_data([], [])
            self.ax.relim()
            self.ax.autoscale_view()
            self.ax.figure.canvas.draw_idle()

    # Mock app instance for testing
    class MockScanParamsFrame(ctk.CTkFrame):
        # Mock the entries needed by load_data
        wavelength_min_entry = ctk.CTkEntry()
        wavelength_max_entry = ctk.CTkEntry()
        wavelength_min_entry.insert(0, "500") # Default values for testing
        wavelength_max_entry.insert(0, "600")

    class MockMainWindow:
        scan_params_frame = MockScanParamsFrame() # Attach mock frame

    class MockApp:
        plotting_module = MockPlottingModule()
        main_window = MockMainWindow() # Attach mock main window
        def update_status_bar(self, msg, error=False):
            print(f"STATUS UPDATE: {msg}" + (" [ERROR]" if error else ""))

    app = ctk.CTk()
    app.geometry("850x600")
    app.title("Analysis Tab Test")

    mock_app_instance = MockApp()

    # Need to pack the mock scan params frame somewhere for entries to exist
    mock_app_instance.main_window.scan_params_frame.pack(pady=5) # Pack it simply

    tab_frame = AnalysisTab(app, mock_app_instance) # Pass mock app instance
    tab_frame.pack(expand=True, fill="both", padx=10, pady=10)

    app.mainloop()
