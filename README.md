
# Polarization-Resolved SHG Automation

## Overview

This software provides a comprehensive solution for automating Polarization-Resolved Second Harmonic Generation (PR-SHG) measurements. It is specifically designed to determine the crystallographic axes of 2D materials, such as monolayers, which is crucial for calculating the interlayer twist angle in van der Waals heterostructures.

The application integrates control over a Thorlabs KDC101 motorized rotation stage (for a half-waveplate) and Princeton Instruments' LightField spectroscopy software, providing a seamless workflow from data acquisition to analysis.

![Software Screenshot](https://github.com/nikodemsokolowski/Polarization-SHG-Controller/raw/main/Fig1.png)

---

---

## Experimental Setup

The diagram below illustrates the principle of the Polarization-Resolved Second Harmonic Generation (PR-SHG) setup.

![PR-SHG Setup Diagram](https://github.com/nikodemsokolowski/Polarization-SHG-Controller/raw/main/setup.png)

### Excitation Path
1.  A **Ti:Sapphire Laser** generates the fundamental beam at a wavelength of ~900 nm.
2.  A **Polarizer** sets the linear polarization of the light.
3.  A **Half-waveplate**, mounted on the KDC101 rotation stage, precisely rotates the polarization plane of the laser beam.

### Detection Path
1.  The **Second Harmonic Generation (SHG) signal** at ~450 nm, is generated from the sample.
2.  The signal travels back through the same set of the **Half-waveplate** and the **Polarizer**.
3.  A **Short-pass Filter** cuts the laser light, transmitting only the SHG signal.
4.  The signal is then analyzed by a **Spectrometer with a CCD camera**, which is controlled by the **LightField** software.

## Features

-   **Hardware Integration:** Full control of a Thorlabs KDC101 rotation stage via the Kinesis SDK.
-   **Software Automation:** Connects to and automates data acquisition using Princeton Instruments' LightField software.
-   **Automated & Manual Control:**
    -   Define start angle, end angle, and step size for fully automated measurement sequences.
    -   Manual stage control (Home, Move To, Move Relative).
    -   Manual single spectrum acquisition.
-   **Live Data Visualization:**
    -   Real-time plotting of acquired spectra.
    -   Live updates of the intensity-vs-angle analysis plot during scans.
-   **Data Analysis:**
    -   Load previously acquired data for re-analysis.
    -   Calculate the maximum intensity within a user-defined spectral range.
    -   Fit the polarization-dependent intensity data to a theoretical model to extract the crystal orientation.
-   **User-Friendly Interface:**
    -   An intuitive GUI built with CustomTkinter.
    -   Includes a status bar, progress bar, and a detailed logging panel.
-   **Testing Mode:** Run the application with simulated hardware for development and testing using the `--mock` flag.

---

## Installation (For End-Users)

The easiest way to use the software is to download the pre-built version.

1.  **Download the latest release:** Go to the [**Releases Page**](https://github.com/nikodemsokolowski/Polarization-SHG-Controller/releases/latest) and download the `.zip` file.
2.  **Extract:** Unzip the downloaded file to a folder on your computer.
3.  **Run:** Double-click the `PolarizationScanController.exe` (or similar) executable file to start the application.

---

## Usage

1.  **Prepare LightField:** Ensure the Princeton Instruments LightField software is **closed**. The controller will launch and connect to it automatically.

2.  **Connect to Hardware:**
    -   In the "Controls" panel at the top left, you will find the connection controls.
    -   Click **"LightField Connect"**. The application will start LightField in the background.
    -   Next, scan for and connect to the KDC101 stage.
    -   **A green light will appear next to each button upon a successful connection.**

3.  **Set Scan Parameters:**
    -   Define the **Start Angle**, **End Angle**, and **Step Size** for the half-waveplate rotation.
    -   Specify the **Save Directory** where the data files will be stored.
    -   Set the **Range (nm)** for the wavelength region of interest used for calculating the maximum intensity.

4.  **Run the Scan:**
    -   Click **"Start Scan"** to begin the automated measurement.
    -   You can monitor the progress with the live spectrum and the updating intensity vs. angle plot.
    -   The scan can be paused, resumed, or aborted at any time.

5.  **Analyze Data:**
    -   Once the scan is complete, or by loading previous data using the **"Load Data (.csv)"** button in the "Intensity Analysis" tab, you can proceed with fitting.
    -   Enter initial guesses for the fit parameters (`y₀`, `A`, `θ₀`).
    -   Click **"Fit Data"** to perform the curve fitting. The results will be displayed.

---

## For Developers: Building from Source

If you want to modify the code or run it directly from source, follow these steps.

### 1. Prerequisites
-   **Python 3.9+** is recommended.
-   **Thorlabs Kinesis:** Must be installed for the KDC101 drivers.
-   **Princeton Instruments LightField:** Must be installed.

### 2. Setup
1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/nikodemsokolowski/Polarization-SHG-Controller.git](https://github.com/nikodemsokolowski/Polarization-SHG-Controller.git)
    cd Polarization-SHG-Controller
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the required Python packages:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Hardware SDK Paths:**
    -   **Thorlabs Kinesis:** The `kdc101_controller.py` script assumes a default installation path of `C:\Program Files\Thorlabs\Kinesis`. If your installation is different, you must update the `KINESIS_PATH` variable in the script.
    -   **LightField SDK:** The `lightfield_controller.py` script will attempt to find the SDK in a default location. If this fails, you can provide the path in the GUI.

### 3. Building an Executable
You can package the application into a standalone executable using PyInstaller.
-   **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```
-   **Build the Executable:**
    A `build.spec` file is included in the repository. Run PyInstaller with this file:
    ```bash
    pyinstaller build.spec
    ```
    This command will create `build` and `dist` folders. The final application is in the `dist` folder.

---

## Code Structure

The project is organized into several modules:

-   `main_app.py`: The main entry point of the application.
-   `gui_main_window.py`: Defines the main window layout.
-   `gui_*.py`: Files that define specific parts of the GUI.
-   `kdc101_controller.py`: Handles communication with the Thorlabs KDC101 stage.
-   `lightfield_controller.py`: Manages the connection to LightField software.
-   `scan_logic.py`: Contains the logic for the measurement scan loop.
-   `plotting_module.py`: Manages all the Matplotlib plots.
-   `analysis_module.py`: Contains functions for data analysis and curve fitting.
-   `mock_hardware.py`: Contains mock controller classes for testing.
-   `build.spec`: The configuration file for PyInstaller.

---

## License

This project is licensed under the MIT License.

