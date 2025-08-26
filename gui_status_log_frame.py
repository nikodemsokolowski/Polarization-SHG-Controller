import customtkinter as ctk
import tkinter as tk
from datetime import datetime

class StatusLogFrame(ctk.CTkFrame):
    """
    Frame for displaying status messages, progress bar, and a log history.
    """
    def __init__(self, master):
        super().__init__(master) # Use default fg_color from theme

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1) # Status label expands
        self.grid_columnconfigure(1, weight=0) # Progress labels fixed
        self.grid_columnconfigure(2, weight=0) # Progress bar fixed
        self.grid_rowconfigure(2, weight=1) # Allow log box to expand

        # --- Row 0: Status Bar ---
        self.status_label = ctk.CTkLabel(self, text="Status: Idle", anchor="w")
        self.status_label.grid(row=0, column=0, columnspan=3, padx=10, pady=(5, 2), sticky="ew")

        # --- Row 1: Progress Info ---
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 5), sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1) # Make progress bar expand if needed

        self.spectra_measured_label = ctk.CTkLabel(self.progress_frame, text="Spectra: - / -", anchor="w")
        self.spectra_measured_label.grid(row=0, column=1, padx=(0, 10), sticky="w")

        self.time_remaining_label = ctk.CTkLabel(self.progress_frame, text="ETA: --:--", anchor="w")
        self.time_remaining_label.grid(row=0, column=2, padx=(0, 10), sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.grid(row=0, column=0, sticky="ew")
        self.progress_bar.set(0) # Initial value


        # --- Row 2: Log Text Area ---
        self.log_textbox = ctk.CTkTextbox(self, state="disabled", wrap="word", height=100) # Start disabled
        self.log_textbox.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="nsew")

        # --- Log Context Menu ---
        self.log_menu = tk.Menu(self.log_textbox, tearoff=0)
        self.log_menu.add_command(label="Copy", command=self.copy_log_selection)
        self.log_menu.add_command(label="Clear Log", command=self.clear_log)
        self.log_textbox.bind("<Button-3>", self.show_log_menu) # Right-click

        self.log_message("Application started.")

    def update_status(self, message: str, error: bool = False):
        """Updates the status label text and color."""
        # Determine color based on theme (simple example)
        # default_color = ctk.ThemeManager.theme["CTkLabel"]["text_color"] # Get default color
        # status_color = "red" if error else default_color[1] # Use dark mode color index [1]
        status_color = "red" if error else "gray" # Simpler fixed colors
        self.status_label.configure(text=f"Status: {message}", text_color=status_color)
        self.log_message(message, is_error=error) # Also log status updates

    def update_progress(self, value: float, current_step: int | None = None, total_steps: int | None = None, eta_sec: float | None = None):
        """
        Updates the progress bar and related labels.

        Args:
            value (float): Progress bar value (0.0 to 1.0).
            current_step (int | None): Current step number (optional).
            total_steps (int | None): Total number of steps (optional).
            eta_sec (float | None): Estimated time remaining in seconds (optional).
        """
        clamped_value = max(0.0, min(1.0, value)) # Ensure value is within range
        self.progress_bar.set(clamped_value)

        if current_step is not None and total_steps is not None:
            self.spectra_measured_label.configure(text=f"Spectra: {current_step} / {total_steps}")
        else:
            self.spectra_measured_label.configure(text="Spectra: - / -")

        if eta_sec is not None and eta_sec >= 0:
            minutes = int(eta_sec // 60)
            seconds = int(eta_sec % 60)
            self.time_remaining_label.configure(text=f"ETA: {minutes:02d}:{seconds:02d}")
        else:
            self.time_remaining_label.configure(text="ETA: --:--")


    def log_message(self, message: str, is_error: bool = False):
        """Adds a timestamped message to the log text area."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{now}] {'ERROR: ' if is_error else ''}{message}\n"

        self.log_textbox.configure(state="normal") # Enable writing
        self.log_textbox.insert(tk.END, log_entry)
        self.log_textbox.see(tk.END) # Scroll to the bottom
        self.log_textbox.configure(state="disabled") # Disable writing

    def show_log_menu(self, event):
        """Shows the right-click context menu for the log."""
        try:
            # Select text under cursor if none selected
            if not self.log_textbox.tag_ranges("sel"):
                # Find the word under the cursor
                index = self.log_textbox.index(f"@{event.x},{event.y}")
                # Basic word selection (might need refinement)
                # self.log_textbox.tag_add("sel", f"{index} wordstart", f"{index} wordend")
                pass # Simple copy/clear doesn't strictly need selection pre-population

            # Enable/disable Copy based on selection
            if self.log_textbox.tag_ranges("sel"):
                self.log_menu.entryconfigure("Copy", state="normal")
            else:
                self.log_menu.entryconfigure("Copy", state="disabled")

            self.log_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.log_menu.grab_release()

    def copy_log_selection(self):
        """Copies the selected text from the log to the clipboard."""
        try:
            selected_text = self.log_textbox.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected_text:
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                self.update_idletasks() # Required on some systems
                print("Log selection copied to clipboard.")
        except tk.TclError:
            print("No text selected in log to copy.") # Handle case where selection disappears
        except Exception as e:
            print(f"Error copying log text: {e}")


    def clear_log(self):
        """Clears all text from the log text area."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", tk.END)
        self.log_textbox.configure(state="disabled")
        self.log_message("Log cleared.")


# Example usage (for testing this frame independently)
if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("600x300")
    app.title("Status Log Frame Test")

    frame = StatusLogFrame(app)
    frame.pack(expand=True, fill="both", padx=10, pady=10)

    # Simulate updates
    frame.update_status("Connecting...")
    frame.update_progress(0.2)
    app.after(1000, lambda: frame.update_status("Connected.", error=False))
    app.after(1500, lambda: frame.update_progress(0.5))
    app.after(2000, lambda: frame.log_message("Starting process..."))
    app.after(2500, lambda: frame.update_progress(0.8))
    app.after(3000, lambda: frame.update_status("Process failed!", error=True))
    app.after(3500, lambda: frame.update_progress(0.0))
    app.after(4000, lambda: frame.log_message("Another message."))

    app.mainloop()
