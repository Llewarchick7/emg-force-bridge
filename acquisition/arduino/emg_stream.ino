// emg_stream.ino
// Arduino Uno sketch to sample one EMG channel at ~1 kHz and stream CSV over Serial
// Connect MyoWare output to A0. Use a reference/ground electrode on the subject.
// WARNING: follow safety guidance in docs/consent_form.md

#include <Arduino.h>

// Configuration constants...
const int emgPin = A0; // Analog input pin for EMG signal
const unsigned long sampleIntervalMicros = 1000UL; // 1000 microseconds = 1 kHz sampling rate
const long baudRate = 115200; // Serial communication speed

// Timing variables...
unsigned long nextSampleTime = 0;
unsigned long firstTs = 0;
bool firstSample = true;

void setup() {
  // Initialize serial communication
  Serial.begin(baudRate);
  
  // Wait for serial port to connect (needed for boards with native USB)
  while (!Serial) { 
    delay(10); 
  }
  
  // Print CSV header
  Serial.println("timestamp_us,adc");
  
  // Initialize timing
  nextSampleTime = micros();
}

void loop() {
  unsigned long now = micros();
  
  // Check if it's time for the next sample
  if (now >= nextSampleTime) {
    // Read EMG signal from analog pin (10-bit ADC: 0-1023)
    int raw = analogRead(emgPin);
    
    // Set reference timestamp on first sample
    if (firstSample) {
      firstTs = now;
      firstSample = false;
    }
    
    // Calculate relative timestamp in microseconds
    unsigned long rel = now - firstTs;
    
    // Output CSV format: timestamp_us,adc_value
    Serial.print(rel);
    Serial.print(",");
    Serial.println(raw);
    
    // Schedule next sample (maintains consistent intervals)
    nextSampleTime += sampleIntervalMicros;
  }
}