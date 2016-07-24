import RPi.GPIO as GPIO
import sys


#setup GPIO using Board numbering (pins, not GPIOs)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(31, GPIO.OUT, initial=0)
GPIO.setup(33, GPIO.OUT, initial=0)


def set_to_on():
    print("ON")
    GPIO.output(31, 1)
    GPIO.output(33, 1)

def set_to_off():
    print("OFF")
    GPIO.output(31, 0)
    GPIO.output(33, 0)

if len(sys.argv) > 1:
    befehl = sys.argv[1]
    if befehl == "on":
        print("los gehts")
        set_to_on()
    else:
        print("Ausschalten")
        set_to_off()
else:
    print("Uebergeben Sie ein Argument ! (on / off)")



