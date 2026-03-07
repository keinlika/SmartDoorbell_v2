from gpiozero import MotionSensor
from signal import pause

# Standard PIR on Pin 17
pir = MotionSensor(17)

def motion_detected():
    print(">>> MOTION SEEN! <<<")

def motion_stopped():
    print("... motion ended ...")

print("Sensor Active. Wave your hand.")

# These "Events" run instantly, no loop needed
pir.when_motion = motion_detected
pir.when_no_motion = motion_stopped

pause()
