import os
import http.client
import unittest

import pytest

class TestCameraConnection(unittest.TestCase):
    def setUp(self):
        self.camera_ip = "192.168.0.10"

    def test_ping_camera(self):
        response = os.system(f"ping -c 1 {self.camera_ip}")
        self.assertEqual(response, 0)

    def test_ping_camera(self):
        response = os.system(f"ping -c 1 {self.camera_ip}")
        self.assertEqual(response, 0)


    def test_curl_camera(self):
        response = os.system(f"curl -s -o /dev/null -w '%{{http_code}}' http://{self.camera_ip}/get_commandlist.cgi")
        self.assertEqual(response, 200)

    def test_plain_python_http_call(self):
        url = f"http://{self.camera_ip}/get_commandlist.cgi"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            conn = http.client.HTTPConnection(self.camera_ip)
            conn.request("GET", url, headers=headers)
            response = conn.getresponse()
            data = response.read()
            conn.close()

            assert response.status == 200
            print("Connection successful:", data.decode())
        except Exception as e:
            pytest.fail(f"Failed to connect to the camera: {e}")

if __name__ == '__main__':
    pytest.main()