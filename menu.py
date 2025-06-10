import pygame
import sys
import os
import threading
import time
import json
import re
import PIL.Image
import datetime


# --- CONFIGURATION ---
CONFIG_FILE = "config.json"
FILE_EXTENSION = ".gzr"
MAX_WAIT_SECONDS = 180

RENAMED_PATTERN = re.compile(
    r"^[^()_]+\(\d{3}\)_[A-Za-z0-9]+\[\d{3}\]_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.gzr$"
)

# --- PYGAME SETUP ---
pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 850, 400
BG_COLOR = (30, 30, 30)
BTN_COLOR = (60, 60, 120)
BTN_HOVER = (100, 100, 180)
TEXT_COLOR = (255, 255, 255)
LOG_BG = (40, 40, 40)
LOG_COLOR = (200, 200, 200)
LOG_BG_INFO = (40, 40, 40)
LOG_BG_WARNING = (60, 60, 20)
LOG_BG_ERROR = (60, 20, 20)
LOG_BG_DEFAULT = (50, 50, 60)  # fallback

FONT = pygame.font.SysFont("consolas", 20)
SMALL_FONT = pygame.font.SysFont("consolas", 16)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("GunZ Replay Organizer")
Icon = PIL.Image.open("icon.ico")
Icon = Icon.tobytes(), Icon.size, Icon.mode
pygame.display.set_icon(pygame.image.fromstring(*Icon))






# --- Button Class ---
class Button:
    def __init__(self, text, x, y, w, h, callback):
        self.text = text
        self.rect = pygame.Rect(x, y, w, h)
        self.callback = callback

    def draw(self, surf, mouse):
        color = BTN_HOVER if self.rect.collidepoint(mouse) else BTN_COLOR
        pygame.draw.rect(surf, color, self.rect)
        txt = FONT.render(self.text, True, TEXT_COLOR)
        surf.blit(txt, (self.rect.x + 10, self.rect.y + (self.rect.height-txt.get_height())//2))

    def handle_event(self, event, mouse):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(mouse):
            self.callback()

# --- Log Area ---
class LogArea:
    def __init__(self, x, y, w, h, max_lines=100):
        self.rect = pygame.Rect(x, y, w, h)
        self.lines = []
        self.max_lines = max_lines
        self.scroll = 0
        self.lock = threading.Lock()
        self.line_height = 24

    def log(self, msg, level="info"):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        color = {"info": LOG_COLOR, "warning": (255, 220, 100), "error": (255, 100, 100)}.get(level, LOG_COLOR)
        wrapped = wrap_text(f"[{now}] {msg}", SMALL_FONT, self.rect.width - 10)
        with self.lock:
            for line in wrapped:
                self.lines.append((line, color))
            if len(self.lines) > self.max_lines:
                self.lines = self.lines[-self.max_lines:]
            self.scroll = 0

    def draw(self, surf):
        pygame.draw.rect(surf, LOG_BG, self.rect)
        pygame.draw.rect(surf, (80,80,80), self.rect, 2)
        with self.lock:
            lines_per_screen = self.rect.height // self.line_height
            total_lines = len(self.lines)
            start = max(0, total_lines - lines_per_screen - self.scroll)
            end = start + lines_per_screen
            visible_lines = self.lines[start:end]
            for i, (line, color) in enumerate(visible_lines):
                y = self.rect.y+5 + i*self.line_height
                if i % 2 == 1:
                    pygame.draw.rect(surf, (50,50,60), (self.rect.x+2, y, self.rect.width-4, self.line_height))
                txt = SMALL_FONT.render(line, True, color)
                surf.blit(txt, (self.rect.x+5, y))

    def scroll_up(self):
        with self.lock:
            # Only scroll up if there are more lines above
            lines_per_screen = self.rect.height // 20
            if self.scroll < max(0, len(self.lines) - lines_per_screen):
                self.scroll += 1

    def scroll_down(self):
        with self.lock:
            if self.scroll > 0:
                self.scroll -= 1

# --- Wrap Text ---
def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

# --- CONFIG HANDLING ---
def ensure_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "WATCHED_FOLDER": "",
            "FILE_IDENTIFIER": "Replay",
            "counter": 1
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(default_config, f, indent=4)
            log_area.log("config.json not found. Created default config.json.")
        except Exception as e:
            log_area.log(f"Error creating default config.json: {e}")

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                return {
                    "WATCHED_FOLDER": cfg.get("WATCHED_FOLDER", ""),
                    "FILE_IDENTIFIER": cfg.get("FILE_IDENTIFIER", "Replay"),
                    "counter": cfg.get("counter", 1)
                }
        else:
            return {"WATCHED_FOLDER": "", "FILE_IDENTIFIER": "Replay", "counter": 1}
    except Exception as e:
        log_area.log(f"Error loading config: {e}")
        return {"WATCHED_FOLDER": "", "FILE_IDENTIFIER": "Replay", "counter": 1}

def save_config():
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "WATCHED_FOLDER": WATCHED_FOLDER,
                "FILE_IDENTIFIER": FILE_IDENTIFIER,
                "counter": counter
            }, f, indent=4)
    except Exception as e:
        log_area.log(f"Error saving config: {e}")

# --- FILENAME LOGIC ---
def get_next_filename(timestamp, gamemode):
    global counter
    try:
        # Extract round info if present in gamemode (e.g., "TDM[3]")
        gamemode_clean = gamemode  # keep brackets for round info
        filename = f"{FILE_IDENTIFIER}({counter:03d})_{gamemode_clean}_{timestamp}{FILE_EXTENSION}"
        while os.path.exists(os.path.join(WATCHED_FOLDER, filename)):
            counter += 1
            filename = f"{FILE_IDENTIFIER}({counter:03d})_{gamemode_clean}_{timestamp}{FILE_EXTENSION}"
        return filename
    except Exception as e:
        log_area.log(f"Error generating filename: {e}")
        return f"error_{int(time.time())}{FILE_EXTENSION}"

def is_renamed(fname):
    return bool(RENAMED_PATTERN.match(fname))

# --- MONITORING THREAD ---
def monitor_folder():
    global counter, status
    try:
        pending_files = {}
        file_timestamps = {}
        while monitoring:
            time.sleep(1)
            try:
                current_files = set(f for f in os.listdir(WATCHED_FOLDER) if f.endswith(FILE_EXTENSION))
            except Exception as e:
                log_area.log(f"Error reading folder: {e}")
                continue

            # Add new files to pending_files, but skip already-renamed files
            for fname in current_files:
                if is_renamed(fname):
                    if fname in pending_files:
                        pending_files.pop(fname, None)
                        file_timestamps.pop(fname, None)
                    continue
                if fname not in pending_files:
                    pending_files[fname] = {'wait': 0, 'last_size': None, 'last_mtime': None, 'stable': 0}
                    log_area.log(f"Queued new file: {fname}")

            # Remove files that no longer exist
            for fname in list(pending_files.keys()):
                if fname not in current_files or is_renamed(fname):
                    log_area.log(f"File disappeared or already renamed: {fname}")
                    pending_files.pop(fname, None)
                    file_timestamps.pop(fname, None)

            # Process pending files
            for fname in list(pending_files.keys()):
                file_path = os.path.join(WATCHED_FOLDER, fname)
                try:
                    stat = os.stat(file_path)
                    size = stat.st_size
                    mtime = stat.st_mtime
                except Exception:
                    log_area.log(f"Could not stat file (may have been deleted): {fname}")
                    continue

                entry = pending_files[fname]

                if size == 0:
                    entry['wait'] += 1
                    if entry['wait'] > MAX_WAIT_SECONDS:
                        log_area.log(f"File {fname} did not finalize in time (>{MAX_WAIT_SECONDS}s), skipping.")
                        pending_files.pop(fname, None)
                        file_timestamps.pop(fname, None)
                    continue

                if entry['last_size'] == size and entry['last_mtime'] == mtime:
                    entry['stable'] += 1
                    if entry['stable'] == 1:
                        log_area.log(f"File {fname} appears finalized, checking for stability...")
                else:
                    if entry['stable'] > 0:
                        log_area.log(f"File {fname} changed again, resetting stability counter.")
                    entry['stable'] = 0
                entry['last_size'] = size
                entry['last_mtime'] = mtime

                if entry['stable'] >= 3:
                    gamemode = fname.split("_", 1)[0]
                    try:
                        with open(file_path, "rb"):
                            pass
                        if fname not in file_timestamps:
                            file_timestamps[fname] = time.strftime("%Y-%m-%d_%H-%M-%S")
                        timestamp = file_timestamps[fname]
                        new_name = get_next_filename(timestamp, gamemode)
                        os.rename(
                            file_path,
                            os.path.join(WATCHED_FOLDER, new_name)
                        )
                        counter += 1
                        save_config()
                        log_area.log(f"Renamed {fname} to {new_name}")
                        pending_files.pop(fname, None)
                        file_timestamps.pop(fname, None)
                    except Exception as e:
                        log_area.log(f"Error renaming {fname}: {e}")
    except Exception as e:
        log_area.log(f"Error in monitor_folder: {e}")

# --- BUTTON CALLBACKS ---
def select_folder():
    global WATCHED_FOLDER
    import tkinter.filedialog
    root = tkinter.Tk()
    root.withdraw()
    folder = tkinter.filedialog.askdirectory()
    root.destroy()
    if folder:
        WATCHED_FOLDER = folder
        save_config()
        log_area.log(f"Selected folder: {WATCHED_FOLDER}")

def set_identifier():
    global FILE_IDENTIFIER, counter
    import tkinter.simpledialog
    root = tkinter.Tk()
    root.withdraw()
    identifier = tkinter.simpledialog.askstring("Set Identifier", "Enter file identifier:")
    root.destroy()
    if identifier:
        FILE_IDENTIFIER = identifier
        counter = 1
        save_config()
        log_area.log(f"Identifier set to: {FILE_IDENTIFIER}. Counter reset to 1.")

def start_monitoring():
    global monitoring, monitor_thread, status
    if not WATCHED_FOLDER:
        log_area.log("No folder selected to monitor.")
        return
    if monitoring:
        log_area.log("Monitoring is already running.")
        return
    monitoring = True
    monitor_thread = threading.Thread(target=monitor_folder, daemon=True)
    monitor_thread.start()
    log_area.log(f"Monitoring started. Watching: {WATCHED_FOLDER} Starting with counter: {counter}")

def reset_counter():
    global counter
    counter = 1
    save_config()
    log_area.log("Counter reset to 1.")

# --- UI STATE ---
ensure_config()
config = load_config()
WATCHED_FOLDER = config["WATCHED_FOLDER"]
FILE_IDENTIFIER = config["FILE_IDENTIFIER"]
counter = config["counter"]
monitoring = False
monitor_thread = None

buttons = [
    Button("Select Folder", 30, 40, 200, 40, select_folder),
    Button("Set Identifier", 30, 90, 200, 40, set_identifier),
    Button("Start Monitoring", 30, 150, 200, 40, start_monitoring),
    Button("Reset Counter", 30, 200, 200, 40, reset_counter),
]

log_area = LogArea(400, 30, 430, 320)
log_area.log("GunZ Replay Organizer started.")

# --- Main Loop ---
clock = pygame.time.Clock()
running = True
while running:
    mouse = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            monitoring = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            for btn in buttons:
                btn.handle_event(event, mouse)
            if event.button == 4:  # scroll up
                log_area.scroll_up()
            elif event.button == 5:  # scroll down
                log_area.scroll_down()

    screen.fill(BG_COLOR)
    for btn in buttons:
        btn.draw(screen, mouse)
    log_area.draw(screen)

    # Labels (simulate folder/identifier/status)
    folder_label = SMALL_FONT.render("Watching:", True, TEXT_COLOR)
    screen.blit(folder_label, (30, 260))

    # Wrap the folder path to fit within a certain width (e.g., 340px)
    wrapped_folder_path = wrap_text(f"{WATCHED_FOLDER or '(none)'}", SMALL_FONT, 340)
    for i, line in enumerate(wrapped_folder_path):
        folder_path_label = SMALL_FONT.render(line, True, TEXT_COLOR)
        screen.blit(folder_path_label, (30, 280 + i * 18))

    identifier_label = SMALL_FONT.render(f"Identifier: {FILE_IDENTIFIER}", True, TEXT_COLOR)
    screen.blit(identifier_label, (30, 300 + (len(wrapped_folder_path)-1)*18))

    status_label = SMALL_FONT.render(f"Status: {'Monitoring' if monitoring else 'Idle'}", True, TEXT_COLOR)
    screen.blit(status_label, (30, 320 + (len(wrapped_folder_path)-1)*18))

    # Draw the updating counter at the bottom
    counter_label = SMALL_FONT.render(f"Counter: {counter}", True, TEXT_COLOR)
    screen.blit(counter_label, (30, HEIGHT - 30))

    pygame.display.flip()
    clock.tick(60)

monitoring = False
pygame.quit()