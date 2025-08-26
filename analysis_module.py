import numpy as np
import logging
from scipy.optimize import curve_fit

# Basic logging setup
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AnalysisModule:
    """
    Handles data analysis tasks like intensity calculation and fitting.
    """
    def __init__(self):
        logging.info("AnalysisModule initialized.")
        # Store analysis parameters if needed (e.g., ROI)
        self.roi = None # Example: [start_pixel, end_pixel]

    def set_roi(self, roi_start: int, roi_end: int):
        """Sets the Region of Interest for intensity calculation."""
        if roi_start >= roi_end:
            logging.error(f"Invalid ROI: Start ({roi_start}) must be less than End ({roi_end}).")
            self.roi = None
            return False
        self.roi = [roi_start, roi_end]
        logging.info(f"Analysis ROI set to: {self.roi}")
        return True

    def calculate_intensity(self, spectrum_data: np.ndarray) -> float:
        """
        Calculates the integrated intensity within the defined ROI.
        If no ROI is set, integrates the entire spectrum.
        """
        if spectrum_data is None or spectrum_data.size == 0:
            logging.warning("calculate_intensity called with empty data.")
            return 0.0

        # Assuming 1D spectrum data for intensity calculation
        if spectrum_data.ndim > 1:
            # Basic handling for 2D: sum all pixels or specific region?
            # For now, just sum the whole 2D array if ROI is not set,
            # otherwise, apply ROI along one dimension (e.g., columns/wavelength)
            logging.warning(f"Calculating intensity for {spectrum_data.ndim}D data. Check logic.")
            if self.roi:
                # Apply ROI along the last dimension (assumed wavelength/pixel axis)
                roi_start, roi_end = self.roi
                if roi_end > spectrum_data.shape[-1]:
                    logging.warning(f"ROI end ({roi_end}) exceeds data dimension ({spectrum_data.shape[-1]}). Clamping.")
                    roi_end = spectrum_data.shape[-1]
                if roi_start >= roi_end:
                    logging.error("Invalid ROI after clamping.")
                    return 0.0
                data_in_roi = spectrum_data[..., roi_start:roi_end]
                return float(np.sum(data_in_roi))
            else:
                return float(np.sum(spectrum_data)) # Sum all elements

        # 1D data handling
        if self.roi:
            roi_start, roi_end = self.roi
            if roi_end > len(spectrum_data):
                logging.warning(f"ROI end ({roi_end}) exceeds data length ({len(spectrum_data)}). Clamping.")
                roi_end = len(spectrum_data)
            if roi_start >= roi_end:
                logging.error("Invalid ROI after clamping.")
                return 0.0
            data_in_roi = spectrum_data[roi_start:roi_end]
            intensity = np.sum(data_in_roi)
            logging.debug(f"Calculated intensity in ROI {self.roi}: {intensity}")
        else:
            intensity = np.sum(spectrum_data)
            logging.debug(f"Calculated intensity (full spectrum): {intensity}")

        return float(intensity)

    def fit_polarization_data(self, angles_deg: np.ndarray, intensities: np.ndarray, fit_type: str = 'cos2') -> tuple[np.ndarray, dict] | tuple[None, None]:
        """
        Fits the intensity vs. angle data to a model function.

        Args:
            angles_deg (np.ndarray): Array of polarization angles in degrees.
            intensities (np.ndarray): Array of corresponding integrated intensities.
            fit_type (str): The type of fit function ('cos2', 'cos4', etc. - placeholder).

        Returns:
            tuple[np.ndarray, dict] | tuple[None, None]:
                - Fitted intensity values corresponding to input angles.
                - Dictionary containing optimized parameters and potentially fit quality info.
                Returns (None, None) on failure.
        """
        if angles_deg is None or intensities is None or len(angles_deg) != len(intensities) or len(angles_deg) < 3:
            logging.error("Invalid input data for fitting.")
            return None, None

        angles_rad = np.radians(angles_deg)

        try:
            if fit_type == 'cos2':
                # I = A * cos^2(theta - phi) + C
                def cos2_model(theta, amplitude, phase_rad, offset):
                    return amplitude * (np.cos(theta - phase_rad)**2) + offset

                # Provide initial guesses (crucial for good fits)
                initial_amplitude = np.max(intensities) - np.min(intensities)
                initial_offset = np.min(intensities)
                # Guess phase based on max intensity location (simplified)
                initial_phase_rad = angles_rad[np.argmax(intensities)]
                p0 = [initial_amplitude, initial_phase_rad, initial_offset]

                params, covariance = curve_fit(cos2_model, angles_rad, intensities, p0=p0)
                amplitude, phase_rad, offset = params

                # Generate fitted curve
                fitted_intensities = cos2_model(angles_rad, *params)

                # Convert phase back to degrees for reporting if desired
                phase_deg = np.degrees(phase_rad) % 360 # Keep within 0-360

                fit_results = {
                    'amplitude': amplitude,
                    'phase_deg': phase_deg,
                    'offset': offset,
                    'phase_rad': phase_rad, # Keep rad for potential reuse
                    # TODO: Add R^2 or other fit quality metrics if needed
                }
                logging.info(f"Fit successful (cos2): Amp={amplitude:.2f}, Phase={phase_deg:.1f}°, Offset={offset:.2f}")
                return fitted_intensities, fit_results

            # elif fit_type == 'cos4':
                # Implement cos^4 model: A * cos^4(theta - phi) + C
                # ...
                # pass

            else:
                logging.error(f"Unsupported fit type: {fit_type}")
                return None, None

        except RuntimeError as e:
            logging.error(f"Fit failed: {e}")
            return None, None
        except Exception as e:
            logging.exception(f"Unexpected error during fitting:")
            return None, None


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    analyzer = AnalysisModule()

    # Test intensity calculation
    mock_data_1d = np.array([10, 20, 100, 110, 30, 15])
    print(f"\nData: {mock_data_1d}")
    intensity_full = analyzer.calculate_intensity(mock_data_1d)
    print(f"Full Intensity: {intensity_full}") # Expected: 285

    analyzer.set_roi(2, 4) # ROI includes indices 2 and 3 (values 100, 110)
    intensity_roi = analyzer.calculate_intensity(mock_data_1d)
    print(f"ROI Intensity: {intensity_roi}") # Expected: 210

    analyzer.set_roi(0, 10) # Test ROI clamping
    intensity_roi_clamped = analyzer.calculate_intensity(mock_data_1d)
    print(f"Clamped ROI Intensity: {intensity_roi_clamped}") # Expected: 285

    # Test fitting
    print("\n--- Fitting Test ---")
    # Generate mock polarization data with noise
    true_amp = 500
    true_phase_deg = 30
    true_offset = 50
    angles = np.linspace(0, 360, 37) # 0 to 360 degrees, 10 deg steps
    angles_rad_test = np.radians(angles)
    noise = np.random.normal(0, 20, len(angles))
    intensities_mock = true_amp * (np.cos(angles_rad_test - np.radians(true_phase_deg))**2) + true_offset + noise

    print(f"Fitting {len(angles)} data points...")
    fitted_curve, fit_params = analyzer.fit_polarization_data(angles, intensities_mock, fit_type='cos2')

    if fit_params:
        print("Fit Parameters:")
        for key, value in fit_params.items():
            print(f"  {key}: {value:.4f}")

        # Optional: Plot results for visual verification
        try:
            import matplotlib.pyplot as plt
            plt.figure()
            plt.plot(angles, intensities_mock, 'bo', label='Mock Data')
            plt.plot(angles, fitted_curve, 'r-', label='Fit')
            plt.xlabel("Angle (°)")
            plt.ylabel("Intensity")
            plt.title("Fitting Test")
            plt.legend()
            plt.grid(True)
            print("Plotting fit results...")
            plt.show()
        except ImportError:
            print("Matplotlib not found, skipping plot.")
    else:
        print("Fitting failed.")
