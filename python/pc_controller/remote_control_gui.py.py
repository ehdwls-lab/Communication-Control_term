import socket
import tkinter as tk
from threading import Thread
import urllib.request
import cv2
import numpy as np
from PIL import Image, ImageTk

# Raspberry Pi Server Configurations
RPI_IP      = '172.20.10.2'  
PORT        = 61499
STREAM_URL  = f"http://{RPI_IP}:8080/video_feed"

class RemoteControl:
    def __init__(self, root):
        self.root = root
        self.root.title("4WD Robot Control Dashboard with Cam")
        self.client_socket = None
        self.connected = False
        self.streaming = True
        
        # Configure Grid Layout Weight
        self.root.grid_columnconfigure(0, weight=2)  # Video Stream Side
        self.root.grid_columnconfigure(1, weight=1)  # Telemetry & Control Side

        # ==================================================
        # LEFT SIDE: Real-time Video Stream Display Panel
        # ==================================================
        self.video_frame = tk.LabelFrame(root, text=" Live Camera View (320x240) ", fg="darkblue", font=("Arial", 11, "bold"))
        self.video_frame.grid(row=0, column=0, rowspan=2, padx=10, pady=10, sticky="nsew")
        
        self.video_label = tk.Label(self.video_frame, text="Waiting for Video Stream...", bg="black", fg="white", width=45, height=15)
        self.video_label.pack(expand=True, fill="both", padx=5, pady=5)

        # ==================================================
        # RIGHT SIDE: Robot Status & Telemetry
        # ==================================================
        self.right_frame = tk.Frame(root)
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="n")

        self.title_label = tk.Label(self.right_frame, text="System Dashboard", font=("Arial", 14, "bold"))
        self.title_label.pack(pady=5)
        
        self.status_label = tk.Label(self.right_frame, text="Waiting for Connection...", fg="red", font=("Arial", 10))
        self.status_label.pack(pady=5)
        
        # Distance Monitoring Widget
        self.distance_label = tk.Label(self.right_frame, text="Distance: -- cm", font=("Arial", 18, "bold"), fg="blue")
        self.distance_label.pack(pady=15)
        
        # ==================================================
        # RIGHT SIDE BOTTOM: Control Buttons Panel
        # ==================================================
        self.ctrl_frame = tk.LabelFrame(self.right_frame, text=" Driving Control Pad ")
        self.ctrl_frame.pack(pady=10, fill="x")

        tk.Button(self.ctrl_frame, text="▲ FORWARD (w)", width=20, bg="lightgreen", command=lambda: self.send('w')).grid(row=0, column=0, columnspan=3, pady=5, padx=5)
        tk.Button(self.ctrl_frame, text="◀ LEFT (a)", width=9, command=lambda: self.send('a')).grid(row=1, column=0, pady=5, padx=5)
        tk.Button(self.ctrl_frame, text="■ STOP (q)", width=9, bg="red", fg="white", command=lambda: self.send('q')).grid(row=1, column=1, pady=5, padx=5)
        tk.Button(self.ctrl_frame, text="RIGHT (d) ▶", width=9, command=lambda: self.send('d')).grid(row=1, column=2, pady=5, padx=5)
        tk.Button(self.ctrl_frame, text="▼ BACKWARD (s)", width=20, bg="orange", command=lambda: self.send('s')).grid(row=2, column=0, columnspan=3, pady=5, padx=5)

        # Keyboard Bindings for Instant Control
        root.bind('<w>', lambda e: self.send('w'))
        root.bind('<s>', lambda e: self.send('s'))
        root.bind('<a>', lambda e: self.send('a'))
        root.bind('<d>', lambda e: self.send('d'))
        root.bind('<q>', lambda e: self.send('q'))

        # Clean Close Handler
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Active Background Networking Threads
        Thread(target=self.connect_to_rpi, daemon=True).start()
        Thread(target=self.start_video_stream_thread, daemon=True).start()
        Thread(target=self.stm_gateway_server, daemon=True).start()

    # ------------------------------------------------------
    def start_video_stream_thread(self):
        self.stream_video()

    # ------------------------------------------------------
    def connect_to_rpi(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((RPI_IP, PORT))
            self.connected = True
            self.status_label.config(text=f"Connected to {RPI_IP}", fg="green")
            print("[GUI] Command socket connection successful")
            Thread(target=self.receive_data, daemon=True).start()
        except Exception as e:
            self.connected = False
            self.status_label.config(text=f"Connection Error: {e}", fg="red")

    # ------------------------------------------------------
    def receive_data(self):
        while self.connected:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    self.connected = False
                    self.status_label.config(text="Disconnected from Server", fg="red")
                    break
                
                messages = data.decode().split('\n')
                for msg in messages:
                    if msg.startswith("DIST:"):
                        try:
                            distance_val = msg.split(":")[1].strip()
                            self.root.after(0, self.update_distance_ui, distance_val)
                        except IndexError:
                            pass
            except:
                self.connected = False
                break

    # ------------------------------------------------------
    def update_distance_ui(self, distance):
        try:
            dist_int = int(distance)
            self.distance_label.config(text=f"Distance: {distance} cm")
            if dist_int < 15:
                self.distance_label.config(fg="red")
            elif dist_int < 40:
                self.distance_label.config(fg="darkorange")
            else:
                self.distance_label.config(fg="green")
        except ValueError:
            self.distance_label.config(text=f"Distance: {distance} cm", fg="blue")

    # ------------------------------------------------------
    def stream_video(self):
        print(f"[GUI] Attempting video stream from {STREAM_URL}")
        cap = None
        
        while self.streaming:
            try:
                if cap is None:
                    cap = cv2.VideoCapture(STREAM_URL)
                    print("[GUI] Video stream server connected")
                
                success, frame = cap.read()
                if success and frame is not None:
                    frame = cv2.resize(frame, (320, 240))
                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                    cv2image = frame
                    img = Image.fromarray(cv2image)
                    imgtk = ImageTk.PhotoImage(image=img)
                    
                    if self.streaming:
                        self.video_label.config(image=imgtk)
                        self.video_label.image = imgtk
                else:
                    cap = None
                    
            except Exception as e:
                cap = None
                if self.streaming:
                    self.video_label.config(image='', text="Waiting for Video Stream...")
                import time
                time.sleep(1)

    # ------------------------------------------------------
    def send(self, cmd):
        if self.client_socket and self.connected:
            try:
                self.client_socket.send(cmd.encode())
                print(f"[GUI] Sent Command: '{cmd}'")
            except:
                self.status_label.config(text="Send Failed!", fg="red")

    # ------------------------------------------------------
    def on_closing(self):
        self.streaming = False
        self.connected = False
        if self.client_socket:
            self.client_socket.close()
        self.root.destroy()
    
    # ------------------------------------------------------
    def stm_gateway_server(self):

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server.bind(("192.168.30.1", 5000))

        server.listen(1)

        print("[STM] Waiting STM32...")

        while True:

            conn, addr = server.accept()

            print(f"[STM] Connected : {addr}")

            while True:

                try:

                    data = conn.recv(1024)

                    if not data:
                        break

                    cmd = data.decode().strip()

                    print(f"[STM] Received : {cmd}")

                    if cmd in ['w', 's', 'a', 'd', 'q']:

                        if self.client_socket and self.connected:

                            self.send(cmd)

                            print(
                                f"[STM] Forwarded -> Pi : {cmd}"
                            )

                except Exception as e:

                    print(f"[STM] Error : {e}")

                    break

            conn.close()

            print("[STM] Disconnected")
            
if __name__ == "__main__":
    root = tk.Tk()
    app = RemoteControl(root)
    root.mainloop()