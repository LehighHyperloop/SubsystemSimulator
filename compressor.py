import json
import paho.mqtt.client as mqtt
import time

SUBSYSTEM = "subsystem/compressor"

# Logic
def stopped_func(t):
    if t == "RUNNING":
        return "VFD_STARTING"
    return False

def vfd_starting_func(t):
    if t == "RUNNING":
        return "COMPRESSOR_STARTING"
    return False

def compressor_starting_func(t):
    if t == "RUNNING":
        return "RUNNING"
    return False

def running_func(t):
    if t == "STOPPED":
        return "COMPRESSOR_STOPPING"
    return False

def compressor_stopping_func(t):
    if t == "STOPPED":
        return "VFD_STOPPING"
    return False

def vfd_stopping_func(t):
    if t == "STOPPED":
        return "STOPPED"
    return False

STATES_MAP = {
    "STOPPED": stopped_func,
    "VFD_STARTING": vfd_starting_func,
    "COMPRESSOR_STARTING": compressor_starting_func,
    "RUNNING": running_func,
    "COMPRESSOR_STOPPING": compressor_stopping_func,
    "VFD_STOPPING": vfd_stopping_func,
    "FAULT": None,
    "ESTOP": None,
}

STATES = []

for k,v in STATES_MAP.iteritems():
    STATES.append(k)

def state_transitions(current, target):
    func = STATES_MAP[current]
    if func:
        new = STATES_MAP[current](target)
        if new == False:
            print("Error switching from " + current + " to " + target)
            return False
        return new
    return False

# External and internal states
_state = {
    "t_state": "STOPPED",
    "state": "STOPPED",
    "pressure": 0
}

def logic_loop(client):
    # Handle state transitions
    if _state["t_state"] != _state["state"]:
        new_state = state_transitions(_state["state"], _state["t_state"])
        if new_state:
            _state["state"] = new_state

    # Handle simulation
    # These rates are totally arbitrary
    if _state["state"] == "RUNNING":
        if _state["pressure"] < 150:
            _state["pressure"] += 25

    if _state["pressure"] > 0:
        _state["pressure"] -= 10

    # Clamp from 0 to 150
    _state["pressure"] = max(0, min(_state["pressure"], 150))

    # Send status updates
    client.publish(SUBSYSTEM, json.dumps(_state))
    time.sleep(0.1);

# Handle actions
def on_message_set(mosq, obj, msg):
    set_msg = json.loads(msg.payload)
    if "t_state" in set_msg:
        if set_msg["t_state"] in STATES:
            _state["t_state"] = set_msg["t_state"]
        else:
            print("Unknown state: " + set_msg["t_state"])

actions = {
    "set": on_message_set,
}

def on_message(mosq, obj, msg):
    if msg.topic.startswith(SUBSYSTEM + "/"):
        postfix = msg.topic.replace(SUBSYSTEM + "/", "", 1) # Replace the first occurance of SUBSYSTEM/ with ""

        if actions[postfix]:
            actions[postfix](mosq, obj, msg)
            return

    # Ignore our own status upgrades
    if msg.topic == SUBSYSTEM:
        return

    # Handle falling through messages
    print(msg.topic + " " + str(msg.payload))


# Setup client
client = mqtt.Client()
client.connect("localhost", 1883)
client.loop_start()

client.on_message = on_message
client.subscribe(SUBSYSTEM + "/#")

while True:
    logic_loop(client)

client.loop_stop()
