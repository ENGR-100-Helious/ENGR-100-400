import math

import serial


L1 = 126.2
L2 = 87.9


arduino = serial.Serial(
    port="/dev/cu.wchusbserial10",
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



def send_angle(angle1, angle2):
    message = f"{round(angle1)},{round(angle2)},140\n"
    data = message.encode("utf-8")
    arduino.write(data)
    print(f"Sending:{message}")


def main():
    try:
        x = float(input("Enter x: "))
        z = float(input("Enter z: "))
    except ValueError:
        print("invalid input")
        return


    if distance_check(x, z) == False:
        print("target can't be reached")
        return


    theta1, theta2 = ik(x, z)

    
    x_check, z_check = fk(theta1, theta2)
    error = math.hypot(x_check-x, z_check-z)
    if error > 1e-6:
        print("calculation error")
        return
    
    
    angle1, angle2 = servoangle(theta1, theta2)

    if not (0<= angle1 <= 180 and 0<=angle2<=180):
        print("servo angle out of range")
        print(f"joint angles: {math.degrees(theta1)}, {math.degrees(theta2)}")
        print(f"servo angles: {angle1}, {angle2}")
        return
    
    send_angle(angle1, angle2)



    
if __name__ == "__main__":
    main()