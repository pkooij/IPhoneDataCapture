import socket, struct, json, cv2, numpy as np

class ARKitClient:
    def __init__(self, ip, port=5555):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((ip, port))
        print(f"Connected to iPhone at {ip}:{port}")

    def recv_exact(self, length):
        data = b''
        while len(data) < length:
            packet = self.sock.recv(length - len(data))
            if not packet:
                return None
            data += packet
        return data

    def get_frames(self):
        while True:
            json_length = struct.unpack('i', self.recv_exact(4))[0]
            json_data = json.loads(self.recv_exact(json_length))

            # Parse out transform & intrinsics
            pose = json_data["transform"]       # 16 floats
            intrinsics = json_data["intrinsics"]  # 9 floats

            jpeg_length = struct.unpack('i', self.recv_exact(4))[0]
            frame_data = self.recv_exact(jpeg_length)
            frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)

            # Depth data (if any)
            depth_length = struct.unpack('i', self.recv_exact(4))[0]
            if depth_length > 0:
                depth_data = self.recv_exact(depth_length)
                width = json_data.get('depthWidth', 256)
                height = json_data.get('depthHeight', 192)
                depth = np.frombuffer(depth_data, dtype=np.float32).reshape((height, width))
            else:
                depth = None

            yield frame, pose, intrinsics, depth
