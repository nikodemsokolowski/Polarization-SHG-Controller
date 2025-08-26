# --- Inside gui_main_window.py ---

import customtkinter as ctk
from customtkinter import CTkScrollableFrame

# Import frame classes
from gui_connection_frame import ConnectionFrame
from gui_scan_params_frame import ScanParamsFrame
from gui_manual_control_frame import ManualControlFrame
from gui_status_log_frame import StatusLogFrame
from gui_plotting_tabs import PlottingTabs

class MainWindow(ctk.CTkFrame):
    """
    Main window structure containing all GUI elements.
    Organizes the different frames (Connection, Scan, Manual, Status, Plotting).
    """
    # 1. Modify the __init__ signature to accept app_instance
    def __init__(self, master, app_instance, **kwargs): # <-- ADDED app_instance parameter
        super().__init__(master, **kwargs)
        # self.master still refers to the PolarizationScanApp instance passed as master
        self.master = master

        # 2. Store the app_instance reference (though self.master could also be used)
        self.app = app_instance # <-- ADDED THIS LINE

        # --- Configure Main Grid ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        # --- Left Column Frames ---
        self.left_scrollable_frame = CTkScrollableFrame(self, label_text="Controls", width=300)
        self.left_scrollable_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # --- Instantiate and place frames *inside* the scrollable frame ---

        # 3. Modify ConnectionFrame creation:
        #    - Pass the stored app_instance using app_instance=self.app
        #    - Access controllers via self.app (cleaner than using master directly here)
        self.connection_frame = ConnectionFrame(
            master=self.left_scrollable_frame, # Parent widget is the scrollable frame
            kdc101_controller=self.app.kdc101_controller, # Access controller via app instance
            lightfield_controller=self.app.lightfield_controller, # Access controller via app instance
            app_instance=self.app # <-- PASS THE APP INSTANCE HERE
        )
        self.connection_frame.pack(pady=(5, 5), padx=10, fill="x", expand=False)

        # Instantiate ManualControlFrame first so we can pass it to ScanParamsFrame
        self.manual_control_frame = ManualControlFrame(self.left_scrollable_frame, app_instance=self.app) # Pass app_instance
        self.manual_control_frame.pack(pady=5, padx=10, fill="x", expand=False)

        # Pass both app_instance and manual_control_frame to ScanParamsFrame
        self.scan_params_frame = ScanParamsFrame(
            master=self.left_scrollable_frame,
            app_instance=self.app,
            manual_control_frame=self.manual_control_frame # Pass the reference
        )
        self.scan_params_frame.pack(pady=5, padx=10, fill="x", expand=False)


        # --- Right Column Frames ---
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        self.right_frame.grid_rowconfigure(0, weight=3)
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        # Update plotting tabs instantiation: Pass the full app instance
        self.plotting_tabs = PlottingTabs(self.right_frame, self.app) # Pass self.app (app_instance)
        self.plotting_tabs.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")

        self.status_log_frame = StatusLogFrame(self.right_frame)
        self.status_log_frame.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")

    # --- No other methods needed in this example, unless you have them ---

# --- End of file ---
