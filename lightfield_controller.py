import logging
import os
import sys
import time
import numpy as np
import typing

# --- Globals for .NET types (populated by load_dlls) ---
clr = None
Automation = None
DeviceType = None
ExperimentSettings = None
CameraSettings = None
SensorTemperatureStatus = None
PYTHONNET_LOADED = False
LF_DLL_LOAD_SUCCESS = False # Tracks if DLLs/Namespaces loaded successfully

# DLL names (V5) - Assuming V5 based on previous context
AUTOMATION_DLL_V5 = "PrincetonInstruments.LightField.AutomationV5.dll"
ADDIN_SUPPORT_DLL = "PrincetonInstruments.LightFieldAddInSupportServices.dll"
VIEW_DLL_V5 = "PrincetonInstruments.LightFieldViewV5.dll" # Added based on working example

class LightFieldController:
    """
    Controller class for Princeton Instruments LightField via Automation (pythonnet).
    Connects to a running LightField instance and controls basic experiment parameters/acquisition.
    """
    def __init__(self):
        """Initializes the controller state."""
        print("--- LFController __init__: START ---")
        self._automation = None
        self._application = None
        self._experiment = None
        self._is_connected = False
        self._dlls_loaded = LF_DLL_LOAD_SUCCESS # Use global flag for initial state
        self.loaded_sdk_path = None # Track which path was used for loading
        print(f"--- LFController __init__: Initial _dlls_loaded={self._dlls_loaded} ---")
        print("--- LFController __init__: END ---")

    def load_dlls(self, user_provided_path: str | None = None) -> bool:
        """
        Attempts to load the required LightField V5 DLLs and import necessary types.
        Prioritizes known default path, then user path, then bundled path (if frozen).
        Uses absolute paths for clr.AddReference when possible.
        """
        global clr, Automation, DeviceType, ExperimentSettings, CameraSettings, SensorTemperatureStatus
        global PYTHONNET_LOADED, LF_DLL_LOAD_SUCCESS

        # --- 1. Check/Import pythonnet ---
        if not PYTHONNET_LOADED:
            try:
                print("--- DEBUG (load_dlls): Attempting import clr...")
                import clr
                PYTHONNET_LOADED = True
                print("--- DEBUG (load_dlls): import clr SUCCESS.")
            except ImportError:
                print("!! ERROR: Cannot load LightField DLLs - pythonnet (clr) is not installed.")
                logging.error("pythonnet (clr) not found. Please install it: pip install pythonnet")
                return False
            except Exception as e:
                print(f"!! ERROR: Importing clr failed: {e}")
                logging.exception(f"Error importing clr: {e}")
                return False

        # --- 2. Check if already loaded ---
        if LF_DLL_LOAD_SUCCESS:
            print("-- INFO: LightField DLLs/Namespaces already loaded.")
            logging.info("LightField DLLs/Namespaces already loaded.")
            self._dlls_loaded = True # Ensure instance flag is also true
            return True

        # --- 3. Determine DLL Directory ---
        sdk_dll_directory_to_use = None
        path_source = "Unknown"
        frozen = getattr(sys, 'frozen', False)
        meipass = getattr(sys, '_MEIPASS', None)

        # Define potential paths
        known_good_path = r"C:\ProgramData\Documents\Princeton Instruments\LightField\Add-in and Automation SDK\Samples\Binaries"
        bundled_lib_path = os.path.join(meipass, 'lib') if frozen and meipass else None

        search_paths = []
        if known_good_path: search_paths.append(("Known Default Path", known_good_path))
        if user_provided_path: search_paths.append(("User Provided Path", user_provided_path))
        if bundled_lib_path: search_paths.append(("Bundled Path", bundled_lib_path))

        # Check paths for required DLLs
        for source, path in search_paths:
            print(f"-- INFO: Checking path ({source}): {path}")
            if path and os.path.isdir(path):
                auto_dll_full = os.path.join(path, AUTOMATION_DLL_V5)
                addin_dll_full = os.path.join(path, ADDIN_SUPPORT_DLL)
                if os.path.isfile(auto_dll_full) and os.path.isfile(addin_dll_full):
                    sdk_dll_directory_to_use = path
                    path_source = source
                    print(f"## SUCCESS: Found required LightField DLLs in {source}: {path}")
                    logging.info(f"Found valid DLLs in {source}: {path}")
                    break
                else:
                    print(f"-- INFO: DLLs not found in {source}: {path}")
            else:
                print(f"-- INFO: Path does not exist or is invalid ({source}): {path}")

        if not sdk_dll_directory_to_use:
            print("!! ERROR: Could not find directory containing required LightField DLLs.")
            logging.error("Could not find LightField DLL directory.")
            return False

        # --- 4. Load DLLs using clr.AddReference (with full path) ---
        print(f"-- INFO: Attempting to load DLLs using determined path ({path_source}): {sdk_dll_directory_to_use}")
        logging.info(f"Attempting clr.AddReference using path: {sdk_dll_directory_to_use}")
        try:
            auto_dll_full = os.path.join(sdk_dll_directory_to_use, AUTOMATION_DLL_V5)
            addin_dll_full = os.path.join(sdk_dll_directory_to_use, ADDIN_SUPPORT_DLL)
            view_dll_full = os.path.join(sdk_dll_directory_to_use, VIEW_DLL_V5) # Path for View DLL

            # Add AddInViews path from the *original* SDK location if it exists
            # This might be needed for dependencies even if DLLs are bundled
            original_addin_views_path = os.path.join(os.path.dirname(sdk_dll_directory_to_use), 'AddInViews')
            if os.path.isdir(original_addin_views_path) and original_addin_views_path not in sys.path:
                sys.path.append(original_addin_views_path)
                print(f"--- DEBUG (load_dlls): Appended original AddInViews path: {original_addin_views_path}")

            print(f"--- DEBUG (load_dlls): Attempting clr.AddReference('{auto_dll_full}')...")
            clr.AddReference(auto_dll_full) # Use full path
            print(f"--- DEBUG (load_dlls): clr.AddReference for AutomationV5 SUCCESS.")

            print(f"--- DEBUG (load_dlls): Attempting clr.AddReference('{addin_dll_full}')...")
            clr.AddReference(addin_dll_full) # Use full path
            print(f"--- DEBUG (load_dlls): clr.AddReference for AddInSupport SUCCESS.")

            # Add View DLL reference
            if os.path.exists(view_dll_full): # Check if it exists before adding
                print(f"--- DEBUG (load_dlls): Attempting clr.AddReference('{view_dll_full}')...")
                clr.AddReference(view_dll_full) # Use full path
                print(f"--- DEBUG (load_dlls): clr.AddReference for ViewV5 SUCCESS.")
            else:
                # Log warning if View DLL is missing, might not be critical but good to know
                print(f"--- WARNING (load_dlls): View DLL not found at '{view_dll_full}', skipping AddReference.")
                logging.warning(f"View DLL not found at '{view_dll_full}', skipping AddReference.")

            logging.info("Successfully added references to LightField V5 DLLs.")

        except Exception as add_ref_e:
            print(f"!! FATAL ERROR (load_dlls): clr.AddReference FAILED: {add_ref_e}")
            logging.exception(f"clr.AddReference failed for path '{sdk_dll_directory_to_use}':")
            return False # Stop if AddReference fails

        # --- 5. Import Namespaces ---
        try:
            print("--- DEBUG (load_dlls): Attempting namespace imports...")
            from PrincetonInstruments.LightField.Automation import Automation as Automation_mod
            from PrincetonInstruments.LightField.AddIns import DeviceType as DeviceType_mod, ExperimentSettings as ExperimentSettings_mod, CameraSettings as CameraSettings_mod
            try:
                from PrincetonInstruments.LightField.AddIns import SensorTemperatureStatus as SensorTemperatureStatus_mod
            except ImportError:
                SensorTemperatureStatus_mod = None
                print("--- WARNING (load_dlls): SensorTemperatureStatus enum not found in AddIns.")
                logging.warning("SensorTemperatureStatus enum not found in AddIns namespace.")

            # Assign to globals
            Automation = Automation_mod
            DeviceType = DeviceType_mod
            ExperimentSettings = ExperimentSettings_mod
            CameraSettings = CameraSettings_mod
            SensorTemperatureStatus = SensorTemperatureStatus_mod

            LF_DLL_LOAD_SUCCESS = True
            self._dlls_loaded = True
            self.loaded_sdk_path = sdk_dll_directory_to_use
            print("## SUCCESS: LightField DLLs loaded and namespaces imported.")
            logging.info("LightField V5 namespaces imported successfully.")
            return True

        except Exception as import_e:
            print(f"!! FATAL ERROR (load_dlls): Namespace import FAILED: {import_e}")
            logging.exception(f"Namespace import failed after AddReference: {import_e}")
            LF_DLL_LOAD_SUCCESS = False
            self._dlls_loaded = False
            self.loaded_sdk_path = None
            return False

    def connect(self) -> bool:
        """
        Connects to an already running LightField application instance.
        Assumes DLLs are loaded. Verifies camera presence.
        """
        if not self._dlls_loaded or not Automation:
            logging.error("Cannot connect: DLLs not loaded successfully.")
            print("!! ERROR: Cannot connect, DLLs not loaded. Call load_dlls() first.")
            return False

        if self._is_connected:
            logging.warning("Already connected to LightField.")
            return True

        try:
            print("-- INFO: Attempting to connect to running LightField instance...")
            logging.info("Connecting to LightField Automation...")
            # Use Automation(True, None) to attach to running instance
            self._automation = Automation(True, None)
            self._application = self._automation.LightFieldApplication
            if self._application is None:
                print("!! ERROR: Failed to get LightFieldApplication object. Is LightField running?")
                logging.error("Failed to get LightFieldApplication object (is LF running?).")
                self._automation = None # Clean up
                return False
            print("-- INFO: LightFieldApplication object obtained (likely attached).")

            self._experiment = self._application.Experiment
            if self._experiment is None:
                print("!! ERROR: Failed to get Experiment object from running LightField.")
                logging.error("Failed to get Experiment object.")
                self._automation = None # Clean up
                self._application = None
                return False
            print("-- INFO: Experiment object obtained.")

            # --- Verify Camera Presence ---
            print("-- INFO: Checking for camera device in current experiment context...")
            logging.info("Checking for camera device...")
            camera_found = False
            if self._experiment.ExperimentDevices is not None and self._experiment.ExperimentDevices.Count > 0:
                print("-- INFO: Devices listed in current experiment:")
                for device in self._experiment.ExperimentDevices:
                    print(f"  - Model: {device.Model}, Type: {device.Type}")
                    if device.Type == DeviceType.Camera:
                        print("--> Camera found.")
                        logging.info(f"Camera found: {device.Model}")
                        camera_found = True
                        break
            else:
                print("-- INFO: No devices found configured in the current experiment context.")
                logging.warning("No devices found in current experiment context.")

            if not camera_found:
                print("!! ERROR: No camera found in the active LightField experiment.")
                logging.error("No camera found in active experiment.")
                # Don't disconnect yet, maybe user wants to load experiment manually in LF
                # self.disconnect() # Clean up? Or allow user to fix in LF?
                # return False # Treat as connection failure if no camera?
                print("-- WARNING: Connection established but no camera detected in active experiment.")
                # Proceed anyway, but warn user. Functions requiring camera might fail.

            self._is_connected = True
            print("## SUCCESS: Connected to LightField.")
            logging.info("Successfully connected to LightField.")
            return True

        except Exception as e:
            print(f"!! ERROR: Exception during connect: {e}")
            logging.exception("Failed to connect to LightField:")
            self._experiment = None
            self._application = None
            self._automation = None
            self._is_connected = False
            return False

    def disconnect(self) -> bool:
        """Disconnects from the LightField application (releases references)."""
        print("-- INFO: Disconnecting from LightField (updating internal state)...")
        logging.info("Disconnecting from LightField (updating internal state).")
        # Comment out reference clearing to potentially keep LF open
        # self._experiment = None
        # self._application = None
        # self._automation = None # Release reference
        self._is_connected = False # Still mark as disconnected internally
        logging.info("LightField internal connection state set to False.")
        print("-- INFO: LightField internal connection state set to False.")
        return True

    def dispose(self):
        """Explicitly dispose of the LightField Automation object."""
        logging.info("Disposing LightField Automation object...")
        if self._automation is not None:
            try:
                # Check if Dispose method exists and call it
                if hasattr(self._automation, 'Dispose') and callable(getattr(self._automation, 'Dispose')):
                    self._automation.Dispose()
                    logging.info("Called self._automation.Dispose()")
                else:
                    logging.warning("self._automation object does not have a callable Dispose method.")
            except Exception as e:
                logging.error(f"Exception during self._automation.Dispose(): {e}")
        else:
            logging.warning("Dispose called but self._automation is None.")
        # Clear references after disposing
        self._experiment = None
        self._application = None
        self._automation = None
        self._is_connected = False


    def is_connected(self) -> bool:
        """Returns True if connected to LightField, False otherwise."""
        # Basic check: are the core objects initialized?
        connected_state = (self._is_connected and
                        self._automation is not None and
                        self._application is not None and
                        self._experiment is not None)
        # Optional: Add a try-except block to ping a property if needed,
        # but this can be slow or cause issues if LF becomes unresponsive.
        # try:
        #     _ = self._application.IsRunning # Example property access
        # except Exception:
        #     connected_state = False
        #     self._is_connected = False # Update internal state if ping fails
        #     logging.warning("LightField connection lost (ping failed).")
        print(f"--- PRINT: Inside LightFieldController.is_connected, returning: {connected_state} ---")
        return connected_state

    def _check_setting(self, setting_name) -> bool:
        """Checks if a setting exists and is available."""
        if not self.is_connected(): return False
        try:
            if self._experiment.Exists(setting_name):
                # print(f"--- DEBUG: Setting '{setting_name}' exists.")
                # is_avail = self._experiment.IsAvailable(setting_name)
                # print(f"--- DEBUG: Setting '{setting_name}' available: {is_avail}.")
                # is_ro = self._experiment.IsReadOnly(setting_name)
                # print(f"--- DEBUG: Setting '{setting_name}' read-only: {is_ro}.")
                # return is_avail # Check if available is more useful than just exists
                return True # Just check existence for now
            else:
                # print(f"--- DEBUG: Setting '{setting_name}' does NOT exist.")
                return False
        except Exception as e:
            print(f"!! ERROR: Checking setting '{setting_name}' failed: {e}")
            logging.warning(f"Error checking setting {setting_name}: {e}")
            return False

    def _get_value(self, setting_name, default_value=None):
        """Safely gets a value from the experiment."""
        if self._check_setting(setting_name):
            try:
                value = self._experiment.GetValue(setting_name)
                # print(f"--- DEBUG: GetValue '{setting_name}' -> {value} (Type: {type(value)})")
                return value
            except Exception as e:
                print(f"!! ERROR: GetValue for '{setting_name}' failed: {e}")
                logging.error(f"GetValue failed for {setting_name}: {e}")
                return default_value
        return default_value

    def _set_value(self, setting_name, value) -> bool:
        """Safely sets a value in the experiment."""
        if self._check_setting(setting_name):
            try:
                if self._experiment.IsReadOnly(setting_name):
                    print(f"!! WARNING: Cannot set '{setting_name}', it is read-only.")
                    logging.warning(f"Cannot set read-only setting: {setting_name}")
                    return False
                # print(f"--- DEBUG: SetValue '{setting_name}' = {value} (Type: {type(value)})")
                self._experiment.SetValue(setting_name, value)
                return True
            except Exception as e:
                print(f"!! ERROR: SetValue for '{setting_name}' = {value} failed: {e}")
                logging.error(f"SetValue failed for {setting_name}={value}: {e}")
                return False
        else:
            print(f"!! WARNING: Cannot set '{setting_name}', setting does not exist.")
            logging.warning(f"Cannot set non-existent setting: {setting_name}")
            return False

    # --- Parameter Access Methods ---

    def get_exposure_time_ms(self) -> typing.Optional[float]:
        """Gets the current exposure time in milliseconds."""
        if not CameraSettings: return None
        return self._get_value(CameraSettings.ShutterTimingExposureTime, default_value=None)

    def set_exposure_time_ms(self, exposure_ms: float) -> bool:
        """Sets the exposure time in milliseconds."""
        if not CameraSettings: return False
        return self._set_value(CameraSettings.ShutterTimingExposureTime, float(exposure_ms))

    def get_sensor_temperature(self) -> typing.Optional[float]:
        """Gets the current sensor temperature reading."""
        if not CameraSettings: return None
        return self._get_value(CameraSettings.SensorTemperatureReading, default_value=None)

    def get_sensor_temperature_status(self) -> typing.Optional[str]:
        """Gets the current sensor temperature status as a string."""
        if not CameraSettings or not SensorTemperatureStatus: return None
        status_enum_val = self._get_value(CameraSettings.SensorTemperatureStatus, default_value=None)
        if status_enum_val is not None:
            try:
                # Convert .NET enum value to its string name
                return SensorTemperatureStatus.GetName(SensorTemperatureStatus, status_enum_val)
            except Exception as e:
                print(f"!! ERROR: Failed to get name for SensorTemperatureStatus enum value {status_enum_val}: {e}")
                logging.warning(f"Failed to get name for SensorTemperatureStatus enum value {status_enum_val}: {e}")
                return f"Enum {status_enum_val}" # Fallback
        return None

    def set_base_filename(self, filename: str) -> bool:
        """Sets the base filename for saving."""
        if not ExperimentSettings: return False
        # Basic validation: remove invalid chars? Or let LightField handle it?
        # For now, just pass it through.
        return self._set_value(ExperimentSettings.FileNameGenerationBaseFileName, str(filename))

    # Note: set_save_path is intentionally omitted as per requirements

    # --- Acquisition Methods ---

    def acquire(self) -> bool:
        """Starts acquisition using current experiment settings and waits for completion."""
        if not self.is_connected():
            print("!! ERROR: Cannot acquire, not connected.")
            logging.error("Acquire called but not connected.")
            return False
        try:
            print("-- INFO: Checking experiment readiness...")
            if self._experiment.IsReadyToRun:
                print("-- INFO: Experiment is ready. Triggering Acquire()...")
                logging.info("Starting LightField acquisition...")
                logging.debug("Calling self._experiment.Acquire()...")
                self._experiment.Acquire() # Blocks until finished? Needs testing.
                logging.debug("self._experiment.Acquire() call finished.")
                # Add delay as requested
                logging.debug("Sleeping for 0.5s after Acquire()...")
                time.sleep(0.5)
                logging.debug("Finished sleeping.")
                # TODO: Add robust waiting if Acquire() is non-blocking (e.g., check IsReadyToRun in a loop with timeout)
                print("## SUCCESS: Acquire() command finished (after delay).")
                logging.info("LightField acquisition finished (after delay).")
                return True
            else:
                print("!! WARNING: Experiment not ready to run. Cannot acquire.")
                logging.warning("LightField experiment not ready to run.")
                return False
        except Exception as e:
            print(f"!! ERROR: Exception during Acquire(): {e}")
            logging.exception("Failed to acquire data in LightField:")
            return False

    def get_data(self) -> typing.Optional[np.ndarray]:
        """
        Gets the most recently acquired data as a NumPy array.
        Returns None if not connected, no data available, or on error.
        """
        if not self.is_connected():
            print("!! ERROR: Cannot get data, not connected.")
            logging.error("get_data called but not connected.")
            return None
        try:
            print("-- INFO: Getting latest image data from LightField...")
            logging.debug("Calling self._experiment.GetLatestImage()...")
            image_data_set = self._experiment.GetLatestImage()
            logging.debug(f"GetLatestImage returned: {type(image_data_set)}") # Log type

            if image_data_set is None:
                print("!! WARNING: GetLatestImage returned None (no data available?).")
                logging.warning("GetLatestImage returned None.")
                return None

            # Assuming 1D spectrum (Height=1) or first frame of 2D
            frame_count = image_data_set.Frames
            if frame_count == 0:
                print("!! WARNING: ImageDataSet contains 0 frames.")
                logging.warning("ImageDataSet contains 0 frames.")
                return None

            print(f"-- INFO: ImageDataSet contains {frame_count} frame(s). Getting frame 0.")
            logging.debug(f"Calling image_data_set.GetFrame(0)... (Frame count: {frame_count})")
            frame = image_data_set.GetFrame(0) # Frame index is 0
            logging.debug(f"GetFrame(0) returned: {type(frame)}") # Log type

            if frame is None:
                print("!! WARNING: GetFrame(0) returned None.")
                logging.warning("GetFrame(0) returned None.")
                return None

            logging.debug("Calling frame.GetData()...")
            buffer = frame.GetData()
            width = frame.Width
            height = frame.Height
            logging.debug(f"Frame dimensions: {width}x{height}. Buffer type: {type(buffer)}")
            print(f"-- INFO: Frame dimensions: {width}x{height}. Buffer type: {type(buffer)}")
            try:
                # Log first few elements if possible
                buffer_len = len(buffer) if hasattr(buffer, '__len__') else -1
                logging.debug(f"Buffer length: {buffer_len}. First 5 elements (if possible): {buffer[:5] if buffer_len > 5 else buffer}")
            except Exception as log_e:
                logging.warning(f"Could not log buffer elements: {log_e}")


            # --- Data Marshalling ---
            # Attempt conversion from System.Array (common case)
            try:
                logging.debug("Attempting conversion: list(buffer)...")
                # Convert buffer to a Python list first
                py_list = list(buffer)
                logging.debug(f"list(buffer) successful. List length: {len(py_list)}")
                # Determine numpy dtype based on frame data format if possible
                # This requires mapping LightField enums to numpy types
                # For now, assume common types like uint16 or float32
                np_dtype = np.uint16 # Default assumption - NEEDS VERIFICATION
                logging.debug(f"Using assumed np_dtype: {np_dtype}")
                # Example: Check frame.DataType if available and map it
                # data_format = frame.DataType # Check actual property name
                # if data_format == SomeLFEnum.MonochromeUnsigned16: np_dtype = np.uint16
                # elif data_format == SomeLFEnum.MonochromeFloating32: np_dtype = np.float32

                logging.debug(f"Attempting conversion: np.array(py_list, dtype={np_dtype})...")
                np_data = np.array(py_list, dtype=np_dtype)
                logging.debug(f"np.array conversion successful. Shape: {np_data.shape}, Dtype: {np_data.dtype}")

                # Reshape based on dimensions
                if height > 1:
                    logging.debug(f"Reshaping to ({height}, {width})...")
                    np_data = np_data.reshape((height, width))
                    logging.debug(f"Reshape successful. Final shape: {np_data.shape}")
                    print(f"## SUCCESS: Retrieved data. Shape: {np_data.shape}, Type: {np_data.dtype}")
                else:
                    # If height is 1, keep as 1D array
                    logging.debug("Height is 1, keeping as 1D array.")
                    print(f"## SUCCESS: Retrieved 1D data. Length: {np_data.shape[0]}, Type: {np_data.dtype}")

                logging.info(f"Successfully retrieved and converted data. Shape: {np_data.shape}, Type: {np_data.dtype}")
                return np_data

            except TypeError as te:
                print(f"!! ERROR: Failed to convert buffer to list/numpy array: {te}. Marshalling needed.")
                logging.error(f"TypeError during buffer conversion: {te}")
                return None
            except Exception as conv_e:
                print(f"!! ERROR: Unexpected error during data conversion: {conv_e}")
                logging.exception(f"Unexpected error during data conversion (buffer type: {type(buffer)}):")
                return None

        except Exception as e:
            print(f"!! ERROR: Exception during get_data: {e}")
            logging.exception("Failed to get data from LightField:")
            return None

# --- Example Usage (for testing script directly) ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    print("\n--- LightField Controller Direct Test ---")

    controller = LightFieldController()

    print("\n--- Testing DLL Loading ---")
    # Pass None to use auto-detection logic
    if controller.load_dlls(None):
        print("--- DLL Load Test: SUCCESS ---")

        print("\n--- Testing Connection ---")
        print("--> Please ensure LightField is running! <---")
        time.sleep(2) # Give user time to read
        if controller.connect():
            print("--- Connection Test: SUCCESS ---")

            print("\n--- Testing Parameter Reading ---")
            exp = controller.get_exposure_time_ms()
            temp = controller.get_sensor_temperature()
            status = controller.get_sensor_temperature_status()
            print(f"Read Exposure: {exp} ms")
            print(f"Read Temperature: {temp} C")
            print(f"Read Temp Status: {status}")

            print("\n--- Testing Parameter Setting ---")
            new_exp = 55.0 # ms
            print(f"Setting Exposure to: {new_exp} ms")
            if controller.set_exposure_time_ms(new_exp):
                print("Set Exposure: SUCCESS. Reading back...")
                time.sleep(0.5)
                read_back_exp = controller.get_exposure_time_ms()
                print(f"Read back Exposure: {read_back_exp} ms")
            else:
                print("Set Exposure: FAILED.")

            new_fname = "DirectTest"
            print(f"Setting Base Filename to: {new_fname}")
            if controller.set_base_filename(new_fname):
                print("Set Filename: SUCCESS.")
            else:
                print("Set Filename: FAILED.")

            print("\n--- Testing Acquisition ---")
            print("--> Ensure camera is ready in LightField! <---")
            time.sleep(2)
            if controller.acquire():
                print("--- Acquisition Test: SUCCESS ---")
                print("\n--- Testing Data Retrieval ---")
                data = controller.get_data()
                if data is not None:
                    print(f"--- Data Retrieval Test: SUCCESS ---")
                    print(f"Data Shape: {data.shape}, Data Type: {data.dtype}")
                    print(f"Data Min: {np.min(data)}, Max: {np.max(data)}, Mean: {np.mean(data):.2f}")
                    # Optional: Plot data if matplotlib is available
                    # try:
                    #     import matplotlib.pyplot as plt
                    #     plt.figure()
                    #     if data.ndim == 1: plt.plot(data)
                    #     elif data.ndim == 2: plt.imshow(data, aspect='auto')
                    #     plt.title("Acquired Spectrum (Direct Test)")
                    #     plt.show()
                    # except ImportError:
                    #     print("(Matplotlib not installed, skipping plot)")
                else:
                    print("--- Data Retrieval Test: FAILED (get_data returned None) ---")
            else:
                print("--- Acquisition Test: FAILED ---")

            print("\n--- Testing Disconnect ---")
            if controller.disconnect():
                print("--- Disconnect Test: SUCCESS ---")
            else:
                print("--- Disconnect Test: FAILED ---")

        else:
            print("--- Connection Test: FAILED ---")
            print("Troubleshooting:")
            print("- Is LightField running?")
            print("- Is a camera configured in the active LightField experiment?")
            print("- Check console for DLL loading errors.")
    else:
        print("--- DLL Load Test: FAILED ---")
        print("Ensure pythonnet is installed and LightField SDK path is correct/accessible.")

    print("\n--- Test Finished ---")
