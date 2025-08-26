import customtkinter as ctk
import tkinter as tk
import numpy as np
import logging
import threading # For background tasks
import time # For delays if needed
import math # For isnan

# Configure basic logging if not already done elsewhere
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ManualControlFrame(ctk.CTkFrame):
    """
    Frame for manual control of the KDC101 stage and LightField acquisition.
    """
    def __init__(self, master, app_instance): # Changed controllers to app_instance
        super().__init__(master, fg_color="transparent")
        self._app = app_instance # Store app instance
        self.kdc_controller = app_instance.kdc101_controller # Get controller from app instance
        self.lf_controller = app_instance.lightfield_controller # Get controller from app instance

        self.grid_columnconfigure(1, weight=1) # Allow entry fields to expand
        self.grid_columnconfigure(3, weight=1) # Allow entry fields to expand

        # --- StringVars for LF parameters ---
        self.lf_current_exposure_var = tk.StringVar(value="N/A")
        self.lf_current_temp_var = tk.StringVar(value="N/A")
        self.lf_current_temp_status_var = tk.StringVar(value="N/A")
        self.lf_set_exposure_var = tk.StringVar(value="") # Default empty
        self.lf_set_filename_var = tk.StringVar(value="") # Default empty

        # --- Title ---
        self.title_label = ctk.CTkLabel(self, text="Manual Control", font=ctk.CTkFont(weight="bold"))
        self.title_label.grid(row=0, column=0, columnspan=4, padx=10, pady=(0, 5), sticky="w")

        # --- KDC101 Manual Control ---
        self.kdc_manual_label = ctk.CTkLabel(self, text="KDC101 Stage:")
        self.kdc_manual_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.kdc_pos_label = ctk.CTkLabel(self, text="Position (°):")
        self.kdc_pos_label.grid(row=2, column=0, padx=10, pady=2, sticky="w")
        self.kdc_pos_value = ctk.CTkLabel(self, text="---.--", width=60, anchor="e")
        self.kdc_pos_value.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        self.kdc_home_button = ctk.CTkButton(self, text="Home", width=60, command=self.home_stage)
        self.kdc_home_button.grid(row=2, column=2, columnspan=2, padx=5, pady=2, sticky="e")

        self.kdc_move_to_label = ctk.CTkLabel(self, text="Move To (°):")
        self.kdc_move_to_label.grid(row=3, column=0, padx=10, pady=2, sticky="w")
        self.kdc_move_to_entry = ctk.CTkEntry(self, placeholder_text="Angle", width=100) # Further Increased width
        self.kdc_move_to_entry.grid(row=3, column=1, padx=5, pady=2, sticky="ew")
        self.kdc_move_to_button = ctk.CTkButton(self, text="Go", width=60, command=self.move_to_stage)
        self.kdc_move_to_button.grid(row=3, column=2, padx=5, pady=2, sticky="w")

        self.kdc_move_rel_label = ctk.CTkLabel(self, text="Move Rel (°):")
        self.kdc_move_rel_label.grid(row=4, column=0, padx=10, pady=2, sticky="w")
        self.kdc_move_rel_entry = ctk.CTkEntry(self, placeholder_text="Step", width=100) # Further Increased width
        self.kdc_move_rel_entry.grid(row=4, column=1, padx=5, pady=2, sticky="ew")
        self.kdc_move_rel_button = ctk.CTkButton(self, text="Go", width=60, command=self.move_relative_stage)
        self.kdc_move_rel_button.grid(row=4, column=2, padx=5, pady=2, sticky="w")

        # KDC Velocity Controls
        self.kdc_vel_label = ctk.CTkLabel(self, text="Max Vel (°/s):")
        self.kdc_vel_label.grid(row=5, column=0, padx=10, pady=2, sticky="w")
        self.kdc_vel_entry = ctk.CTkEntry(self, placeholder_text="10.0", width=60)
        self.kdc_vel_entry.grid(row=5, column=1, padx=5, pady=2, sticky="ew")

        self.kdc_accel_label = ctk.CTkLabel(self, text="Accel (°/s²):")
        self.kdc_accel_label.grid(row=6, column=0, padx=10, pady=2, sticky="w")
        self.kdc_accel_entry = ctk.CTkEntry(self, placeholder_text="10.0", width=60)
        self.kdc_accel_entry.grid(row=6, column=1, padx=5, pady=2, sticky="ew")

        self.kdc_set_vel_button = ctk.CTkButton(self, text="Set Velocity", width=100, command=self.set_velocity_params)
        self.kdc_set_vel_button.grid(row=5, column=2, rowspan=2, padx=5, pady=2, sticky="nsew")


        # --- LightField Manual Control ---
        self.lf_manual_label = ctk.CTkLabel(self, text="LightField:", font=ctk.CTkFont(weight="bold"))
        self.lf_manual_label.grid(row=7, column=0, padx=10, pady=(15, 5), sticky="w")

        # --- LF Parameter Display ---
        self.lf_refresh_params_button = ctk.CTkButton(self, text="Refresh", width=60, command=self.read_lf_parameters_threaded)
        self.lf_refresh_params_button.grid(row=7, column=3, padx=5, pady=(15,5), sticky="e")

        self.lf_exp_disp_label = ctk.CTkLabel(self, text="Exposure (ms):")
        self.lf_exp_disp_label.grid(row=8, column=0, padx=10, pady=2, sticky="w")
        self.lf_exp_disp_value = ctk.CTkLabel(self, textvariable=self.lf_current_exposure_var, anchor="w")
        self.lf_exp_disp_value.grid(row=8, column=1, padx=5, pady=2, sticky="ew")

        self.lf_temp_disp_label = ctk.CTkLabel(self, text="Sensor Temp (C):")
        self.lf_temp_disp_label.grid(row=9, column=0, padx=10, pady=2, sticky="w")
        self.lf_temp_disp_value = ctk.CTkLabel(self, textvariable=self.lf_current_temp_var, anchor="w")
        self.lf_temp_disp_value.grid(row=9, column=1, padx=5, pady=2, sticky="ew")

        self.lf_status_disp_label = ctk.CTkLabel(self, text="Temp Status:")
        self.lf_status_disp_label.grid(row=10, column=0, padx=10, pady=2, sticky="w")
        self.lf_status_disp_value = ctk.CTkLabel(self, textvariable=self.lf_current_temp_status_var, anchor="w")
        self.lf_status_disp_value.grid(row=10, column=1, padx=5, pady=2, sticky="ew")

        # --- LF Parameter Setting ---
        self.lf_set_exp_label = ctk.CTkLabel(self, text="Set Exp (ms):")
        self.lf_set_exp_label.grid(row=8, column=2, padx=10, pady=2, sticky="w")
        self.lf_set_exp_entry = ctk.CTkEntry(self, textvariable=self.lf_set_exposure_var, width=80)
        self.lf_set_exp_entry.grid(row=8, column=3, padx=5, pady=2, sticky="ew")

        self.lf_set_fname_label = ctk.CTkLabel(self, text="Set Filename:")
        self.lf_set_fname_label.grid(row=9, column=2, padx=10, pady=2, sticky="w")
        self.lf_set_fname_entry = ctk.CTkEntry(self, textvariable=self.lf_set_filename_var, width=120)
        self.lf_set_fname_entry.grid(row=9, column=3, padx=5, pady=2, sticky="ew")

        self.lf_set_params_button = ctk.CTkButton(self, text="Set LF Params", command=self.set_lf_parameters_threaded)
        self.lf_set_params_button.grid(row=10, column=2, columnspan=2, padx=5, pady=5, sticky="ew")

        # --- LF Acquisition ---
        self.lf_acquire_button = ctk.CTkButton(self, text="Acquire Single Spectrum", command=self.acquire_single_spectrum) # Use threaded version
        self.lf_acquire_button.grid(row=11, column=0, columnspan=4, padx=10, pady=(10, 5), sticky="ew")

        # Initial state: disable controls until connected
        self.set_controls_state(kdc_connected=False, lf_connected=False)

    def home_stage(self):
        """Callback for the Home button."""
        logging.info("Manual Control: Home button clicked.")
        self.update_status("Homing KDC101 stage...")
        if self.kdc_controller and self.kdc_controller.is_connected():
            try:
                # Consider running in thread later if blocking
                self.kdc_controller.home()
                self.update_status("KDC101 homing initiated.")
                # TODO: Start polling position after home completes or use wait_for_move
                # Consider disabling move buttons during home
            except RuntimeError as e: # Catch specific controller errors
                self.update_status(f"KDC Home Error: {e}", error=True)
                logging.error(f"RuntimeError homing stage: {e}")
            except Exception as e: # Catch unexpected errors
                self.update_status(f"Unexpected KDC Home Error: {e}", error=True)
                logging.exception("Unexpected error homing stage:")
        else:
            self.update_status("KDC101 not connected.", error=True)
            logging.warning("Home command ignored: KDC101 not connected.")

    def move_to_stage(self):
        """Callback for the Move To button."""
        try:
            angle_str = self.kdc_move_to_entry.get()
            angle = float(angle_str)
            logging.info(f"Manual Control: Move To button clicked (Angle: {angle}).")
            self.update_status(f"Moving KDC101 to {angle:.2f}°...")
            if self.kdc_controller and self.kdc_controller.is_connected():
                # Consider running in thread later if blocking
                self.kdc_controller.move_to(angle)
                self.update_status(f"KDC101 move to {angle:.2f}° initiated.")
                # TODO: Start polling position or use wait_for_move
                # Consider disabling move buttons during move
            else:
                self.update_status("KDC101 not connected.", error=True)
                logging.warning("Move To command ignored: KDC101 not connected.")
        except ValueError:
            self.update_status(f"Invalid angle '{angle_str}' for Move To.", error=True)
            logging.warning(f"Invalid input for Move To: {angle_str}")
        except RuntimeError as e: # Catch specific controller errors
            self.update_status(f"KDC Move To Error: {e}", error=True)
            logging.error(f"RuntimeError moving stage: {e}")
        except Exception as e: # Catch unexpected errors
            self.update_status(f"Unexpected KDC Move To Error: {e}", error=True)
            logging.exception("Unexpected error moving stage:")

    def move_relative_stage(self):
        """Callback for the Move Relative button."""
        step_str = self.kdc_move_rel_entry.get()
        print(f"--- DEBUG (move_relative_stage): Button clicked. Value read: '{step_str}' ---") # Add log
        try:
            step = float(step_str)
            print(f"--- DEBUG (move_relative_stage): Parsed step: {step} ---") # Add log
            logging.info(f"Manual Control: Move Relative button clicked (Step: {step}).")
            self.update_status(f"Moving KDC101 by {step:.2f}°...")
            if self.kdc_controller and self.kdc_controller.is_connected():
                print(f"--- DEBUG (move_relative_stage): Calling kdc_controller.move_relative({step}) ---") # Add log
                # Consider running in thread later if blocking
                self.kdc_controller.move_relative(step)
                print(f"--- DEBUG (move_relative_stage): kdc_controller.move_relative call finished ---") # Add log
                self.update_status(f"KDC101 relative move ({step:.2f}°) initiated.")
                # TODO: Start polling position or use wait_for_move
                # Consider disabling move buttons during move
            else:
                self.update_status("KDC101 not connected.", error=True)
                logging.warning("Move Relative command ignored: KDC101 not connected.")
        except ValueError:
            self.update_status(f"Invalid step '{step_str}' for Move Relative.", error=True)
            logging.warning(f"Invalid input for Move Relative: {step_str}")
        except RuntimeError as e: # Catch specific controller errors
            self.update_status(f"KDC Move Relative Error: {e}", error=True)
            logging.error(f"RuntimeError moving stage relatively: {e}")
        except Exception as e: # Catch unexpected errors
            self.update_status(f"Unexpected KDC Move Relative Error: {e}", error=True)
            logging.exception("Unexpected error moving stage relatively:")

    def acquire_single_spectrum(self):
        """Callback for the Acquire Single Spectrum button - starts worker thread."""
        logging.info("Manual Control: Acquire Single Spectrum clicked.")
        if self.lf_controller and self.lf_controller.is_connected():
            self.lf_acquire_button.configure(state="disabled") # Disable button during acquire
            self.update_status("Starting single acquisition...")
            # Run in thread
            acq_thread = threading.Thread(target=self._acquire_single_worker, daemon=True)
            acq_thread.start()
        else:
            self.update_status("LightField not connected.", error=True)
            logging.warning("Acquire Single Spectrum ignored: LightField not connected.")

    def _acquire_single_worker(self):
        """Worker function for single acquisition (runs in background thread)."""
        success = False
        spectrum_data = None
        error_msg = None
        try:
            # Note: We use the settings currently active in LightField,
            # assuming they were set via "Set LF Params" or manually in LF.
            if self.lf_controller.acquire(): # Returns True on success
                spectrum_data = self.lf_controller.get_data()
                if spectrum_data is not None:
                    success = True
                    logging.info(f"Acquired spectrum data, shape: {spectrum_data.shape}")
                else:
                    error_msg = "Spectrum acquired but failed to get data."
            else:
                error_msg = "Spectrum acquisition failed (acquire returned False)."
        except RuntimeError as e:
            error_msg = f"LightField Acquire Error: {e}"
            logging.error(f"RuntimeError acquiring spectrum: {e}")
        except Exception as e:
            error_msg = f"Unexpected LightField Acquire Error: {e}"
            logging.exception("Error acquiring spectrum:")

        # Schedule GUI update back on main thread
        self._app.after(0, lambda: self._handle_acquire_single_result(success, spectrum_data, error_msg))

    def _handle_acquire_single_result(self, success: bool, data: np.ndarray | None, error_msg: str | None):
        """Handles GUI updates after single acquisition attempt (runs in main thread)."""
        self.lf_acquire_button.configure(state="normal") # Re-enable button
        if success and data is not None:
            self.update_status("Single spectrum acquired.")
            # Update live plot via main app's plotting module
            if hasattr(self._app, 'plotting_module') and self._app.plotting_module:
                # Commented out as requested to disable plotting on single acquire
                # try:
                #     self._app.plotting_module.update_live_plot(data)
                # except Exception as plot_e:
                #     logging.error(f"Error updating live plot: {plot_e}")
                #     self.update_status(f"Plot Error: {plot_e}", error=True)
                pass # Keep block structure
            else:
                logging.warning("Plotting module not found on main app instance.")
            # Optionally refresh displayed parameters after acquisition
            self.read_lf_parameters_threaded()
        else:
            final_msg = error_msg or "Unknown acquisition error."
            self.update_status(final_msg, error=True)

    def set_velocity_params(self):
        """Callback for the Set Velocity button."""
        try:
            max_vel_str = self.kdc_vel_entry.get() or "10.0" # Use placeholder if empty
            accel_str = self.kdc_accel_entry.get() or "10.0" # Use placeholder if empty
            max_vel = float(max_vel_str)
            accel = float(accel_str)

            if max_vel <= 0 or accel <= 0:
                raise ValueError("Velocity and acceleration must be positive.")

            logging.info(f"Manual Control: Set Velocity clicked (MaxVel={max_vel}, Accel={accel}).")
            self.update_status(f"Setting KDC101 velocity/acceleration...")

            if self.kdc_controller and self.kdc_controller.is_connected():
                # Note: The controller's set_velocity expects degrees/sec and degrees/sec^2
                # Unit conversions to device units happen inside the controller method.
                # Need to verify those conversions in kdc101_controller.py are correct for KDC101.
                self.kdc_controller.set_velocity(max_velocity_dps=max_vel, acceleration_dps2=accel)
                self.update_status(f"KDC101 velocity set (Max: {max_vel:.1f}°/s, Accel: {accel:.1f}°/s²).")
            else:
                self.update_status("KDC101 not connected.", error=True)
                logging.warning("Set Velocity command ignored: KDC101 not connected.")

        except ValueError as e:
            self.update_status(f"Invalid velocity/acceleration value: {e}", error=True)
            logging.warning(f"Invalid input for Set Velocity: Vel='{max_vel_str}', Accel='{accel_str}'")
        except RuntimeError as e: # Catch specific controller errors
            self.update_status(f"KDC Set Velocity Error: {e}", error=True)
            logging.error(f"RuntimeError setting velocity: {e}")
        except Exception as e: # Catch unexpected errors
            self.update_status(f"Unexpected KDC Set Velocity Error: {e}", error=True)
            logging.exception("Unexpected error setting velocity:")


    def update_position_display(self, position: float):
        """Updates the current position label, handling potential NaN values."""
        # Import math if not already imported at the top of the file
        import math
        if position is None or math.isnan(position):
            display_text = "---.--"
            # Optionally log that an invalid position was received
            # logging.debug("Received invalid position (None or NaN) for display.")
        else:
            try:
                display_text = f"{position:.2f}"
            except (TypeError, ValueError):
                # Handle potential formatting errors, though float should be fine
                display_text = "Error"
                logging.warning(f"Could not format position value: {position}")

        self.kdc_pos_value.configure(text=display_text)

    def set_controls_state(self, kdc_connected: bool, lf_connected: bool):
        """Enable or disable manual control widgets based on connection status."""
        logging.info(f"Setting controls state: kdc_connected={kdc_connected}, lf_connected={lf_connected}")
        kdc_state = "normal" if kdc_connected else "disabled"
        lf_state = "normal" if lf_connected else "disabled" # Determine state based on lf_connected

        # KDC Controls - Buttons
        kdc_buttons = [
            self.kdc_home_button, self.kdc_move_to_button,
            self.kdc_move_rel_button, self.kdc_set_vel_button
        ]
        for widget in kdc_buttons:
            widget.configure(state=kdc_state)

        # KDC Controls - Entry Fields (explicitly set state)
        kdc_entries = [
            self.kdc_move_to_entry, self.kdc_move_rel_entry,
            self.kdc_vel_entry, self.kdc_accel_entry
        ]
        for widget in kdc_entries:
            widget.configure(state=kdc_state) # Set state based on kdc_connected


        # Position display is always enabled, just shows '---.--' when disabled/disconnected
        if not kdc_connected:
            # self.update_position_display(0.0) # Don't force to 0, just show placeholder
            self.kdc_pos_value.configure(text="---.--")
        # else: # Optionally update position immediately when connected? Needs polling setup.
        # If you want to attempt an immediate update upon connection:
        # try:
        #     if self.kdc_controller:
        #         pos = self.kdc_controller.get_position()
        #         self.update_position_display(pos)
        # except Exception as e:
        #     logging.warning(f"Failed initial position update on connect: {e}")
        #     self.kdc_pos_value.configure(text="Error")


        # LightField Controls - Apply the determined lf_state
        lf_widgets = [
            self.lf_refresh_params_button,
            self.lf_set_exp_entry,
            self.lf_set_fname_entry,
            self.lf_set_params_button,
            self.lf_acquire_button
        ]
        logging.debug(f"Applying LF state '{lf_state}' to {len(lf_widgets)} widgets.") # Add log
        for widget in lf_widgets:
            try: # Add try-except just in case a widget is None unexpectedly
                widget_name = getattr(widget, '_name', str(widget)) # Try to get a name
                widget.configure(state=lf_state)
                logging.debug(f"  - Set state='{lf_state}' for widget: {widget_name}") # Add log
            except Exception as e:
                logging.error(f"Error configuring state for widget {widget}: {e}")

        # Clear display fields if not connected
        if not lf_connected:
            self.lf_current_exposure_var.set("N/A")
            self.lf_current_temp_var.set("N/A")
            self.lf_current_temp_status_var.set("N/A")
            self.lf_set_exposure_var.set("") # Clear set fields too
            self.lf_set_filename_var.set("")
        else:
            # If connecting, trigger an initial parameter read
            self.read_lf_parameters_threaded()


    # --- LF Parameter Read/Set ---

    def read_lf_parameters_threaded(self):
        """Reads current LF parameters in a background thread."""
        if self.lf_controller and self.lf_controller.is_connected():
            self.update_status("Reading LightField parameters...")
            # Disable refresh button while reading
            self.lf_refresh_params_button.configure(state="disabled")
            read_thread = threading.Thread(target=self._read_lf_params_worker, daemon=True)
            read_thread.start()
        else:
            self.update_status("Cannot read: LightField not connected.", error=True)

    def _read_lf_params_worker(self):
        """Worker to read LF parameters."""
        params = {'exposure': None, 'temp': None, 'status': None}
        error_msg = None
        try:
            params['exposure'] = self.lf_controller.get_exposure_time_ms()
            params['temp'] = self.lf_controller.get_sensor_temperature()
            params['status'] = self.lf_controller.get_sensor_temperature_status()
        except Exception as e:
            error_msg = f"Error reading LF params: {e}"
            logging.exception("Error reading LF parameters in worker:")

        self._app.after(0, lambda: self._handle_read_lf_params_result(params, error_msg))

    def _handle_read_lf_params_result(self, params: dict, error_msg: str | None):
        """Update GUI with read parameters."""
        self.lf_refresh_params_button.configure(state="normal") # Re-enable button
        if error_msg:
            self.update_status(error_msg, error=True)
            self.lf_current_exposure_var.set("Error")
            self.lf_current_temp_var.set("Error")
            self.lf_current_temp_status_var.set("Error")
        else:
            exp_val = f"{params['exposure']:.3f}" if params['exposure'] is not None else "N/A"
            temp_val = f"{params['temp']:.2f}" if params['temp'] is not None else "N/A"
            status_val = params['status'] if params['status'] is not None else "N/A"

            self.lf_current_exposure_var.set(exp_val)
            self.lf_current_temp_var.set(temp_val)
            self.lf_current_temp_status_var.set(status_val)
            self.update_status("LightField parameters updated.")

    def set_lf_parameters_threaded(self):
        """Sets LF parameters in a background thread."""
        if self.lf_controller and self.lf_controller.is_connected():
            exp_str = self.lf_set_exposure_var.get()
            fname_str = self.lf_set_filename_var.get()
            try:
                exposure_ms = float(exp_str) if exp_str else None # Allow empty to skip
                filename = fname_str if fname_str else None # Allow empty to skip

                if exposure_ms is None and filename is None:
                    self.update_status("No parameters entered to set.", error=True)
                    return

                self.update_status("Setting LightField parameters...")
                self.lf_set_params_button.configure(state="disabled") # Disable button
                set_thread = threading.Thread(target=self._set_lf_params_worker, args=(exposure_ms, filename), daemon=True)
                set_thread.start()

            except ValueError:
                self.update_status(f"Invalid exposure value: '{exp_str}'", error=True)
        else:
            self.update_status("Cannot set: LightField not connected.", error=True)

    def _set_lf_params_worker(self, exposure_ms: float | None, filename: str | None):
        """Worker to set LF parameters."""
        results = {'exposure': None, 'filename': None} # None=not attempted, True=success, False=fail
        error_msg = None
        try:
            if exposure_ms is not None:
                results['exposure'] = self.lf_controller.set_exposure_time_ms(exposure_ms)
            if filename is not None:
                results['filename'] = self.lf_controller.set_base_filename(filename)
        except Exception as e:
            error_msg = f"Error setting LF params: {e}"
            logging.exception("Error setting LF parameters in worker:")

        self._app.after(0, lambda: self._handle_set_lf_params_result(results, error_msg))

    def _handle_set_lf_params_result(self, results: dict, error_msg: str | None):
        """Update GUI after setting LF parameters."""
        self.lf_set_params_button.configure(state="normal") # Re-enable button
        if error_msg:
            self.update_status(error_msg, error=True)
        else:
            msgs = []
            if results['exposure'] is True: msgs.append("Exposure set.")
            elif results['exposure'] is False: msgs.append("Exposure FAILED.")
            if results['filename'] is True: msgs.append("Filename set.")
            elif results['filename'] is False: msgs.append("Filename FAILED.")

            if not msgs: final_msg = "No parameters were set."
            else: final_msg = " ".join(msgs)
            self.update_status(final_msg, error=(False in results.values()))

            # Refresh displayed parameters if anything was set successfully
            if True in results.values():
                self.read_lf_parameters_threaded()


    def update_status(self, message: str, error: bool = False):
        """Updates the main status bar (delegates)."""
        # Use the stored app instance reference
        if hasattr(self._app, 'update_status_bar'):
            self._app.update_status_bar(message, error)
        else:
            # Fallback if the method doesn't exist (e.g., during standalone testing)
            print(f"Status Update (Frame): {message}" + (" (Error)" if error else ""))

# Example usage (for testing this frame independently)
if __name__ == "__main__":
    # Mock controllers for testing
    class MockController:
        def __init__(self, name="Mock"): self._connected = True; self.name = name
        def is_connected(self): return self._connected
        def home(self): print(f"{self.name}: Homing...")
        def move_to(self, pos): print(f"{self.name}: Moving to {pos}...")
        def move_relative(self, step): print(f"{self.name}: Moving by {step}...")
        def acquire(self, exp, acc): print(f"{self.name}: Acquiring (exp={exp}, acc={acc})..."); return [1,2,3] # Simulate data
        def get_position(self): import random; return random.uniform(0, 360)

    app = ctk.CTk()
    app.geometry("400x300")
    app.title("Manual Control Frame Test")

    # Add dummy status update method
    def update_status_bar(message, error=False): print(f"APP STATUS: {message}" + (" [ERROR]" if error else ""))
    app.update_status_bar = update_status_bar

    # Mock main window and scan params frame for exposure/accum access
    class MockScanParams: exposure_entry = ctk.CTkEntry(app); accumulations_entry = ctk.CTkEntry(app)
    class MockMainWindow: scan_params_frame = MockScanParams()
    class MockMaster: main_window = MockMainWindow(); update_status_bar = update_status_bar
    app.main_window = MockMainWindow() # Attach to app instance for the frame's master.master access

    mock_kdc = MockController("KDC101")
    mock_lf = MockController("LightField")

    frame = ManualControlFrame(app, mock_kdc, mock_lf)
    frame.pack(expand=True, fill="both", padx=10, pady=10)
    frame.set_controls_state(True) # Enable controls for testing

    # Simulate position updates
    def update_pos():
        if mock_kdc.is_connected():
            frame.update_position_display(mock_kdc.get_position())
        app.after(1000, update_pos) # Update every second
    # update_pos() # Uncomment to test position updates

    app.mainloop()
