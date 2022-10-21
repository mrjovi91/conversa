import socket
from settings.settings import Settings
import traceback

settings = Settings()

class ChatClient:
    def __init__(self):
        self._header_size = settings.header_size
        self._identifier = 'Client > '
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((settings.server_ip, settings.server_port))  
        print(self.receive_msg())

    def mainloop(self):
        while True:
            try:
                msg = input(self._identifier)
                if msg == '/q':
                    self.send_msg('/q')
                    break
                self.send_msg(f'{self._identifier }{msg}')
                response = self.receive_msg()
                print(response)
            except:
                error = traceback.format_exc()
                print(error)
                break
        self._sock.close()

    def send_msg(self, msg):
        msg = msg + '\r\n'
        payload = f'{len(msg):<{self._header_size}}'+msg
        self._sock.send(payload.encode('utf-8'))

    def receive_msg(self):
        buffer = ""
        new_msg = True
        while True:
            raw_request = self._sock.recv(self._header_size)
            if new_msg:
                msglen = int(raw_request.decode("utf-8"))
                new_msg = False
                continue
            buffer += raw_request.decode("utf-8")
            if len(buffer) >= msglen:
                break
        return buffer.strip()


def main():
    client = ChatClient()
    client.mainloop()

if __name__ == "__main__":
    main()