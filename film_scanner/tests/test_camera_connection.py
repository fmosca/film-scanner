import os
import http.client
import subprocess

import pytest

class TestCameraConnection:
    @pytest.fixture(scope="class")
    def camera_ip(self):
        """Fixture to provide camera IP address"""
        return "192.168.0.10"

    def test_ping_camera(self, camera_ip):
        """Test that the camera responds to ping"""
        response = os.system(f"ping -c 1 {camera_ip}")
        assert response == 0, f"Ping to {camera_ip} failed"

    def test_curl_camera(self, camera_ip):
        """Test camera endpoint using curl, verifying 200 status code"""
        # Use subprocess.run for better output handling
        curl_cmd = [
            'curl',
            '-s',
            '-o', '/dev/null',
            '-w', '%{http_code}',
            f'http://{camera_ip}/get_commandlist.cgi'
        ]

        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True
        )
        assert result.stdout.strip() == '200', \
            f"Expected HTTP 200 status code, got {result.stdout.strip()}"


    def test_plain_python_http_call(self, camera_ip):
        """Test HTTP connection using Python's http.client"""
        url = f"/get_commandlist.cgi"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            conn = http.client.HTTPConnection(camera_ip)
            conn.request("GET", url, headers=headers)
            response = conn.getresponse()
            data = response.read()
            conn.close()

            assert response.status == 200, f"HTTP status code is not 200, got {response.status}"
            print("Connection successful:", data.decode())
        except Exception as e:
            pytest.fail(f"Failed to connect to the camera: {e}")

# Optional: If you want to run this directly
if __name__ == '__main__':
    pytest.main([__file__, '-v'])