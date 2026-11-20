import math

import serial
import time

L1 = 126.2
L2 = 87.9


arduino = serial.Serial(
    port="/dev/cu.wchusbserial110",
    baudrate = 115200,
    timeout = 1
)

def distance_check(x, z):
    distance = math.hypot(x, z)

    if abs(L1-L2)<= distance <= L1 + L2:
        return True
    else:
        return False
    

def ik(x, z):
    cos_theta2 = (x**2 + z**2 - L1**2 - L2**2) / (2 * L1 * L2)
    theta2 = -math.acos(cos_theta2)

    theta1 = math.atan2(z, x) - math.atan2(L2 * math.sin(theta2), L1 + L2 * math.cos(theta2))

    return theta1, theta2

def fk(theta1, theta2):
    x = L1 * math.cos(theta1) + L2 * math.cos(theta1 + theta2)
    z = L1 * math.sin(theta1) + L2 * math.sin(theta1 + theta2)

    return x, z

def servoangle(theta1, theta2):
    angle1 = 180- math.degrees(theta1)
    angle2 = 180+math.degrees(theta2)
    return angle1, angle2

def send_angle(angle1, angle2, gripper):
    message = f"{round(angle1)},{round(angle2)},{round(gripper)}\n"
    arduino.write(message.encode("utf-8"))
    arduino.flush()
    print(f"Sent: {message.strip()}")


def main():

    time.sleep(2)

    try:

        theta1, theta2 = ik(120, 25)
        theta3, theta4 = ik(50, 35)
        angle1, angle2 = servoangle(theta1, theta2)
        angle3, angle4 = servoangle (theta3, theta4)

        if not (0 <= angle1 <= 180 and 0 <= angle2 <= 180):
            print(f"target out of range: {angle1}, {angle2}")
            return
        
        if not (0 <= angle3 <= 180 and 0 <= angle4 <= 180):
            print(f"target out of range: {angle3}, {angle4}")
            return


        send_angle(90, 90, 130)
        time.sleep(2)


        send_angle(angle1, angle2, 130)
        time.sleep(3)


        send_angle(angle1, angle2, 160)
        time.sleep(1)


        send_angle(90, 90, 160)
        time.sleep(3)

        print("grad the object and go back to orginal")

        send_angle(angle3, angle4, 160)
        time.sleep(3)

        send_angle(angle3, angle4, 130)
        time.sleep(3)

        send_angle(90, 90, 130)
        time.sleep(2)
        print("loose, transport done")

    finally:
        arduino.close()


if __name__ == "__main__":
    main()
