import numpy as np
import os
import logging
from datetime import datetime

def save_scan_data(filename: str, angle_target: float, angle_actual: float, spectrum_data: np.ndarray):
    """
    Saves the acquired spectrum data along with metadata to a text file.

    Args:
        filename (str): The full path to the file where data should be saved.
        angle_target (float): The target polarization angle for this step.
        angle_actual (float): The actual position read from the stage.
        spectrum_data (np.ndarray): The acquired spectrum data (assumed 1D or 2D).
    """
    try:
        # Ensure the directory exists
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            logging.info(f"Created directory: {directory}")

        # Prepare header information
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = (
            f"# Polarization Scan Data\n"
            f"# Timestamp: {timestamp}\n"
            f"# Target Angle (deg): {angle_target:.4f}\n"
            f"# Actual Angle (deg): {angle_actual:.4f}\n"
            # TODO: Add wavelength/pixel calibration info if available
            # TODO: Add exposure, accumulations, other relevant metadata
            f"# Data Columns: Pixel_Index Intensity (or Wavelength Intensity)\n"
            f"# Shape: {spectrum_data.shape}\n"
            f"# ------------------------------------\n"
        )

        # Assuming 1D data for now (e.g., spectrum intensity vs pixel index)
        if spectrum_data.ndim == 1:
            # Create an index column
            indices = np.arange(len(spectrum_data))
            data_to_save = np.column_stack((indices, spectrum_data))
            fmt = ['%d', '%.6e'] # Format for index and intensity
        elif spectrum_data.ndim == 2:
            # Handle 2D data (e.g., image) - needs more thought on TXT format
            # Maybe save as CSV? Or just save raw numbers?
            logging.warning("Saving 2D data to TXT is basic. Consider CSV or binary formats.")
            # Flattening for basic save, but loses structure:
            # data_to_save = spectrum_data.flatten()
            # Or save row by row?
            data_to_save = spectrum_data # Save as is, np.savetxt handles 2D
            fmt = '%.6e' # Format for all elements
        else:
            logging.error(f"Unsupported data dimension for saving: {spectrum_data.ndim}")
            return False

        # Save the data
        np.savetxt(filename, data_to_save, fmt=fmt, header=header.strip(), comments='')
        logging.info(f"Successfully saved data to {filename}")
        return True

    except IOError as e:
        logging.error(f"IOError saving data to {filename}: {e}")
        return False
    except Exception as e:
        logging.exception(f"Unexpected error saving data to {filename}:")
        return False

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_dir = "test_scan_output"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)

    # 1D data test
    mock_spectrum_1d = np.linspace(1000, 100, 10) + np.random.rand(10) * 10
    filename_1d = os.path.join(test_dir, "test_data_1d_ang45.0.txt")
    print(f"\nSaving 1D data to {filename_1d}...")
    save_scan_data(filename_1d, 45.0, 45.0123, mock_spectrum_1d)

    # 2D data test
    mock_spectrum_2d = np.random.rand(3, 4) * 1000
    filename_2d = os.path.join(test_dir, "test_data_2d_ang90.0.txt")
    print(f"\nSaving 2D data to {filename_2d}...")
    save_scan_data(filename_2d, 90.0, 89.9876, mock_spectrum_2d)

    print(f"\nCheck the '{test_dir}' directory for output files.")
