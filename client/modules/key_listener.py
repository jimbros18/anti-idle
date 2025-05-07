import json
import os
import time
import threading
from pynput import keyboard
from pynput.keyboard import Key, Listener

# File with keybinds
KEYBINDS_FILE = "client/keybinds.json"
# Command names that will be executed
COMMANDS = {
    "start_record": "start_recording",
    "stop": "stop",
    "start_task": "play_task",
}

# Special keys mapping
SPECIAL_KEYS = {k.name: k for k in [
    Key.f1, Key.f2, Key.f3, Key.f4, Key.f5, Key.f6,
    Key.f7, Key.f8, Key.f9, Key.f10, Key.f11, Key.f12,
    Key.ctrl_l, Key.alt_l, Key.shift_l, Key.enter, Key.space
]}

# Track pressed keys
pressed_keys = set()
# Store loaded keybinds
keybinds = {}
# File check interval (seconds)
CHECK_INTERVAL = 5
# Last modification time
last_modified = 0

def load_keybinds():
    """Load keybinds from JSON file."""
    global keybinds, last_modified
    
    if not os.path.exists(KEYBINDS_FILE):
        print(f"Keybinds file not found: {KEYBINDS_FILE}")
        return False
    
    current_modified = os.path.getmtime(KEYBINDS_FILE)
    if current_modified == last_modified:
        # print("No changes to keybinds file")
        return True
    
    try:
        with open(KEYBINDS_FILE, 'r') as f:
            app_data = json.load(f)
        
        keybinds_data = app_data.get("keybinds", {})
        new_keybinds = {}
        for action, [modifier_str, key_str] in keybinds_data.items():
            modifier = SPECIAL_KEYS.get(modifier_str)
            key = SPECIAL_KEYS.get(key_str, key_str)
            if modifier and action in COMMANDS:
                new_keybinds[action] = (modifier, key)
        
        keybinds = new_keybinds
        last_modified = current_modified
        print("Keybinds loaded:", {action: (mod.name, key.name if hasattr(key, 'name') else key) 
                                  for action, (mod, key) in keybinds.items()})
        return True
            
    except Exception as e:
        print(f"Error loading keybinds: {e}")
    return False

def is_paused():
    """Check if the listener should be paused."""
    return os.path.exists("pause_listener.trigger")

def check_keybinds_file():
    """Periodically check if keybinds file has changed."""
    while True:
        if not is_paused():  # Only check keybinds when not paused
            load_keybinds()
        time.sleep(CHECK_INTERVAL)

def execute_command(command):
    """Execute a command in the main app by creating a trigger file."""
    # print(f"Executing command: {command}")
    with open(f"{command}.trigger", 'w') as f:
        f.write(str(time.time()))

def on_press(key):
    if is_paused():
        return  # Skip key detection when paused
    pressed_keys.add(key)
    # print(f"Key pressed: {key} (type: {type(key)})")
    # print(f"Current pressed keys: {[k.name if hasattr(k, 'name') else k for k in pressed_keys]}")
    
    for action, (modifier, bind_key) in keybinds.items():
        if modifier in pressed_keys:
            key_matches = False
            if isinstance(bind_key, str) and hasattr(key, 'char') and key.char:
                key_matches = key.char.lower() == bind_key
                print(f"String comparison: '{key.char.lower()}' == '{bind_key}' = {key_matches}")
            elif isinstance(bind_key, Key) and isinstance(key, Key):
                key_matches = key == bind_key
                print(f"Key object comparison: {key} == {bind_key} = {key_matches}")
            if key_matches:
                print(f"Detected keybind for action: {action}")
                execute_command(COMMANDS[action])
                pressed_keys.clear()  # Clear after triggering to prevent repeats
                break

def on_release(key):
    if is_paused():
        return  # Skip key release when paused
    if key in pressed_keys:
        pressed_keys.remove(key)
        # print(f"Key released: {key}")
    
    if key == Key.esc and Key.ctrl_l in pressed_keys:
        return False

def main():
    if not load_keybinds():
        print("No valid keybinds found. Creating default keybinds file...")
        default_keybinds = {
            "start_record": ["shift_l", "r"],
            "stop": ["shift_l", "q"],
            "start_task": ["shift_l", "s"]
        }
        with open(KEYBINDS_FILE, 'w') as f:
            json.dump({"app_name": "Recorder", "keybinds": default_keybinds}, f, indent=2)
        load_keybinds()
    
    threading.Thread(target=check_keybinds_file, daemon=True).start()
    
    print("Key listener started (press Ctrl+Esc to exit)")
    with Listener(on_press=on_press, on_release=on_release) as listener:
        while listener.running:
            if is_paused():
                # print("Key listener paused")
                time.sleep(1)  # Reduce CPU usage while paused
            else:
                time.sleep(0.1)  # Small sleep to avoid tight loop when active
        listener.join()

if __name__ == "__main__":
    main()