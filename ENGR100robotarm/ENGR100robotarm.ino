#include <Servo.h>

Servo servo_s;
Servo servo_e;
Servo servo_g;

int current1 = 90;
int current2 = 90;
int current3 = 130;

void setup() {
  Serial.begin(115200);

  servo_s.attach(4);
  servo_e.attach(5);
  servo_g.attach(6);

  servo_s.write(90);
  servo_e.write(90);
  servo_g.write(130);
}

void loop() {
  if (Serial.available() > 0) {
    String message = Serial.readStringUntil('\n');

    int separator1 = message.indexOf(',');
    int separator2 = message.indexOf(',', separator1 + 1);

    // Check message format
    if (separator1 == -1 || separator2 == -1) {
      return;
    }

    String first = message.substring(0, separator1);
    String second = message.substring(separator1 + 1, separator2);
    String third = message.substring(separator2 + 1);

    int angle1 = first.toInt();
    int angle2 = second.toInt();
    int angle3 = third.toInt();


while (current1 != angle1 || current2 != angle2 || current3 != angle3) {
  if (current1 < angle1) current1++;
  else if (current1 > angle1) current1--;

  if (current2 < angle2) current2++;
  else if (current2 > angle2) current2--;

  if (current3 < angle3) current3++;
  else if (current3 > angle3) current3--;

  servo_s.write(current1);
  servo_e.write(current2);
  servo_g.write(current3);

  delay(25);
}

    servo_s.write(angle1);
    servo_e.write(angle2);
    servo_g.write(angle3);
  }
}