class ChatSession:
    def __init__(self, session_id, username):
        self._session_id = session_id
        self._username = username
        self._lobby = None
        self._room = None

    @property
    def session_id(self):
        return self._session_id

    @property
    def username(self):
        return self._username

    @property
    def lobby(self):
        return self._lobby

    @property
    def room(self):
        return self._room

    @lobby.setter
    def lobby(self, lobby):
        self._lobby = lobby

    @room.setter
    def room(self, room):
        self._room = room