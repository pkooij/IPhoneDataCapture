import sys
import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import splprep, splev
import shutil
import time
import threading
from ARKitClient import ARKitClient
from PyQt5.QtWidgets import QApplication, QLineEdit, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox, QLabel
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
import os  # Import the 'os' module


# -------------------------
# Global Variables and State
# -------------------------
recorded_trajectory = []  # List of dicts: {"time": float, "pose": list, "frame": image}
mode = "idle"           # Can be "idle", "recording", or "playback"
is_recording = False

# Playback control variables
playback_running = False
current_playback_time = 0.0
last_update_time = None
total_duration = 0.0
spline_tck = None
x_fine = None
y_fine = None
z_fine = None
times_array = None

# Global variable for ARKit stream display
last_frame = None  # Latest frame received from ARKit

# Global variable for the playback QTimer (set later)
playback_timer = None

# FPS count
frame_count = 0
fps = 0.0
fps_timer_start = time.time()

# Default Export Hz
export_hz = 4

# -------------------------
# ARKit Recording Loop (background thread)
# -------------------------
def arkit_loop():
    global mode, is_recording, recorded_trajectory, last_frame, frame_count
    IPHONE_IP = "192.168.1.21"
    client = ARKitClient(IPHONE_IP)
    print("ARKit loop started. Mode:", mode)
    while mode == "recording":
        try:
            frame, pose, intrinsics, depth = next(client.get_frames())
        except StopIteration:
            break
        last_frame = frame.copy()
        frame_count += 1
        if is_recording:
            recorded_trajectory.append({
                "time": time.time(),
                "pose": pose[:],
                "frame": frame.copy()
            })
    print("ARKit loop ended.")

# -------------------------
# Playback Update Function (invoked by QTimer)
# -------------------------
def updatePlaybackTimer():
    global current_playback_time, last_update_time, total_duration, playback_running, mode, btnTogglePlayback
    if mode != "playback":
        return
    now = time.time()
    if playback_running:
        dt = now - last_update_time
        last_update_time = now
        current_playback_time += dt
        if current_playback_time >= total_duration:
            current_playback_time = total_duration
            playback_running = False
            if playback_timer is not None:
                playback_timer.stop()
            # Reset mode so that playback can be restarted.
            mode = "idle"
            btnTogglePlayback.setText("Start Playback")
            print("Playback finished. Press 'Start Playback' to replay.")
    update_plot()

def set_axes_equal(ax):
    """Set equal scaling with Y-axis upwards clearly."""
    x_limits = ax.get_xlim3d()
    y_limits = ax.get_ylim3d()
    z_limits = ax.get_zlim3d()

    x_range = abs(x_limits[1] - x_limits[0])
    y_range = abs(y_limits[1] - y_limits[0])
    z_range = abs(z_limits[1] - z_limits[0])
    plot_radius = 0.5 * max(x_range, y_range, z_range)

    x_middle = np.mean(x_limits)
    y_middle = np.mean(y_limits)
    z_middle = np.mean(z_limits)

    ax.set_xlim3d([x_middle - plot_radius, x_middle + plot_radius])
    ax.set_ylim3d([y_middle - plot_radius, y_middle + plot_radius])
    ax.set_zlim3d([z_middle - plot_radius, z_middle + plot_radius])

    # Set Y-axis upwards view angle for clarity
    ax.view_init(elev=20, azim=-60)

def export_to_colmap():
    global export_hz
    from scipy.spatial.transform import Rotation as R
    
    if len(recorded_trajectory) < 2:
        print("Not enough frames recorded to export.")
        return
    
    export_dir = "colmap_export"
    images_dir = os.path.join(export_dir, "images")
    sparse_dir = os.path.join(export_dir, "sparse")
    
    # Clear existing images if the directory exists
    if os.path.exists(images_dir):
        shutil.rmtree(images_dir) # remove the whole directory and its content
    
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(sparse_dir, exist_ok=True)
    
    # Compute time interval for sampling
    times = np.array([entry["time"] for entry in recorded_trajectory])
    duration = times[-1] - times[0]
    interval = 1.0 / export_hz  # Convert Hz to time interval
    
    sampled_trajectory = []
    last_sampled_time = times[0]
    for entry in recorded_trajectory:
        if entry["time"] >= last_sampled_time:
            sampled_trajectory.append(entry)
            last_sampled_time += interval
    
    print(f"Exporting {len(sampled_trajectory)} frames at {export_hz} Hz.")
    
    with open(os.path.join(sparse_dir, "cameras.txt"), 'w') as f:
        f.write("# Camera_ID Model Width Height fx fy cx cy\n")
        f.write("1 PINHOLE 1920 1440 1450 1450 960 540\n")
    
    with open(os.path.join(sparse_dir, "images.txt"), "w") as f:
        f.write("# Image_ID qw qx qy qz tx ty tz Camera_ID Name\n")
        for idx, entry in enumerate(sampled_trajectory):
            T = np.array(entry["pose"]).reshape(4,4)
            position = T[:3, 3]
            rotation = R.from_matrix(T[:3, :3])
            qw, qx, qy, qz = rotation.as_quat()
            tx, ty, tz = position
            image_name = f"frame_{idx:04d}.jpg"
            cv2.imwrite(os.path.join(images_dir, image_name), entry["frame"])
            f.write(f"{idx+1} {qw} {qx} {qy} {qz} {tx} {ty} {tz} 1 {image_name}\n")
    
    print("Exported trajectory to COLMAP format successfully!")

# -------------------------
# Update the Matplotlib 3D Plot
# -------------------------
def update_plot():
    global current_playback_time, total_duration, spline_tck, recorded_trajectory, times_array, x_fine, y_fine, z_fine
    if spline_tck is None:
        return

    u_current = np.clip(current_playback_time / total_duration, 0, 1)
    x_cur, y_cur, z_cur = splev(u_current, spline_tck)

    # Convert positions from meters to millimeters
    x_cur_mm, y_cur_mm, z_cur_mm = x_cur * 1000, y_cur * 1000, z_cur * 1000
    x_fine_mm = np.array(x_fine) * 1000
    y_fine_mm = np.array(y_fine) * 1000
    z_fine_mm = np.array(z_fine) * 1000

    # Find the recorded frame closest in time
    idx = np.argmin(np.abs(times_array - current_playback_time))
    entry = recorded_trajectory[idx]
    T = np.array(entry["pose"], dtype=np.float32).reshape(4, 4).T
    R = T[:3, :3]  # Rotation matrix

    # Update the matplotlib 3D plot with Y-axis upwards
    ax.cla()
    
    # Swap axes to set Y as upwards: (X, Z, Y)
    ax.plot(x_fine_mm, z_fine_mm, y_fine_mm, 'b-', label="Smooth Trajectory")
    ax.scatter([x_cur_mm], [z_cur_mm], [y_cur_mm], color='r', s=50, label="Phone Position")

    arrow_length_mm = 20  # Length in mm for visibility
    ax.quiver(x_cur_mm, z_cur_mm, y_cur_mm, R[0,0], R[2,0], R[1,0], length=arrow_length_mm, color='r', normalize=True)
    ax.quiver(x_cur_mm, z_cur_mm, y_cur_mm, R[0,1], R[2,1], R[1,1], length=arrow_length_mm, color='g', normalize=True)
    ax.quiver(x_cur_mm, z_cur_mm, y_cur_mm, R[0,2], R[2,2], R[1,2], length=arrow_length_mm, color='b', normalize=True)

    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Z (mm)")  # original Z axis becomes depth
    ax.set_zlabel("Y (mm) [Up]")  # Y-axis is upwards
    ax.set_title(f"Trajectory Playback (Time: {current_playback_time:.2f} s)")
    ax.legend()

    set_axes_equal(ax)
    plt.draw()

    # Also show the corresponding image in a separate OpenCV window
    cv2.imshow("Playback Image", entry["frame"])
    cv2.waitKey(1)

# -------------------------
# Preprocess Recorded Data for Playback
# -------------------------
def preprocess_recorded_data():
    global times_array, total_duration, spline_tck, x_fine, y_fine, z_fine, recorded_trajectory
    times_array = np.array([entry["time"] for entry in recorded_trajectory])
    t0 = times_array[0]
    times_array = times_array - t0  # Normalize time so first frame is t=0
    total_duration = times_array[-1]
    positions = []
    for entry in recorded_trajectory:
        T = np.array(entry["pose"], dtype=np.float32).reshape(4, 4).T
        pos = T[:3, 3]
        positions.append(pos)
    positions = np.array(positions)
    u_data = times_array / total_duration
    spline_tck, _ = splprep([positions[:,0], positions[:,1], positions[:,2]], u=u_data, s=0)
    # Sample many points along the spline for plotting the smooth trajectory
    u_fine_arr = np.linspace(0, 1, 300)
    global x_fine, y_fine, z_fine  # This line is likely redundant, but doesn't hurt
    x_fine, y_fine, z_fine = splev(u_fine_arr, spline_tck)

# -------------------------
# UI Callback Functions for Recording and Playback
# -------------------------
def start_recording_callback():
    global mode, is_recording, recorded_trajectory
    if mode != "recording":
        print("Starting recording...")
        recorded_trajectory = []  # Clear previous recording data
        mode = "recording"
        is_recording = True
        threading.Thread(target=arkit_loop, daemon=True).start()

def stop_recording_callback():
    global is_recording, mode
    if mode == "recording":
        is_recording = False
        mode = "idle"
        print("Recording stopped. {} frames recorded.".format(len(recorded_trajectory)))

# Callback Function for Export Button
def export_to_colmap_callback():
    preprocess_recorded_data()
    export_to_colmap()
    print("COLMAP export completed.")

def toggle_playback_callback():
    global mode, playback_running, last_update_time, playback_timer, current_playback_time, btnTogglePlayback
    if mode != "playback":
        # If not in playback mode, start playback.
        if len(recorded_trajectory) < 2:
            print("Not enough data recorded for playback.")
            return
        preprocess_recorded_data()
        mode = "playback"
        playback_running = True
        current_playback_time = 0.0
        last_update_time = time.time()
        if playback_timer is not None:
            playback_timer.start(30)  # Start the playback timer at ~33 Hz
        btnTogglePlayback.setText("Pause Playback")
        print("Playback started.")
    else:
        # Mode is playback; toggle pause/resume.
        if playback_running:
            # Pause playback.
            playback_running = False
            if playback_timer is not None:
                playback_timer.stop()
            btnTogglePlayback.setText("Resume Playback")
            print("Playback paused.")
        else:
            # Resume playback.
            playback_running = True
            last_update_time = time.time()
            if playback_timer is not None:
                playback_timer.start(30)
            btnTogglePlayback.setText("Pause Playback")
            print("Playback resumed.")

# -------------------------
# Setup Matplotlib Figure for Playback
# -------------------------
plt.ion()  # Turn on interactive mode for matplotlib
fig = plt.figure("Trajectory Playback")
ax = fig.add_subplot(111, projection='3d')

# -------------------------
# PyQt5 UI: Main Window with Physical Buttons and ARKit Stream Display
# -------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ARKit Recorder & Player Controls")
        self.setupUI()
        # Timer for updating the ARKit stream display
        self.streamTimer = QTimer()
        self.streamTimer.timeout.connect(self.updateArkitStream)
        self.streamTimer.start(1)  # Update as fast as possible (~100Hz)
        # Create the global playback_timer
        global playback_timer
        playback_timer = QTimer()
        playback_timer.timeout.connect(updatePlaybackTimer)

    def setupUI(self):
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        layout = QVBoxLayout()
        centralWidget.setLayout(layout)

        # ARKit Stream Display
        self.streamLabel = QLabel("ARKit Stream")
        self.streamLabel.setAlignment(Qt.AlignCenter)
        self.streamLabel.setFixedSize(640, 480)
        layout.addWidget(self.streamLabel)

        # FPS Label
        self.fpsLabel = QLabel("FPS: 0.0")
        self.fpsLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.fpsLabel)

        # Recording Controls
        recGroup = QGroupBox("Recording Controls")
        recLayout = QHBoxLayout()
        recGroup.setLayout(recLayout)
        self.btnStartRecord = QPushButton("Start Recording")
        self.btnStopRecord = QPushButton("Stop Recording")
        recLayout.addWidget(self.btnStartRecord)
        recLayout.addWidget(self.btnStopRecord)
        layout.addWidget(recGroup)

        # Playback Controls
        playGroup = QGroupBox("Playback Controls")
        playLayout = QHBoxLayout()
        playGroup.setLayout(playLayout)
        global btnTogglePlayback
        btnTogglePlayback = QPushButton("Start Playback")
        playLayout.addWidget(btnTogglePlayback)
        layout.addWidget(playGroup)

        # **Export to COLMAP Button**
        exportGroup = QGroupBox("Export")
        exportLayout = QHBoxLayout()
        exportGroup.setLayout(exportLayout)
        self.btnExportColmap = QPushButton("Export to COLMAP")
        exportLayout.addWidget(self.btnExportColmap)
        layout.addWidget(exportGroup)

        # Hz Input
        hzLayout = QHBoxLayout()
        hzLabel = QLabel("Export Hz (2-4 Hz recommended):")
        self.export_hz_input = QLineEdit(str(export_hz))  # Corrected: Added 'self.'
        hzLayout.addWidget(hzLabel)
        hzLayout.addWidget(self.export_hz_input) # Corrected: Added 'self.'
        layout.addLayout(hzLayout)

        # Connect button signals to callbacks
        self.btnStartRecord.clicked.connect(start_recording_callback)
        self.btnStopRecord.clicked.connect(stop_recording_callback)
        btnTogglePlayback.clicked.connect(toggle_playback_callback)
        self.btnExportColmap.clicked.connect(self.export_colmap_callback)

    def export_colmap_callback(self):
        self.set_export_hz()  # Update export Hz before exporting
        export_to_colmap()

    def set_export_hz(self):  # Moved inside the class
        global export_hz
        try:
            new_hz = int(self.export_hz_input.text())
            if 1 <= new_hz <= 50:
                export_hz = new_hz
                print(f"Export Hz set to: {export_hz} Hz")
            else:
                print("Please enter a value between 1 and 50 Hz.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    def updateArkitStream(self):
        global last_frame, fps, frame_count, fps_timer_start
        if last_frame is not None:
            rgb_frame = cv2.cvtColor(last_frame, cv2.COLOR_BGR2RGB)
            height, width, channel = rgb_frame.shape
            bytesPerLine = 3 * width
            qImg = QImage(rgb_frame.data, width, height, bytesPerLine, QImage.Format_RGB888)
            self.streamLabel.setPixmap(QPixmap.fromImage(qImg).scaled(self.streamLabel.size(), Qt.KeepAspectRatio))

            # FPS calculation (every second)
            elapsed = time.time() - fps_timer_start
            if elapsed >= 1.0:
                fps = frame_count / elapsed
                frame_count = 0
                fps_timer_start = time.time()
                self.fpsLabel.setText(f"FPS: {fps:.1f}")

    def export_colmap_callback(self):
        self.set_export_hz()  # Update export Hz before exporting
        export_to_colmap()

    def set_axes_equal(ax):
        """Set 3D plot axes to equal scale so that spheres appear as spheres and lines are not distorted."""
        x_limits = ax.get_xlim3d()
        y_limits = ax.get_ylim3d()
        z_limits = ax.get_zlim3d()

        x_range = abs(x_limits[1] - x_limits[0])
        y_range = abs(y_limits[1] - y_limits[0])
        z_range = abs(z_limits[1] - z_limits[0])
        plot_radius = 0.5 * max(x_range, y_range, z_range)

        x_middle = np.mean(x_limits)
        y_middle = np.mean(y_limits)
        z_middle = np.mean(z_limits)
        
        ax.set_xlim3d([x_middle - plot_radius, x_middle + plot_radius])
        ax.set_ylim3d([y_middle - plot_radius, y_middle + plot_radius])
        ax.set_zlim3d([z_middle - plot_radius, z_middle + plot_radius])


# -------------------------
# Main Application Startup
# -------------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    exit_code = app.exec_()
    
    # Cleanup on exit
    cv2.destroyAllWindows()
    plt.ioff()
    plt.show()
    print("Program finished.")
    sys.exit(exit_code)
