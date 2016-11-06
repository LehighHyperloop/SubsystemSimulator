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
e_state = {
    "state": "STOPPED",
    "pressure": 0
}
i_state = {
    "target_state": "STOPPED"
}

def logic_loop(client):
    # Handle state transitions
    if i_state["target_state"] != e_state["state"]:
        new_state = state_transitions(e_state["state"], i_state["target_state"])
        if new_state:
            e_state["state"] = new_state

    # Handle simulation
    # These rates are totally arbitrary
    if e_state["state"] == "RUNNING":
        if e_state["pressure"] < 150:
            e_state["pressure"] += 25

    if e_state["pressure"] > 0:
        e_state["pressure"] -= 10

    # Clamp from 0 to 150
    e_state["pressure"] = max(0, min(e_state["pressure"], 150))

    # Send status updates
    client.publish(SUBSYSTEM, json.dumps(e_state))
    time.sleep(0.1);

# Handle actions
def on_message_set(mosq, obj, msg):
    set_msg = json.loads(msg.payload)
    if "state" in set_msg:
        if set_msg["state"] in STATES:
            i_state["target_state"] = set_msg["state"]
        else:
            print("Unknown state: " + set_msg["state"])

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
client.connect("192.168.0.100", 1883)
client.loop_start()

client.on_message = on_message
client.subscribe(SUBSYSTEM + "/#")

while True:
    logic_loop(client)

client.loop_stop()
