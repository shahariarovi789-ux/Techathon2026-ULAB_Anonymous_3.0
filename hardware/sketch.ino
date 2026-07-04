int light1 = 13;
int light2 = 12;
int light3 = 11;
int fan1_relay = 10;
int fan2_relay = 9;

void setup() {
  pinMode(light1, OUTPUT);
  pinMode(light2, OUTPUT);
  pinMode(light3, OUTPUT);
  pinMode(fan1_relay, OUTPUT);
  pinMode(fan2_relay, OUTPUT);
}

void loop() {
  // Power ON devices
  digitalWrite(light1, HIGH);
  digitalWrite(light2, HIGH);
  digitalWrite(light3, HIGH);
  digitalWrite(fan1_relay, HIGH); 
  digitalWrite(fan2_relay, HIGH);
  
  delay(2000); // Keep on for 2 seconds
  
  // Power OFF devices
  digitalWrite(light1, LOW);
  digitalWrite(light2, LOW);
  digitalWrite(light3, LOW);
  digitalWrite(fan1_relay, LOW);
  digitalWrite(fan2_relay, LOW);
  
  delay(2000); // Keep off for 2 seconds
}
