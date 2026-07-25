Raspberry Pi Color-Tracking Camera

A Raspberry Pi 5 camera system that detects a selected color with OpenCV and moves a two-axis pan-and-tilt camera mount to keep the target near the center of the frame.

Current features

Captures live video using Picamera2

Converts each frame to HSV color space

Creates and cleans a target-color mask

Finds the largest valid target

Smooths the detected target position

Uses proportional control to move the pan and tilt servos

Controls two servos through a PCA9685 board

Limits servo angles and movement speed for safer testing

Displays the camera view, target mask, tracking status, and servo angles

Releases the camera and servos during shutdown

Project structure

Camera_Tracking_System/
├── track_ObjectV1.py
├── camera_mount.py
├── README.md
└── .gitignore

track_ObjectV1.py contains the camera, OpenCV, target detection, and tracking loop.

camera_mount.py contains the MotorController class for the pan and tilt servos.

Hardware

Raspberry Pi 5

Raspberry Pi Camera Module

Two-servo pan-and-tilt camera mount

PCA9685 16-channel servo driver

Separate regulated 5–6 V servo power supply

Jumper wires

Do not power both servos directly from the Raspberry Pi. Power the servos through the PCA9685 V+ terminal using a suitable external supply, and connect the external supply ground to the Raspberry Pi/PCA9685 ground.

Default PCA9685 wiring

Raspberry Pi or supply

PCA9685

3.3 V

VCC

GPIO 2 / SDA, physical pin 3

SDA

GPIO 3 / SCL, physical pin 5

SCL

Raspberry Pi ground

GND

External 5–6 V positive

V+

External supply ground

GND

The current code uses:

PCA9685 channel 0 for pan

PCA9685 channel 1 for tilt

PCA9685 I2C address 0x40

Raspberry Pi setup

Update the Raspberry Pi and install the required system packages:

sudo apt update
sudo apt full-upgrade -y
sudo apt install -y git python3-picamera2 python3-opencv python3-numpy python3-venv i2c-tools

Enable I2C:

sudo raspi-config nonint do_i2c 0
sudo reboot

After the Raspberry Pi restarts, clone the repository:

mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/GKrow02/Camera_Tracking_System.git
cd Camera_Tracking_System

Create a virtual environment that can access Raspberry Pi system packages:

python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install adafruit-circuitpython-servokit

Test the hardware

Test the Raspberry Pi camera:

rpicam-hello --timeout 5000

Check that the PCA9685 is detected:

i2cdetect -y 1

The PCA9685 will normally appear as 40 in the I2C table.

Run the tracker

Activate the virtual environment:

cd ~/Projects/Camera_Tracking_System
source .venv/bin/activate

Run the program:

python3 track_ObjectV1.py

Press q inside the video window to stop. You can also stop the program with Ctrl+C.

Current target color

The current HSV range is:

LOWER_TARGET_COLOR = np.array([20, 80, 120], dtype=np.uint8)
UPPER_TARGET_COLOR = np.array([40, 255, 255], dtype=np.uint8)

This range targets yellow to yellow-green objects and is suitable as a starting point for testing with a bright tennis ball. Lighting conditions will affect the ideal values.

OpenCV HSV ranges are:

Hue: 0–179

Saturation: 0–255

Value: 0–255

Important settings

The main settings are near the top of track_ObjectV1.py:

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_RATE = 30
SHOW_WINDOWS = True

DEAD_ZONE = 60
MINIMUM_AREA = 500.0
KP = 0.03
MAX_SERVO_SPEED = 45.0
SMOOTHING_ALPHA = 0.2

PAN_DIRECTION = 1.0
TILT_DIRECTION = 1.0

If one servo moves the camera away from the target, change that axis direction from 1.0 to -1.0.

For example:

PAN_DIRECTION = -1.0

Servo safety limits

The default limits in camera_mount.py are:

pan_min_angle = 10.0
pan_max_angle = 170.0
tilt_min_angle = 20.0
tilt_max_angle = 160.0

These are conservative starting values. Test each axis slowly and reduce the limits if the mount reaches a physical stop, strains, or buzzes.

Running without a desktop display

When using SSH without a monitor, change this setting in track_ObjectV1.py:

SHOW_WINDOWS = False

Then stop the program with Ctrl+C.

Development status

This is an early hardware prototype. The next steps are hardware testing, servo-direction calibration, safe-angle calibration, HSV tuning, and controller tuning on the Raspberry Pi.

## Development status

This is an early hardware prototype. Before increasing the tracking speed, confirm the servo directions and safe mechanical angle limits for the specific mount.
