# simulate.py — coloque na raiz do projeto
import sys
sys.path.insert(0, ".")

from database import connection, schema
from learning import reinforcement
from playback.events import EventType, PlaybackEvent

connection.init("data/player.db")
schema.migrate()

# Simula: faixa 1 ouvida até o final no mood Focus, noite de segunda
event = PlaybackEvent(
    type=EventType.END_OF_TRACK,
    track_id=1,
    position=1.0,
    active_mood="Focus",
    active_period="Night",
    active_weekday="Monday",
)
reinforcement.process(event)
print("Pesos atualizados.")