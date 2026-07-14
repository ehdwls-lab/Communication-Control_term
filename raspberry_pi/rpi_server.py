import socket
import can
import threading
import cv2
from flask import Flask, Response
from picamera2 import Picamera2

PORT = 61499
CAN_BITRATE = 500000
STREAM_PORT = 8080

bus = None
tcp_conn = None
conn_lock = threading.Lock()

app = Flask(__name__)

picam2 = None


def init_can():
    global bus

    try:
        bus = can.interface.Bus(
            channel='can0',
            interface='socketcan'
        )

        print("[CAN] Connection Success")
        return True

    except Exception as e:
        print(f"[CAN] Initialization Failed: {e}")
        return False


def can_receive_thread():
    global tcp_conn

    print("[CAN] Receive thread started")

    while True:
        try:
            msg = bus.recv(timeout=1.0)

            if msg is None:
                continue

            if msg.arbitration_id == 0x11:

                distance = msg.data[0]

                print(
                    f"[CAN RX] Front Distance Data: {distance} cm"
                )

                with conn_lock:
                    if tcp_conn:
                        try:
                            tcp_conn.send(
                                f"DIST:{distance}\n".encode()
                            )
                        except:
                            pass

            else:

                data_str = ''.join(
                    chr(b)
                    for b in msg.data
                    if b != 0
                )

                print(
                    f"[CAN RX] ID:{hex(msg.arbitration_id)} "
                    f"DATA:{data_str}"
                )

                with conn_lock:
                    if tcp_conn:
                        try:
                            tcp_conn.send(
                                f"CAN:{hex(msg.arbitration_id)}:{data_str}\n".encode()
                            )
                        except:
                            pass

        except Exception as e:
            print(f"[CAN RX] Error: {e}")

def send_can_command(cmd):
    global bus

    if bus is None:
        return

    try:

        data = [ord(cmd)] + [0] * 7

        msg = can.Message(
            arbitration_id=0x10,
            data=data,
            is_extended_id=False
        )

        bus.send(msg)

        print(
            f"[CAN TX] Command Sent: '{cmd}'"
        )

    except Exception as e:
        print(f"[CAN TX] Send Failed: {e}")


def handle_client(conn, addr):
    global tcp_conn

    print(f"[TCP] Client Connected: {addr}")

    with conn_lock:
        tcp_conn = conn

    try:

        while True:

            data = conn.recv(1024)

            if not data:
                break

            cmd = data.decode().strip()

            print(f"[TCP RX] Received: {cmd}")

            if cmd in ['w', 'a', 's', 'd', 'q']:
                send_can_command(cmd)

    except Exception as e:
        print(f"[TCP] Client Error: {e}")

    finally:

        with conn_lock:
            tcp_conn = None

        conn.close()

        print(
            f"[TCP] Client Disconnected: {addr}"
        )


def generate_frames():
    global picam2

    while True:

        try:

            frame = picam2.capture_array()

            ret, buffer = cv2.imencode(
                '.jpg',
                frame
            )

            if not ret:
                continue

            frame_bytes = buffer.tobytes()

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n'
                + frame_bytes +
                b'\r\n'
            )

        except Exception as e:
            print(f"[CAMERA] Frame Error: {e}")
            break


@app.route('/video_feed')
def video_feed():

    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/')
def home():
    return "Camera Server Running"


def start_flask():

    app.run(
        host='0.0.0.0',
        port=STREAM_PORT,
        threaded=True,
        use_reloader=False
    )

def start_server():

    global picam2

    print("[CAMERA] Initializing Camera...")

    picam2 = Picamera2()

    config = picam2.create_preview_configuration(
        main={"size": (640, 480)}
    )

    picam2.configure(config)

    picam2.start()

    print("[CAMERA] Camera Initialized")

    if not init_can():
        print(
            "[WARNING] CAN not available"
        )

    if bus:
        t_can = threading.Thread(
            target=can_receive_thread,
            daemon=True
        )

        t_can.start()

    t_flask = threading.Thread(
        target=start_flask,
        daemon=True
    )

    t_flask.start()

    print(
        f"[CAMERA] Streaming server started on port {STREAM_PORT}"
    )

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind(
        ('0.0.0.0', PORT)
    )

    server.listen(5)

    print(
        f"[TCP] Server started on port {PORT}. Waiting..."
    )

    try:

        while True:

            conn, addr = server.accept()

            t_client = threading.Thread(
                target=handle_client,
                args=(conn, addr),
                daemon=True
            )

            t_client.start()

    except KeyboardInterrupt:

        print("\n[SERVER] Shutdown")

    finally:

        server.close()

        if picam2:
            picam2.stop()

        if bus:
            bus.shutdown()


if __name__ == "__main__":
    start_server()
