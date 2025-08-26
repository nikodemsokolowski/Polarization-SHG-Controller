# Polarization Scan Controller

A Python desktop application for automating polarization-resolved Second Harmonic Generation (SHG) measurements.

## Features

*   Controls Thorlabs KDC101 rotation stage via Kinesis SDK (`ctypes`).
*   Controls Princeton Instruments LightField software via Automation (`pythonnet`).
*   GUI built with CustomTkinter.
*   Configurable scan parameters (angle range, step, exposure, accumulations).
*   Manual stage control (home, move to, move relative).
*   Manual single spectrum acquisition.
*   Live spectrum display.
*   Polarization-dependent intensity analysis plot with optional fitting.
*   Status bar, progress bar, and logging panel.
*   Saves raw data (TODO: Implement saving in `scan_logic.py` using `file_io_utils.py`).
*   Mock hardware mode for testing without connected devices (`python main_app.py --mock`).

## Prerequisites

1.  **Python 3.x:** Recommended 3.9+
2.  **Thorlabs Kinesis:** Must be installed in the default location (`C:\Program Files\Thorlabs\Kinesis`). The application relies on finding the necessary DLLs (`Thorlabs.MotionControl.DeviceManager.dll`, `Thorlabs.MotionControl.KCube.DCServo.dll`) within this directory.
3.  **Princeton Instruments LightField:** Must be installed. The application attempts to find the Automation DLLs (`PrincetonInstruments.LightField.AutomationV2.dll`, `PrincetonInstruments.LightFieldAddInSupportServices.dll`) relative to the path specified by the `LIGHTFIELD_INSTALL_PATH` environment variable, or defaults to `C:\Program Files\Princeton Instruments\LightField` if the variable is not set. Ensure the DLLs are present in the expected subdirectories (`Automation\AutomationV2` and `AddInSupport`).
4.  **Required Python Packages:** Install using pip:
    ```bash
    pip install customtkinter matplotlib numpy scipy pythonnet
    ```
    *(Note: `pythonnet` installation might require specific .NET framework versions depending on your system and LightField version.)*

## Installation / Setup

1.  **Clone the repository or download the source code.**
2.  **Install Prerequisites:** Ensure Python, Kinesis, LightField, and the required Python packages (see above) are installed correctly.
3.  **(Optional) Set Environment Variables:**
    *   If your LightField installation is not in the default path, set the `LIGHTFIELD_INSTALL_PATH` environment variable to your LightField installation directory (e.g., `D:\Programs\LightField`).
4.  **Verify Hardware Connections:** Connect the KDC101 stage and ensure the spectrometer is connected and configured within LightField.

## Running the Application

### From Source

Navigate to the project directory in your terminal and run:

```bash
python main_app.py
```

To run with simulated hardware (useful for UI testing or development without devices):

```bash
python main_app.py --mock
```

### From Executable (After Building)

1.  **Build the Executable:**
    *   Ensure `pyinstaller` is installed (`pip install pyinstaller`).
    *   Navigate to the project directory in your terminal.
    *   Run PyInstaller using the spec file:
        ```bash
        pyinstaller build.spec
        ```
    *   This will create a `dist` folder containing the executable (`PolarizationScanController.exe`) and associated files.
    *   **Note:** The `build.spec` file may need adjustments (e.g., adding hidden imports for `clr` namespaces, explicitly including Kinesis/LightField DLLs if not found automatically) depending on your specific environment and package versions. Debugging PyInstaller builds can involve trial and error. Check the build warnings and output for clues.

2.  **Run the Executable:**
    *   Navigate to the `dist/PolarizationScanController` folder.
    *   Double-click `PolarizationScanController.exe`.

## Usage

1.  **Device Connections:**
    *   Click "Scan" to detect connected KDC101 devices.
    *   Select the desired KDC101 serial number from the dropdown.
    *   Click "Connect" for KDC101. Status will update.
    *   Click "Connect" for LightField. Status will update. (Ensure LightField software is running).
2.  **Scan Parameters:**
    *   Enter the desired Start Angle, End Angle, and Step Size in degrees.
    *   Enter the Exposure time (seconds) and number of Accumulations for LightField.
    *   Select a Save Directory using "Browse".
    *   Enter a Base Filename for saved data.
3.  **Run Scan:**
    *   Click "Start Scan". The scan will proceed through the angles, acquiring data at each step.
    *   Progress is shown in the progress bar and status messages.
    *   Live spectrum and intensity vs. angle plots will update.
    *   Click "Stop Scan" to abort the current scan.
4.  **Manual Control:**
    *   Use the "Home", "Move To", and "Move Rel" controls for the KDC101 stage (requires connection).
    *   The current stage position is updated periodically.
    *   Click "Acquire Single Spectrum" to take one measurement using LightField (requires connection).
5.  **Plots:**
    *   **Live Spectrum:** Shows the most recently acquired spectrum. Use the toolbar to zoom/pan.
    *   **Intensity Analysis:** Shows the integrated intensity (from ROI or full spectrum) vs. the measured polarization angle. A fit (e.g., cos^2) is applied after the scan completes.
6.  **Status/Log:**
    *   The bottom status bar shows the latest message.
    *   The log panel provides a history of operations and errors. Right-click to copy or clear.

## Code Structure

The application follows a modular structure to keep individual files concise:

*   `main_app.py`: Main application class, orchestrates GUI and controllers.
*   `gui_*.py`: Files defining different parts of the CustomTkinter GUI.
*   `kdc101_controller.py`: KDC101 hardware communication (`ctypes`).
*   `lightfield_controller.py`: LightField hardware communication (`pythonnet`).
*   `scan_logic.py`: Core scan loop execution (threaded).
*   `analysis_module.py`: Data processing (intensity calculation, fitting).
*   `plotting_module.py`: Updates Matplotlib plots.
*   `file_io_utils.py`: Helper functions for saving data (TODO).
*   `mock_hardware.py`: Mock controllers for testing.
*   `build.spec`: PyInstaller configuration.
*   `README.md`: This file.
