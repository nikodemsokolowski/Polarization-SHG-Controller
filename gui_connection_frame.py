import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import logging
import threading # Import threading
import os        # Needed for browse_lf_sdk_path, path checking

# Make sure logging is configured elsewhere in your app, or uncomment below
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ConnectionFrame(ctk.CTkFrame):
    """
    Frame for device connection controls (KDC101, LightField).
    Uses threading for potentially blocking hardware operations.
    """
    def __init__(self, master, kdc101_controller, lightfield_controller, app_instance): # <-- ADD app_instance
        super().__init__(master, fg_color="transparent")
        self.kdc_controller = kdc101_controller
        self.lf_controller = lightfield_controller
        self._app = app_instance # <-- USE the passed instance directly

        self.grid_columnconfigure(1, weight=1) # Make combobox expand

        # --- Title ---
        self.title_label = ctk.CTkLabel(self, text="Device Connections", font=ctk.CTkFont(weight="bold"))
        self.title_label.grid(row=0, column=0, columnspan=3, padx=10, pady=(0, 5), sticky="w")

        # --- KDC101 Rotation Stage ---
        self.kdc_label = ctk.CTkLabel(self, text="KDC101 Stage:")
        self.kdc_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.kdc_scan_button = ctk.CTkButton(self, text="Scan", width=60, command=self.scan_kdc_devices_threaded) # Use threaded version
        self.kdc_scan_button.grid(row=1, column=2, padx=(0,5), pady=5, sticky="e")

        self.kdc_devices_combobox = ctk.CTkComboBox(self, values=[""], state="disabled", command=None)
        self.kdc_devices_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.kdc_devices_combobox.set("Scan or Enter SN")

        self.kdc_connect_button = ctk.CTkButton(self, text="Connect", width=80, command=self.toggle_kdc_connection_threaded) # Use threaded version
        self.kdc_connect_button.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="e")

        self.kdc_status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.kdc_status_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="w")
        self.kdc_status_indicator = ctk.CTkLabel(self.kdc_status_frame, text="●", text_color="gray", font=ctk.CTkFont(size=16))
        self.kdc_status_indicator.pack(side="left", padx=(0, 5))
        self.kdc_status_label = ctk.CTkLabel(self.kdc_status_frame, text="Status: Disconnected", text_color="gray")
        self.kdc_status_label.pack(side="left")

        # --- LightField Spectrometer ---
        self.lf_label = ctk.CTkLabel(self, text="LightField:")
        self.lf_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")

        self.lf_connect_button = ctk.CTkButton(self, text="Connect", width=80, command=self.toggle_lf_connection_threaded) # Use threaded version
        self.lf_connect_button.grid(row=4, column=1, columnspan=2, padx=5, pady=5, sticky="e")

        self.lf_status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.lf_status_frame.grid(row=5, column=0, columnspan=3, padx=10, pady=5, sticky="w")
        self.lf_status_indicator = ctk.CTkLabel(self.lf_status_frame, text="●", text_color="gray", font=ctk.CTkFont(size=16))
        self.lf_status_indicator.pack(side="left", padx=(0, 5))
        self.lf_status_label = ctk.CTkLabel(self.lf_status_frame, text="Status: Disconnected", text_color="gray")
        self.lf_status_label.pack(side="left")

        # --- LightField SDK Path Selection ---
        # Removed static label

        # Actual path entry and browse button
        self.lf_sdk_path_label = ctk.CTkLabel(self, text="LF SDK Path:")
        self.lf_sdk_path_label.grid(row=6, column=0, padx=10, pady=5, sticky="w") # Back to original row

        # Set desired default path directly
        default_lf_install_path = r"C:\Program Files\Princeton Instruments\LightField"
        self.lf_sdk_path_var = tk.StringVar(value=default_lf_install_path)
        self.lf_sdk_path_entry = ctk.CTkEntry(self, textvariable=self.lf_sdk_path_var, state="normal") # Editable
        self.lf_sdk_path_entry.grid(row=6, column=1, padx=5, pady=5, sticky="ew") # Back to original row

        self.lf_sdk_browse_button = ctk.CTkButton(self, text="Browse...", width=80, command=self.browse_lf_sdk_path)
        self.lf_sdk_browse_button.grid(row=6, column=2, padx=(0,5), pady=5, sticky="e") # Back to original row

        # Removed call to _find_and_set_default_lf_path()

    # --- KDC101 Methods ---

    def scan_kdc_devices_threaded(self):
        """Initiates KDC101 device scan in a separate thread."""
        if self.kdc_controller is None:
            self.update_status("KDC Controller not available.", error=True)
            logging.warning("scan_kdc_devices_threaded called but KDC Controller is None.")
            return

        self.update_status("Scanning for KDC101 devices...")
        # Disable scan button during scan
        self.kdc_scan_button.configure(state="disabled")
        self.kdc_devices_combobox.set("Scanning...")
        self.kdc_devices_combobox.configure(state="disabled")

        # Start the scan in a background thread
        scan_thread = threading.Thread(target=self._perform_kdc_scan, daemon=True)
        scan_thread.start()

    def _perform_kdc_scan(self):
        """Worker function to perform KDC101 scan (runs in background thread)."""
        devices = []
        error = None
        try:
            devices = self.kdc_controller.scan_devices()
        except RuntimeError as e:
            error = f"KDC Scan Error: {e}"
            logging.error(f"RuntimeError scanning KDC devices: {e}")
        except Exception as e:
            error = f"Unexpected KDC Scan Error: {e}"
            logging.exception("Unexpected error scanning KDC devices:")

        # Schedule the result handler back on the main thread
        self._app.after(0, lambda: self._handle_kdc_scan_result(devices, error))

    def _handle_kdc_scan_result(self, devices: list, error: str | None):
        """Handles the result of the KDC scan (runs in main thread)."""
        # Re-enable scan button regardless of outcome
        self.kdc_scan_button.configure(state="normal")
        self.kdc_devices_combobox.configure(state="normal") # Allow typing

        if error:
            self.update_status(error, error=True)
            self.kdc_devices_combobox.configure(values=[""]) # Clear values
            self.kdc_devices_combobox.set("Scan Error - Enter SN")
        elif devices:
            self.kdc_devices_combobox.configure(values=devices)
            self.kdc_devices_combobox.set(devices[0]) # Pre-select first
            self.update_status(f"KDC Scan: Found {len(devices)}. Select or type SN.")
        else:
            self.kdc_devices_combobox.configure(values=[""]) # Clear values
            self.kdc_devices_combobox.set("No devices found - Enter SN")
            self.update_status("KDC Scan: No devices found. Enter SN manually.")


    def toggle_kdc_connection_threaded(self):
        """Initiates KDC101 connect/disconnect in a separate thread."""
        if not self.kdc_controller:
            self.update_status("KDC Controller not available.", error=True)
            logging.warning("toggle_kdc_connection_threaded called but KDC Controller is None.")
            return

        serial_no = self.kdc_devices_combobox.get().strip()
        is_currently_connected = self.kdc_controller.is_connected()

        if not is_currently_connected:
            # Validate serial number only when connecting
            if not serial_no or any(placeholder in serial_no.lower() for placeholder in ["select", "found", "enter sn", "error", "scanning"]):
                self.update_status("Please enter or select a valid KDC serial number.", error=True)
                logging.warning(f"Connect KDC called with invalid input: '{serial_no}'")
                return
        else:
            # Use the controller's stored serial number for disconnect confirmation
            serial_no = self.kdc_controller.serial_no or serial_no # Fallback just in case

        logging.info(f"Attempting KDC {'disconnect' if is_currently_connected else 'connect'} using SN: {serial_no}")

        # Disable buttons/combobox during operation
        self.kdc_connect_button.configure(state="disabled")
        self.kdc_scan_button.configure(state="disabled")
        self.kdc_devices_combobox.configure(state="disabled")
        status_msg = f"Disconnecting KDC {serial_no}..." if is_currently_connected else f"Connecting to KDC {serial_no}..."
        self.update_status(status_msg)

        # Start connect/disconnect in background thread
        conn_thread = threading.Thread(
            target=self._perform_kdc_connect_disconnect,
            args=(is_currently_connected, serial_no),
            daemon=True
        )
        conn_thread.start()

    def _perform_kdc_connect_disconnect(self, is_currently_connected: bool, serial_no: str):
        """Worker function for KDC connect/disconnect (runs in background thread)."""
        success = False
        error = None
        try:
            if is_currently_connected:
                success = self.kdc_controller.disconnect()
                # Disconnect should ideally always return True or raise error if failed internally
                if not success: # Handle unexpected False return from disconnect
                    logging.warning(f"KDC disconnect method returned False for {serial_no}")
                    # Treat as disconnected anyway for UI state consistency
                    success = True # Assume it's effectively disconnected
            else:
                success = self.kdc_controller.connect(serial_no)
        except RuntimeError as e:
            error = f"KDC {'Disconnect' if is_currently_connected else 'Connect'} Error: {e}"
            logging.error(f"RuntimeError toggling KDC connection: {e}")
        except Exception as e:
            error = f"Unexpected KDC {'Disconnect' if is_currently_connected else 'Connect'} Error: {e}"
            logging.exception("Unexpected error toggling KDC connection:")

        final_state_connected = self.kdc_controller.is_connected() # Check actual state after operation

        # Schedule result handler back on main thread
        self._app.after(0, lambda: self._handle_kdc_result(final_state_connected, serial_no, error))

    def _handle_kdc_result(self, is_connected: bool, serial_no: str, error: str | None):
        """Handles the result of KDC connect/disconnect (runs in main thread)."""
        print("--- PRINT: EXECUTING MODIFIED _handle_kdc_result (v2) ---") # Version marker
        logging.debug("--- LOG DEBUG: EXECUTING MODIFIED _handle_kdc_result (v2) ---")

        app_instance_to_check = None # Initialize to None
        has_method = False
        app_type_str = "Unknown or Error during inspection"

        # --- Modified debugging block ---
        print("--- PRINT: Attempting to inspect self._app ---")
        try:
            # Directly access self._app here - this might be where an error occurs
            app_instance_to_check = self._app

            # Check if it's None FIRST
            if app_instance_to_check is None:
                print("--- PRINT: ERROR! self._app is None! ---")
                logging.error("self._app is None in _handle_kdc_result")
                # Keep app_instance_to_check as None
            else:
                # If not None, proceed with inspection
                print(f"--- PRINT: self._app seems OK. Type: {type(app_instance_to_check)} ---")
                app_type_str = str(type(app_instance_to_check)) # Get type as string

                # Now check for the attribute
                print(f"--- PRINT: Checking for 'update_manual_controls_state' on type {app_type_str} ---")
                has_method = hasattr(app_instance_to_check, 'update_manual_controls_state')
                print(f"--- PRINT: Does self._app have method? {has_method} ---")

        except Exception as e:
            # Catch ANY exception during the above inspection block
            print(f"--- PRINT: EXCEPTION during self._app inspection: {e} ---")
            logging.error(f"EXCEPTION during self._app inspection in _handle_kdc_result: {e}", exc_info=True) # Log full traceback
            app_instance_to_check = None # Ensure it's None if inspection failed
        # --- End modified debugging block ---


        # Update connection frame status regardless
        self.update_kdc_status(connected=is_connected)

        # Update main status bar message
        if error:
            self.update_status(error, error=True)
        else:
            status_msg = f"KDC {serial_no} {'connected' if is_connected else 'disconnected'}."
            self.update_status(status_msg)

        # --- Now, act based on the inspection results ---
        print("--- PRINT: Checking if method can be called ---")
        if app_instance_to_check is not None and has_method:
            print(f"--- PRINT: Method found on {app_type_str}, attempting call ---")
            logging.debug("Found 'update_manual_controls_state' on self._app, calling it.")
            try:
                # Call the method
                app_instance_to_check.update_manual_controls_state()
                print("--- PRINT: Call to update_manual_controls_state successful ---")
            except Exception as call_e:
                # Catch errors during the actual method call
                print(f"--- PRINT: EXCEPTION during call to update_manual_controls_state: {call_e} ---")
                logging.error(f"Error CALLING update_manual_controls_state: {call_e}", exc_info=True)
        elif app_instance_to_check is not None and not has_method:
            # Instance exists, but method is missing
            print(f"--- PRINT: Method NOT found on object of type {app_type_str} ---")
            logging.warning("Main application instance missing 'update_manual_controls_state' method.") # Keep original warning
            logging.warning(f"Details: self._app object is {app_instance_to_check} of type {app_type_str}")
        else:
            # Instance was None or inspection failed
            print(f"--- PRINT: Cannot call method because self._app was None or inspection failed ---")
            logging.error("Cannot call update_manual_controls_state because self._app reference is invalid or inspection failed.")
        print("--- PRINT: Finished _handle_kdc_result ---")


    # --- LightField Methods ---

    def browse_lf_sdk_path(self):
        """Initiates the LF SDK path selection in a separate thread."""
        logging.info("Browse LF SDK path initiated.")
        self.update_status("Opening folder browser...")
        # Disable button while browsing
        self.lf_sdk_browse_button.configure(state="disabled")

        # Start the browse dialog in a background thread
        browse_thread = threading.Thread(target=self._perform_browse_dialog, daemon=True)
        browse_thread.start()

    def _perform_browse_dialog(self):
        """Worker function to show the directory dialog (runs in background thread)."""
        selected_path = None
        error = None
        try:
            # --- Simplified initial directory logic ---
            initial_dir = r"C:\ProgramData\Documents\Princeton Instruments\LightField" # Parent of known good path
            if not os.path.isdir(initial_dir): # Fallback if ProgramData path doesn't exist
                initial_dir = os.path.expanduser("~") # Use home directory
            if not os.path.isdir(initial_dir): # Fallback if home is weird
                initial_dir = "C:/"
            # --- End Simplified Logic ---

            logging.debug(f"Opening browse dialog with initialdir='{initial_dir}' in background thread.")

            selected_path = filedialog.askdirectory(
                title="Select LightField Add-in and Automation SDK Folder",
                initialdir=initial_dir,
            )
            logging.debug(f"Browse dialog returned: {selected_path} in background thread.")

        except Exception as e:
            error = f"Error during folder browse: {e}"
            logging.exception("Error occurred in browse dialog thread:")

        # Schedule the result handler back on the main thread
        # Pass the selected path and any error message
        if hasattr(self._app, 'after'):
            self._app.after(0, lambda: self._handle_browse_result(selected_path, error))
        else:
            logging.error("Cannot schedule browse result handler: self._app has no 'after' method.")
            # Fallback: Try to re-enable button directly (unsafe, but better than nothing)
            try:
                self.lf_sdk_browse_button.configure(state="normal")
            except Exception:
                pass # Ignore errors if widget is destroyed

    def _handle_browse_result(self, selected_path: str | None, error: str | None):
        """Handles the result from the browse dialog (runs in main thread)."""
        # Re-enable the browse button
        self.lf_sdk_browse_button.configure(state="normal")

        if error:
            self.update_status(error, error=True)
            logging.error(f"Browse dialog handling error: {error}")
            return # Stop processing if there was an error opening the dialog

        if selected_path:
            # Basic validation (optional, but good)
            looks_valid = os.path.isdir(os.path.join(selected_path, "Samples", "Binaries")) or \
                        os.path.isdir(os.path.join(selected_path, "Binaries")) or \
                        os.path.isfile(os.path.join(selected_path, "PrincetonInstruments.LightField.AutomationV5.dll"))

            if looks_valid:
                self.lf_sdk_path_var.set(selected_path)
                logging.info(f"LightField SDK path selected: {selected_path}")
                self.update_status(f"LightField SDK path set: ...{os.path.basename(selected_path)}")
            else:
                logging.warning(f"Selected path '{selected_path}' does not appear to contain expected LF SDK files/folders.")
                self.update_status(f"Warning: Selected path might not be the correct LF SDK folder.", error=True)
                self.lf_sdk_path_var.set(selected_path) # Still set it but warn
        else:
            logging.info("LightField SDK path selection cancelled.")
            self.update_status("Folder selection cancelled.") # Update status bar


    def toggle_lf_connection_threaded(self):
        """Initiates LightField connect/disconnect in a separate thread."""
        if not self.lf_controller:
            self.update_status("LightField Controller not available.", error=True)
            logging.warning("toggle_lf_connection_threaded called but LF Controller is None.")
            return

        is_currently_connected = self.lf_controller.is_connected()
        sdk_path = self.lf_sdk_path_var.get()

        if not is_currently_connected:
            # Check if SDK path is valid only when connecting
            if not sdk_path or "Select LightField" in sdk_path or "not found" in sdk_path:
                self.update_status("Please provide a valid LightField SDK path first.", error=True)
                logging.warning(f"LightField connection attempt with invalid path: '{sdk_path}'")
                return

        logging.info(f"Attempting LightField {'disconnect' if is_currently_connected else 'connect'}...")

        # Disable button during operation
        self.lf_connect_button.configure(state="disabled")
        status_msg = "Disconnecting LightField..." if is_currently_connected else "Connecting to LightField..."
        self.update_status(status_msg)

        # Start connect/disconnect in background thread
        conn_thread = threading.Thread(
            target=self._perform_lf_connect_disconnect,
            args=(is_currently_connected, sdk_path),
            daemon=True
        )
        conn_thread.start()


    def _perform_lf_connect_disconnect(self, is_currently_connected: bool, sdk_path: str):
        """Worker function for LF connect/disconnect (runs in background thread)."""
        success = False
        error = None
        try:
            if is_currently_connected:
                success = self.lf_controller.disconnect()
                # Assume disconnect is successful unless error is raised
                success = True # Override return value for consistency
            else:
                # Load DLLs first (may raise error if path is bad)
                if not self.lf_controller.load_dlls(sdk_path):
                    # Should have been caught by raising RuntimeError in controller ideally
                    raise RuntimeError("Failed to load LightField DLLs (path validation failed in controller).")

                # Now attempt connection
                success = self.lf_controller.connect()
        except RuntimeError as e: # Catch errors from load_dlls or connect/disconnect
            error = f"LightField Controller Error: {e}"
            logging.error(f"RuntimeError toggling LightField connection: {e}")
        except Exception as e: # Catch unexpected errors (e.g., pythonnet/COM issues)
            if "System.Runtime.InteropServices.COMException" in str(e):
                error = "LightField connection failed (COM Error). Is LF running?"
            else:
                error = f"Unexpected LightField Connection Error: {e}"
            logging.exception("Unexpected error toggling LightField connection:")

        final_state_connected = self.lf_controller.is_connected()

        # Schedule result handler back on main thread
        self._app.after(0, lambda: self._handle_lf_result(final_state_connected, error))


    def _handle_lf_result(self, is_connected: bool, error: str | None):
        """Handles the result of LF connect/disconnect (runs in main thread)."""
        self.update_lf_status(connected=is_connected) # Updates buttons/indicators

        if error:
            self.update_status(error, error=True)
        else:
            status_msg = f"LightField {'connected' if is_connected else 'disconnected'}."
            self.update_status(status_msg)
            
                        # If successfully connected, update the path entry field
            if is_connected and self.lf_controller and self.lf_controller.loaded_sdk_path:
                detected_path = self.lf_controller.loaded_sdk_path
                print(f"-- DEBUG: LF Connected, setting path entry to: {detected_path}") # Debug print
                self.lf_sdk_path_var.set(detected_path)
            elif not is_connected:
                # Reset to placeholder if disconnected (optional)
                # self.lf_sdk_path_var.set("Select LightField SDK Path...")
                pass
            # --- REMOVED: Don't overwrite path entry after connection ---
            # if is_connected and self.lf_controller and self.lf_controller.loaded_sdk_path:
            #     detected_path = self.lf_controller.loaded_sdk_path
            #     print(f"-- DEBUG: LF Connected, setting path entry to: {detected_path}") # Debug print
            #     self.lf_sdk_path_var.set(detected_path)

        # Always trigger the main app's state update function
        print(f"--- DEBUG (_handle_lf_result): Calling _app.update_manual_controls_state() ---") # Add log
        if hasattr(self._app, 'update_manual_controls_state'):
            self._app.update_manual_controls_state()
        else:
            logging.warning("Main application instance missing 'update_manual_controls_state' method.")

    # Removed _find_and_set_default_lf_path method

    # --- Status Update Methods ---

    def update_kdc_status(self, connected: bool):
        """Updates the KDC101 status label, indicator, button text, and related widget states."""
        if connected:
            status_text = f"Status: Connected ({self.kdc_controller.serial_no})"
            status_color = "green"
            indicator_color = "green"
            button_text = "Disconnect"
            scan_state = "disabled"
            combo_state = "disabled" # Combobox is disabled when connected
        else:
            status_text = "Status: Disconnected"
            status_color = "gray"
            indicator_color = "gray"
            button_text = "Connect"
            scan_state = "normal"
            combo_state = "normal" # Combobox is editable when disconnected
            current_text = self.kdc_devices_combobox.get()
            # Reset placeholder text only if disconnected and showing old SN or error
            if not current_text or current_text == self.kdc_controller.serial_no or "error" in current_text.lower():
                self.kdc_devices_combobox.set("Scan or Enter SN")

        self.kdc_status_label.configure(text=status_text, text_color=status_color)
        self.kdc_status_indicator.configure(text_color=indicator_color)
        self.kdc_connect_button.configure(text=button_text, state="normal") # Re-enable connect/disconnect button
        self.kdc_scan_button.configure(state=scan_state)
        self.kdc_devices_combobox.configure(state=combo_state)


    def update_lf_status(self, connected: bool):
        """Updates the LightField status label, indicator, and button text."""
        if connected:
            status_text = "Status: Connected"
            status_color = "green"
            indicator_color = "green"
            button_text = "Disconnect"
        else:
            status_text = "Status: Disconnected"
            status_color = "gray"
            indicator_color = "gray"
            button_text = "Connect"

        self.lf_status_label.configure(text=status_text, text_color=status_color)
        self.lf_status_indicator.configure(text_color=indicator_color)
        self.lf_connect_button.configure(text=button_text, state="normal") # Re-enable connect/disconnect button


    def update_status(self, message: str, error: bool = False):
        """Updates the main status bar (delegates to master.master which is the app instance)."""
        if hasattr(self._app, 'update_status_bar'):
            self._app.update_status_bar(message, error)
        else:
            print(f"Status Update (Frame): {message}" + (" (Error)" if error else ""))


# --- Example usage (for testing this frame independently) ---
# Note: Threading requires a running event loop (app.mainloop())
# Mock controllers need to simulate delays if testing responsiveness.

if __name__ == "__main__":
    import time # For mock delays

    logging.basicConfig(level=logging.INFO)

    # Mock controllers for testing with simulated delays
    class MockKDCController:
        def __init__(self, name="MockKDC"):
            self._connected = False
            self.name = name
            self._devices = ["27000001", "27000002", "27000003"]
            self.serial_no = None
        def scan_devices(self):
            logging.info(f"{self.name}: Scanning...")
            time.sleep(1.5) # Simulate scan delay
            # Test error case:
            # raise RuntimeError("Mock KDC Scan Failed!")
            return self._devices
        def connect(self, serial=None):
            logging.info(f"{self.name}: Connecting... ({serial})")
            time.sleep(2.0) # Simulate connect delay
            if serial in self._devices:
                # Test error case:
                # raise RuntimeError(f"Mock KDC Connect Failed for {serial}!")
                self._connected = True
                self.serial_no = serial
                return True
            else:
                logging.error(f"Mock connect failed for {serial}")
                return False
        def disconnect(self):
            logging.info(f"{self.name}: Disconnecting ({self.serial_no})...")
            time.sleep(0.5) # Simulate disconnect delay
            # Test error case:
            # raise RuntimeError("Mock KDC Disconnect Failed!")
            self._connected = False
            self.serial_no = None
            return True # Assume disconnect always "succeeds" for mock
        def is_connected(self): return self._connected

    class MockLFController:
        def __init__(self, name="MockLF"):
            self._connected = False
            self.name = name
            self._dlls_loaded = False
        def load_dlls(self, path):
            logging.info(f"{self.name}: Loading DLLs from {path}...")
            time.sleep(0.3)
            if not path or "bad_path" in path:
                # raise RuntimeError("Mock LF DLL Load Failed!")
                return False
            self._dlls_loaded = True
            return True
        def connect(self):
            logging.info(f"{self.name}: Connecting...")
            if not self._dlls_loaded:
                raise RuntimeError("DLLs not loaded before connect call")
            time.sleep(1.5) # Simulate connect delay
            # Test error case:
            # raise RuntimeError("Mock LF Connect Failed!")
            # Test COM Error:
            # raise Exception("System.Runtime.InteropServices.COMException Mock")
            self._connected = True
            return True
        def disconnect(self):
            logging.info(f"{self.name}: Disconnecting...")
            time.sleep(0.5) # Simulate disconnect delay
            # raise RuntimeError("Mock LF Disconnect Failed!")
            self._connected = False
            self._dlls_loaded = False # Assume disconnect unloads DLLs implicitly
            return True # Assume disconnect always "succeeds" for mock
        def is_connected(self): return self._connected


    # --- Setup Mock App ---
    app = ctk.CTk()
    app.geometry("450x300")
    app.title("Connection Frame Test (Threaded)")

    # Mock status bar method on the app instance
    status_bar_label = ctk.CTkLabel(app, text="Status: Idle", anchor="w")
    status_bar_label.pack(side="bottom", fill="x", padx=10, pady=5)
    def update_status_bar(message, error=False):
        print(f"APP STATUS: {message}" + (" [ERROR]" if error else "")) # Keep console log
        status_bar_label.configure(
            text=f"{'Error: ' if error else ''}{message}",
            text_color="red" if error else "gray"
        )
    app.update_status_bar = update_status_bar

    # Mock manual controls update method on the app instance
    def update_manual_controls_state():
        print("APP MOCK: Updating manual controls state...")
        logging.info("APP MOCK: Updating manual controls state...")
    app.update_manual_controls_state = update_manual_controls_state

    # --- Create Controllers and Frame ---
    mock_kdc = MockKDCController()
    mock_lf = MockLFController()

    # The frame expects master.master to be the app instance
    mock_main_window = ctk.CTkFrame(app) # Dummy container
    mock_main_window.master = app # Link it back to the app

    frame = ConnectionFrame(mock_main_window, mock_kdc, mock_lf) # Pass dummy container
    frame.pack(expand=True, fill="both", padx=10, pady=10)

    # --- Start Event Loop ---
    app.mainloop()
