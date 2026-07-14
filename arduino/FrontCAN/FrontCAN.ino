#include <SPI.h>
#include <mcp_can.h>

const unsigned long MY_ID = 0x11;
const int CAN_CS_PIN  = 10;
MCP_CAN CAN(CAN_CS_PIN);

// 모터 핀
const int ENA = 9;  const int IN1 = 8;  const int IN2 = 7;
const int ENB = 5;  const int IN3 = 4;  const int IN4 = 3;

// 초음파 센서 핀 (아날로그 인 활용)
const int TRIG_PIN = A0;
const int ECHO_PIN = A1;

unsigned long lastTxTime = 0;
bool isEmergencyStop = false;

void setup() {
  Serial.begin(115200);

  pinMode(ENA, OUTPUT); pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(ENB, OUTPUT); pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);
  
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  if (CAN.begin(MCP_ANY, CAN_500KBPS, MCP_8MHZ) == CAN_OK) {
    Serial.println("Front CAN Init Success! (500kbps)");
  } else {
    Serial.println("CAN Init Failed...");
    while(1);
  }

  CAN.setMode(MCP_NORMAL);
}

void loop() {
  unsigned char len = 0;
  unsigned char buf[8];
  unsigned long receiveId;

  // 1. 초음파 센서 거리 측정
  digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH);
  int distance = duration * 0.034 / 2;

  // 예외 처리 (센서 오류로 0이 찍힐 때 방지)
  if (distance == 0) distance = 999; 

  // 2. 비상 정지 로직 (15cm 이내면 앞바퀴 강제 정지)
  if (distance < 15) {
    if (!isEmergencyStop) {
      executeCommand('q'); // 강제 정지
      isEmergencyStop = true;
      Serial.println("[⚠️ EMERGENCY] Front Brake Activated!");
    }
  } else {
    isEmergencyStop = false;
  }

  // 3. CAN 명령 수신 및 처리
  if (CAN_MSGAVAIL == CAN.checkReceive()) {
    CAN.readMsgBuf(&receiveId, &len, buf);

    // 내 ID나 브로드캐스트 명령이고, 비상 정지 상태가 아닐 때만 주행 명령 수행
    if (receiveId == MY_ID || receiveId == 0x10) {
      char cmd = (char)buf[0];
      if (isEmergencyStop && cmd == 'w') {
        // 비상 정지 중에는 전진('w') 명령 무시
        executeCommand('q');
      } else {
        executeCommand(cmd);
      }
    }
  }

  // 4. 0.3초마다 전역 버스에 거리 데이터 송신 (라파와 뒤쪽 아두이노가 들음)
  if (millis() - lastTxTime > 300) {
    unsigned char txData[1] = {(unsigned char)distance};
  if (CAN.sendMsgBuf(MY_ID, 0, 1, txData) == CAN_OK) {
    Serial.print("Sent Distance: "); 
    Serial.print(distance);          // concat 대신 일반 print를 사용합니다.
    Serial.println("cm");
  }
    lastTxTime = millis();
  }
}

void executeCommand(char cmd) {
  switch (cmd) {
    case 'w':
      digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);  analogWrite(ENA, 200);
      digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);  analogWrite(ENB, 200);
      break;
    case 's':
      digitalWrite(IN1, LOW);  digitalWrite(IN2, HIGH); analogWrite(ENA, 200);
      digitalWrite(IN3, LOW);  digitalWrite(IN4, HIGH); analogWrite(ENB, 200);
      break;
    case 'a':
      digitalWrite(IN1, LOW);  digitalWrite(IN2, HIGH); analogWrite(ENA, 200);
      digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);  analogWrite(ENB, 200);
      break;
    case 'd':
      digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);  analogWrite(ENA, 200);
      digitalWrite(IN3, LOW);  digitalWrite(IN4, HIGH); analogWrite(ENB, 200);
      break;
    case 'q':
      analogWrite(ENA, 0); analogWrite(ENB, 0);
      break;
  }
}