import os
import sqlite3
import sys
import threading
import time
from tkinter import messagebox
from typing import Dict

import customtkinter as ctk
import pyperclip
import pystray
import yaml
from PIL import Image
from steam_totp import generate_twofactor_code_for_time


def load_config():
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()
ROOT_DIR = _config["ROOT_DIR"]
sys.path.insert(0, ROOT_DIR)
from utils.logger import get_custom_logger

logger = get_custom_logger()


# database file
DB_FILE = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db\database.db"
ICON_PATH = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\executables\icons\twofa.ico"


def get_steam_credentials(steam_username: str) -> Dict[str, str]:
    """
    Retrieve Steam credentials from the database for a given username.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        query = """
        SELECT steam_password, steam_shared_secret, steam_identity_secret 
        FROM accounts 
        WHERE steam_username = ?
        """

        cursor.execute(query, (steam_username,))
        result = cursor.fetchone()

        if result is None:
            raise Exception(f"No credentials found for username: {steam_username}")

        credentials = {
            "steam_password": result[0],
            "steam_shared_secret": result[1],
            "steam_identity_secret": result[2],
        }

        return credentials

    except sqlite3.Error as e:
        raise Exception(f"database error: {str(e)}")


def get_twofa_code(steam_username: str) -> str:
    """
    Generates a two-factor authentication code for the given Steam username.
    """
    try:
        credentials = get_steam_credentials(steam_username)
        steam_shared_secret: str = credentials["steam_shared_secret"]
        return generate_twofactor_code_for_time(steam_shared_secret)
    except Exception as e:
        messagebox.showerror("Error", str(e))
        return ""


def get_icon_path():
    """Find the correct path to the icon file"""
    if getattr(sys, "frozen", False):
        # Running as executable
        base_path = sys._MEIPASS
        icon_path = os.path.join(base_path, "twofa.ico")
    else:
        # Running as script - use the known path
        icon_path = ICON_PATH

    if os.path.exists(icon_path):
        return icon_path
    else:
        # Fallback paths
        fallback_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "twofa.ico"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.ico"),
        ]

        for path in fallback_paths:
            if os.path.exists(path):
                return path

    # If nothing is found, return the default path and handle failure later
    return ICON_PATH


def show_window(icon, item):
    """Restores the main window when clicked in the system tray"""
    icon.stop()
    app.after(0, app.deiconify)


def exit_app(icon, item):
    """Properly closes the application from the system tray"""
    icon.stop()
    app.after(0, app.destroy)


def minimize_to_tray():
    """Minimizes the window to the system tray"""
    app.withdraw()
    create_tray_icon()


def create_tray_icon():
    """Creates and displays the system tray icon"""
    try:
        icon_path = get_icon_path()
        image = Image.open(icon_path)

        menu = pystray.Menu(
            pystray.MenuItem("Show", show_window), pystray.MenuItem("Exit", exit_app)
        )

        icon = pystray.Icon("steam_auth_generator", image, "Steam Auth Generator", menu)

        # Run the icon in a separate thread
        threading.Thread(target=icon.run, daemon=True).start()
    except Exception as e:
        logger.error(f"Error setting up tray icon: {e}")
        # If there's an error, create a fallback icon
        fallback_icon = Image.new("RGB", (64, 64), color=(76, 194, 255))
        icon = pystray.Icon(
            "steam_auth_generator",
            fallback_icon,
            "Steam Auth Generator",
            pystray.Menu(
                pystray.MenuItem("Show", show_window),
                pystray.MenuItem("Exit", exit_app),
            ),
        )
        threading.Thread(target=icon.run, daemon=True).start()


def generate_code(event=None):
    """Generates a Steam 2FA code and minimizes to tray."""
    username = entry_username.get().strip()
    if not username:
        messagebox.showwarning("Input Error", "Please enter a Steam username.")
        return
    code = get_twofa_code(username)
    if code:
        label_code.configure(text=f"{code}")

        # Copy to clipboard using pyperclip
        pyperclip.copy(code)

        # Add a small delay to ensure clipboard operation completes
        time.sleep(0.1)

        # Minimize the app to the system tray
        minimize_to_tray()


def main():
    global app, entry_username, label_code

    # Set theme and appearance
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    # Create the main window
    app = ctk.CTk()
    app.title("Steam Auth Generator")
    app.geometry("400x300")
    app.resizable(False, False)

    frame = ctk.CTkFrame(app)
    frame.pack(pady=20, padx=40, fill="both", expand=True)

    title_label = ctk.CTkLabel(
        frame, text="Steam 2FA Code Generator", font=ctk.CTkFont(size=20, weight="bold")
    )
    title_label.pack(pady=(20, 30))

    username_frame = ctk.CTkFrame(frame, fg_color="transparent")
    username_frame.pack(fill="x", padx=10, pady=(0, 20))

    username_label = ctk.CTkLabel(
        username_frame, text="Steam Username:", font=ctk.CTkFont(size=14)
    )
    username_label.pack(side="top", anchor="w", pady=(0, 5))

    entry_username = ctk.CTkEntry(
        username_frame,
        placeholder_text="Enter your Steam username",
        height=35,
        width=300,
        border_width=1,
    )
    entry_username.pack(side="top", fill="x")

    generate_button = ctk.CTkButton(
        frame,
        text="Generate Code",
        command=generate_code,
        height=40,
        font=ctk.CTkFont(size=14, weight="bold"),
    )
    generate_button.pack(pady=15)

    code_frame = ctk.CTkFrame(frame, fg_color="#1a1a1a", corner_radius=6)
    code_frame.pack(fill="x", padx=10, pady=10)

    code_title = ctk.CTkLabel(
        code_frame, text="Generated 2FA Code:", font=ctk.CTkFont(size=12)
    )
    code_title.pack(pady=(10, 5))

    label_code = ctk.CTkLabel(
        code_frame,
        text="",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color="#4cc2ff",
    )
    label_code.pack(pady=(0, 15))

    footer = ctk.CTkLabel(
        frame,
        text="Codes will be automatically copied to clipboard",
        font=ctk.CTkFont(size=10),
        text_color="gray",
    )
    footer.pack(pady=(10, 0))

    # Bind Enter key to generate_code function
    app.bind("<Return>", generate_code)

    # Bind close event to minimize to tray
    app.protocol("WM_DELETE_WINDOW", minimize_to_tray)

    app.mainloop()


if __name__ == "__main__":
    main()
