import time

import cv2
import numpy as np
from picamera2 import Picamera2

from camera_mount import MotorController


# ============================================================
# CAMERA AND DISPLAY SETTINGS
# ============================================================

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_RATE = 30
SHOW_WINDOWS = True


# ============================================================
# TRACKING SETTINGS
# ============================================================

DEAD_ZONE = 60
MINIMUM_AREA = 500.0

# Proportional gain. The controller output is treated as degrees/second.
KP = 0.03
MAX_SERVO_SPEED = 10.0
MAXIMUM_DT = 0.10

SMOOTHING_ALPHA = 0.2
TARGET_HOLD_TIME = 1.0

# Change either value to -1.0 if that servo moves away from the target.
PAN_DIRECTION = -1.0
TILT_DIRECTION = 1.0

# This HSV range is yellow/green-yellow, suitable for an initial tennis-ball
# or brightly colored target test. It is not a blue range.
LOWER_TARGET_COLOR = np.array([85, 40, 80], dtype=np.uint8)
UPPER_TARGET_COLOR = np.array([130, 255, 255], dtype=np.uint8)

NOISE_KERNEL = np.ones((5, 5), dtype=np.uint8)


# ============================================================
# IMAGE-PROCESSING FUNCTIONS
# ============================================================

def create_target_mask(frame: np.ndarray) -> np.ndarray:
    """Creates a cleaned binary mask for the configured HSV target color."""
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    target_mask = cv2.inRange(
        hsv_frame,
        LOWER_TARGET_COLOR,
        UPPER_TARGET_COLOR,
    )

    target_mask = cv2.morphologyEx(
        target_mask,
        cv2.MORPH_OPEN,
        NOISE_KERNEL,
    )
    target_mask = cv2.morphologyEx(
        target_mask,
        cv2.MORPH_CLOSE,
        NOISE_KERNEL,
    )

    return target_mask


def find_target(target_mask: np.ndarray):
    """Returns x, y, width, height, and area for the largest valid target."""
    contours, _ = cv2.findContours(
        target_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if not contours:
        return None

    largest_contour = max(contours, key=cv2.contourArea)
    area = float(cv2.contourArea(largest_contour))

    if area <= MINIMUM_AREA:
        return None

    x, y, width, height = cv2.boundingRect(largest_contour)
    return x, y, width, height, area


def smooth_position(
    object_center_x: int,
    object_center_y: int,
    previous_smoothed_x: float | None,
    previous_smoothed_y: float | None,
):
    """Applies exponential smoothing to the detected target center."""
    if previous_smoothed_x is None or previous_smoothed_y is None:
        smoothed_x = float(object_center_x)
        smoothed_y = float(object_center_y)
    else:
        smoothed_x = (
            SMOOTHING_ALPHA * object_center_x
            + (1.0 - SMOOTHING_ALPHA) * previous_smoothed_x
        )
        smoothed_y = (
            SMOOTHING_ALPHA * object_center_y
            + (1.0 - SMOOTHING_ALPHA) * previous_smoothed_y
        )

    return smoothed_x, smoothed_y, int(smoothed_x), int(smoothed_y)


def calculate_controller(
    tracked_x: int,
    tracked_y: int,
    screen_center_x: int,
    screen_center_y: int,
):
    """Calculates tracking errors and requested servo speeds."""
    error_x = tracked_x - screen_center_x
    error_y = tracked_y - screen_center_y

    pan_speed = 0.0
    tilt_speed = 0.0

    if abs(error_x) > DEAD_ZONE:
        pan_speed = PAN_DIRECTION * KP * error_x

    if abs(error_y) > DEAD_ZONE:
        tilt_speed = TILT_DIRECTION * KP * error_y

    pan_speed = float(np.clip(
        pan_speed,
        -MAX_SERVO_SPEED,
        MAX_SERVO_SPEED,
    ))
    tilt_speed = float(np.clip(
        tilt_speed,
        -MAX_SERVO_SPEED,
        MAX_SERVO_SPEED,
    ))

    return error_x, error_y, pan_speed, tilt_speed


def update_servo_angles(
    pan_angle: float,
    tilt_angle: float,
    pan_speed: float,
    tilt_speed: float,
    dt: float,
):
    """Integrates servo speed commands over the elapsed frame time."""
    safe_dt = min(max(dt, 0.0), MAXIMUM_DT)
    return (
        pan_angle + pan_speed * safe_dt,
        tilt_angle + tilt_speed * safe_dt,
    )


def determine_tracking_status(
    target_detected: bool,
    last_seen_time: float | None,
    current_time: float,
):
    if target_detected:
        return "TRACKING", (0, 255, 0), False

    if (
        last_seen_time is not None
        and current_time - last_seen_time <= TARGET_HOLD_TIME
    ):
        return "TARGET TEMPORARILY LOST", (0, 255, 255), False

    return "TARGET LOST", (0, 0, 255), True


# ============================================================
# DRAWING FUNCTIONS
# ============================================================

def draw_screen_guides(
    frame: np.ndarray,
    screen_center_x: int,
    screen_center_y: int,
) -> None:
    cv2.circle(
        frame,
        (screen_center_x, screen_center_y),
        5,
        (255, 0, 0),
        -1,
    )
    cv2.rectangle(
        frame,
        (
            screen_center_x - DEAD_ZONE,
            screen_center_y - DEAD_ZONE,
        ),
        (
            screen_center_x + DEAD_ZONE,
            screen_center_y + DEAD_ZONE,
        ),
        (255, 255, 255),
        1,
    )


def draw_target(
    frame: np.ndarray,
    x: int,
    y: int,
    width: int,
    height: int,
    tracked_x: int,
    tracked_y: int,
    screen_center_x: int,
    screen_center_y: int,
) -> None:
    cv2.rectangle(
        frame,
        (x, y),
        (x + width, y + height),
        (0, 255, 0),
        2,
    )
    cv2.circle(frame, (tracked_x, tracked_y), 5, (0, 0, 255), -1)
    cv2.line(
        frame,
        (screen_center_x, screen_center_y),
        (tracked_x, tracked_y),
        (0, 255, 255),
        1,
    )


def draw_information(
    frame: np.ndarray,
    tracking_status: str,
    status_color: tuple[int, int, int],
    pan_angle: float,
    tilt_angle: float,
) -> None:
    cv2.putText(
        frame,
        tracking_status,
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        status_color,
        2,
    )
    cv2.putText(
        frame,
        f"Pan angle: {pan_angle:.1f}",
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 255),
        2,
    )
    cv2.putText(
        frame,
        f"Tilt angle: {tilt_angle:.1f}",
        (20, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 255),
        2,
    )


# ============================================================
# HARDWARE SETUP
# ============================================================

def create_camera() -> Picamera2:
    """Configures a ribbon-cable Raspberry Pi camera for OpenCV."""
    camera = Picamera2()

    configuration = camera.create_video_configuration(
        main={
            "size": (FRAME_WIDTH, FRAME_HEIGHT),
            # Picamera2's RGB888 stream is ordered for OpenCV BGR use.
            "format": "RGB888",
        },
        controls={"FrameRate": FRAME_RATE},
        buffer_count=4,
    )

    camera.configure(configuration)
    camera.start()

    # Allow automatic exposure and white balance to settle.
    time.sleep(1.0)
    return camera


# ============================================================
# MAIN PROGRAM
# ============================================================

def main() -> None:
    camera: Picamera2 | None = None
    camera_mount: MotorController | None = None

    try:
        camera_mount = MotorController()
        camera = create_camera()

        smoothed_x = None
        smoothed_y = None

        pan_angle = camera_mount.pan_angle
        tilt_angle = camera_mount.tilt_angle

        previous_time = time.perf_counter()
        last_seen_time = None

        while True:
            frame = camera.capture_array("main")

            if frame is None:
                print("The camera frame could not be read.")
                break

            current_time = time.perf_counter()
            dt = current_time - previous_time
            previous_time = current_time

            frame_height, frame_width = frame.shape[:2]
            screen_center_x = frame_width // 2
            screen_center_y = frame_height // 2

            target_detected = False
            draw_screen_guides(frame, screen_center_x, screen_center_y)

            target_mask = create_target_mask(frame)
            target = find_target(target_mask)

            if target is not None:
                target_detected = True
                last_seen_time = current_time

                x, y, width, height, area = target
                object_center_x = x + width // 2
                object_center_y = y + height // 2

                (
                    smoothed_x,
                    smoothed_y,
                    tracked_x,
                    tracked_y,
                ) = smooth_position(
                    object_center_x,
                    object_center_y,
                    smoothed_x,
                    smoothed_y,
                )

                (
                    error_x,
                    error_y,
                    pan_speed,
                    tilt_speed,
                ) = calculate_controller(
                    tracked_x,
                    tracked_y,
                    screen_center_x,
                    screen_center_y,
                )

                requested_pan, requested_tilt = update_servo_angles(
                    pan_angle,
                    tilt_angle,
                    pan_speed,
                    tilt_speed,
                    dt,
                )

                pan_angle = camera_mount.set_pan_angle(requested_pan)
                tilt_angle = camera_mount.set_tilt_angle(requested_tilt)

                draw_target(
                    frame,
                    x,
                    y,
                    width,
                    height,
                    tracked_x,
                    tracked_y,
                    screen_center_x,
                    screen_center_y,
                )

                print(
                    f"Area: {area:7.1f} | "
                    f"Error X: {error_x:4d} | "
                    f"Error Y: {error_y:4d} | "
                    f"Pan: {pan_angle:6.2f} | "
                    f"Tilt: {tilt_angle:6.2f}"
                )

            (
                tracking_status,
                status_color,
                target_fully_lost,
            ) = determine_tracking_status(
                target_detected,
                last_seen_time,
                current_time,
            )

            if target_fully_lost:
                smoothed_x = None
                smoothed_y = None

            draw_information(
                frame,
                tracking_status,
                status_color,
                pan_angle,
                tilt_angle,
            )

            if SHOW_WINDOWS:
                cv2.imshow("Camera Tracker", frame)
                cv2.imshow("Target Mask", target_mask)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        print("\nTracking stopped.")

    finally:
        if camera is not None:
            camera.stop()
            camera.close()

        cv2.destroyAllWindows()

        if camera_mount is not None:
            camera_mount.cleanup()


if __name__ == "__main__":
    main()
