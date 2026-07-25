import math

from adafruit_servokit import ServoKit


class MotorController:
    """Controls the pan and tilt servos through a PCA9685 board."""

    def __init__(
        self,
        pan_channel: int = 1,
        tilt_channel: int = 0,
        pan_min_angle: float = -360,
        pan_max_angle: float = 360,
        tilt_min_angle: float = -180,
        tilt_max_angle: float = 180,
        start_pan_angle: float = 0,
        start_tilt_angle: float = 0,
        i2c_address: int = 0x40,
    ) -> None:
        if pan_min_angle >= pan_max_angle:
            raise ValueError("pan_min_angle must be less than pan_max_angle.")
        if tilt_min_angle >= tilt_max_angle:
            raise ValueError("tilt_min_angle must be less than tilt_max_angle.")

        self.pan_min_angle = float(pan_min_angle)
        self.pan_max_angle = float(pan_max_angle)
        self.tilt_min_angle = float(tilt_min_angle)
        self.tilt_max_angle = float(tilt_max_angle)

        self.driver = ServoKit(channels=16, address=i2c_address)
        self.pan_servo = self.driver.servo[pan_channel]
        self.tilt_servo = self.driver.servo[tilt_channel]

        # Leave the default pulse-width calibration until the exact servo
        # model is known and its safe mechanical range has been tested.
        self.pan_servo.actuation_range = 180
        self.tilt_servo.actuation_range = 180

        self.pan_angle = self._clamp_angle(
            start_pan_angle,
            self.pan_min_angle,
            self.pan_max_angle,
            "pan",
        )
        self.tilt_angle = self._clamp_angle(
            start_tilt_angle,
            self.tilt_min_angle,
            self.tilt_max_angle,
            "tilt",
        )

        self.pan_servo.angle = self.pan_angle
        self.tilt_servo.angle = self.tilt_angle

    @staticmethod
    def _clamp_angle(
        angle: float,
        minimum: float,
        maximum: float,
        axis_name: str,
    ) -> float:
        angle = float(angle)

        if not math.isfinite(angle):
            raise ValueError(f"{axis_name} angle must be a finite number.")

        return max(minimum, min(maximum, angle))

    def set_pan_angle(self, angle: float) -> float:
        self.pan_angle = self._clamp_angle(
            angle,
            self.pan_min_angle,
            self.pan_max_angle,
            "pan",
        )
        self.pan_servo.angle = self.pan_angle
        return self.pan_angle

    def set_tilt_angle(self, angle: float) -> float:
        self.tilt_angle = self._clamp_angle(
            angle,
            self.tilt_min_angle,
            self.tilt_max_angle,
            "tilt",
        )
        self.tilt_servo.angle = self.tilt_angle
        return self.tilt_angle

    def cleanup(self) -> None:
        """Stops sending servo pulses."""
        self.pan_servo.angle = None
        self.tilt_servo.angle = None
