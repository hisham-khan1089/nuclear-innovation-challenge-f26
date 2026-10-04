const int POT = A0;
const int GREEN_LED = 7;
const int RED_LED = 8;

char reactorState = 'N';

// Potentiometer sending
unsigned long previousPotTime = 0;
const unsigned long potInterval = 20;   // Send reading every 20 ms

// SCRAM blinking
unsigned long previousBlinkTime = 0;
const unsigned long blinkInterval = 300;
bool redLedState = false;

void setup() {
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);

  Serial.begin(9600);

  // Start NORMAL
  digitalWrite(GREEN_LED, HIGH);
  digitalWrite(RED_LED, LOW);
}

void loop() {

  // =========================================
  // 1. READ COMMANDS FROM PYTHON IMMEDIATELY
  // =========================================
  while (Serial.available() > 0) {

    char incoming = Serial.read();

    if (incoming == 'N' || incoming == 'H' || incoming == 'S') {

      reactorState = incoming;

      // Immediately set LEDs when state changes
      if (reactorState == 'N') {
        digitalWrite(GREEN_LED, HIGH);
        digitalWrite(RED_LED, LOW);
        redLedState = false;
      }

      else if (reactorState == 'H') {
        digitalWrite(GREEN_LED, LOW);
        digitalWrite(RED_LED, HIGH);
        redLedState = true;
      }

      else if (reactorState == 'S') {
        digitalWrite(GREEN_LED, LOW);

        // Start SCRAM with red ON immediately
        digitalWrite(RED_LED, HIGH);
        redLedState = true;
        previousBlinkTime = millis();
      }
    }
  }


  // =========================================
  // 2. SEND POTENTIOMETER VALUE TO PYTHON
  // =========================================
  unsigned long currentTime = millis();

  if (currentTime - previousPotTime >= potInterval) {

    previousPotTime = currentTime;

    int reading = analogRead(POT);

    // Constrain first so map doesn't produce weird values
    reading = constrain(reading, 3, 1010);

    int cleanvalue = map(reading, 3, 1010, 0, 1023);

    Serial.println(cleanvalue);
  }


  // =========================================
  // 3. BLINK RED DURING SCRAM
  // =========================================
  if (reactorState == 'S') {

    if (currentTime - previousBlinkTime >= blinkInterval) {

      previousBlinkTime = currentTime;

      redLedState = !redLedState;

      digitalWrite(RED_LED, redLedState);
    }
  }
}