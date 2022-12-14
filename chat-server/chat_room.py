import datetime
from chat_session import ChatSession
from custom_exceptions import JoinLobbyException, JoinRoomException, LoginException, LogoutException, UnauthenticatedException, UnauthorizedParticipentException, UnknownActionException
from helpers import generate_session_id, StoppableThread
from settings.settings import Settings

import json
import socket
import threading
import traceback
import time

settings = Settings()

class ChatRoom:
    def __init__(self):
        self._header_size = settings.header_size
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.bind((settings.server_ip, settings.server_port))
        self._server.listen(settings.max_connections_accepted)
        self._room_name = "Default Room"
        self._sessions = {}
        self._participants = {}
        print('[*] Chat Server Has Started')

    def _session_printer(self):
        while True:
            print("Active Sessions: ")
            for session in self._sessions:
                print(session)
            print()

            print("Participants: ")
            for participant in self._participants:
                print(participant)
            print()
            time.sleep(10)

    def mainloop(self):
        session_monitor_hander = StoppableThread(target=self._session_printer, args=())
        session_monitor_hander.start()
        while True:
            try:
                client, address = self._server.accept()
                print(f'[*] New connection from {address[0]}')
                client.settimeout(5.0)
                client_handler = threading.Thread(target=self.handle_client, args=(client, address))
                client_handler.start()
            except KeyboardInterrupt:
                break
        session_monitor_hander.stop()
        self._server.close()

    def login(self, request):
        try:
            username = request['username']
            session_id = generate_session_id()
            while session_id in self._sessions.keys():
                session_id = generate_session_id()
            user_session = ChatSession(
                session_id = session_id,
                username = username
            )
            self._sessions[session_id] = user_session
            return {'username': username, 'session_id': session_id}
        except:
            print(traceback.format_exc())
            raise LoginException('Login failed')

    def logout(self, request):
        try:
            username = request['username']
            session_id = request['session_id']
            del self._sessions[session_id]
            return f'{username} with session id {session_id} has logout successfully!'
        except:
            raise LogoutException('Logout failed')

    def lobby(self, request):
        return "function coming soon"

    def _format_chat_packet(self, message, username=None):
        now = datetime.datetime.now()
        timestamp = now.strftime("%d/%m/%Y %H:%M:%S")
        return {
            "timestamp": timestamp, 
            "type": "chat_msg",
            "username": username, 
            "message": message
        }

    def broadcast(self, message, username=None):
        chat_packet = self._format_chat_packet(message, username)
        for session_id, sock in self._participants.items():
            if sock is not None:
                try:
                    self.send_msg(sock, json.dumps(chat_packet))
                except:
                    self._participants[session_id] = None

    def keep_alive_client_receive_channel(self, session):
        counter = 0
        while True:
            if session.session_id not in self._participants:
                break
            now = datetime.datetime.now()
            timestamp = now.strftime("%d/%m/%Y %H:%M:%S")
            keep_alive_msg = {"timestamp": timestamp, "message": "ping", "type": "keep-alive"}
            self.send_msg(self._participants[session.session_id], json.dumps(keep_alive_msg))
            try:
                response = json.loads(self.receive_msg(self._participants[session.session_id]))
                if response['session_id'] != session.session_id:
                    break
                if counter != 0:
                    counter = 0
            except:
                counter += 1
                if counter == 3:
                    break
            time.sleep(5)

    def room(self, request, sock):
        action = request['action']
        session = self._sessions[request['session_id']]

        if action == "join":
            if session.session_id in self._participants:
                raise JoinRoomException('Error: User has already joined the room.')
            self._participants[session.session_id] = None
            return f'Successfully joined room {self._room_name}'

        elif action == 'send':
            if session.session_id in self._participants.keys():
                print(request)
                self.broadcast(request['message'], session.username)
                return 'Message sent'
            raise UnauthorizedParticipentException('User is not a member of this room!')

        elif action == 'receive':
            if session.session_id not in self._participants.keys():
                raise UnauthorizedParticipentException('User is not a member of this room!')
            
            self.send_msg(sock, json.dumps({'message': 'opening channel', 'result': 'success'}))
            self._participants[session.session_id] = sock
            time.sleep(1)
            self.keep_alive_client_receive_channel(session)
            if session.session_id in self._participants.keys():
                if self._participants[session.session_id] is not None:
                    try:
                        self._participants[session.session_id].close()
                    except:
                        pass
                    del self._participants[session.session_id]
                self._participants[session.session_id] = None
            return 'receive channel terminated'

        elif action == 'leave':
            if self._participants[session.session_id] is not None:
                self._participants[session.session_id].close()
            del self._participants[session.session_id] 
            return f'Exited room {self._room_name}'

        else:
            raise UnknownActionException("Unrecognized action.")


    def handle_client(self, client, address):
        with client as sock:
            try:
                request = json.loads(self.receive_msg(sock))
                if request['function'] == 'login':
                    output = self.login(request)
                    result = 'success'
                else:
                    if 'session_id' not in request.keys():
                        raise UnauthenticatedException('User not login')
                    if request['session_id'] is None:
                        raise UnauthenticatedException('User not login')
                    session_id = request['session_id']
                    if session_id not in self._sessions:
                        raise UnauthenticatedException('User not login')

                    if request['function'] == 'lobby':
                        output = self.lobby(request)
                        
                    elif request['function'] == 'room':
                        output = self.room(request, sock)
                        result = 'success'
                    elif request['function'] == 'logout':
                        output = self.logout(request)
                        result = 'success'
                    else:
                        output = {
                            'error':'unknown_function', 
                            'details': 'Function not found.'
                        }
                        result = 'failed'
            except JoinLobbyException as ex:
                output = {'error':'join_lobby_error', 'details': str(ex)}
                result =  'failed'

            except JoinRoomException as ex:
                output = {'error':'join_room_error', 'details': str(ex)}
                result =  'failed'
            
            except LoginException as ex:
                output = {'error':'login_error', 'details': str(ex)}
                result =  'failed'
            
            except LogoutException as ex:
                output = {'error':'logout_error', 'details': str(ex)}
                result = 'failed'
                
            except UnauthenticatedException as ex:
                output = {'error':'authentication_error', 'details': str(ex)}
                result = 'failed'
                
            except UnauthorizedParticipentException as ex:
                output = {'error':'unauthorized_participant', 'details': str(ex)}
                result = 'failed'
                
            except UnknownActionException as ex:
                output = {'error':'unknown_action_error', 'details': str(ex)}
                result =  'failed'
            except Exception as ex:
                print(traceback.format_exc())
                output = {'error':'general_error', 'details': str(ex)}
                result = 'failed'
                
            self.send_msg(sock, json.dumps({'message': output, 'result': result}))
            sock.close()
        print(f'[*] {address[0]} has disconnected from the server\r\n')

    def send_msg(self, sock, msg):
        msg = msg + '\r\n'
        payload = f'{len(msg):<{self._header_size}}'+msg
        print(payload)
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
    app = ChatRoom()
    app.mainloop()

if __name__ == "__main__":
    main()