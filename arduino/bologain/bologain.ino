const byte x10 = 0;
const byte x100 = 1;
const byte x200 = 2;
const byte x1000 = 3;

const byte npins = 4;

const bool polarities[] = {true, false, false, true};
const byte pins[] = {8, 9, 10, 11};

const byte ascii0 = 48;

byte parse_response(char response) {
  return byte(response) - ascii0;
}

void write_line(byte gain, bool state) {
  digitalWrite(pins[gain], polarities[gain] == state);
}

void set_gain(byte gain) {
  write_line(gain, true);
  for (byte n = 0; n < npins; n++) {
    if (n == gain) {
      continue;
    }
    write_line(n, false);
  }
}

void setup() {
  for (byte n = 0; n < npins; n++) {
    pinMode(pins[n], OUTPUT);
  }
  Serial.begin(9600);
  while (!Serial) {;}
}

void loop() {
  while (!Serial.available()) {;}
  set_gain(parse_response(Serial.read()));
}
