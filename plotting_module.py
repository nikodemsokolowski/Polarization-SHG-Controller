import logging
import logging
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes # For type hinting
import re # For filename parsing
from scipy.optimize import curve_fit # For fitting
import os # For basename in loading

class PlottingModule:
    """
    Handles updating the Matplotlib plots embedded in the GUI tabs.
    """
    def __init__(self):
        logging.info("PlottingModule initialized.")
        self.live_ax: Axes | None = None
        self.analysis_ax: Axes | None = None

        # Store references to plot lines for efficient updates
        self.live_plot_line = None
        self.intensity_plot_points = None
        self.fit_plot_line = None

        # Store data for analysis plot
        self.angle_data = []
        self.intensity_data = []

        # Store fit function details (can be set by GUI later)
        self._fit_function = None
        self._fit_param_names = []

    # --- Setup Methods (called by GUI tabs during initialization) ---

    def setup_live_plot(self, ax: Axes):
        """Configures the Axes object for the live spectrum plot."""
        self.live_ax = ax
        self.live_ax.set_title("Live Spectrum")
        self.live_ax.set_xlabel("Pixel Index") # Default, can be updated if calibration exists
        self.live_ax.set_ylabel("Intensity (Counts)")
        self.live_ax.grid(True)
        # Initialize the plot line (empty data initially)
        self.live_plot_line, = self.live_ax.plot([], [], marker='.', linestyle='-', markersize=4)
        logging.info("Live plot axes configured.")
        # Ensure layout is adjusted
        try:
            self.live_ax.figure.tight_layout()
        except Exception as e:
            logging.warning(f"Error during live plot tight_layout: {e}")


    def setup_analysis_plot(self, ax: Axes):
        """Configures the Axes object for the intensity analysis plot."""
        self.analysis_ax = ax
        self.analysis_ax.set_title("Intensity vs. Polarization Angle")
        self.analysis_ax.set_xlabel("Polarization Angle (°)")
        self.analysis_ax.set_ylabel("Integrated Intensity (a.u.)")
        self.analysis_ax.grid(True)
        # Initialize plot lines (empty data initially)
        self.intensity_plot_points, = self.analysis_ax.plot([], [], 'bo', label='Data', markersize=5) # Points for data
        self.fit_plot_line, = self.analysis_ax.plot([], [], 'r-', label='Fit') # Line for fit
        self.analysis_ax.legend()
        logging.info("Analysis plot axes configured.")
        # Ensure layout is adjusted
        try:
            self.analysis_ax.figure.tight_layout(rect=[0, 0, 1, 0.97]) # Adjust rect if needed
        except Exception as e:
            logging.warning(f"Error during analysis plot tight_layout: {e}")


    # --- Update Methods (called by scan logic or analysis module) ---

    def update_live_plot(self, spectrum_data: np.ndarray, x_axis: np.ndarray | None = None):
        """
        Updates the live spectrum plot with new data.

        Args:
            spectrum_data (np.ndarray): The 1D array of intensity values.
            x_axis (np.ndarray | None): Optional array for the x-axis (e.g., wavelength).
                                        If None, pixel indices are used.
        """
        if self.live_ax is None or self.live_plot_line is None:
            logging.warning("Live plot axes not initialized. Cannot update plot.")
            return

        if spectrum_data is None or spectrum_data.ndim != 1:
            logging.warning(f"Invalid spectrum data for live plot (ndim={spectrum_data.ndim if spectrum_data is not None else 'None'}).")
            # Optionally clear the plot?
            # self.live_plot_line.set_data([], [])
            return

        if x_axis is None:
            x_data = np.arange(len(spectrum_data))
            self.live_ax.set_xlabel("Pixel Index")
        elif len(x_axis) == len(spectrum_data):
            x_data = x_axis
            self.live_ax.set_xlabel("Wavelength (nm)") # Assume nm if x_axis provided
        else:
            logging.warning("x_axis length mismatch with spectrum_data. Using pixel indices.")
            x_data = np.arange(len(spectrum_data))
            self.live_ax.set_xlabel("Pixel Index")

        # Update plot data
        self.live_plot_line.set_data(x_data, spectrum_data)

        # Rescale axes
        self.live_ax.relim()
        self.live_ax.autoscale_view()

        # Redraw the canvas (use draw_idle for efficiency)
        try:
            self.live_ax.figure.canvas.draw_idle()
            logging.debug("Live plot updated.")
        except Exception as e:
            logging.error(f"Error drawing live plot canvas: {e}")

    def add_analysis_point(self, angle: float, intensity: float):
        """Adds a single data point to the internal storage for the analysis plot."""
        self.angle_data.append(angle)
        self.intensity_data.append(intensity)
        logging.debug(f"Added analysis point: Angle={angle:.2f}, Intensity={intensity:.2f}")
        # Update the plot immediately with the new point
        self.update_analysis_plot()

    def add_intensity_analysis_point(self, angle: float, max_intensity: float):
        """Adds a single data point (angle, max_intensity) from dynamic scan analysis."""
        if self.analysis_ax is None:
            logging.warning("Analysis plot axes not initialized. Cannot add point.")
            return
        self.angle_data.append(angle)
        self.intensity_data.append(max_intensity)
        logging.debug(f"Added dynamic analysis point: Angle={angle:.2f}, Max Intensity={max_intensity:.3f}")
        # Update the plot immediately
        self.update_analysis_plot()


    def update_analysis_plot(self, fit_curve: np.ndarray | None = None, fit_angles: np.ndarray | None = None):
        """
        Updates the analysis plot with current data points and optionally a fit curve.

        Args:
            fit_curve (np.ndarray | None): The y-values of the fitted curve.
            fit_angles (np.ndarray | None): The x-values (angles) corresponding to the fit_curve.
                                            If None, assumes fit corresponds to self.angle_data.
        """
        if self.analysis_ax is None or self.intensity_plot_points is None or self.fit_plot_line is None:
            logging.warning("Analysis plot axes not initialized. Cannot update plot.")
            return

        # Update data points
        self.intensity_plot_points.set_data(self.angle_data, self.intensity_data)

        # Update fit line
        if fit_curve is not None:
            if fit_angles is None:
                # Assume fit corresponds to the collected angle data, sort for line plot
                sorted_indices = np.argsort(self.angle_data)
                fit_angles_sorted = np.array(self.angle_data)[sorted_indices]
                fit_curve_sorted = fit_curve[sorted_indices]
                self.fit_plot_line.set_data(fit_angles_sorted, fit_curve_sorted)
            elif len(fit_angles) == len(fit_curve):
                # Use provided angles for fit curve (already sorted assumed)
                self.fit_plot_line.set_data(fit_angles, fit_curve)
            else:
                logging.warning("Fit curve angles length mismatch. Fit not plotted.")
                self.fit_plot_line.set_data([], []) # Clear fit line
        else:
            self.fit_plot_line.set_data([], []) # Clear fit line if no fit provided

        # Rescale axes
        self.analysis_ax.relim()
        self.analysis_ax.autoscale_view()

        # Redraw the canvas
        try:
            self.analysis_ax.figure.canvas.draw_idle()
            logging.debug("Analysis plot updated.")
        except Exception as e:
            logging.error(f"Error drawing analysis plot canvas: {e}")

    def clear_analysis_data(self):
        """Clears the stored data and resets the analysis plot."""
        logging.info("Clearing analysis data and plot.")
        self.angle_data = []
        self.intensity_data = []
        # Call update_analysis_plot to clear the visual plot as well
        self.update_analysis_plot(fit_curve=None, fit_angles=None)
    
    def cleanup(self):
        """Cleans up Matplotlib figures and resources."""
        logging.info("Cleaning up plotting resources...")
        try:
            if self.live_ax and self.live_ax.figure:
                logging.debug("Closing live plot figure.")
                # Clear the figure first, then close it
                self.live_ax.figure.clf()
                plt.close(self.live_ax.figure)
                self.live_ax = None # Clear references
                self.live_plot_line = None
            if self.analysis_ax and self.analysis_ax.figure:
                logging.debug("Closing analysis plot figure.")
                # Clear the figure first, then close it
                self.analysis_ax.figure.clf()
                plt.close(self.analysis_ax.figure)
                self.analysis_ax = None # Clear references
                self.intensity_plot_points = None
                self.fit_plot_line = None
            logging.info("Plotting resources cleaned up.")
        except Exception as e:
            logging.exception("Error during plotting resource cleanup:")


    # --- New Data Loading and Fitting Methods ---

    def load_analysis_data(self, filepaths: list[str], wvl_min: float | None, wvl_max: float | None) -> tuple[bool, str]:
        """
        Loads intensity data from multiple CSV files, calculates max intensity in range,
        and updates the analysis plot.

        Args:
            filepaths (list[str]): List of paths to CSV files.
            wvl_min (float | None): Minimum wavelength for max intensity calculation.
            wvl_max (float | None): Maximum wavelength for max intensity calculation.

        Returns:
            tuple[bool, str]: (success_flag, status_message)
        """
        logging.info(f"Loading analysis data from {len(filepaths)} files. Range: [{wvl_min}, {wvl_max}]")
        self.clear_analysis_data() # Clear previous data first

        loaded_count = 0
        error_messages = []

        if wvl_min is None or wvl_max is None or wvl_min >= wvl_max:
            msg = "Invalid wavelength range provided for loading."
            logging.error(msg)
            return False, msg

        for fpath in filepaths:
            filename = os.path.basename(fpath)
            logging.debug(f"Processing file: {filename}")
            try:
                # Extract angle from filename (e.g., "Name_10p0.csv" or "Name_-10p5.csv")
                match = re.search(r'_(-?\d+)p(\d+)', filename)
                if not match:
                    logging.warning(f"Could not extract angle from filename: {filename}. Skipping.")
                    error_messages.append(f"No angle in {filename}")
                    continue

                angle_str = f"{match.group(1)}.{match.group(2)}"
                angle = float(angle_str)

                # Load data (expecting wavelength, intensity)
                loaded_data = np.loadtxt(fpath, delimiter='\t')
                if loaded_data.ndim != 2 or loaded_data.shape[1] != 2:
                    logging.warning(f"Unexpected data shape {loaded_data.shape} in {filename}. Skipping.")
                    error_messages.append(f"Bad format in {filename}")
                    continue

                wavelength_data = loaded_data[:, 0]
                intensity_data_full = loaded_data[:, 1]

                # Calculate max intensity in range
                mask = (wavelength_data >= wvl_min) & (wavelength_data <= wvl_max)
                if not np.any(mask):
                    logging.warning(f"No data points found within range [{wvl_min}, {wvl_max}] in {filename}. Skipping.")
                    error_messages.append(f"No data in range for {filename}")
                    continue

                max_intensity = np.max(intensity_data_full[mask])

                # Add data point
                self.angle_data.append(angle)
                self.intensity_data.append(max_intensity)
                loaded_count += 1
                logging.debug(f"Loaded point from {filename}: Angle={angle:.2f}, Max Intensity={max_intensity:.3f}")

            except FileNotFoundError:
                logging.error(f"File not found: {fpath}")
                error_messages.append(f"Not found: {filename}")
            except ValueError as ve:
                logging.error(f"ValueError processing {filename}: {ve}")
                error_messages.append(f"Value error in {filename}")
            except Exception as e:
                logging.exception(f"Unexpected error processing {filename}:")
                error_messages.append(f"Error in {filename}")

        if loaded_count > 0:
            self.update_analysis_plot() # Update plot with loaded data
            msg = f"Loaded {loaded_count}/{len(filepaths)} files."
            if error_messages:
                msg += f" Errors: {'; '.join(error_messages)}"
            logging.info(msg)
            return True, msg
        else:
            msg = "Failed to load any valid data points."
            if error_messages:
                msg += f" Errors: {'; '.join(error_messages)}"
            logging.error(msg)
            return False, msg


    def fit_intensity_data(self, fit_func, p0, bounds, fixed_params_mask=None, param_names=None) -> tuple[dict | None, dict | None, str]:
        """
        Fits the current angle_data and intensity_data using scipy.optimize.curve_fit.

        Args:
            fit_func: The model function to fit (should accept angle in degrees).
            p0 (list): Initial guess for parameters.
            bounds (tuple): Bounds for parameters ( (min_bounds), (max_bounds) ).
            fixed_params_mask (list[bool] | None): Boolean mask indicating which parameters are fixed.
                                                If None, all parameters are varied.
            param_names (list[str] | None): Names of the parameters for result display.

        Returns:
            tuple[dict | None, dict | None, str]: (fit_params, fit_errors, status_message)
                fit_params: Dictionary of optimized parameter names and values.
                fit_errors: Dictionary of parameter names and standard deviations.
                status_message: Message indicating success or failure.
        """
        if not self.angle_data or not self.intensity_data or len(self.angle_data) < 3:
            msg = "Not enough data points to perform fit."
            logging.warning(msg)
            return None, None, msg

        if param_names and len(param_names) != len(p0):
            msg = "Mismatch between param_names and p0 length."
            logging.error(msg)
            return None, None, msg

        angles_deg = np.array(self.angle_data)
        intensities = np.array(self.intensity_data)

        # --- Handle fixed parameters (if any) ---
        # curve_fit doesn't directly support fixing parameters easily.
        # A common way is to wrap the function.
        varied_indices = [i for i, fixed in enumerate(fixed_params_mask) if not fixed] if fixed_params_mask else list(range(len(p0)))
        fixed_indices = [i for i, fixed in enumerate(fixed_params_mask) if fixed] if fixed_params_mask else []

        if not varied_indices:
            msg = "No parameters selected for fitting."
            logging.warning(msg)
            return None, None, msg

        # Create a wrapper function that only takes the varied parameters
        def wrapped_fit_func(x, *varied_args):
            all_args = list(p0) # Start with initial guesses (or fixed values)
            for i, arg_val in enumerate(varied_args):
                all_args[varied_indices[i]] = arg_val
            # Fixed parameters remain at their p0 value
            return fit_func(x, *all_args)

        # Adjust p0 and bounds for the wrapper function
        p0_varied = [p0[i] for i in varied_indices]
        bounds_varied = ([bounds[0][i] for i in varied_indices], [bounds[1][i] for i in varied_indices])
        # --- End Handle fixed parameters ---


        logging.info(f"Attempting curve fit with p0={p0_varied}, bounds={bounds_varied}")
        try:
            # Use the wrapper function and adjusted parameters
            popt_varied, pcov_varied = curve_fit(
                wrapped_fit_func,
                angles_deg, # Pass angles in degrees
                intensities,
                p0=p0_varied,
                bounds=bounds_varied,
                maxfev=5000 # Increase max iterations
            )

            # Reconstruct full popt and pcov
            popt = list(p0) # Start with initial/fixed values
            perr = [np.inf] * len(p0) # Initialize errors
            pcov = np.full((len(p0), len(p0)), np.inf) # Initialize full covariance

            for i, idx_varied in enumerate(varied_indices):
                popt[idx_varied] = popt_varied[i]
                # Fill diagonal elements for varied params' errors
                if pcov_varied.shape == (len(popt_varied), len(popt_varied)):
                    perr[idx_varied] = np.sqrt(np.diag(pcov_varied))[i] if np.diag(pcov_varied)[i] >= 0 else np.inf
                    # Fill the corresponding submatrix in the full pcov
                    for j, idx_varied2 in enumerate(varied_indices):
                        pcov[idx_varied, idx_varied2] = pcov_varied[i, j]
                else: # Handle cases where curve_fit returns 1D variance array
                    if i < len(pcov_varied):
                        perr[idx_varied] = np.sqrt(pcov_varied[i]) if pcov_varied[i] >= 0 else np.inf
                        pcov[idx_varied, idx_varied] = pcov_varied[i]


            # Generate smooth curve for plotting
            min_angle, max_angle = np.min(angles_deg), np.max(angles_deg)
            fit_angles_deg = np.linspace(min_angle, max_angle, 200)
            fit_curve = fit_func(fit_angles_deg, *popt) # Use original function with full popt

            # Update the plot with the fit
            self.update_analysis_plot(fit_curve=fit_curve, fit_angles=fit_angles_deg)

            # Prepare results dictionaries
            fit_params_dict = {name: val for name, val in zip(param_names, popt)} if param_names else {f'p{i}': val for i, val in enumerate(popt)}
            fit_errors_dict = {name: err for name, err in zip(param_names, perr)} if param_names else {f'p{i}_err': err for i, err in enumerate(perr)}

            msg = "Fit successful."
            logging.info(f"Fit successful. Params: {fit_params_dict}, Errors: {fit_errors_dict}")
            return fit_params_dict, fit_errors_dict, msg

        except RuntimeError as e:
            msg = f"Fit failed: {e}"
            logging.error(msg)
            # Clear any previous fit line
            self.update_analysis_plot(fit_curve=None, fit_angles=None)
            return None, None, msg
        except ValueError as e:
            msg = f"Fit failed (ValueError): {e}"
            logging.error(msg)
            self.update_analysis_plot(fit_curve=None, fit_angles=None)
            return None, None, msg
        except Exception as e:
            msg = f"Fit failed (Unexpected Error): {e}"
            logging.exception("Unexpected error during curve fitting:")
            self.update_analysis_plot(fit_curve=None, fit_angles=None)
            return None, None, msg
