import time
import time
import numpy as np
import logging
import random
import typing # Add typing import

# Basic logging setup
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MockKDC101Controller:
    """
    Mock version of the KDC101Controller for testing without hardware.
    Simulates basic behavior and delays.
    """
    def __init__(self):
        self._pos = 0.0
        self._connected = False
        self._devices = ["SIM_27000001", "SIM_27000002"] # Simulated serial numbers
        self.connected_serial = None
        logging.info("MockKDC101Controller initialized.")

    def scan_devices(self) -> list[str]:
        logging.info("MockKDC: Scanning for devices...")
        time.sleep(0.3) # Simulate scan time
        return self._devices

    def connect(self, serial_no: str) -> bool:
        logging.info(f"MockKDC: Attempting to connect to {serial_no}...")
        time.sleep(0.5) # Simulate connection time
        if serial_no in self._devices:
            self._connected = True
            self.connected_serial = serial_no
            logging.info(f"MockKDC: Connected to {serial_no}.")
            return True
        else:
            logging.error(f"MockKDC: Connection failed for {serial_no} (invalid serial).")
            return False

    def disconnect(self) -> bool:
        logging.info(f"MockKDC: Disconnecting from {self.connected_serial}...")
        time.sleep(0.1)
        self._connected = False
        self.connected_serial = None
        logging.info("MockKDC: Disconnected.")
        return True

    def is_connected(self) -> bool:
        return self._connected

    def home(self):
        if not self.is_connected(): raise RuntimeError("MockKDC: Not connected.")
        logging.info(f"MockKDC: Homing {self.connected_serial}...")
        time.sleep(1.5) # Simulate homing time
        self._pos = 0.0
        logging.info("MockKDC: Homing complete.")

    def move_to(self, position_deg: float):
        if not self.is_connected(): raise RuntimeError("MockKDC: Not connected.")
        logging.info(f"MockKDC: Moving {self.connected_serial} to {position_deg:.2f}°...")
        # Simulate move time based on distance (simple approximation)
        move_time = abs(position_deg - self._pos) / 20.0 # Assume 20 deg/sec avg speed
        time.sleep(max(0.1, move_time))
        self._pos = position_deg
        logging.info(f"MockKDC: Move complete. Position: {self._pos:.2f}°")

    def move_relative(self, displacement_deg: float):
        if not self.is_connected(): raise RuntimeError("MockKDC: Not connected.")
        target_pos = self._pos + displacement_deg
        logging.info(f"MockKDC: Moving {self.connected_serial} by {displacement_deg:.2f}° (to {target_pos:.2f}°)...")
        move_time = abs(displacement_deg) / 20.0
        time.sleep(max(0.1, move_time))
        self._pos = target_pos
        logging.info(f"MockKDC: Relative move complete. Position: {self._pos:.2f}°")

    def get_position(self) -> float:
        if not self.is_connected(): raise RuntimeError("MockKDC: Not connected.")
        # Simulate slight position noise/reading variability
        current_pos = self._pos + random.uniform(-0.01, 0.01)
        logging.debug(f"MockKDC: Getting position -> {current_pos:.2f}°")
        return current_pos

    def set_velocity(self, min_velocity_dps=0, acceleration_dps2=10, max_velocity_dps=10):
        if not self.is_connected(): raise RuntimeError("MockKDC: Not connected.")
        logging.info(f"MockKDC: Setting velocity params (Min={min_velocity_dps}, Accn={acceleration_dps2}, Max={max_velocity_dps})")
        # No actual effect in mock

    def wait_for_move(self, timeout_s: float = 30.0):
        # In mock, moves are blocking (via time.sleep), so this doesn't need to do much.
        # Could add a small delay just to simulate polling time if needed.
        if not self.is_connected(): raise RuntimeError("MockKDC: Not connected.")
        logging.debug("MockKDC: wait_for_move called (no-op in mock as moves are blocking).")
        time.sleep(0.05) # Simulate minimal check time


class MockLightFieldController:
    """
    Mock version of the LightFieldController for testing without hardware/software.
    Simulates basic behavior and delays.
    """
    def __init__(self):
        self._is_connected = False
        self._last_spectrum = None
        self._exposure = 0.1
        self._accumulations = 1
        self.loaded_sdk_path = None # Add this to match real controller interface
        logging.info("MockLightFieldController initialized.")

    def load_dlls(self, sdk_path: str | None = None) -> bool:
        """Mock method to simulate loading DLLs."""
        logging.info(f"MockLF: 'Loading' DLLs (path ignored: {sdk_path})...")
        time.sleep(0.05) # Simulate tiny delay
        self.loaded_sdk_path = "mock_path" # Simulate setting a path
        logging.info("MockLF: DLLs 'loaded'.")
        return True

    def connect(self) -> bool:
        logging.info("MockLF: Connecting to LightField...")
        time.sleep(0.8) # Simulate connection time
        self._is_connected = True
        logging.info("MockLF: Connected.")
        return True

    def disconnect(self) -> bool:
        logging.info("MockLF: Disconnecting...")
        time.sleep(0.2)
        self._is_connected = False
        logging.info("MockLF: Disconnected.")
        return True

    def is_connected(self) -> bool:
        return self._is_connected

    def set_experiment_settings(self, exposure_sec: float, accumulations: int = 1, base_filename: str = "scan"):
        if not self.is_connected(): raise RuntimeError("MockLF: Not connected.")
        logging.info(f"MockLF: Setting Exp={exposure_sec}s, Accums={accumulations}, File={base_filename}")
        self._exposure = exposure_sec
        self._accumulations = accumulations
        return True

    def acquire(self) -> bool:
        if not self.is_connected(): raise RuntimeError("MockLF: Not connected.")
        logging.info(f"MockLF: Acquiring (Exp={self._exposure}s, Accums={self._accumulations})...")
        acq_time = self._exposure * self._accumulations + 0.1 # Simulate acquisition + overhead
        time.sleep(max(0.1, acq_time))

        # Generate simulated spectrum data (e.g., Gaussian peak + noise)
        pixels = 1024
        peak_pos = random.uniform(200, 800)
        peak_width = random.uniform(20, 50)
        peak_intensity = random.uniform(5000, 50000) * self._exposure * self._accumulations
        noise_level = peak_intensity * 0.02

        x = np.arange(pixels)
        signal = peak_intensity * np.exp(-((x - peak_pos)**2) / (2 * peak_width**2))
        noise = np.random.normal(0, noise_level**0.5, pixels)
        baseline = random.uniform(50, 200)

        self._last_spectrum = signal + noise + baseline
        self._last_spectrum[self._last_spectrum < 0] = 0 # No negative counts

        logging.info("MockLF: Acquisition complete.")
        return True

    def get_data(self) -> typing.Union[np.ndarray, None]:
        if not self.is_connected(): raise RuntimeError("MockLF: Not connected.")
        if self._last_spectrum is not None:
            logging.debug("MockLF: Getting data...")
            return self._last_spectrum.copy() # Return a copy
        else:
            logging.warning("MockLF: No data acquired yet.")
            return None

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("--- Testing Mock KDC101 ---")
    mock_kdc = MockKDC101Controller()
    devices = mock_kdc.scan_devices()
    print(f"Found: {devices}")
    if devices:
        if mock_kdc.connect(devices[0]):
            print(f"Connected: {mock_kdc.is_connected()}")
            print(f"Pos: {mock_kdc.get_position():.2f}")
            mock_kdc.home()
            print(f"Pos after home: {mock_kdc.get_position():.2f}")
            mock_kdc.move_to(30.5)
            mock_kdc.move_relative(-10.2)
            print(f"Final Pos: {mock_kdc.get_position():.2f}")
            mock_kdc.disconnect()
            print(f"Connected: {mock_kdc.is_connected()}")
        else:
            print("Connection failed.")

    print("\n--- Testing Mock LightField ---")
    mock_lf = MockLightFieldController()
    if mock_lf.connect():
        print(f"Connected: {mock_lf.is_connected()}")
        mock_lf.set_experiment_settings(0.5, 3)
        if mock_lf.acquire():
            data = mock_lf.get_data()
            if data is not None:
                print(f"Acquired data shape: {data.shape}")
                # import matplotlib.pyplot as plt
                # plt.plot(data)
                # plt.title("Mock Spectrum")
                # plt.show()
            else:
                print("Failed to get data.")
        else:
            print("Acquisition failed.")
        mock_lf.disconnect()
        print(f"Connected: {mock_lf.is_connected()}")
    else:
        print("Connection failed.")
