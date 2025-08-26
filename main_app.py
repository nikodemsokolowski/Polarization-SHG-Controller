import customtkinter as ctk
import logging
import time # For periodic updates (though managed by 'after' now)
import sys # To check command-line arguments
import threading # <-- Import threading
import lightfield_controller
print(f"--- IMPORTING lightfield_controller FROM: {lightfield_controller.__file__} ---")

# Assuming gui_main_window is in the same directory or correctly in sys.path
try:
    from gui_main_window import MainWindow
except ImportError as e:
    print(f"ERROR: Failed to import MainWindow from gui_main_window: {e}")
    sys.exit(1)


# Conditionally import real or mock hardware
USE_MOCK = "--mock" in sys.argv

if USE_MOCK:
    try:
        from mock_hardware import MockKDC101Controller as KDC101Controller
        from mock_hardware import MockLightFieldController as LightFieldController
        print("--- USING MOCK HARDWARE ---")
    except ImportError as e:
        print(f"ERROR: Failed to import mock hardware: {e}. Check mock_hardware.py.")
        sys.exit(1)
else:
    try:
        from kdc101_controller import KDC101Controller
        from lightfield_controller import LightFieldController
    except ImportError as e:
        print(f"ERROR: Failed to import real hardware controllers: {e}. Check controller files and dependencies (pythonnet, Kinesis, LF SDK).")
        sys.exit(1)

# Assuming other modules are accessible
try:
    from scan_logic import ScanLogic
    from analysis_module import AnalysisModule
    from plotting_module import PlottingModule
except ImportError as e:
    print(f"ERROR: Failed to import core modules (ScanLogic, Analysis, Plotting): {e}")
    sys.exit(1)

# Basic logging setup
log_level = logging.DEBUG # Keep DEBUG for detailed output
logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

class PolarizationScanApp(ctk.CTk):
    """
    Main application class for the Polarization Scan Controller.
    Orchestrates the GUI and controller interactions.
    Includes threaded periodic position updates and safe closing mechanism.
    """
    def __init__(self):
        super().__init__()

        self._is_closing = False # <-- Flag to indicate shutdown sequence

        self.title("Polarization Scan Controller")
        self.geometry("1200x800")

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # --- Initialize Controllers ---
        try:
            self.kdc101_controller = KDC101Controller()
            logging.info(f"{'Mock' if USE_MOCK else ''}KDC101Controller instantiated.")
        except Exception as e:
            logging.exception("Failed to instantiate KDC101Controller:")
            self.kdc101_controller = None

        try:
            self.lightfield_controller = LightFieldController()
            logging.info(f"{'Mock' if USE_MOCK else ''}LightFieldController instantiated.")
            # --- Force early DLL load attempt for debugging ---
            if not USE_MOCK and self.lightfield_controller:
                print("--- Attempting early DLL load... ---")
                try:
                    # Pass None, load_dlls has internal logic to find path
                    load_success = self.lightfield_controller.load_dlls(None)
                    print(f"--- Early DLL load attempt finished. Success: {load_success} ---")
                except Exception as dll_load_e:
                    print(f"--- EXCEPTION during early DLL load attempt: {dll_load_e} ---")
                    logging.error(f"Exception during early DLL load: {dll_load_e}")
            # --- End early DLL load ---
            print("-" * 40)
            print(f"--- PRINT IMMEDIATELY AFTER CREATION (and early load attempt) ---")
            print(f"--- Type: {type(self.lightfield_controller)}")
            print(f"--- Does it have 'is_connected'? {hasattr(self.lightfield_controller, 'is_connected')}")
            print(f"--- Does it have 'disconnect'? {hasattr(self.lightfield_controller, 'disconnect')}")
            print("-" * 40)
        except Exception as e:
            logging.exception(f"Failed to instantiate {'Mock' if USE_MOCK else ''}LightFieldController:")
            self.lightfield_controller = None

        # --- Initialize Modules ---
        self.analysis_module = AnalysisModule()
        logging.info("AnalysisModule instantiated.")
        self.plotting_module = PlottingModule()
        logging.info("PlottingModule instantiated.")

        # --- Initialize Scan Logic ---
        self.scan_logic = ScanLogic(
            kdc_controller=self.kdc101_controller,
            lf_controller=self.lightfield_controller,
            analysis_module=self.analysis_module,
            plotting_module=self.plotting_module,
            status_callback=self.update_status_bar,
            progress_callback=self.update_progress_display, # Use new combined method
            completion_callback=self.on_scan_completed,
            eta_callback=self.update_eta_display # Pass the new callback
        )
        logging.info("ScanLogic instantiated.")

        # --- Create GUI ---
        try:
            # Pass self (PolarizationScanApp instance) as 'app_instance'
            self.main_window = MainWindow(master=self, app_instance=self)
            self.main_window.pack(expand=True, fill="both")
        except Exception as e:
            logging.exception("Failed to create MainWindow GUI:")
            self.destroy() # Attempt cleanup even if GUI fails
            return

        # --- Periodic Updates ---
        self.position_update_ms = 200 # Update interval in milliseconds (faster refresh)
        self.position_update_job = None
        self.start_periodic_updates()

        # --- Window Closing Handler ---
        # REMOVED: self.protocol("WM_DELETE_WINDOW", ...) - Using destroy override instead

        # --- Initial Status ---
        self.update_status_bar("Application initialized.")
        self.update_manual_controls_state() # Set initial state


    # --- Callback Methods ---

    def on_scan_completed(self, success: bool, message: str):
        """Callback function passed to ScanLogic, executed when scan finishes."""
        if self._is_closing: return # Prevent execution during shutdown
        logging.info(f"Scan completion callback received: Success={success}, Msg='{message}'")
        self.after(0, lambda: self._handle_scan_completion_gui(success, message))

    def _handle_scan_completion_gui(self, success: bool, message: str):
        """Handles GUI updates after scan completion (runs in main thread)."""
        if self._is_closing: return # Prevent execution during shutdown
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'scan_params_frame'):
            self.main_window.scan_params_frame.scan_finished_callback(success, message)
        else:
            logging.error("Cannot find scan_params_frame to signal scan completion.")
        self.update_status_bar(message, error=not success)

    # --- GUI Update Methods ---

    def update_status_bar(self, message: str, error: bool = False):
        """Updates the status bar in the StatusLogFrame."""
        if self._is_closing: return # Prevent execution during shutdown
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'status_log_frame'):
            self.after(0, lambda msg=message, err=error:
                    self.main_window.status_log_frame.update_status(msg, err))
        else:
            log_func = logging.error if error else logging.info
            log_func(f"Status Update (Early/No GUI): {message}")

    # --- Combined Progress Update Method ---
    def update_progress_display(self, value: float, current_step: int | None = None, total_steps: int | None = None, eta_sec: float | None = None):
        """Updates the progress bar, step count, and ETA in the StatusLogFrame."""
        if self._is_closing: return # Prevent execution during shutdown
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'status_log_frame'):
            # Pass all arguments to the frame's update method
            self.after(0, lambda v=value, cs=current_step, ts=total_steps, eta=eta_sec:
                    self.main_window.status_log_frame.update_progress(v, cs, ts, eta))

    # --- Separate ETA Update (kept for potential direct use, though combined is preferred now) ---
    def update_eta_display(self, eta_string: str):
        """Updates the ETA display in the StatusLogFrame."""
        # This might be redundant now if update_progress_display handles ETA
        # Kept for clarity or if direct ETA update is needed elsewhere
        if self._is_closing: return
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'status_log_frame'):
            # Assuming status_log_frame has an update_eta method
            if hasattr(self.main_window.status_log_frame, 'update_eta'):
                self.after(0, lambda eta=eta_string:
                        self.main_window.status_log_frame.update_eta(eta))
            else: # Fallback if only update_progress exists
                logging.warning("update_eta method not found on status_log_frame, ETA might not display separately.")


    def log_message(self, message: str, is_error: bool = False):
        """Adds a message to the log text area in the StatusLogFrame."""
        if self._is_closing: return # Prevent execution during shutdown
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'status_log_frame'):
            self.after(0, lambda msg=message, err=is_error:
                    self.main_window.status_log_frame.log_message(msg, err))

    # --- Threaded Periodic Position Update ---

    def start_periodic_updates(self):
        """Starts the periodic task initiator for KDC101 position updates."""
        def _periodic_update_task_initiator():
            if self._is_closing: return # Stop if closing

            try:
                if self.kdc101_controller and self.kdc101_controller.is_connected() and self.winfo_exists():
                    fetch_thread = threading.Thread(target=self._fetch_kdc_position_background, daemon=True)
                    fetch_thread.start()
            except Exception as e:
                logging.error(f"Unhandled exception in periodic update initiator: {e}")
            finally:
                # Reschedule only if not closing
                if not self._is_closing and self.winfo_exists():
                    self.position_update_job = self.after(self.position_update_ms, _periodic_update_task_initiator)

        self.stop_periodic_updates()
        if not self._is_closing: # Don't start if already closing during init
            self.position_update_job = self.after(self.position_update_ms, _periodic_update_task_initiator)
            logging.info("Started periodic position update initiator.")

    def stop_periodic_updates(self):
        """Stops the periodic position update initiator."""
        if self.position_update_job:
            self.after_cancel(self.position_update_job)
            self.position_update_job = None
            logging.info("Stopped periodic position updates.")

    def _fetch_kdc_position_background(self):
        """Fetches KDC101 position in a background thread."""
        if self._is_closing: return

        position = float('nan')
        error = None
        try:
            if self.kdc101_controller:
                position = self.kdc101_controller.get_position()
            else:
                error = "KDC Controller unavailable in background thread."
        except RuntimeError as e:
            error = f"RuntimeError getting KDC position: {e}"
            logging.warning(error)
        except Exception as e:
            error = f"Unexpected error getting KDC position: {e}"
            logging.exception(error)

        # Schedule UI update only if not closing
        if not self._is_closing and self.winfo_exists():
            self.after(0, lambda: self._update_position_display_mainthread(position, error))

    def _update_position_display_mainthread(self, position: float, error: str | None):
        """Updates the position display (runs in main thread)."""
        if self._is_closing: return # Prevent execution during shutdown

        if error:
            position = float('nan')

        if (hasattr(self, 'main_window') and self.main_window and
            hasattr(self.main_window, 'manual_control_frame') and self.main_window.manual_control_frame and
            hasattr(self.main_window.manual_control_frame, 'update_position_display')):
            try:
                self.main_window.manual_control_frame.update_position_display(position)
            except Exception as e:
                logging.error(f"Error calling update_position_display on manual frame: {e}")

    # --- State Update Method ---

    def update_manual_controls_state(self):
        """ Checks device connection status and updates the ManualControlFrame's widget states."""
        if self._is_closing: return # Prevent execution during shutdown

        kdc_connected = False
        lf_connected = False

        # Safely check KDC status
        if self.kdc101_controller:
            try:
                kdc_connected = self.kdc101_controller.is_connected()
            except Exception as e:
                logging.error(f"Error checking KDC status in update_manual_controls_state: {e}")
                kdc_connected = False
        logging.debug(f"Checking KDC connection status for GUI update: {kdc_connected}")

        # Safely check LightField status
        if self.lightfield_controller:
            try:
                # *** IMPORTANT: Check if this is the source of the error ***
                if hasattr(self.lightfield_controller, 'is_connected'):
                    lf_connected = self.lightfield_controller.is_connected()
                else:
                    logging.error("'is_connected' method MISSING from self.lightfield_controller object!")
                    lf_connected = False # Assume not connected if method is missing
            except Exception as e:
                # Log the specific error from the is_connected call if it exists
                logging.error(f"Error calling/checking LF is_connected in update_manual_controls_state: {e}")
                lf_connected = False
        logging.debug(f"Checking LF connection status for GUI update: {lf_connected}")

        # Update the ManualControlFrame
        if (hasattr(self, 'main_window') and self.main_window and
            hasattr(self.main_window, 'manual_control_frame') and self.main_window.manual_control_frame):
            print(f"--- DEBUG (main_app.update_manual_controls_state): Calling manual_frame.set_controls_state with kdc={kdc_connected}, lf={lf_connected} ---") # Log before call
            logging.debug(f"Calling manual_control_frame.set_controls_state(kdc_connected={kdc_connected}, lf_connected={lf_connected})")
            try:
                self.main_window.manual_control_frame.set_controls_state(
                    kdc_connected=kdc_connected,
                    lf_connected=lf_connected
                )
                if kdc_connected:
                    self._update_position_display_mainthread(float('nan'), None)
                    immediate_fetch_thread = threading.Thread(target=self._fetch_kdc_position_background, daemon=True)
                    immediate_fetch_thread.start()
            except Exception as e:
                logging.error(f"Error calling set_controls_state on manual frame: {e}")
        else:
            logging.warning("Could not find main_window or manual_control_frame to update state.")


    # --- Application Closing ---

    # Renamed from on_closing
    def _perform_cleanup(self):
        """Handles cleanup actions before the application window is destroyed."""
        if self._is_closing: return # Prevent double execution
        self._is_closing = True # Set the closing flag

        logging.info("Performing cleanup actions...")
        self.stop_periodic_updates()

        # Stop Scan Thread First
        if self.scan_logic and self.scan_logic.is_running():
            logging.info("Stopping active scan...")
            self.scan_logic.stop_scan()
            scan_thread = getattr(self.scan_logic, '_scan_thread', None)
            if scan_thread and scan_thread.is_alive():
                logging.info("Waiting for scan thread to exit (max 2s)...")
                scan_thread.join(timeout=2.0)
                if scan_thread.is_alive(): logging.warning("Scan thread did not exit cleanly.")
                else: logging.info("Scan thread exited.")
            elif self.scan_logic.is_running(): logging.warning("Scan logic running but no thread found?")

        # --- Debugging LightFieldController just before disconnect attempt ---
        print("--- PRINT (Cleanup): Checking lightfield_controller before disconnect ---")
        controller_to_check = self.lightfield_controller
        lf_can_disconnect = False
        if controller_to_check:
            print(f"--- PRINT (Cleanup): Type of self.lightfield_controller: {type(controller_to_check)}")
            has_is_connected = hasattr(controller_to_check, 'is_connected')
            has_disconnect = hasattr(controller_to_check, 'disconnect')
            print(f"--- PRINT (Cleanup): Does it have 'is_connected'? {has_is_connected}")
            print(f"--- PRINT (Cleanup): Does it have 'disconnect'? {has_disconnect}")
            if has_is_connected and has_disconnect:
                try:
                    if controller_to_check.is_connected():
                            lf_can_disconnect = True
                except Exception as e:
                        print(f"--- PRINT (Cleanup): EXCEPTION during is_connected check: {e} ---")
                        logging.error(f"Error checking LF is_connected during cleanup: {e}")
            else:
                print("--- PRINT (Cleanup): is_connected or disconnect method MISSING ---")
                logging.error("is_connected or disconnect method missing from lightfield_controller!")
        else:
            print("--- PRINT (Cleanup): self.lightfield_controller is None ---")
        # --- End Debugging Block ---


        # Disconnect KDC
        if self.kdc101_controller and self.kdc101_controller.is_connected():
            logging.info("Disconnecting KDC101...")
            try:
                self.kdc101_controller.disconnect()
            except Exception as e:
                logging.exception("Error disconnecting KDC101:")

        # --- Dispose LightField Automation Object ---
        # Call the new dispose method to explicitly release the automation object
        if self.lightfield_controller and hasattr(self.lightfield_controller, 'dispose'):
            logging.info("Calling LightField controller dispose...")
            try:
                self.lightfield_controller.dispose()
                logging.info("LightField controller dispose finished.")
            except Exception as e:
                logging.exception("Error disposing LightField controller:")
        else:
            logging.warning("LightField controller not found or has no dispose method.")
        # --- End Dispose LightField ---


        # Cleanup Plotting
        if hasattr(self, 'plotting_module') and self.plotting_module and hasattr(self.plotting_module, 'cleanup'):
            logging.debug("Calling plotting module cleanup...")
            try:
                self.plotting_module.cleanup()
            except Exception as e:
                logging.exception("Error during plotting cleanup:")

        # Process pending Tkinter events before destroying (optional)
        try:
            logging.debug("Processing idle tasks before destroy...")
            self.update_idletasks()
            self.update()
            logging.debug("Idle tasks processed.")
        except Exception as e:
            logging.warning(f"Exception during update_idletasks/update on close: {e}")

        logging.info("Cleanup finished.")
        # --- IMPORTANT: DO NOT CALL self.destroy() HERE ---

    # Overridden destroy method
    def destroy(self):
        """Overrides the default destroy method to perform cleanup first."""
        logging.info("Window destroy initiated...")
        if not self._is_closing: # Ensure cleanup runs only once
            try:
                self._perform_cleanup() # Call the cleanup logic
            except Exception as e:
                logging.exception("Error during cleanup in overridden destroy method:")

        # IMPORTANT: Always call the original destroy method from the parent class
        logging.info("Calling super().destroy() to close window.")
        super().destroy()

# --- Main Execution ---
if __name__ == "__main__":
    # (Keep the dependency check block as it was)
    if not USE_MOCK:
        try:
            import clr
            pass
        except ImportError:
            print("\nERROR: pythonnet ('clr') not found. Please install it: pip install pythonnet")
            print("Real hardware control will not work.\n")
        except Exception as e:
            print(f"\nERROR: Failed to import pythonnet or Kinesis DLLs might be missing/incorrect.")
            print(f"Ensure Kinesis is installed and pythonnet is working.")
            print(f"Specific error: {e}\n")

    app = PolarizationScanApp()
    if app.winfo_exists():
        try:
            app.mainloop()
        except Exception as e:
            logging.exception("Exception occurred in mainloop:") # Catch errors during mainloop
    else:
        logging.error("Application startup failed, GUI window does not exist.")
