import time
import numpy as np
import threading
import logging
import os

# Assuming controllers and modules are imported for type hinting
# from kdc101_controller import KDC101Controller
# from lightfield_controller import LightFieldController
from analysis_module import AnalysisModule # Import
from plotting_module import PlottingModule # Import
# from file_io_utils import save_scan_data # Import save function later

class ScanLogic:
    """
    Handles the execution of the polarization scan loop in a separate thread.
    Communicates with hardware controllers and modules, and updates the GUI via callbacks.
    """
    # Add eta_callback to __init__
    def __init__(self, kdc_controller, lf_controller, analysis_module: AnalysisModule, plotting_module: PlottingModule,
                status_callback, progress_callback, completion_callback, eta_callback):
        """
        Initializes the ScanLogic.

        Args:
            kdc_controller: Instance of KDC101Controller.
            lf_controller: Instance of LightFieldController.
            analysis_module: Instance of AnalysisModule.
            plotting_module: Instance of PlottingModule.
            status_callback: Function to update the GUI status bar.
            progress_callback: Function to update the GUI progress bar and step count.
            completion_callback: Function to call when the scan finishes.
            eta_callback: Function to update the GUI ETA display.
        """
        self.kdc = kdc_controller
        self.lf = lf_controller
        self.analyzer = analysis_module
        self.plotter = plotting_module
        self.update_status = status_callback
        self.update_progress = progress_callback # This likely needs modification in main_app to handle ETA
        self.update_eta = eta_callback # Store the new callback
        self.scan_completed = completion_callback

        self._scan_thread = None
        self._abort_event = threading.Event() # Renamed from _stop_event
        self._pause_event = threading.Event()
        self._pause_event.set() # Start in the "not paused" state (event is set)
        self.scan_parameters = {} # Stores parameters for the current scan
        self.scan_running = False
        self._current_scan_params = {} # Store validated params for loop access

    def is_running(self):
        """Returns True if a scan is currently active."""
        return self.scan_running and self._scan_thread is not None and self._scan_thread.is_alive()

    def start_scan(self, parameters: dict):
        """Starts the scan sequence in a new thread."""
        logging.debug("ScanLogic.start_scan called.") # Log entry
        if self.is_running():
            logging.warning("Scan is already running.")
            self.update_status("Scan is already in progress.", error=True)
            return

        # Log connection checks
        kdc_conn = self.kdc and self.kdc.is_connected()
        lf_conn = self.lf and self.lf.is_connected()
        logging.debug(f"Connection check: KDC={kdc_conn}, LF={lf_conn}")

        if not kdc_conn:
            self.update_status("KDC101 not connected. Cannot start scan.", error=True)
            self.scan_completed(success=False, message="Scan failed: KDC101 not connected.")
            return
        if not lf_conn:
            self.update_status("LightField not connected. Cannot start scan.", error=True)
            self.scan_completed(success=False, message="Scan failed: LightField not connected.")
            return

        # Store validated parameters for access within the loop
        self._current_scan_params = parameters.copy()
        self.scan_parameters = parameters # Keep this for potential external access? Or remove? Let's keep for now.

        self._abort_event.clear() # Clear abort flag
        self._pause_event.set() # Ensure scan starts in non-paused state
        self.scan_running = True

        self.update_status("Starting scan...")
        self.update_progress(0)

        # Create and start the thread
        logging.debug("Creating scan thread...") # Log before thread creation
        self._scan_thread = threading.Thread(target=self._run_scan_loop, daemon=True)
        logging.debug("Starting scan thread...") # Log before thread start
        self._scan_thread.start()
        logging.info(f"Scan thread started with parameters: {parameters}")

    def stop_scan(self):
        """Signals the scan thread to stop."""
        # This method seems unused now, replaced by abort_scan
        if not self.is_running():
            logging.warning("Stop scan called, but no scan is running.")
            return

        logging.info("Stop signal received for scan thread.")
        self.update_status("Stopping scan...")
        # Assuming _stop_event was the old name for _abort_event
        self._abort_event.set() # Use the correct event name
        self._pause_event.set() # Ensure it can exit if paused
        # The completion callback will be called from within the thread when it exits

    # --- New Pause/Resume Methods ---
    def pause_scan(self):
        """Signals the scan thread to pause."""
        if self.is_running():
            logging.info("Pause signal received for scan thread.")
            self.update_status("Pausing scan...")
            self._pause_event.clear() # Clear the event to block wait()

    def resume_scan(self):
        """Signals the scan thread to resume."""
        if self.is_running():
            logging.info("Resume signal received for scan thread.")
            self.update_status("Resuming scan...")
            self._pause_event.set() # Set the event to unblock wait()

    # --- Renamed stop_scan to abort_scan ---
    def abort_scan(self):
        """Signals the scan thread to abort (stop after current step)."""
        if not self.is_running():
            logging.warning("Abort scan called, but no scan is running.")
            return

        logging.info("Abort signal received for scan thread.")
        self.update_status("Aborting scan...")
        self._abort_event.set()
        # Ensure scan resumes if paused, so it can check the abort flag and exit
        self._pause_event.set()
        # The completion callback will be called from within the thread when it exits


    def _run_scan_loop(self):
        """The main loop executed by the scan thread."""
        logging.debug("_run_scan_loop thread started.") # Log thread entry
        try:
            # Use the stored _current_scan_params for reliability within the thread
            start = self._current_scan_params['start_angle']
            end = self._current_scan_params['end_angle']
            step = self._current_scan_params['step_angle']
            add_pos_to_fname = self._current_scan_params['add_position_to_filename']
            plot_live = self._current_scan_params.get('plot_live_spectrum', True)
            # --- Get NEW plotting params ---
            plot_dynamic_intensity = self._current_scan_params.get('plot_dynamic_intensity', False)
            wvl_min = self._current_scan_params.get('wavelength_min', None)
            wvl_max = self._current_scan_params.get('wavelength_max', None)
            # --- End NEW plotting params ---


            # --- Get other params (exposure, accum, save dir, base filename) ---
            logging.debug("Getting exposure time...")
            try:
                exposure_ms = self.lf.get_exposure_time_ms() or 100.0 # Read from LF or default 100ms
                exposure_sec = exposure_ms / 1000.0
            except Exception as e:
                logging.warning(f"Could not read exposure, using default: {e}")
                exposure_sec = 0.1 # Fallback default
                self.update_status("Warning: Could not read exposure, using default.", error=True)

            logging.debug("Getting accumulations...")
            try:
                # Accumulations might not be directly readable, use a default or get from elsewhere if added
                accumulations = 1 # Default
            except Exception as e:
                logging.warning(f"Could not read accumulations, using default: {e}")
                accumulations = 1

            # Get base filename from parameters, default if not found
            base_filename = self.scan_parameters.get('base_filename', 'scan_data')
            # Get save directory from parameters
            save_directory = self.scan_parameters.get('save_directory', '.') # Default to current dir
            logging.info(f"Scan Params: Exp={exposure_sec*1000:.1f}ms, Accum={accumulations}, Base={base_filename}, SaveDir={save_directory}, Plot={plot_live}")
            # --- End Get other params ---

            logging.debug("Calculating angles...")
            angles = np.arange(start, end + step / 2, step)
            if abs(angles[-1] - end) > abs(step / 2):
                angles = np.arange(start, end, step)
            num_steps = len(angles)
            logging.info(f"Scan angles ({num_steps} steps): {angles}")

            start_time = time.time() # Record start time for ETA calculation

            # if self.plotter:
                # Commented out plotting/analysis
                # self.plotter.clear_analysis_data()

            all_results = []
            logging.debug("Starting scan loop...")
            for i, angle in enumerate(angles):
                logging.debug(f"--- Loop Start: Step {i+1}/{num_steps}, Target Angle: {angle:.2f} ---")
                # --- Check for Abort Signal ---
                if self._abort_event.is_set():
                    logging.info("Abort event detected, exiting scan loop.")
                    self.update_status("Scan aborted by user.")
                    return # Exit the loop

                # --- Check for Pause Signal (before starting next step) ---
                logging.debug(f"Loop {i+1}/{num_steps}: Checking pause event...")
                self._pause_event.wait() # Blocks if event is cleared (paused)
                logging.debug(f"Loop {i+1}/{num_steps}: Pause check passed (or resumed).")

                # --- Check for Abort Signal AGAIN after potential pause ---
                if self._abort_event.is_set():
                    logging.info("Abort event detected after pause, exiting scan loop.")
                    self.update_status("Scan aborted by user.")
                    return # Exit the loop

                # --- Proceed with the scan step ---
                self.update_status(f"Step {i+1}/{num_steps}: Moving to {angle:.2f}°")
                logging.info(f"Moving to angle: {angle:.2f}")

                self.kdc.move_to(angle)
                self.kdc.wait_for_move(timeout_s=30)
                time.sleep(0.1)
                current_pos = self.kdc.get_position()
                logging.info(f"Stage reached: {current_pos:.2f}° (Target: {angle:.2f}°, Step: {i+1}/{num_steps})")
                self.update_status(f"Step {i+1}/{num_steps}: Acquiring at {current_pos:.2f}°")

                # --- Set LF Filename based on checkbox ---
                step_filename = base_filename
                if add_pos_to_fname:
                    pos_str = f"{current_pos:.1f}".replace('.', 'p')
                    step_filename = f"{base_filename}_{pos_str}"
                logging.debug(f"Setting LF base filename to: {step_filename}")
                try:
                    if not self.lf.set_base_filename(step_filename):
                        logging.warning(f"Could not set base filename to '{step_filename}' in LightField.")
                        self.update_status(f"Warning: Failed to set filename '{step_filename}'", error=True)
                    else:
                        logging.info(f"Set LightField base filename to: {step_filename}")
                except Exception as fname_e:
                    logging.error(f"Error setting filename '{step_filename}': {fname_e}")
                    self.update_status(f"Error setting filename: {fname_e}", error=True)
                # --- End Set LF Filename ---

                logging.debug("Calling lf.acquire()...")
                if not self.lf.acquire():
                    raise RuntimeError(f"LightField acquisition command failed at angle {angle:.2f}°")
                logging.debug("lf.acquire() finished.")

                # --- Load data from saved CSV file ---
                wavelength_data = None
                intensity_data = None
                csv_filename = f"{step_filename}.csv" # Assume .csv extension
                full_csv_path = os.path.join(save_directory, csv_filename)
                logging.info(f"Attempting to load spectrum from: {full_csv_path}")

                # Wait briefly for the file to appear (e.g., max 3 seconds)
                file_found = False
                max_wait_time = 3.0
                wait_interval = 0.2
                elapsed_time = 0.0
                while elapsed_time < max_wait_time:
                    if os.path.exists(full_csv_path):
                        file_found = True
                        logging.info(f"Found file: {full_csv_path}")
                        break
                    time.sleep(wait_interval)
                    elapsed_time += wait_interval
                    logging.debug(f"Waiting for file {csv_filename}... ({elapsed_time:.1f}s)")

                if file_found:
                    try:
                        logging.debug(f"Loading data from {full_csv_path} using np.loadtxt with tab delimiter...")
                        # Load data, specifying tab delimiter, no header
                        loaded_data = np.loadtxt(full_csv_path, delimiter='\t')
                        if loaded_data.ndim == 2 and loaded_data.shape[1] == 2:
                            wavelength_data = loaded_data[:, 0]
                            intensity_data = loaded_data[:, 1]
                            logging.info(f"Successfully loaded {len(wavelength_data)} points from {csv_filename}")
                        else:
                            logging.warning(f"Loaded data from {csv_filename} has unexpected shape: {loaded_data.shape}")
                    except Exception as load_e:
                        logging.error(f"Error loading data from {full_csv_path}: {load_e}")
                        self.update_status(f"Error loading file {csv_filename}", error=True)
                else:
                    logging.warning(f"File not found after {max_wait_time}s: {full_csv_path}")
                    self.update_status(f"File not found: {csv_filename}", error=True)
                # --- End Load data ---


                # --- Update Plotting (if data loaded and checkbox enabled) ---
                logging.debug(f"Checking plotting condition: plot_live={plot_live}, plotter exists={self.plotter is not None}, data loaded={wavelength_data is not None}")
                if plot_live and self.plotter and wavelength_data is not None and intensity_data is not None:
                    try:
                        logging.debug("Calling plotter.update_live_plot...")
                        # Correct argument order: intensity first, wavelength as optional x_axis
                        self.plotter.update_live_plot(intensity_data, x_axis=wavelength_data)
                        logging.debug("Called plotter.update_live_plot with loaded data")
                    except Exception as plot_e:
                        logging.error(f"Error calling update_live_plot: {plot_e}")
                        self.update_status(f"Plotting Error: {plot_e}", error=True)
                # --- End Update Live Plotting ---

                # --- Calculate Max Intensity for Dynamic Plot (if enabled and data valid) ---
                logging.debug(f"Checking dynamic intensity plot condition: enabled={plot_dynamic_intensity}, plotter exists={self.plotter is not None}, wvl_min={wvl_min}, wvl_max={wvl_max}, wvl_data exists={wavelength_data is not None}, int_data exists={intensity_data is not None}")
                if (plot_dynamic_intensity and self.plotter and
                        wvl_min is not None and wvl_max is not None and
                        wavelength_data is not None and intensity_data is not None):
                    try:
                        # Create mask for wavelength range
                        mask = (wavelength_data >= wvl_min) & (wavelength_data <= wvl_max)
                        if np.any(mask): # Check if any data falls within the range
                            max_intensity_in_range = np.max(intensity_data[mask])
                            actual_angle = current_pos # Use the actual position measured
                            logging.info(f"Dynamic Plot: Angle={actual_angle:.2f}, Max Intensity ({wvl_min}-{wvl_max}nm)={max_intensity_in_range:.3f}")
                            # Call the NEW plotting method (to be added in plotting_module.py)
                            self.plotter.add_intensity_analysis_point(actual_angle, max_intensity_in_range)
                        else:
                            logging.warning(f"No data points found within wavelength range [{wvl_min}, {wvl_max}] for angle {current_pos:.2f}")
                    except Exception as dyn_plot_e:
                        logging.error(f"Error calculating/plotting dynamic max intensity: {dyn_plot_e}")
                        self.update_status(f"Dyn. Plot Error: {dyn_plot_e}", error=True)
                # --- End Calculate Max Intensity ---


                # --- Intensity Calculation (OLD - can still run if data loaded, but maybe remove later?) ---
                intensity = 0.0 # Keep for now, might be used elsewhere or removed later
                if self.analyzer and intensity_data is not None:
                    logging.debug("Calculating intensity...")
                    try:
                        intensity = self.analyzer.calculate_intensity(intensity_data) # Pass intensity array
                        logging.info(f"Calculated intensity: {intensity:.2f}")
                    except Exception as calc_e:
                        logging.error(f"Error calculating intensity: {calc_e}")
                        self.update_status(f"Analysis Error: {calc_e}", error=True)
                elif not self.analyzer:
                    logging.warning("AnalysisModule not available, cannot calculate intensity.")
                else: # Analyzer exists but intensity_data is None
                    logging.warning("Intensity data not loaded, cannot calculate intensity.")


                # if self.plotter:
                    # Commented out plotting/analysis
                    # self.plotter.add_analysis_point(current_pos, intensity)

                result_entry = {'angle_target': angle, 'angle_actual': current_pos, 'intensity': intensity}
                all_results.append(result_entry)

                # --- Calculate and Update Progress/ETA ---
                progress = (i + 1) / num_steps
                elapsed_time = time.time() - start_time
                eta_sec = None
                if i > 0: # Avoid division by zero and estimate after first step
                    time_per_step = elapsed_time / (i + 1)
                    remaining_steps = num_steps - (i + 1)
                    eta_sec = remaining_steps * time_per_step
                    logging.debug(f"ETA Calculation: Elapsed={elapsed_time:.1f}s, Time/Step={time_per_step:.2f}s, Remaining={remaining_steps}, ETA={eta_sec:.1f}s")

                # Call progress update - assuming it handles step count and ETA
                # For now, pass all info. The receiving function needs to handle it.
                self.update_progress(progress, current_step=(i + 1), total_steps=num_steps, eta_sec=eta_sec)
                # --- End Progress/ETA Update ---

                logging.debug(f"--- Loop End: Step {i+1}/{num_steps} ---")

            # Scan finished successfully
            logging.info("Scan loop completed successfully.")
            self.update_status("Scan finished.") # Removed "Performing final analysis..."
            self.update_progress(1.0)

            # Report scan finished, even if data retrieval failed for some steps
            # self.update_status("Scan finished.") # Moved up
            self.scan_completed(success=True, message="Scan finished (data retrieval may have failed for some steps).")

        except RuntimeError as e:
            logging.error(f"RuntimeError during scan: {e}")
            self.update_status(f"Scan Error: {e}", error=True)
            self.scan_completed(success=False, message=f"Scan Error: {e}")
        except TimeoutError as e:
            logging.error(f"TimeoutError during scan: {e}")
            self.update_status(f"Scan Timeout: {e}", error=True)
            self.scan_completed(success=False, message=f"Scan Timeout: {e}")
        except Exception as e:
            logging.exception("Unexpected error during scan loop:")
            self.update_status(f"Unexpected Scan Error: {e}", error=True)
            # Ensure completion callback is called on unexpected error
            self.scan_completed(success=False, message=f"Unexpected Scan Error: {e}")
        finally:
            logging.info("Scan loop finished or exited. Running finally block.")
            self.scan_running = False
            self.update_progress(0, eta_sec=None) # Clear progress and ETA on exit
            # Ensure completion callback is called if loop finishes normally or aborts cleanly
            # Check if it was already called due to an error
            if not self._abort_event.is_set() and 'e' not in locals(): # Check if finished normally
                # Message was set previously for normal completion
                pass # scan_completed called at end of try block
            elif self._abort_event.is_set(): # Check if aborted
                # Check if completion already called by an error during abort sequence
                if 'e' not in locals():
                    self.scan_completed(success=False, message="Scan aborted by user.")
            # else: # Error occurred, scan_completed called in except block
            #     pass


# Example usage (for testing logic without GUI)
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    class MockKDC:
        def __init__(self): self._pos = 0.0; self._connected = True
        def is_connected(self): return self._connected
        def move_to(self, angle): logging.debug(f"MockKDC: Moving to {angle:.2f}"); time.sleep(0.2); self._pos = angle
        def wait_for_move(self, timeout_s): logging.debug("MockKDC: Waiting for move..."); time.sleep(0.1)
        def get_position(self): return self._pos
        def connect(self, sn): self._connected = True; return True
        def disconnect(self): self._connected = False; return True

    class MockLF:
        def __init__(self): self._connected = True
        def is_connected(self): return self._connected
        def acquire(self): logging.debug("MockLF: Acquiring..."); time.sleep(0.3); return True
        def get_data(self): logging.debug("MockLF: Getting data..."); return np.random.rand(10)
        def connect(self): self._connected = True; return True
        def disconnect(self): self._connected = False; return True
        def set_experiment_settings(self, *args): logging.debug(f"MockLF: Settings updated {args}")

    class MockAnalyzer:
        def calculate_intensity(self, data): return np.sum(data) if data is not None else 0
        def fit_polarization_data(self, ang, inten, fit_type):
            logging.debug(f"MockAnalyzer: Fitting {len(ang)} points, type={fit_type}")
            if len(ang) > 2:
                fit_curve = np.max(inten) * np.cos(np.radians(2*ang))**2 + np.min(inten)
                fit_params = {'amplitude': np.max(inten)-np.min(inten), 'phase_deg': 0, 'offset': np.min(inten)}
                return fit_curve, fit_params
            return None, None

    class MockPlotter:
        def __init__(self): self.angle_data = []; self.intensity_data = []
        def clear_analysis_data(self): self.angle_data = []; self.intensity_data = []; logging.debug("MockPlotter: Cleared data")
        def update_live_plot(self, data, x_axis=None): logging.debug(f"MockPlotter: Update live plot (size={data.size if data is not None else 0})")
        def add_analysis_point(self, angle, intensity): self.angle_data.append(angle); self.intensity_data.append(intensity); logging.debug(f"MockPlotter: Added analysis point ({angle:.1f}, {intensity:.1f})")
        def update_analysis_plot(self, fit_curve=None, fit_angles=None): logging.debug(f"MockPlotter: Update analysis plot (Fit={fit_curve is not None})")

    def mock_status(msg, error=False): print(f"STATUS: {msg}" + (" [ERROR]" if error else ""))
    def mock_progress(val): print(f"PROGRESS: {val:.2f}")
    def mock_completion(success, message): print(f"COMPLETED: Success={success}, Msg='{message}'")

    mock_kdc = MockKDC()
    mock_lf = MockLF()
    mock_analyzer = MockAnalyzer()
    mock_plotter = MockPlotter()

    scanner = ScanLogic(mock_kdc, mock_lf, mock_analyzer, mock_plotter,
                        mock_status, mock_progress, mock_completion)

    scan_params = {
        'start_angle': 0, 'end_angle': 90, 'step_angle': 15,
        'exposure': 0.1, 'accumulations': 1,
        'save_dir': '.', 'base_filename': 'mock_scan'
    }

    print("--- Starting Mock Scan ---")
    scanner.start_scan(scan_params)

    if scanner._scan_thread:
        scanner._scan_thread.join(timeout=10)
        if scanner._scan_thread.is_alive():
            print("ERROR: Scan thread did not finish!")

    print("--- Mock Scan Test Finished ---")
