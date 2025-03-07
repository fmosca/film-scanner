#!/usr/bin/env python3
"""
Script to download a screennail directly via HTTP from an Olympus camera.
"""
import io
import sys
import time
import requests
from PIL import Image
from olympuswifi.camera import OlympusCamera  # Only used for listing images

def get_screennail_direct():
    """Connect to camera and get a screennail using direct HTTP requests."""
    try:
        # Camera API constants
        CAMERA_IP = "192.168.0.10"
        BASE_URL = f"http://{CAMERA_IP}"
        HEADERS = {
            "User-Agent": "OlympusCameraKit",
            "Accept": "*/*"
        }
        
        # Initialize camera just for listing images
        print("Connecting to camera...")
        camera = OlympusCamera()
        
        # Switch to playback mode
        print("Switching to playback mode...")
        requests.get(f"{BASE_URL}/switch_cammode.cgi?mode=play", headers=HEADERS)
        time.sleep(1)  # Short pause to ensure mode switch completes
        
        # List images using the library
        print("Listing images...")
        images = list(camera.list_images(dir='/DCIM/100OLYMP'))
        if not images:
            print("Error: No images found on camera.")
            return False
        
        # Get the last image
        last_image = images[-1]
        print(f"Selected image: {last_image.file_name}")
        
        # Construct URLs for different image types
        image_path = last_image.file_name
        thumbnail_url = f"{BASE_URL}/get_thumbnail.cgi?DIR={image_path}"
        screennail_url = f"{BASE_URL}/get_screennail.cgi?DIR={image_path}"
        full_image_url = f"{BASE_URL}{image_path}"
        
        # Try to download the screennail
        print(f"Downloading screennail via direct HTTP request...")
        print(f"URL: {screennail_url}")
        response = requests.get(screennail_url, headers=HEADERS)
        
        if response.status_code == 200:
            # Process the image data
            screennail_data = response.content
            
            try:
                image = Image.open(io.BytesIO(screennail_data))
                width, height = image.size
                print(f"\nScreennail Dimensions: {width} × {height} pixels")
                print(f"Image Format: {image.format}")
                print(f"Mode: {image.mode}")
                print(f"Data Size: {len(screennail_data)} bytes")
                
                # Save the screennail for inspection
                output_file = "screennail_direct.jpg"
                image.save(output_file)
                print(f"Saved screennail to: {output_file}")
                
                # Now try to get thumbnail for comparison
                print("\nDownloading thumbnail for comparison...")
                thumb_response = requests.get(thumbnail_url, headers=HEADERS)
                if thumb_response.status_code == 200:
                    thumb_image = Image.open(io.BytesIO(thumb_response.content))
                    print(f"Thumbnail Dimensions: {thumb_image.size[0]} × {thumb_image.size[1]} pixels")
                    print(f"Thumbnail Data Size: {len(thumb_response.content)} bytes")
                    thumb_image.save("thumbnail_direct.jpg")
                    print(f"Saved thumbnail to: thumbnail_direct.jpg")
                
                return True
            except Exception as e:
                print(f"Error processing image: {e}")
                return False
        else:
            print(f"Error: HTTP status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Olympus Screennail Direct HTTP Request")
    print("=====================================")
    
    # Ensure camera is connected to WiFi before running
    print("Make sure your computer is connected to the camera's WiFi network.")
    input("Press Enter to continue...")
    
    success = get_screennail_direct()
    sys.exit(0 if success else 1)