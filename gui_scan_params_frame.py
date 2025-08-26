# gui_scan_params_frame.py
import customtkinter as ctk
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import logging # Added for logging
import os # <-- Import the os module
import numpy as np # <-- Import numpy for validation

class ScanParamsFrame(ctk.CTkFrame):
    """
    Frame for configuring polarization scan parameters.
    """
    # Accept manual_control_frame reference
    def __init__(self, master, app_instance, manual_control_frame):
        super().__init__(master, fg_color="transparent")
        self._app = app_instance # Store app instance
        self.scan_logic = app_instance.scan_logic # Get scan_logic from app instance
        self.manual_control_frame = manual_control_frame # Store reference

        self.grid_columnconfigure(1, weight=1) # Allow entry fields to expand

        # --- Title ---
        self.title_label = ctk.CTkLabel(self, text="Scan Parameters", font=ctk.CTkFont(weight="bold"))
        self.title_label.grid(row=0, column=0, columnspan=3, padx=10, pady=(0, 5), sticky="w")

        # --- Angle Parameters ---
        self.start_angle_label = ctk.CTkLabel(self, text="Start Angle (°):")
        self.start_angle_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.start_angle_entry = ctk.CTkEntry(self, placeholder_text="0.0", width=80)
        self.start_angle_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.end_angle_label = ctk.CTkLabel(self, text="End Angle (°):")
        self.end_angle_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.end_angle_entry = ctk.CTkEntry(self, placeholder_text="360.0", width=80)
        self.end_angle_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        self.step_angle_label = ctk.CTkLabel(self, text="Step Size (°):")
        self.step_angle_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.step_angle_entry = ctk.CTkEntry(self, placeholder_text="5.0", width=80)
        self.step_angle_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # --- Filename Option ---
        self.add_position_checkbox_var = tk.IntVar(value=0) # Variable for checkbox state
        self.add_position_checkbox = ctk.CTkCheckBox(
            self, text="Add position at the end filename",
            variable=self.add_position_checkbox_var
        )
        self.add_position_checkbox.grid(row=4, column=0, columnspan=3, padx=10, pady=5, sticky="w") # Reduced pady

        # --- Save Directory ---
        self.save_dir_label = ctk.CTkLabel(self, text="Save Directory:")
        self.save_dir_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.save_dir_var = tk.StringVar(value="") # Variable for directory path
        self.save_dir_entry = ctk.CTkEntry(self, textvariable=self.save_dir_var, placeholder_text="Directory for .csv files")
        self.save_dir_entry.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
        self.browse_button = ctk.CTkButton(self, text="Browse...", width=80, command=self.browse_directory)
        self.browse_button.grid(row=5, column=2, padx=5, pady=5, sticky="w")

        # --- Plotting Option ---
        self.plot_live_checkbox_var = tk.IntVar(value=1) # Default to plotting enabled
        self.plot_live_checkbox = ctk.CTkCheckBox(
            self, text="Plot Live Spectrum",
            variable=self.plot_live_checkbox_var
        )
        self.plot_live_checkbox.grid(row=6, column=0, columnspan=3, padx=10, pady=5, sticky="w") # Row 6

        # --- Dynamic Intensity Plotting Option ---
        self.plot_intensity_checkbox_var = tk.IntVar(value=0) # Default to disabled
        self.plot_intensity_checkbox = ctk.CTkCheckBox(
            self, text="Dynamically plot max Intensity",
            variable=self.plot_intensity_checkbox_var,
            command=self._toggle_wavelength_entries # Enable/disable entries based on checkbox
        )
        self.plot_intensity_checkbox.grid(row=7, column=0, columnspan=3, padx=10, pady=5, sticky="w") # New row 7

        # --- Wavelength Range Frame ---
        self.wavelength_range_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.wavelength_range_frame.grid(row=8, column=0, columnspan=3, padx=5, pady=0, sticky="ew") # New row 8
        self.wavelength_range_frame.grid_columnconfigure((1, 3), weight=1) # Allow entries to expand slightly

        self.wavelength_min_label = ctk.CTkLabel(self.wavelength_range_frame, text="Range Min (nm):")
        self.wavelength_min_label.grid(row=0, column=0, padx=(5,2), pady=2, sticky="w")
        self.wavelength_min_entry = ctk.CTkEntry(self.wavelength_range_frame, placeholder_text="e.g. 500", width=70)
        self.wavelength_min_entry.grid(row=0, column=1, padx=(0,5), pady=2, sticky="ew")

        self.wavelength_max_label = ctk.CTkLabel(self.wavelength_range_frame, text="Max (nm):")
        self.wavelength_max_label.grid(row=0, column=2, padx=(5,2), pady=2, sticky="w")
        self.wavelength_max_entry = ctk.CTkEntry(self.wavelength_range_frame, placeholder_text="e.g. 600", width=70)
        self.wavelength_max_entry.grid(row=0, column=3, padx=(0,5), pady=2, sticky="ew")

        # --- Scan Control Buttons ---
        self.scan_button = ctk.CTkButton(self, text="Start Scan", command=self.start_scan)
        self.scan_button.grid(row=9, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="ew") # Adjusted row to 9

        # Frame for Pause/Resume/Abort buttons
        self.control_button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_button_frame.grid(row=10, column=0, columnspan=3, padx=5, pady=0, sticky="ew") # Adjusted row to 10
        self.control_button_frame.grid_columnconfigure((0, 1, 2), weight=1) # Distribute space

        self.pause_button = ctk.CTkButton(self.control_button_frame, text="Pause Scan", command=self.pause_scan, state="disabled", fg_color="orange", hover_color="#FF8C00") # Darker Orange
        self.pause_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.resume_button = ctk.CTkButton(self.control_button_frame, text="Resume Scan", command=self.resume_scan, state="disabled", fg_color="green", hover_color="darkgreen")
        self.resume_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.abort_button = ctk.CTkButton(self.control_button_frame, text="Abort Scan", command=self.abort_scan, state="disabled", fg_color="red", hover_color="darkred")
        self.abort_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # TODO: Add validation for numeric entries

    def browse_directory(self):
        """Opens a dialog to select the save directory."""
        directory = filedialog.askdirectory()
        if directory:
            self.save_dir_var.set(directory) # Update the StringVar
            logging.info(f"Save directory selected: {directory}")

    def get_scan_parameters(self):
        """Retrieves and validates scan parameters from the GUI."""
        params = {}
        try:
            params['start_angle'] = float(self.start_angle_entry.get() or 0.0)
            params['end_angle'] = float(self.end_angle_entry.get() or 360.0)
            params['step_angle'] = float(self.step_angle_entry.get() or 5.0)
            if params['step_angle'] == 0: raise ValueError("Step angle cannot be zero")

            params['add_position_to_filename'] = bool(self.add_position_checkbox_var.get())

            if params['start_angle'] == params['end_angle']:
                raise ValueError("Start and End angles cannot be the same")

            # --- Get filename from ManualControlFrame ---
            if self.manual_control_frame and hasattr(self.manual_control_frame, 'lf_set_filename_var'):
                base_filename = self.manual_control_frame.lf_set_filename_var.get()
                if base_filename:
                    params['base_filename'] = base_filename
                else:
                    params['base_filename'] = "scan_data"
                    logging.warning("Filename entry is empty, using default 'scan_data'.")
            else:
                params['base_filename'] = "scan_data"
                logging.error("ManualControlFrame reference not available in ScanParamsFrame.")
            # --- End Get filename ---

            # --- Get Save Directory ---
            save_dir = self.save_dir_var.get()
            if not save_dir:
                # Default to current directory or raise error if required
                save_dir = "."
                logging.warning("Save directory is empty, defaulting to current directory.")
                # Optionally update status bar: self.update_status("Warning: Save directory empty.", error=True)
            elif not os.path.isdir(save_dir):
                raise ValueError(f"Save directory does not exist: {save_dir}")
            params['save_directory'] = save_dir
            # --- End Get Save Directory ---

            # --- Get Plotting Options ---
            params['plot_live_spectrum'] = bool(self.plot_live_checkbox_var.get())
            params['plot_dynamic_intensity'] = bool(self.plot_intensity_checkbox_var.get())
            # --- End Get Plotting Options ---

            # --- Get Wavelength Range (only if dynamic plot enabled) ---
            params['wavelength_min'] = None
            params['wavelength_max'] = None
            if params['plot_dynamic_intensity']:
                try:
                    min_str = self.wavelength_min_entry.get()
                    max_str = self.wavelength_max_entry.get()
                    if not min_str or not max_str:
                        raise ValueError("Wavelength range entries cannot be empty if dynamic plot is enabled.")
                    wvl_min = float(min_str)
                    wvl_max = float(max_str)
                    if wvl_min >= wvl_max:
                        raise ValueError("Wavelength Min must be less than Max.")
                    if wvl_min < 0 or wvl_max < 0:
                        raise ValueError("Wavelength values must be positive.")
                    params['wavelength_min'] = wvl_min
                    params['wavelength_max'] = wvl_max
                except ValueError as e_wvl:
                    # Re-raise with a more specific prefix
                    raise ValueError(f"Invalid Wavelength Range: {e_wvl}") from e_wvl
            # --- End Get Wavelength Range ---

            return params
        except ValueError as e:
            self.update_status(f"Invalid Parameter: {e}", error=True)
            print(f"Parameter validation error: {e}")
            return None

    def start_scan(self):
        """Callback for the Start Scan button."""
        logging.debug("Start Scan button clicked.") # Log button click
        logging.debug("Calling get_scan_parameters...") # Log before get params
        params = self.get_scan_parameters()
        logging.debug(f"get_scan_parameters returned: {params}") # Log returned params
        if params:
            # print(f"Starting scan with parameters: {params}") # Already logged above
            self.update_status("Starting scan...")
            # Update button states for starting scan
            self._set_button_states(scan_running=True, scan_paused=False)
            # Disable parameter entry during scan
            self._set_param_widgets_state("disabled")

            # Use the stored app instance reference
            if self._app.scan_logic:
                logging.debug("Calling self._app.scan_logic.start_scan...") # Log before calling scan logic
                self._app.scan_logic.start_scan(params)
            else:
                self.update_status("Scan Logic not initialized.", error=True)
                logging.error("Start Scan clicked but Scan Logic not found in main app.")
                # If logic isn't there, manually reset buttons/widgets state after a delay
                self.after(100, lambda: self._set_button_states(scan_running=False, scan_paused=False))
                self.after(100, lambda: self._set_param_widgets_state("normal"))

    # --- New Pause/Resume/Abort Methods ---
    def pause_scan(self):
        """Callback for the Pause Scan button."""
        logging.info("Pause Scan button clicked.")
        if self._app.scan_logic and self._app.scan_logic.is_running():
            self._app.scan_logic.pause_scan()
            self._set_button_states(scan_running=True, scan_paused=True)
        else:
            logging.warning("Pause clicked but scan logic not running/available.")

    def resume_scan(self):
        """Callback for the Resume Scan button."""
        logging.info("Resume Scan button clicked.")
        if self._app.scan_logic and self._app.scan_logic.is_running():
            self._app.scan_logic.resume_scan()
            self._set_button_states(scan_running=True, scan_paused=False)
        else:
            logging.warning("Resume clicked but scan logic not running/available.")

    def abort_scan(self):
        """Callback for the Abort Scan button."""
        logging.info("Abort Scan button clicked.")
        self.update_status("Aborting scan...") # Give immediate feedback

        # Use the stored app instance reference
        if self._app.scan_logic and self._app.scan_logic.is_running():
            self._app.scan_logic.abort_scan()
            # Disable pause/resume/abort immediately
            self.pause_button.configure(state="disabled")
            self.resume_button.configure(state="disabled")
            self.abort_button.configure(state="disabled")
            # The scan_finished_callback will handle the final state reset.
        else:
            self.update_status("Scan Logic not running or not initialized.", error=True)
            logging.error("Abort Scan clicked but Scan Logic not running/available.")
            # If logic isn't there, manually reset buttons/widgets state
            self._set_button_states(scan_running=False, scan_paused=False)
            self._set_param_widgets_state("normal")

    def scan_finished_callback(self, success: bool, message: str):
        """
        Callback executed by ScanLogic (via main_app) when the scan finishes,
        is aborted, or encounters an error during execution in its thread.
        This method handles re-enabling the GUI elements. Should reset everything
        to the idle state.
        """
        logging.info(f"Scan Params Frame notified of scan completion: Success={success}, Msg='{message}'")
        # Reset button states to idle (scan not running)
        self._set_button_states(scan_running=False, scan_paused=False)
        # Re-enable parameter widgets
        self._set_param_widgets_state("normal")

    def _set_param_widgets_state(self, state="normal"):
        """Enable/disable parameter entry widgets."""
        widgets = [
            self.start_angle_entry, self.end_angle_entry, self.step_angle_entry,
            self.add_position_checkbox,
            self.save_dir_entry, self.browse_button,
            self.plot_live_checkbox,
            self.plot_intensity_checkbox, # Add new checkbox
            self.wavelength_min_entry, # Add new entry
            self.wavelength_max_entry # Add new entry
        ]
        for widget in widgets:
            # Don't disable wavelength entries if the checkbox is checked,
            # unless the overall state is 'disabled' (scan running)
            if widget in [self.wavelength_min_entry, self.wavelength_max_entry]:
                if state == "normal" and not self.plot_intensity_checkbox_var.get():
                    widget.configure(state="disabled") # Disable if checkbox is off and not scanning
                else:
                    widget.configure(state=state) # Follow overall state (normal/disabled)
            else:
                widget.configure(state=state) # Apply state to other widgets

    def _toggle_wavelength_entries(self):
        """Enable/disable wavelength entries based on the checkbox state."""
        if self.plot_intensity_checkbox_var.get():
            self.wavelength_min_entry.configure(state="normal")
            self.wavelength_max_entry.configure(state="normal")
        else:
            self.wavelength_min_entry.configure(state="disabled")
            self.wavelength_max_entry.configure(state="disabled")

    # --- New Helper Method for Button States ---
    def _set_button_states(self, scan_running: bool, scan_paused: bool):
        """Centralized method to manage scan control button states."""
        if scan_running:
            self.scan_button.configure(state="disabled")
            self.abort_button.configure(state="normal")
            if scan_paused:
                self.pause_button.configure(state="disabled")
                self.resume_button.configure(state="normal")
            else: # Running but not paused
                self.pause_button.configure(state="normal")
                self.resume_button.configure(state="disabled")
        else: # Not running (idle or finished/aborted)
            self.scan_button.configure(state="normal")
            self.pause_button.configure(state="disabled")
            self.resume_button.configure(state="disabled")
            self.abort_button.configure(state="disabled")

    def update_status(self, message: str, error: bool = False):
        """Updates the main status bar (delegates)."""
        if hasattr(self._app, 'update_status_bar'):
            self._app.update_status_bar(message, error)
        else:
            print(f"Status Update (Frame): {message}" + (" (Error)" if error else ""))

# Example usage (for testing this frame independently)
if __name__ == "__main__":
    # This example won't fully work without the main app structure
    # but can be used for basic layout checks.
    app = ctk.CTk()
    app.geometry("400x450")
    app.title("Scan Params Frame Test")

    # Dummy app instance and manual frame for testing
    class MockManualFrame:
        lf_set_filename_var = tk.StringVar(value="test_mock_file")
    class MockApp:
        scan_logic = None # No real logic needed for layout test
        def update_status_bar(self, msg, error=False): print(f"STATUS: {msg}")
    mock_app = MockApp()
    mock_manual = MockManualFrame()

    frame = ScanParamsFrame(app, mock_app, mock_manual)
    frame.pack(expand=True, fill="both", padx=10, pady=10)
    frame._set_button_states(scan_running=False, scan_paused=False) # Set initial state

    app.mainloop()
