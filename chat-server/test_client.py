import datetime
import json
from re import M
import socket
import traceback

from helpers import StoppableThread
from settings.settings import Settings

settings = Settings()

class TestClient:
    def __init__(self):
        self._header_size = settings.header_size
        self._username = input("Enter username: ")
        self._session_id = None

    def process_request(self, request):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((settings.server_ip, settings.server_port))
        self.send_msg(sock, json.dumps(request))
        response = json.loads(self.receive_msg(sock))
        sock.close()
        del sock
        return response

    def login(self):
        request = {
            'function': 'login',
            'username': self._username
        }
        response = self.process_request(request)
        print(response)
        if response['result'] == 'failed':
            return False
        self._session_id = response['message']['session_id']
        return True

    def logout(self):
        request = {
            'function': 'logout',
            'username': self._username,
            'session_id': self._session_id
        }
        response = self.process_request(request)
        if response['result'] == 'failed':
            return False
        print(response['message'])
        self._session_id = None
        return True

    def join_room(self):
        request = {
            'function': 'room',
            'action': 'join',
            'session_id': self._session_id
        }
        response = self.process_request(request)
        print(response)
        if response['result'] == 'failed':
            return False
        print(response['message'])
        return True

    def leave_room(self):
        request = {
            'function': 'room',
            'action': 'leave',
            'session_id': self._session_id
        }
        response = self.process_request(request)
        print(response)
        if response['result'] == 'failed':
            return False
        return True

    def open_recv_channel(self, sock):
        while True:
            new_event = json.loads(self.receive_msg(sock))
            if new_event['type'] == 'chat_msg':
                print(f'{new_event["timestamp"]} {new_event["username"]}: {new_event["message"]}')
            elif new_event['type'] == "keep-alive":
                now = datetime.datetime.now()
                timestamp = now.strftime("%d/%m/%Y %H:%M:%S")
                response = {
                    "timestamp": timestamp,
                    "type": "keep-alive",
                    "session_id": self._session_id,
                    "message": "pong"
                }
                self.send_msg(sock, json.dumps(response))

    def chat_loop(self):
        print('Starting chat...')
        request = {
            'function': 'room',
            'action': 'receive',
            'session_id': self._session_id
        }

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((settings.server_ip, settings.server_port))
        self.send_msg(sock, json.dumps(request))

        #handle unauth error
        payload = self.receive_msg(sock)
        print(payload)
        response = json.loads(payload)
        print(response)
        if response['result'] == 'failed':
            print('Faled to join chat.')
            return

        incoming_chat_handler = StoppableThread(target=self.open_recv_channel, args=(sock,))
        incoming_chat_handler.start()
        while True:
            msg = input()
            if msg == '/q':
                break
            request = {
                'function': 'room',
                'action': 'send',
                'session_id': self._session_id,
                'message': msg
            }
            response = self.process_request(request)
            if response['result'] == 'error':
                print('ERROR: The message failed to be sent')
        
        incoming_chat_handler.stop()
        sock.close()
        print('Ending chat...')

    def mainloop(self):
        while True:
            print('''
            Menu:
            1. Login
            2. Join Room
            3. Interact with Room
            4. Leave Room
            5. Logout
            0. Quit''')
            choice = int(input("Choice: "))

            if choice == 0:
                break
            elif choice == 1:
                print('Logging in...')
                print(self.login())
                print(self._session_id)
            elif choice == 2:
                print('Joining room...')
                print(self.join_room())
            elif choice == 3:
                self.chat_loop()
            elif choice == 4:
                print(self.leave_room())
            elif choice == 5:
                print(self.logout())
            print()

    def send_msg(self, sock, msg):
        msg = msg + '\r\n'
        payload = f'{len(msg):<{self._header_size}}'+msg
        sock.send(payload.encode('utf-8'))

    def receive_msg(self, sock):
        buffer = ""
        new_msg = True
        while True:
            raw_request = sock.recv(self._header_size)
            if new_msg:
                msglen = int(raw_request.decode("utf-8"))
                new_msg = False
                continue
            buffer += raw_request.decode("utf-8")
            if len(buffer) >= msglen:
                break
        return buffer.strip()


def main():
    client = TestClient()
    client.mainloop()

if __name__ == "__main__":
    main()