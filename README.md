# Raspberry Pi Color-Tracking Camera

A Raspberry Pi 5 camera system that detects a selected color with OpenCV and automatically moves a two-axis pan-and-tilt mount to keep the object near the center of the frame.

## What it does

- Captures live video with a Raspberry Pi camera
- Isolates a target color using HSV thresholds
- Filters small areas of image noise
- Finds the largest matching object
- Moves pan and tilt servos through a PCA9685 controller
- Keeps servo motion inside configurable safety limits
- Optionally displays the live camera feed, mask, and tracking marker

## Hardware

- Raspberry Pi 5
- Raspberry Pi Camera Module
- Two-servo pan-and-tilt camera mount
- PCA9685 16-channel servo driver
- Separate regulated 5–6 V servo power supply
- Jumper wires

> Do not power the servos directly from the Raspberry Pi. Connect the external servo supply ground to the Raspberry Pi/PCA9685 ground.

### Default wiring

| Raspberry Pi / supply | PCA9685 |
|---|---|
| 3.3 V | VCC |
| GPIO 2 / SDA (pin 3) | SDA |
| GPIO 3 / SCL (pin 5) | SCL |
| Ground (pin 6) | GND |
| External 5–6 V positive | V+ |
| External supply ground | GND |

The code uses PCA9685 channel `0` for pan and channel `1` for tilt.

## Raspberry Pi setup

Enable I2C:

```bash
sudo raspi-config
```

Select **Interface Options → I2C → Enable**, then reboot.

Install the camera and OpenCV packages:

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-opencv python3-venv i2c-tools
```

Create an environment that can access the Raspberry Pi system packages:

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Confirm that the camera and servo board are detected:

```bash
rpicam-hello --timeout 3000
i2cdetect -y 1
```

The PCA9685 normally appears at address `40`.

## Run the tracker

The default HSV range targets many bright green objects:

```bash
python -m src.main --show
```

Press `q` to stop. You can also stop with `Ctrl+C`.

To track a different color, pass its lower and upper HSV limits:

```bash
python -m src.main --lower-hsv 20,100,100 --upper-hsv 35,255,255 --show
```

OpenCV uses:

- Hue: `0–179`
- Saturation: `0–255`
- Value: `0–255`

Useful starting hue ranges:

| Color | Lower HSV | Upper HSV |
|---|---:|---:|
| Green | `35,80,80` | `85,255,255` |
| Yellow | `20,100,100` | `35,255,255` |
| Blue | `90,80,70` | `130,255,255` |

Lighting changes the ideal thresholds, so these values will usually need calibration.

## Project structure

```text
Camera_Tracking_System/
├── src/
│   ├── color_tracker.py
│   ├── main.py
│   └── motor_controller.py
├── .gitignore
├── README.md
└── requirements.txt
```

## Adjustable settings

The main command supports:

- `--pan-channel` and `--tilt-channel`
- `--min-angle` and `--max-angle`
- `--pan-gain` and `--tilt-gain`
- `--dead-zone`
- `--min-area`
- `--invert-pan` and `--invert-tilt`
- `--lower-hsv` and `--upper-hsv`

Run `python -m src.main --help` to see every option.

## Development status

This is an early hardware prototype. Before increasing the tracking speed, confirm the servo directions and safe mechanical angle limits for the specific mount.
