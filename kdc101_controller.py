import time
import os
import sys
import logging
import math # For isnan

# --- Pythonnet Setup ---
try:
    import clr
    PYTHONNET_LOADED = True
except ImportError:
    logging.error("pythonnet (clr) not found. Please install it: pip install pythonnet")
    PYTHONNET_LOADED = False
except Exception as e:
    logging.exception(f"Error importing clr: {e}")
    PYTHONNET_LOADED = False

# --- Kinesis CLI Configuration ---
KINESIS_PATH = r"C:\Program Files\Thorlabs\Kinesis"
# Define required DLLs
DEVICE_MANAGER_DLL = "Thorlabs.MotionControl.DeviceManagerCLI.dll"
GENERIC_MOTOR_DLL = "Thorlabs.MotionControl.GenericMotorCLI.dll"
KCUBE_DCSERVO_DLL = "Thorlabs.MotionControl.KCube.DCServoCLI.dll"

# --- Load Kinesis DLLs ---
KINESIS_DLL_LOAD_SUCCESS = False
if PYTHONNET_LOADED:
    try:
        # Check if Kinesis path exists
        if not os.path.isdir(KINESIS_PATH):
            raise FileNotFoundError(f"Kinesis directory not found at: {KINESIS_PATH}")

        # Add references to the required DLLs
        dll_path = os.path.join(KINESIS_PATH, DEVICE_MANAGER_DLL)
        generic_motor_dll_path = os.path.join(KINESIS_PATH, GENERIC_MOTOR_DLL)
        kcube_dll_path = os.path.join(KINESIS_PATH, KCUBE_DCSERVO_DLL)

        if not os.path.isfile(dll_path): raise FileNotFoundError(f"{DEVICE_MANAGER_DLL} not found at {dll_path}")
        if not os.path.isfile(generic_motor_dll_path): raise FileNotFoundError(f"{GENERIC_MOTOR_DLL} not found at {generic_motor_dll_path}")
        if not os.path.isfile(kcube_dll_path): raise FileNotFoundError(f"{KCUBE_DCSERVO_DLL} not found at {kcube_dll_path}")

        clr.AddReference(dll_path)
        clr.AddReference(generic_motor_dll_path)
        clr.AddReference(kcube_dll_path)
        logging.info("Successfully added references to Kinesis CLI DLLs.")

        # Import necessary Thorlabs classes
        from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI, SimulationManager, DeviceConfiguration
        # Remove VelocityParameters and JogParameters from this import as they cause ImportErrors
        from Thorlabs.MotionControl.GenericMotorCLI import GenericMotorCLI, MotorDirection
        from Thorlabs.MotionControl.KCube.DCServoCLI import KCubeDCServo
        from System import Decimal # For .NET decimal type

        KINESIS_DLL_LOAD_SUCCESS = True

    except FileNotFoundError as e:
        logging.error(f"Kinesis DLL loading failed: {e}")
        logging.error(f"Please ensure Kinesis is installed at: {KINESIS_PATH}")
    except Exception as e:
        logging.exception(f"Failed to load Kinesis DLLs or import classes: {e}")
        # Ensure namespaces are None on failure
        DeviceManagerCLI = None
        KCubeDCServo = None
        GenericMotorCLI = None
        Decimal = None
else:
    DeviceManagerCLI = None
    KCubeDCServo = None
    GenericMotorCLI = None
    Decimal = None


class KDC101Controller:
    """
    Controller class for Thorlabs KDC101 using Kinesis .NET CLI via pythonnet.
    """
    # Default timeouts (in milliseconds)
    DEFAULT_POLLING_RATE = 250
    DEFAULT_TIMEOUT_SETTINGS = 5000
    DEFAULT_TIMEOUT_MOVE = 60000 # 60 seconds

    def __init__(self):
        self.device: KCubeDCServo = None # Type hint for the device object
        self.serial_no: str = None
        self._is_connected_and_initialized = False

        if not PYTHONNET_LOADED or not KINESIS_DLL_LOAD_SUCCESS:
            logging.error("KDC101 Controller initialized but pythonnet/Kinesis DLLs failed to load.")
            # Optionally raise an exception
            # raise RuntimeError("KDC101 pythonnet/Kinesis DLLs could not be loaded.")

    def _check_prerequisites(self):
        """Checks if pythonnet and Kinesis DLLs/classes are loaded."""
        if not PYTHONNET_LOADED or not KINESIS_DLL_LOAD_SUCCESS or not DeviceManagerCLI or not KCubeDCServo or not Decimal:
            raise RuntimeError("Kinesis DLLs/Classes not loaded. Cannot perform operation.")
        return True

    def scan_devices(self) -> list[str]:
        """Scans for connected Kinesis devices and returns a list of KDC101 serial numbers."""
        self._check_prerequisites()
        serial_numbers_list = []
        try:
            logging.info("Building Kinesis device list...")
            DeviceManagerCLI.BuildDeviceList()
            # Get device list for KDC101 specifically
            serial_numbers = DeviceManagerCLI.GetDeviceList(KCubeDCServo.DevicePrefix)

            if serial_numbers is not None and serial_numbers.Count > 0:
                serial_numbers_list = [str(sn) for sn in serial_numbers]
                logging.info(f"Found KDC101 devices: {serial_numbers_list}")
            else:
                logging.info("No KDC101 devices found.")

        except Exception as e:
            logging.exception(f"An error occurred during Kinesis device scan: {e}")
            # Fallback or re-raise depending on desired behavior
            # raise RuntimeError("Failed to scan Kinesis devices") from e
        return serial_numbers_list

    def connect(self, serial_no: str) -> bool:
        """Connects to the KDC101 device with the specified serial number."""
        self._check_prerequisites()
        if not isinstance(serial_no, str):
            logging.error("Serial number must be a string.")
            return False
        if self.is_connected():
            if self.serial_no == serial_no:
                logging.warning(f"Device {serial_no} is already connected.")
                return True
            else:
                logging.warning(f"Another device ({self.serial_no}) is connected. Disconnect first.")
                return False

        try:
            logging.info(f"Attempting to connect to KDC101: {serial_no}...")
            # Create the device instance
            self.device = KCubeDCServo.CreateKCubeDCServo(serial_no)
            if self.device is None:
                raise RuntimeError(f"Failed to create KCubeDCServo instance for {serial_no}.")

            # Connect to the device
            self.device.Connect(serial_no)
            time.sleep(0.25) # Short pause after connect

            # Wait for settings to be initialized
            if not self.device.IsSettingsInitialized():
                logging.info("Waiting for device settings to initialize...")
                self.device.WaitForSettingsInitialized(self.DEFAULT_TIMEOUT_SETTINGS)

            if not self.device.IsSettingsInitialized():
                logging.error("Device settings failed to initialize within timeout.")
                self.device.Disconnect(True)
                self.device = None
                return False

            logging.info("Device connected and settings initialized.")

            # Load the motor configuration from the device
            logging.info("Loading motor configuration from device...")
            # Use UseDeviceSettings to load the config stored on the device
            motor_config = self.device.LoadMotorConfiguration(serial_no, DeviceConfiguration.DeviceSettingsUseOptionType.UseDeviceSettings)
            if motor_config is None:
                logging.warning("LoadMotorConfiguration returned None. Using default settings might lead to incorrect behavior.")
            else:
                logging.info(f"Motor configuration loaded. Device Settings Name: {motor_config.DeviceSettingsName}")

            # Start polling and enable the device
            logging.info("Starting polling and enabling device...")
            self.device.StartPolling(self.DEFAULT_POLLING_RATE)
            time.sleep(0.5) # Allow polling to start
            self.device.EnableDevice()
            time.sleep(1.0) # Allow time for enable command

            # Final check
            if not self.device.IsConnected or not self.device.IsEnabled:
                raise RuntimeError("Device failed to connect or enable properly after commands.")

            self.serial_no = serial_no
            self._is_connected_and_initialized = True
            logging.info(f"KDC101 {serial_no} connected and enabled successfully.")
            return True

        except Exception as e:
            logging.exception(f"Failed to connect to KDC101 {serial_no}: {e}")
            if self.device:
                try:
                    self.device.Disconnect(True)
                except Exception as disc_e:
                    logging.error(f"Error during disconnect after connection failure: {disc_e}")
            self.device = None
            self.serial_no = None
            self._is_connected_and_initialized = False
            return False

    def disconnect(self) -> bool:
        """Disconnects the currently connected KDC101 device."""
        if not self.is_connected():
            logging.warning("Not currently connected to any KDC101 device.")
            return False # Already disconnected

        try:
            logging.info(f"Disconnecting KDC101: {self.serial_no}...")
            if self.device:
                # Attempt to stop polling, catching potential errors
                try:
                    # Assuming StopPolling() exists even if IsPolling property doesn't
                    self.device.StopPolling()
                    logging.debug("Polling stopped.")
                except AttributeError:
                    logging.warning("'StopPolling' attribute/method not found, skipping.")
                except Exception as poll_e:
                    logging.warning(f"Error stopping polling: {poll_e}")

                # Attempt to disable device
                try:
                    if self.device.IsEnabled: # Check IsEnabled before disabling
                        self.device.DisableDevice()
                        logging.debug("Device disabled.")
                        time.sleep(0.2) # Short pause after disable
                    else:
                        logging.debug("Device already disabled.")
                except AttributeError:
                    logging.warning("'IsEnabled' or 'DisableDevice' attribute/method not found, skipping disable.")
                except Exception as disable_e:
                    logging.warning(f"Error disabling device: {disable_e}")

                # Disconnect the device
                self.device.Disconnect(True) # Pass True to release resources
                logging.info(f"Device {self.serial_no} disconnected.")
            return True
        except Exception as e:
            logging.exception(f"Error during KDC101 disconnection: {e}")
            return False # Indicate disconnection failed
        finally:
            # Ensure state is updated even if errors occurred
            self.device = None
            self.serial_no = None
            self._is_connected_and_initialized = False

    def is_connected(self) -> bool:
        """Returns True if connected and initialized, False otherwise."""
        # Check both the internal flag and the device object's status if available
        # Simplify the check for GUI purposes. Primarily care if the device object exists,
        # is connected, and settings are initialized. Enabling might fail non-critically.
        if self.device is not None:
            try:
                # Check IsConnected and IsSettingsInitialized
                is_conn = self.device.IsConnected
                is_init = self.device.IsSettingsInitialized()
                self._is_connected_and_initialized = is_conn and is_init
                # Optionally log the IsEnabled state if debugging enable issues
                # if self._is_connected_and_initialized:
                #     logging.debug(f"is_connected check: IsConnected={is_conn}, IsSettingsInitialized={is_init}, IsEnabled={self.device.IsEnabled}")

            except Exception as e:
                # If checking status fails, assume not connected
                logging.warning(f"Error checking KDC101 connection status: {e}")
                self._is_connected_and_initialized = False
        else:
            self._is_connected_and_initialized = False
        return self._is_connected_and_initialized

    def home(self):
        """Homes the KDC101 stage."""
        if not self.is_connected(): raise RuntimeError("KDC101 not connected.")
        try:
            logging.info(f"Homing KDC101: {self.serial_no}...")
            self.device.Home(self.DEFAULT_TIMEOUT_MOVE) # Use built-in timeout
            logging.info(f"Homing complete for {self.serial_no}.")
        except Exception as e:
            logging.exception(f"An error occurred during homing for {self.serial_no}:")
            raise RuntimeError(f"Homing failed: {e}") from e

    def move_to(self, position_deg: float):
        """Moves the stage to the specified absolute position in degrees."""
        if not self.is_connected(): raise RuntimeError("KDC101 not connected.")
        try:
            target_angle_dec = Decimal(position_deg) # Convert to .NET Decimal
            logging.info(f"Moving KDC101 {self.serial_no} to {target_angle_dec}°...")
            self.device.MoveTo(target_angle_dec, self.DEFAULT_TIMEOUT_MOVE) # Use built-in timeout
            logging.info(f"Move to {target_angle_dec}° complete for {self.serial_no}.")
        except ValueError as ve:
            logging.error(f"Invalid angle format for move_to: {position_deg}")
            raise ValueError(f"Invalid angle: {position_deg}") from ve
        except Exception as e:
            logging.exception(f"An error occurred during move_to for {self.serial_no}:")
            raise RuntimeError(f"MoveTo failed: {e}") from e

    def move_relative(self, displacement_deg: float):
        """Moves the stage by the specified relative displacement in degrees."""
        """Simulates relative move by getting current position and calling move_to."""
        if not self.is_connected(): raise RuntimeError("KDC101 not connected.")
        logging.info(f"Simulating relative move for {self.serial_no} by {displacement_deg}°...")
        print(f"--- DEBUG (kdc_controller.move_relative - SIMULATED): Received displacement_deg={displacement_deg} ---")
        try:
            # 1. Get the relative angle change as Decimal
            displacement_dec = Decimal(displacement_deg)
            print(f"--- DEBUG (kdc_controller.move_relative - SIMULATED): Converted displacement to Decimal: {displacement_dec} ---")

            # 2. Get the current position (returns float or NaN)
            print("--- DEBUG (kdc_controller.move_relative - SIMULATED): Reading current position... ---")
            current_position_float = self.get_position()
            print(f"--- DEBUG (kdc_controller.move_relative - SIMULATED): Read position: {current_position_float} ---")

            if math.isnan(current_position_float):
                logging.error("Could not get current position. Cannot perform relative move.")
                raise RuntimeError("Could not get current position for relative move.")

            current_position_dec = Decimal(current_position_float)

            # 3. Calculate the target absolute position
            target_position_dec = current_position_dec + displacement_dec
            logging.info(f"Current: {current_position_dec}°, Change: {displacement_dec}°, Target: {target_position_dec}°")
            print(f"--- DEBUG (kdc_controller.move_relative - SIMULATED): Calculated Target: {target_position_dec} ---")

            # 4. Move to the target absolute position using the existing move_to method
            # move_to handles the Decimal conversion and Kinesis call
            self.move_to(float(str(target_position_dec))) # Convert back to float for move_to

            logging.info(f"Simulated relative move ({displacement_dec}°) complete for {self.serial_no}.")

        except ValueError as ve:
            logging.error(f"Invalid displacement format for move_relative: {displacement_deg}")
            raise ValueError(f"Invalid displacement: {displacement_deg}") from ve
        except RuntimeError as rt_e: # Catch errors from get_position or move_to
            logging.error(f"Runtime error during simulated relative move: {rt_e}")
            raise rt_e # Re-raise
        except Exception as e:
            logging.exception(f"An unexpected error occurred during simulated move_relative for {self.serial_no}:")
            raise RuntimeError(f"Simulated MoveRelative failed: {e}") from e

    def get_position(self) -> float:
        """Gets the current stage position in degrees."""
        if not self.is_connected():
            logging.warning("get_position called but not connected.")
            return float('nan') # Not a number indicates disconnected/error

        try:
            # Position property directly returns Decimal
            position_dec = self.device.Position
            position_float = float(str(position_dec))
            logging.debug(f"KDC101 position: {position_float:.4f}° (Decimal: {position_dec})")
            return position_float
        except Exception as e:
            logging.exception(f"An error occurred while getting position for {self.serial_no}:")
            # Return NaN on error to avoid crashing periodic updates
            return float('nan')

    def set_velocity(self, min_velocity_dps=0.0, acceleration_dps2=10.0, max_velocity_dps=10.0):
        """Sets the velocity parameters in degrees/sec and degrees/sec^2."""
        if not self.is_connected(): raise RuntimeError("KDC101 not connected.")
        try:
            logging.info(f"Setting velocity params for {self.serial_no}: "
                        f"MinVel={min_velocity_dps:.2f}, Accn={acceleration_dps2:.2f}, MaxVel={max_velocity_dps:.2f} (dps)")
            # Get the device's current velocity parameters object
            # The specific type comes from the device driver, not GenericMotorCLI directly
            vel_params = self.device.GetVelocityParams()
            logging.debug(f"Current velocity params type: {type(vel_params)}")
            # Update attributes directly on the retrieved object
            vel_params.MinVelocity = Decimal(min_velocity_dps)
            vel_params.Acceleration = Decimal(acceleration_dps2)
            vel_params.MaxVelocity = Decimal(max_velocity_dps)
            # Set the updated struct back to the device
            self.device.SetVelocityParams(vel_params)
            logging.info("Velocity parameters set successfully.")
        except ValueError as ve:
            logging.error(f"Invalid value provided for velocity/acceleration: {ve}")
            raise ValueError("Invalid velocity/acceleration value") from ve
        except Exception as e:
            logging.exception(f"An error occurred setting velocity for {self.serial_no}:")
            raise RuntimeError(f"SetVelocity failed: {e}") from e

    def wait_for_move(self, timeout_s: float = 30.0):
        """
        Waits for the current move or home operation to complete by polling status.
        Note: CLI MoveTo/Home methods are blocking, so this might be redundant
            unless finer-grained status checking during the move is needed.
        """
        if not self.is_connected(): raise RuntimeError("KDC101 not connected.")
        logging.info(f"Waiting for move/home completion on {self.serial_no} (timeout={timeout_s}s)...")
        start_time = time.time()
        try:
            while time.time() - start_time < timeout_s:
                status = self.device.Status # Get the status object
                if not status.IsMoving and not status.IsHoming:
                    logging.info(f"Move/home appears complete for {self.serial_no}.")
                    return True
                time.sleep(0.1) # Polling interval
            logging.warning(f"Wait for move timed out after {timeout_s}s for {self.serial_no}.")
            raise TimeoutError(f"Move did not complete within {timeout_s} seconds.")
        except Exception as e:
            logging.exception(f"Error while waiting for move on {self.serial_no}:")
            raise RuntimeError(f"Wait for move failed: {e}") from e


# Example Usage (Basic Test) - Keep this for standalone testing if needed
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG) # Show more detail for testing

    if not KINESIS_DLL_LOAD_SUCCESS:
        print("\nKinesis DLLs failed to load. Cannot run hardware tests.")
        sys.exit(1)

    controller = KDC101Controller()
    print("\nKinesis DLLs loaded successfully.")
    try:
        print("Scanning for devices...")
        devices = controller.scan_devices()
        print(f"Found devices: {devices}")

        if not devices:
            print("No KDC101 devices found. Exiting test.")
        else:
            serial_to_test = devices[0] # Test with the first found device
            print(f"\n--- Testing with device: {serial_to_test} ---")

            print(f"Connecting to {serial_to_test}...")
            if controller.connect(serial_to_test):
                print("Connected successfully.")

                try:
                    # Get initial position
                    pos = controller.get_position()
                    if not math.isnan(pos): print(f"Initial position: {pos:.4f}°")

                    # Set velocity (example values)
                    # print("Setting velocity...")
                    # controller.set_velocity(max_velocity_dps=5.0, acceleration_dps2=5.0)

                    # Home the device (USE WITH CAUTION - ENSURE SAFE OPERATION)
                    # print("Homing device (ensure clear path)...")
                    # controller.home()
                    # print("Homing complete.")
                    # pos = controller.get_position()
                    # if not math.isnan(pos): print(f"Position after homing: {pos:.4f}°")

                    # Move to position (USE WITH CAUTION)
                    target_pos = 15.0
                    print(f"Moving to {target_pos}°...")
                    controller.move_to(target_pos)
                    # No explicit wait needed here as MoveTo is blocking
                    print("Move complete.")
                    pos = controller.get_position()
                    if not math.isnan(pos): print(f"Position after move_to: {pos:.4f}°")
                    time.sleep(1)

                    # Move relative (USE WITH CAUTION)
                    rel_move = -5.0
                    print(f"Moving relatively by {rel_move}°...")
                    controller.move_relative(rel_move)
                    # No explicit wait needed here
                    print("Relative move complete.")
                    pos = controller.get_position()
                    if not math.isnan(pos): print(f"Position after relative move: {pos:.4f}°")
                    time.sleep(1)

                except RuntimeError as e:
                    print(f"Runtime Error during test: {e}")
                except TimeoutError as e:
                    print(f"Timeout Error during test: {e}")
                except Exception as e:
                    print(f"Unexpected Error during test: {e}")
                finally:
                    # Disconnect
                    print("Disconnecting...")
                    controller.disconnect()
                    print("Disconnected.")
            else:
                print(f"Failed to connect to {serial_to_test}.")

    except RuntimeError as e:
        print(f"Runtime Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print(f"Runtime Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    print("\nTest finished.")
