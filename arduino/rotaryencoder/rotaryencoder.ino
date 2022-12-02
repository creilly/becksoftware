volatile long counter = 0;  //This variable will increase or decrease depending on the rotation of encoder

void setup() {
  Serial.begin(9600);
  while (!Serial) {;}

  pinMode(2, INPUT_PULLUP);  // internal pullup input pin 2

  pinMode(3, INPUT_PULLUP);  // internal pullup input pin 3
                             //Setting up interrupt
  //A rising pulse from encodenren activated ai0(). AttachInterrupt 0 is DigitalPin nr 2 on moust Arduino.
  attachInterrupt(0, ai0, RISING);

  //B rising pulse from encodenren activated ai1(). AttachInterrupt 1 is DigitalPin nr 3 on moust Arduino.
  attachInterrupt(1, ai1, RISING);

  // // put your setup code here, to run once:
  // Serial.begin(9600);
  // while (!Serial) {;}
}

void loop() {
  // while (!Serial.available()) {;}
  // char c = Serial.read();
  // Serial.print(counter);
  // Serial.print(' ');
  // Serial.flush();

  // put your main code here, to run repeatedly:
  while (!Serial.available()) {;}
  char c = Serial.read();
  Serial.print(counter);
  Serial.print(' ');
}

void ai0() {
  // ai0 is activated if DigitalPin nr 2 is going from LOW to HIGH
  // Check pin 3 to determine the direction
  if (digitalRead(3) == LOW) {
    counter++;
  } else {
    counter--;
  }
}

void ai1() {
  // ai0 is activated if DigitalPin nr 3 is going from LOW to HIGH
  // Check with pin 2 to determine the direction
  if (digitalRead(2) == LOW) {
    counter--;
  } else {
    counter++;
  }
}