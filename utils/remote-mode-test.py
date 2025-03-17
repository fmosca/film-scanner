#!/usr/bin/env python3
"""
Test script that handles mode switching between live view and remote shutter.
"""
import time
import sys
import io
import threading
import queue
import tkinter as tk
from PIL import Image, ImageTk
from olympuswifi.camera import OlympusCamera
from olympuswifi.liveview import LiveViewReceiver

class RemoteModeTest:
    def __init__(self):
        self.camera = OlympusCamera()
        self.img_queue = queue.Queue(maxlen=5)
        self.receiver = None
        self.thread = None
        self.running = False
        self.current_mode = None  # 'liveview' or 'shutter'
        
    def setup_ui(self):
        self.root = tk.Tk()
        self.root.title("Remote Mode Test")
        self.root.geometry("800x600")
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Control frame
        control_frame = tk.Frame(self.root)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        # Live view button
        self.liveview_btn = tk.Button(control_frame, text="Start Live View", command=self.start_live_view)
        self.liveview_btn.pack(side=tk.LEFT, padx=5)
        
        # Remote shutter button
        self.shutter_btn = tk.Button(control_frame, text="Switch to Remote Shutter", command=self.switch_to_shutter)
        self.shutter_btn.pack(side=tk.LEFT, padx=5)
        
        # Capture button
        self.capture_btn = tk.Button(control_frame, text="Capture", command=self.take_picture)
        self.capture_btn.pack(side=tk.LEFT, padx=5)
        
        # Image view
        self.image_frame = tk.Frame(self.root, bg="black")
        self.image_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(self.image_frame, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Status updates frame
        self.log_frame = tk.Frame(self.root)
        self.log_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        self.log_text = tk.Text(self.log_frame, height=5, width=60)
        self.log_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        scrollbar = tk.Scrollbar(self.log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Start frame checking
        self.root.after(33, self.check_for_frames)
        
        # Configure window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        return self.root
    
    def log(self, message):
        """Add message to log window"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        print(message)
    
    def update_status(self, message):
        """Update status bar"""
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def start_live_view(self):
        """Start live view mode"""
        if self.current_mode == 'liveview':
            self.log("Live view already active")
            return
            
        try:
            self.update_status("Switching to recording mode...")
            self.camera.send_command('switch_cammode', mode='rec', lvqty="0640x0480")
            time.sleep(1)
            
            self.update_status("Starting live view...")
            self.camera.start_liveview(port=40000, lvqty="0640x0480")
            time.sleep(0.5)
            
            # Clear any existing frames
            while not self.img_queue.empty():
                self.img_queue.get_nowait()
            
            # Start receiver
            self.receiver = LiveViewReceiver(self.img_queue)
            self.thread = threading.Thread(target=self.receiver.receive_packets, args=[40000])
            self.thread.daemon = True
            self.thread.start()
            
            self.running = True
            self.current_mode = 'liveview'
            self.update_status("Live view active")
            self.log("Live view started")
            
            # Update button states
            self.liveview_btn.config(state=tk.DISABLED)
            self.shutter_btn.config(state=tk.NORMAL)
            self.capture_btn.config(state=tk.DISABLED)
            
        except Exception as e:
            self.update_status(f"Error: {e}")
            self.log(f"Error starting live view: {e}")
    
    def switch_to_shutter(self):
        """Switch to remote shutter mode"""
        if self.current_mode == 'shutter':
            self.log("Already in remote shutter mode")
            return
            
        try:
            if self.running:
                self.update_status("Stopping live view...")
                self.receiver.shut_down()
                self.camera.stop_liveview()
                self.running = False
                time.sleep(1)
            
            self.update_status("Switching to shutter mode...")
            self.camera.send_command('switch_cammode', mode='shutter')
            time.sleep(1)
            
            self.current_mode = 'shutter'
            self.update_status("Remote shutter mode active")
            self.log("Switched to remote shutter mode")
            
            # Update button states
            self.liveview_btn.config(state=tk.NORMAL)
            self.shutter_btn.config(state=tk.DISABLED)
            self.capture_btn.config(state=tk.NORMAL)
            
        except Exception as e:
            self.update_status(f"Error: {e}")
            self.log(f"Error switching to shutter mode: {e}")
    
    def take_picture(self):
        """Take a picture in remote shutter mode"""
        if self.current_mode != 'shutter':
            self.log("Must be in remote shutter mode to take picture")
            return
            
        try:
            self.update_status("Taking picture...")
            self.log("Sending shutter commands...")
            
            # First press
            self.log("1st press...")
            self.camera.send_command('exec_shutter', com='1stpush')
            time.sleep(0.5)
            
            # Second press
            self.log("2nd press...")
            self.camera.send_command('exec_shutter', com='2ndpush')
            time.sleep(1)
            
            # Release
            self.log("Release...")
            self.camera.send_command('exec_shutter', com='2ndrelease')
            time.sleep(0.5)
            self.camera.send_command('exec_shutter', com='1strelease')
            
            self.update_status("Picture taken")
            self.log("Picture captured")
            
        except Exception as e:
            self.update_status(f"Error: {e}")
            self.log(f"Error taking picture: {e}")
    
    def check_for_frames(self):
        """Check for new frames and update display"""
        if self.running:
            try:
                if not self.img_queue.empty():
                    frame = self.img_queue.get_nowait()
                    self.display_frame(frame)
            except queue.Empty:
                pass
        
        # Schedule next check
        self.root.after(33, self.check_for_frames)
    
    def display_frame(self, frame):
        """Display a frame on the canvas"""
        try:
            if frame and frame.jpeg:
                # Convert to image
                image = Image.open(io.BytesIO(frame.jpeg))
                
                # Get canvas size
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                
                if canvas_width > 10 and canvas_height > 10:
                    # Scale image to fit
                    img_width, img_height = image.size
                    scale = min(canvas_width / img_width, canvas_height / img_height)
                    
                    if scale < 1:
                        new_width = int(img_width * scale)
                        new_height = int(img_height * scale)
                        image = image.resize((new_width, new_height), Image.LANCZOS)
                
                # Display
                self.photo = ImageTk.PhotoImage(image)
                self.canvas.delete("all")
                self.canvas.create_image(
                    canvas_width/2, canvas_height/2,
                    image=self.photo,
                    anchor=tk.CENTER
                )
        except Exception as e:
            self.log(f"Error displaying frame: {e}")
    
    def on_close(self):
        """Handle window close"""
        try:
            if self.running:
                self.receiver.shut_down()
                self.camera.stop_liveview()
        except:
            pass
        self.root.destroy()

def main():
    app = RemoteModeTest()
    root = app.setup_ui()
    root.mainloop()

if __name__ == "__main__":
    main()
