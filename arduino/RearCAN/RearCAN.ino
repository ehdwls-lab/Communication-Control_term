#include <SPI.h>
#include <mcp_can.h>

const unsigned long MY_ID = 0x12;
const int CAN_CS_PIN  = 10;
MCP_CAN CAN(CAN_CS_PIN);

// 모터 핀
const int ENA = 9;  const int IN1 = 8;  const int IN2 = 7;
const int ENB = 5;  const int IN3 = 4;  const int IN4 = 3;

// RGB LED 핀 (아날로그 인 활용)
const int RED_LED = A2;
const int GRN_LED = A3;
const int BLU_LED = A4;

bool isEmergencyStop = false;
char currentCmd = 'q';

void setup() {
  Serial.begin(115200);

  pinMode(ENA, OUTPUT); pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(ENB, OUTPUT); pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);
  
  pinMode(RED_LED, OUTPUT);
  pinMode(GRN_LED, OUTPUT);
  pinMode(BLU_LED, OUTPUT);

  if (CAN.begin(MCP_ANY, CAN_500KBPS, MCP_8MHZ) == CAN_OK) {
    Serial.println("Rear CAN Init Success! (500kbps)");
  } else {
    Serial.println("CAN Init Failed...");
    while(1);
  }

  CAN.setMode(MCP_NORMAL);
  setLED(0, 0, 255); // 초기 상태 파란색 (정지)
}

void loop() {
  unsigned char len = 0;
  unsigned char buf[8];
  unsigned long receiveId;

  if (CAN_MSGAVAIL == CAN.checkReceive()) {
    CAN.readMsgBuf(&receiveId, &len, buf);

    // 케이스 1: 앞쪽 아두이노(0x11)로부터 거리 데이터를 수신한 경우
    if (receiveId == 0x11) {
      int receivedDistance = buf[0];
      Serial.print("[CAN RX From Front] Distance: "); Serial.print(receivedDistance); Serial.println("cm");

      // 거리에 따른 실시간 LED 색상 피드백 및 강제 제동
      if (receivedDistance < 15) {
        setLED(255, 0, 0); // 빨간색 (위험)
        executeCommand('q'); // 뒷바퀴도 강제 정지
        isEmergencyStop = true;
      } else if (receivedDistance < 40) {
        setLED(255, 150, 0); // 노란색/주황색 (주의)
        isEmergencyStop = false;
        executeCommand(currentCmd); // 원래 속도 복구
      } else {
        isEmergencyStop = false;
        if (currentCmd == 'q') {
          setLED(0, 0, 255); // 완전 정지 상태면 파란색
        } else {
          setLED(0, 255, 0); // 주행 중이고 안전하면 초록색
        }
        executeCommand(currentCmd);
      }
    }

    // 케이스 2: 라즈베리 파이(0x10) 또는 전용 명령 수신
    if (receiveId == MY_ID || receiveId == 0x10) {
      char cmd = (char)buf[0];
      currentCmd = cmd; // 현재 명령 저장

      if (cmd == 'q') {
        setLED(0, 0, 255); // 사용자가 정지 누르면 파란색
      }

      if (isEmergencyStop && cmd == 'w') {
        executeCommand('q'); // 위험 상황 시 전진 명령 방어
      } else {
        executeCommand(cmd);
      }
    }
  }
}

// LED 제어 편의 함수
void setLED(int r, int g, int b) {
  // PWM 지원 핀이 아니므로 전압 분배식 오프라인 제어 (HIGH/LOW)
  digitalWrite(RED_LED, r > 0 ? HIGH : LOW);
  digitalWrite(GRN_LED, g > 0 ? HIGH : LOW);
  digitalWrite(BLU_LED, b > 0 ? HIGH : LOW);
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