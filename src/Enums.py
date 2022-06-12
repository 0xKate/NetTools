from enum import Enum


class EventMsg(Enum):
    Exit = 'EVT_Exit'

class PROTO(Enum):
    TCP = 0
    UDP = 1