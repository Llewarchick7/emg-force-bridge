// emg_stream.ino
// Arduino Uno sketch to sample one EMG channel at ~1 kHz and stream CSV over Serial
// Connect MyoWare output to A0. Use a reference/ground electrode on the subject.
// WARNING: follow safety guidance in docs/consent_form.md

const int emgPin = A0;
const unsigned long sampleIntervalMicros = 1000UL; // 1 kHz
unsigned long nextSampleTime = 0;
unsigned long firstTs = 0;
bool firstSample = true;

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }
  Serial.println("timestamp_us,adc");
  nextSampleTime = micros();
}

void loop() {
  unsigned long now = micros();
  if (now >= nextSampleTime) {
    int raw = analogRead(emgPin); // 10-bit ADC 0..1023
    if (firstSample) {
      firstTs = now;
      firstSample = false;
    }
    unsigned long rel = now - firstTs;
    Serial.print(rel);
    Serial.print(",");
    Serial.println(raw);
    nextSampleTime += sampleIntervalMicros;
  }
}