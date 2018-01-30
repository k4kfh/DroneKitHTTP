#!/usr/bin/python

import dronekit
import time

vehicle = dronekit.connect("udpout:10.1.1.10:14560", status_printer=None, wait_ready=True)
lastHeading = 0
lastTime = 0
currentHeading = 0
currentTime = 0
timeElapsed = 0

lastHeading = vehicle.heading
lastTime = time.time()

currentHeading = vehicle.heading
currentTime = time.time()

while True:
    currentHeading = vehicle.heading
    currentTime = time.time()
    if (lastHeading is not currentHeading):
        timeElapsed = currentTime - lastTime
        print(timeElapsed)
    lastHeading = currentHeading
    lastTime = currentTime
