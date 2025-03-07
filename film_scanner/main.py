"""
Entry point for the Film Negative Scanner application.
"""
import os
import sys
import tkinter as tk
from film_scanner.film_scanner_app import FilmScannerApp
from film_scanner.image_processor import ImageProcessor


def main():
    """Main entry point for the application."""
    try:
        # Set process priority higher for better performance
        try:
            if sys.platform == 'win32':
                # On Windows
                import psutil
                p = psutil.Process(os.getpid())
                p.nice(psutil.HIGH_PRIORITY_CLASS)
            else:
                # On Unix-like systems (Linux, macOS)
                os.nice(-10)  # Higher priority
        except (ImportError, PermissionError):
            # Ignore if we can't set priority or if psutil is not installed
            pass
            
        # Configure Tkinter for better performance
        root = tk.Tk()
        
        # Allow Tkinter to use hardware acceleration if available
        try:
            root.tk.call('tk', 'scaling', 1.0)  # Consistent scaling
            root.option_add('*tearOff', False)  # Disable tear-off menus
        except Exception:
            pass
            
        # Set window icon if available
        try:
            # Find the application directory
            app_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(app_dir, 'assets', 'icon.png')
            if os.path.exists(icon_path):
                img = tk.PhotoImage(file=icon_path)
                root.iconphoto(True, img)
        except Exception:
            pass
            
        # Create and run the application
        app = FilmScannerApp(root)
        
        # Handle application shutdown gracefully
        def on_closing():
            try:
                ImageProcessor.clear_cache()  # Clear any image caches
                app.camera_manager.stop_live_view()  # Stop camera connection
                root.destroy()
                sys.exit(0)
            except Exception as e:
                print(f"Error during shutdown: {e}")
                sys.exit(1)
                
        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()
        
    except Exception as e:
        print(f"Error initializing application: {str(e)}")
        
        # Show error in GUI if possible
        try:
            error_root = tk.Tk()
            error_root.title("Film Scanner - Error")
            tk.Label(
                error_root, 
                text=f"Error starting Film Scanner:\n\n{str(e)}", 
                pady=20, 
                padx=20
            ).pack()
            tk.Button(
                error_root, 
                text="OK", 
                command=error_root.destroy, 
                width=10
            ).pack(pady=(0, 20))
            error_root.mainloop()
        except:
            pass  # If even the error window fails, just exit


if __name__ == "__main__":
    main()
