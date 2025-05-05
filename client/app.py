import time
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
# import tkinter.filedialog as filedialog
from tkinter import END, filedialog, simpledialog, messagebox
from ttkbootstrap.constants import *
from pynput import mouse, keyboard
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.keyboard import Listener
import threading
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import json
import os
import pickle
import subprocess
import sys
import atexit
# import asyncio

from modules.app_utils import *

# Global process variable for key_listener.py
key_listener_process = None
settings_active = False  # Flag to track if settings page is in focus

def start_key_listener():
    """Start key_listener.py in the background using the same Python interpreter."""
    global key_listener_process
    if not os.path.exists("client/modules/key_listener.py"):
        print("Error: key_listener.py not found in current directory")
        return
    python_executable = sys.executable
    key_listener_process = subprocess.Popen([python_executable, "client/modules/key_listener.py"])
    print(f"Started key_listener.py in background with PID: {key_listener_process.pid}")

def stop_key_listener():
    """Stop the key_listener.py process."""
    global key_listener_process
    if key_listener_process and key_listener_process.poll() is None:
        print("Stopping key_listener.py...")
        key_listener_process.terminate()
        try:
            key_listener_process.wait(timeout=2)
            print("key_listener.py stopped gracefully")
        except subprocess.TimeoutExpired:
            key_listener_process.kill()
            print("key_listener.py forcefully stopped")
    key_listener_process = None

atexit.register(stop_key_listener)

# Initialize controllers
mouse_ctrl = MouseController()
keyboard_ctrl = KeyboardController()

# Store recorded events
events = []
recording = False
looping = False
playing = False

# Current sequence name (for saving)
current_sequence_name = "Untitled"
default_save_dir = "client/saved_sequences"

# Time to wait between loops (in seconds)
LOOP_INTERVAL = 5

# Special keys mapping
SPECIAL_KEYS = {k.name: k for k in [
    Key.f1, Key.f2, Key.f3, Key.f4, Key.f5, Key.f6,
    Key.f7, Key.f8, Key.f9, Key.f10, Key.f11, Key.f12,
    Key.ctrl_l, Key.alt_l, Key.shift_l, Key.enter, Key.space
]}

# Default keybinds (matching key_listener.py)
DEFAULT_KEYBINDS = {
    "start_record": ["shift_l", "s"],
    "stop_record": ["shift_l", "p"],
    "start_task": ["shift_l", "r"],
    "end_task": ["shift_l", "q"]
}

# File to store keybinds
KEYBINDS_FILE = "client/keybinds.json"

# Current keybinds (modifiable)
keybinds = DEFAULT_KEYBINDS.copy()
pending_keybinds = keybinds.copy()

# Default app name
DEFAULT_APP_NAME = "Anti-Idle"

# ========================== Functions for mouse/keyboard events recording ==============================

def on_move(x, y):
    if recording:
        events.append(('move', (x, y), time.time()))

def on_click(x, y, button, pressed):
    if recording and pressed:
        events.append(('click', (x, y, button), time.time()))

def on_press(key):
    if recording:
        events.append(('key_press', key, time.time()))

def on_release(key):
    if recording:
        events.append(('key_release', key, time.time()))

# ============================== Record and playback functions ===================================
def start_recording():
    global recording, current_sequence_name
    if not recording:
        current_sequence_name = "Untitled"
        recording = True
        events.clear()
        status_var.set("Recording started...")
        print("start_recording executed")

def stop_recording():
    global recording
    if recording:
        recording = False
        if events:
            status_var.set(f"Recording stopped ({len(events)} events)")
            root.after(0, ask_to_save)
        else:
            status_var.set("Recording stopped (no events)")
        print("stop_recording executed")

def playback():
    global playing
    if not events:
        status_var.set("No events recorded!")
        return
    playing = True
    status_var.set("Playing...")
    print("playback started")
    start_time = events[0][2]
    for event in events:
        if not looping:
            print("playback stopped by looping flag")
            break
        action, data, event_time = event
        sleep_time = max(0, event_time - start_time)
        elapsed = 0
        while elapsed < sleep_time and looping:
            time.sleep(min(0.1, sleep_time - elapsed))
            elapsed += 0.1
        if not looping:
            print("playback interrupted mid-sleep")
            break
        if action == 'move':
            mouse_ctrl.position = data
        elif action == 'click':
            x, y, button = data
            mouse_ctrl.position = (x, y)
            mouse_ctrl.click(button)
        elif action == 'key_press':
            keyboard_ctrl.press(data)
        elif action == 'key_release':
            keyboard_ctrl.release(data)
        start_time = event_time
    for key in [Key.shift_l, Key.shift_r, Key.ctrl_l, Key.ctrl_r, Key.alt_l, Key.alt_r]:
        keyboard_ctrl.release(key)
    playing = False
    print("playback finished")

def loop_playback():
    global looping, playing
    looping = True
    print("loop_playback started")
    while looping:
        playback()
        if looping:
            status_var.set(f"Wait {LOOP_INTERVAL}s...")
            elapsed = 0
            while elapsed < LOOP_INTERVAL and looping:
                time.sleep(min(0.1, LOOP_INTERVAL - elapsed))
                elapsed += 0.1
            print(f"Loop interval completed: {LOOP_INTERVAL}s")
    status_var.set("Task stopped.")
    playing = False
    print("loop_playback stopped")

def start_task():
    if not looping and events:
        status_var.set("Starting loop...")
        print("start_task executed")
        threading.Thread(target=loop_playback, daemon=True).start()

def end_task():
    global looping
    looping = False
    status_var.set("Stopping task...")
    for key in [Key.shift_l, Key.shift_r, Key.ctrl_l, Key.ctrl_r, Key.alt_l, Key.alt_r]:
        keyboard_ctrl.release(key)
    print("end_task executed")

# ========================== File operations for sequences =======================================================
def save_sequence():
    global events, current_sequence_name
    # Check if there are events to save
    if not events:
        messagebox.showwarning("Warning", "No events to save")
        return
    
    # Ensure default save directory exists
    if not os.path.exists(default_save_dir):
        os.makedirs(default_save_dir)
    
    # Open standard file save dialog
    initial_dir = os.path.abspath(default_save_dir)  # Default to default_save_dir
    file_path = filedialog.asksaveasfilename(
        initialdir=initial_dir,
        title="Save Sequence",
        defaultextension=".seq",
        filetypes=[("Sequence files", "*.seq"), ("All files", "*.*")],
        initialfile=current_sequence_name if current_sequence_name != "Untitled" else ""
    )
    
    # Check if user selected a file (didn't cancel)
    if file_path:
        try:
            # Update current_sequence_name based on selected file
            current_sequence_name = os.path.basename(file_path)
            if not current_sequence_name.endswith('.seq'):
                current_sequence_name += '.seq'
                file_path = os.path.join(os.path.dirname(file_path), current_sequence_name)
            
            # Save events using pickle
            with open(file_path, 'wb') as f:
                pickle.dump(events, f)
            
            # Refresh sequence list
            refresh_sequence_list()
            print(f"Sequence saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save sequence: {e}")

# def load_sequence():
#     global events, current_sequence_name
#     if not os.path.exists(default_save_dir):
#         os.makedirs(default_save_dir)
#     file_path = filedialog.askopenfilename(initialdir=default_save_dir, title="Load Sequence", filetypes=(("Sequence files", "*.seq"), ("All files", "*.*")))
#     if file_path:
#         try:
#             with open(file_path, 'rb') as f:
#                 events = pickle.load(f)
#             current_sequence_name = os.path.basename(file_path)
#             status_var.set(f"Loaded: {current_sequence_name} ({len(events)} events)")
#         except Exception as e:
#             messagebox.showerror("Error", f"Failed to load sequence: {e}")

def ask_to_save():
    if messagebox.askyesno("Save Sequence", "Do you want to save this sequence?"):
        save_sequence()

def delete_sequence(filename):
    file_path = os.path.join(default_save_dir, filename)
    if os.path.exists(file_path):
        if messagebox.askyesno("Confirm Delete", f"Delete sequence: {filename}?"):
            try:
                os.remove(file_path)
                refresh_sequence_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete file: {e}")

def rename_sequence(old_name):
    old_path = os.path.join(default_save_dir, old_name)
    if os.path.exists(old_path):
        new_name = simpledialog.askstring("Rename Sequence", "Enter new name:", initialvalue=os.path.splitext(old_name)[0])
        if new_name:
            if not new_name.endswith('.seq'):
                new_name += '.seq'
            new_path = os.path.join(default_save_dir, new_name)
            try:
                os.rename(old_path, new_path)
                refresh_sequence_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to rename file: {e}")

def create_sequence_item(parent, filename):
    frame = ttk.Frame(parent)
    frame.pack(fill=X, pady=2)
    name_btn = ttk.Button(frame, text=filename, bootstyle=DEFAULT, command=lambda: load_specific_sequence(filename))
    name_btn.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
    btn_frame = ttk.Frame(frame)
    btn_frame.pack(side=RIGHT)
    ttk.Button(btn_frame, text="🔄", width=2, bootstyle=INFO, command=lambda: rename_sequence(filename)).pack(side=LEFT, padx=1)
    ttk.Button(btn_frame, text="❌", width=2, bootstyle=DANGER, command=lambda: delete_sequence(filename)).pack(side=LEFT, padx=1)
    return frame

def load_specific_sequence(filename):
    global events, current_sequence_name
    file_path = os.path.join(default_save_dir, filename)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'rb') as f:
                events = pickle.load(f)
            current_sequence_name = filename
            status_var.set(f"Loaded: {filename} ({len(events)} events)")
            show_main()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load sequence: {e}")

def refresh_sequence_list():
    for widget in sequence_frame.winfo_children():
        if widget != sequence_title_frame:
            widget.destroy()
    if not os.path.exists(default_save_dir):
        os.makedirs(default_save_dir)
    seq_files = [f for f in os.listdir(default_save_dir) if f.endswith('.seq')]
    if seq_files:
        for filename in sorted(seq_files):
            create_sequence_item(sequence_frame, filename)
    else:
        ttk.Label(sequence_frame, text="No saved sequences found", bootstyle="secondary").pack(pady=20)

# =================================== Keybind management ====================================================
def save_keybinds_to_file():
    app_data = {"app_name": app_name_var.get(), "keybinds": keybinds}
    with open(KEYBINDS_FILE, 'w') as f:
        json.dump(app_data, f, indent=2)
    print(f"Keybinds saved to {KEYBINDS_FILE}")

def load_keybinds_from_file():
    global keybinds, pending_keybinds
    if not os.path.exists(KEYBINDS_FILE):
        print(f"Keybinds file not found: {KEYBINDS_FILE}, creating default")
        save_keybinds_to_file()
        return False
    try:
        with open(KEYBINDS_FILE, 'r') as f:
            app_data = json.load(f)
        if "app_name" in app_data:
            app_name_var.set(app_data["app_name"])
        keybinds_data = app_data.get("keybinds", {})
        new_keybinds = {}
        for action, [modifier_str, key_str] in keybinds_data.items():
            if action in DEFAULT_KEYBINDS:
                new_keybinds[action] = [modifier_str, key_str]
        if new_keybinds:
            keybinds = new_keybinds
            pending_keybinds = keybinds.copy()
            update_keybind_labels()
            print("Keybinds loaded successfully")
            return True
        else:
            keybinds = DEFAULT_KEYBINDS.copy()
            pending_keybinds = keybinds.copy()
            save_keybinds_to_file()
            update_keybind_labels()
            print("No valid keybinds found, reset to defaults")
            return False
    except Exception as e:
        print(f"Error loading keybinds: {e}")
        return False

def reset_to_defaults():
    global keybinds, pending_keybinds
    app_name_var.set(DEFAULT_APP_NAME)
    title_label.config(text=DEFAULT_APP_NAME)
    root.title(DEFAULT_APP_NAME)
    keybinds = DEFAULT_KEYBINDS.copy()
    pending_keybinds = DEFAULT_KEYBINDS.copy()
    update_keybind_labels()

def update_keybind(action, modifier_name, key_name):
    if modifier_name in SPECIAL_KEYS and action in pending_keybinds:
        pending_keybinds[action] = [modifier_name, key_name]
        print(f"Pending update for {action}: {modifier_name}+{key_name}")

def record_keybind(label, action):
    label.config(text="Press combo...")
    temp_keys = []

    def on_key_press(key):
        if key in SPECIAL_KEYS.values():
            key_name = key.name
        elif hasattr(key, 'char') and key.char:
            key_name = key.char.lower()
        else:
            return
        if key_name not in temp_keys and len(temp_keys) < 2:
            temp_keys.append(key_name)
            label.config(text="+".join(temp_keys))

    def on_key_release(key):
        if key in SPECIAL_KEYS.values():
            key_name = key.name
        elif hasattr(key, 'char') and key.char:
            key_name = key.char.lower()
        else:
            return
        if key_name in temp_keys:
            temp_keys.remove(key_name)
        if not temp_keys and len(label.cget("text").split("+")) == 2:
            modifier_name, key_name = label.cget("text").split("+")
            update_keybind(action, modifier_name, key_name)
            listener.stop()

    listener = Listener(on_press=on_key_press, on_release=on_key_release)
    listener.start()

def apply_keybinds():
    global keybinds
    keybinds = pending_keybinds.copy()
    title_label.config(text=app_name_var.get())
    root.title(app_name_var.get())
    update_keybind_labels()
    save_keybinds_to_file()
    print("Keybinds updated:", {action: f"{mod}+{key}" for action, [mod, key] in keybinds.items()})

def update_keybind_labels():
    action_map = {
        "start": "start_record",
        "stop": "stop_record",
        "task": "start_task",
        "end": "end_task"
    }
    for widget in settings_frame.winfo_children():
        if isinstance(widget, ttk.Frame):
            children = widget.winfo_children()
            if len(children) >= 2:
                action_label = children[0]
                keybind_label = children[1]
                if isinstance(action_label, ttk.Label) and action_label.cget("text") != "Title:":
                    short_action = action_label.cget("text").replace(":", "").lower()
                    full_action = action_map.get(short_action)
                    if full_action is None:
                        print(f"Warning: No mapping for short_action '{short_action}'")
                        continue
                    modifier, key = pending_keybinds[full_action]
                    keybind_label.config(text=f"{modifier}+{key}")

# =============================== Window management =====================================
def start_drag(event):
    root.x = event.x
    root.y = event.y

def drag_window(event):
    deltax = event.x - root.x
    deltay = event.y - root.y
    x = root.winfo_x() + deltax
    y = root.winfo_y() + deltay
    root.geometry(f"+{x}+{y}")

# icon = None
def hide_to_tray():
    global icon
    # If an icon already exists, stop it to prevent duplicates
    if icon is not None:
        try:
            icon.stop()
            icon = None
            print("Existing tray icon stopped")
        except Exception as e:
            print(f"Error stopping existing tray icon: {e}")
    
    root.withdraw()  # Hide the window to start in system tray
    try:
        # Try loading a custom icon (ensure the path is correct)
        image = Image.open("client/assets/icon.png")  # Updated path as per your code
    except FileNotFoundError:
        # Fallback to a simple black-and-white square if icon.png is missing
        image = Image.new('RGB', (16, 16), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((4, 4, 12, 12), fill=(255, 255, 255))
        print("Warning: icon.png not found, using fallback icon")
    
    # Create a new tray icon with proper callbacks
    icon = pystray.Icon("Recorder", image, "Action Recorder", menu=pystray.Menu(
        item('Restore', lambda: show_app()),  # Use lambda to defer execution
        item('Quit', lambda: close_app())     # Use lambda to defer execution
    ))
    threading.Thread(target=icon.run, daemon=True).start()
    print("Hidden to tray with new icon")

def show_app(icon=None):
    global  root
    # Restore the window
    root.deiconify()
    root.geometry("200x255+100+100")
    root.attributes('-topmost', True)
    root.update()
    root.attributes('-topmost', False)
    root.lift()
    
    # Stop the tray icon to remove it from the system tray
    if icon is not None:
        try:
            icon.stop()
            icon = None
            print("Tray icon stopped on restore")
        except Exception as e:
            print(f"Error stopping tray icon on restore: {e}")
    print("Restored window")

def close_app():
    global looping, icon, mouse_listener, keyboard_listener
    looping = False
    # Stop listeners
    if mouse_listener:
        mouse_listener.stop()
    if keyboard_listener:
        keyboard_listener.stop()
    # Stop tray icon if it exists
    if icon:
        try:
            icon.stop()
            icon = None
            print("Tray icon stopped on close")
        except Exception as e:
            print(f"Error stopping tray icon on close: {e}")
    # Stop key listener process
    stop_key_listener()
    # Clean up trigger file
    if os.path.exists("client/pause_listener.trigger"):
        os.remove("client/pause_listener.trigger")
    # Release modifier keys
    for key in [Key.shift_l, Key.shift_r, Key.ctrl_l, Key.ctrl_r, Key.alt_l, Key.alt_r]:
        keyboard_ctrl.release(key)
    root.destroy()
    print("App fully closed")

def check_for_triggers():
    global settings_active
    if settings_active:
        # print("Triggers paused (settings active)")
        root.after(100, check_for_triggers)
        return
    # print("Checking triggers...")
    for command in ["start_recording", "stop_recording", "start_task", "end_task"]:
        trigger_file = f"{command}.trigger"
        if os.path.exists(trigger_file):
            print(f"Trigger file found: {trigger_file}")
            try:
                globals()[command]()
                os.remove(trigger_file)
                print(f"Trigger {command} executed and file removed")
            except Exception as e:
                print(f"Error executing triggered command {command}: {e}")
    root.after(100, check_for_triggers)

# ================================= Navigation functions ===================================
def show_main():
    global settings_active
    settings_frame.pack_forget()
    sequence_frame.pack_forget()
    main_frame.pack(expand=True, fill=BOTH, padx=5, pady=5)
    settings_active = False
    if os.path.exists("client/pause_listener.trigger"):
        os.remove("client/pause_listener.trigger")
    print("Main page shown, triggers resumed")

def show_sequences():
    global settings_active
    main_frame.pack_forget()
    settings_frame.pack_forget()
    sequence_frame.pack(expand=True, fill=BOTH, padx=5, pady=5)
    settings_active = False
    if os.path.exists("client/pause_listener.trigger"):
        os.remove("client/pause_listener.trigger")
    print("Sequences page shown, triggers resumed")

def show_settings():
    global settings_active
    main_frame.pack_forget()
    sequence_frame.pack_forget()
    info_frm.pack_forget()
    act_frm.pack_forget()
    settings_frame.pack(expand=True, fill=BOTH, padx=5, pady=5)
    settings_active = True
    with open("client/pause_listener.trigger", "w") as f:
        f.write("")  # Create pause signal for key_listener.py
    print("Settings page shown, triggers paused")

def show_info():
    # content = find_txt()
    key = read_serial(KEY_PATH)
    if key:
        activate(key['key'])
    else:    
        main_frame.pack_forget()
        sequence_frame.pack_forget()
        settings_frame.pack_forget()
        info_frm.pack(expand=True, fill=BOTH, padx=5, pady=5)

def activate_btn(ser_key):
    data = validate_key(ser_key)
    if data is None:
        print(f'app.py: {data}')
        info_lbl.config(text='Invalid serial key!')
    elif data['status'] == 'licensed':
        # print(f'activate: {data}')
        activate(data)


def activate(content):
    main_frame.pack_forget()
    sequence_frame.pack_forget()
    settings_frame.pack_forget()
    info_frm.pack_forget()
    act_frm.pack(expand=True, fill=BOTH, padx=5, pady=5)
    sk_entry.delete(0, END)  # Clear existing content
    sk_entry.insert(0,str(content))
    
# ========================================== GUI variables ==============================================
status_var = None
app_name_var = None
root = None
main_frame = None
settings_frame = None
sequence_frame = None
info_frm = None
icon = None
mouse_listener = None
keyboard_listener = None
title_label = None
ser_key = None
act_frm = None
sk_entry = None
act_lbl = None
info_lbl = None

def center_window(root, width, height):
    """Center the window on the primary screen."""
    root.update_idletasks()  # Ensure window metrics are ready
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")

def create_gui():
    global status_var, app_name_var, root, main_frame, settings_frame, sequence_frame, ser_key, sk_entry, info_lbl
    global title_label, sequence_title_frame, mouse_listener, keyboard_listener, info_frm, act_frm, act_lbl
    
    root = ttk.Window(themename='darkly')
    # root.geometry("200x255")
    root.overrideredirect(True)
    root.resizable(False, False)
    
    app_name_var = ttk.StringVar(value=DEFAULT_APP_NAME)
    root.title(app_name_var.get())

    # Define window size
    WINDOW_WIDTH = 200
    WINDOW_HEIGHT = 255
    center_window(root, WINDOW_WIDTH, WINDOW_HEIGHT)
    
    title_bar = ttk.Frame(root, bootstyle="dark")
    title_bar.pack(fill=X, pady=0, ipady=5)
    title_label = ttk.Label(title_bar, text=app_name_var.get(), bootstyle="inverse-dark")
    title_label.pack(side=LEFT, padx=5)
    ttk.Button(title_bar, text="x", command=close_app, bootstyle="danger", padding=(1, 1), width=2).pack(side=RIGHT, padx=5)
    ttk.Button(title_bar, text="-", command=hide_to_tray, bootstyle=SECONDARY, padding=(1, 1), width=2).pack(side=RIGHT, padx=5)
    title_bar.bind("<Button-1>", start_drag)
    title_bar.bind("<B1-Motion>", drag_window)
    
    status_var = ttk.StringVar(value="Ready")
    
    main_frame = ttk.Frame(root)
    main_frame.pack(expand=True, fill=BOTH, padx=5, pady=5)
    
    ttk.Label(main_frame, textvariable=status_var).pack(pady=5)
    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(pady=5)

        # Click + style logic
    def on_label_click(label_key):
        for lbl in labels.values():
            lbl.configure(style="TLabel")
        labels[label_key].configure(style="Active.TLabel")
        actions[label_key]()

    def on_hover_enter(e):
        e.widget.configure(style="Hover.TLabel")

    def on_hover_leave(e):
        if e.widget != active_label:
            e.widget.configure(style="TLabel")

    # Actions
    def start_recording(): print("Recording started.")
    def stop_recording(): print("Recording stopped.")
    def start_task(): print("Task started.")
    def end_task(): print("Task ended.")

    # Styles
    style = ttk.Style()
    style.configure("TLabel", padding=10)
    style.configure("Hover.TLabel", background="#666", foreground="white", padding=10)
    style.configure("Active.TLabel", background="#5bc0de", foreground="white", padding=10, relief="groove")

    labels = {}
    actions = {
        "start_rec": start_recording,
        "stop_rec": stop_recording,
        "start_task": start_task,
        "end_task": end_task
    }

    tooltips = {
    "start_rec": "Begin recording session",
    "stop_rec": "Stop the recording",
    "start_task": "Begin task execution",
    "end_task": "Stop and finalize task"
}
    
    active_label = None

    def iconizer(image_path, size):
            size = (size, size)
            image = Image.open(image_path).resize(size, Image.LANCZOS)
            return ImageTk.PhotoImage(image)

        # Store icons to prevent garbage collection
    icons = {
        "start_rec": iconizer("client/assets/record.png", 20),
        "stop_rec": iconizer("client/assets/stop.png", 20),
        "start_task": iconizer("client/assets/play.png", 20),
        "end_task": iconizer("client/assets/pause.png", 20),
        "save": iconizer("client/assets/save.png", 20),
        "load": iconizer("client/assets/folder.png", 20)
    }

    # Create interactive labels
    for i, (key, text) in enumerate([
        ("start_rec", "Start Rec"),
        ("stop_rec", "Stop Rec"),
        ("start_task", "Start Task"),
        ("end_task", "End Task")
    ]):
        row, col = divmod(i, 2)
        label = ttk.Label(btn_frame, text=text, image=icons[key], compound="top", style="TLabel")
        label.grid(row=row, column=col, padx=5, pady=5)

        label.bind("<Enter>", on_hover_enter)
        label.bind("<Leave>", on_hover_leave)
        label.bind("<Button-1>", lambda e, k=key: on_label_click(k))
        ToolTip(label, text=tooltips[key])  # ✅ Use only ttkbootstrap's tooltip
        labels[key] = label



    # ttk.Button(btn_frame, text="Start Rec", image=start, command=start_recording, bootstyle=SUCCESS).grid(row=0, column=0, padx=5, pady=5)
    # ttk.Button(btn_frame, text="Stop Rec", command=stop_recording, bootstyle=WARNING).grid(row=0, column=1, padx=5, pady=5)
    # ttk.Button(btn_frame, text="Start Task", image=play, command=start_task, bootstyle=INFO).grid(row=1, column=0, padx=5, pady=5)
    # ttk.Button(btn_frame, text="End Task", command=end_task, bootstyle=DANGER).grid(row=1, column=1, padx=5, pady=5)
    
    file_frame = ttk.Frame(main_frame)
    file_frame.pack(pady=5)
    ttk.Button(file_frame, text="Save", command=save_sequence, bootstyle=SUCCESS).grid(row=0, column=0, padx=5, pady=5)
    # ttk.Button(file_frame, text="Load", command=load_sequence, bootstyle=INFO).grid(row=0, column=1, padx=5, pady=5)
    
    nav_frame = ttk.Frame(main_frame)
    nav_frame.pack(pady=(10, 5))
    ttk.Button(nav_frame, text="Sequences", command=show_sequences, bootstyle=PRIMARY).pack(side=LEFT, padx=2)
    ttk.Button(nav_frame, text="Settings", command=show_settings, bootstyle=SECONDARY).pack(side=LEFT, padx=2)
    
    settings_frame = ttk.Frame(root)
    title_frame = ttk.Frame(settings_frame)
    title_frame.pack(pady=2)
    ttk.Label(title_frame, text="Title:", width=10).pack(side=LEFT)
    ttk.Entry(title_frame, textvariable=app_name_var, width=10).pack(side=LEFT)
    
    action_labels = {
        "start_record": "Start:",
        "stop_record": "Stop:",
        "start_task": "Task:",
        "end_task": "End:"
    }

    for action, (modifier, key) in keybinds.items():
        frame = ttk.Frame(settings_frame)
        frame.pack(pady=2, padx=10, fill="x")
        ttk.Label(frame, text=action_labels[action], width=10).pack(side=LEFT)
        label_key = ttk.Label(frame, text=f"{modifier}+{key}", font=("Arial", 10), cursor="hand2")
        label_key.pack(side=LEFT, padx=10)
        label_key.bind("<Button-1>", lambda event, a=action, l=label_key: record_keybind(l, a))
    
    btn_frame = ttk.Frame(settings_frame)
    btn_frame.pack(pady=5)
    ttk.Button(btn_frame, text="Apply", command=apply_keybinds, bootstyle=SUCCESS).grid(row=0, column=0, padx=2)
    ttk.Button(btn_frame, text="Default", command=reset_to_defaults, bootstyle=WARNING).grid(row=0, column=1, padx=2)
    ttk.Button(btn_frame, text="Back", command=show_main, bootstyle=SECONDARY).grid(row=0, column=2, padx=2)
    ttk.Button(btn_frame, text="i", command=show_info, bootstyle=SECONDARY).grid(row=1, column=2, padx=2, pady=20)
    
    info_frm = ttk.Frame(root)
    info_frm.grid_columnconfigure(0, weight=1)
    info_lbl = ttk.Label(info_frm, text='Activate')
    info_lbl.grid(row=0, column=0, padx=5, pady=5)
    ser_key = ttk.StringVar()
    ttk.Entry(info_frm, width=50, textvariable=ser_key).grid(row=1, column=0, padx=5, pady=5)
    ttk.Button(info_frm, text='Run', command=lambda:activate_btn(ser_key.get())).grid(row=2, column=0, padx=5, pady=5)
    ttk.Button(info_frm, text='Back', width=5, padding=(2,2), command=show_settings).grid(row=3, column=0, pady=(70,0), sticky='e')

    act_frm = ttk.Frame(root)
    act_frm.grid_columnconfigure(0, weight=1)
    act_lbl = ttk.Label(act_frm, text='App Activated')
    act_lbl.grid(row=0, column=0, padx=5, pady=5)
    ttk.Label(act_frm, text='Serial Key').grid(row=1, column=0, padx=5, pady=5)
    sk_entry = ttk.Entry(act_frm)
    sk_entry.grid(row=2, column=0, padx=5, pady=5)
    ttk.Button(act_frm, text="Back", command=show_settings, bootstyle=SECONDARY).grid(row=3, column=0, padx=2)
    
    sequence_frame = ttk.Frame(root)
    sequence_title_frame = ttk.Frame(sequence_frame)
    sequence_title_frame.pack(fill=X, pady=5)
    ttk.Label(sequence_title_frame, text="Saved Sequences", font=("Arial", 10, "bold")).pack(side=LEFT)
    ttk.Button(sequence_title_frame, text="↻", width=2, command=refresh_sequence_list, bootstyle=INFO).pack(side=RIGHT, padx=2)
    ttk.Button(sequence_title_frame, text="Back", command=show_main, bootstyle=SECONDARY).pack(side=RIGHT, padx=2)

    
    for key in [Key.shift_l, Key.shift_r, Key.ctrl_l, Key.ctrl_r, Key.alt_l, Key.alt_r]:
        keyboard_ctrl.release(key)
    
    mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click)
    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    mouse_listener.start()
    keyboard_listener.start()
    
    start_key_listener()
    load_keybinds_from_file()
    check_for_triggers()
    
    stat = status_check()
    if stat is None:
        messagebox.showwarning("Error.", "Please relaunch the app.")
        root.destroy()
        return
    elif stat == 'licensed':
        print('LICENSED')
    elif stat <= 14:
        messagebox.showinfo("Trial", f"{14-stat} days left of your trial.")
    elif stat > 14:
        messagebox.showwarning("Trial period ended.", "Your 14-day trial has ended.")
        root.destroy()
        return
    
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))
    # hide_to_tray()
    root.mainloop()

if __name__ == "__main__":
    if not os.path.exists(default_save_dir):
        os.makedirs(default_save_dir)
    create_gui()