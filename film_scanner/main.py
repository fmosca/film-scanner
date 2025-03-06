"""
Entry point for the Film Negative Scanner application.
"""
import tkinter as tk
from film_scanner.film_scanner_app import FilmScannerApp


def main():
    """Main entry point for the application."""
    try:
        root = tk.Tk()
        app = FilmScannerApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Error initializing application: {str(e)}")


if __name__ == "__main__":
    main()