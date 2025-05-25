# GunZ Replay Organizer

A Python GUI tool to automatically organize and rename your GunZ replay (`.gzr`) files as they are created.  
The script monitors a selected folder, waits for new replay files to finish saving, and renames them with a consistent, informative format.

**Warning** - When selecting a folder and starting monitoring all .gzr files will be renamed sequentially. (Suggest moving these to a folder within the Replays folder to prevent altering older files.)(Planned to fix)

---

## Features

- **Automatic folder monitoring** for new `.gzr` files
- **Waits for files to finish writing** before renaming (handles temp files and up to 3 min game time)
- **Customizable file identifier**
- **Sequential counter** for easy sorting
- **Gamemode extraction** from original filename
- **Timestamped filenames**
- **Persistent configuration** (`config.json`)
- **GUI log window** for status and errors

---

## Usage

1. **Install Python 3** (if not already installed).
2. **Install dependencies** (Tkinter is included with most Python installations).
3. **Run the script:**
   ```
   python index.py
   ```
4. **Select the folder** where your GunZ replays are saved.
5. **Set your preferred identifier** (optional).
6. **Click "Start Monitoring"** to begin automatic renaming.
7. **Check the log window** for status and errors.

---

## Filename Format

Renamed files will look like:
```
001_IDENTIFIER[GAMEMODE]_YYYY-MM-DD_HH-MM-SS.gzr
```
- `001` = Counter
- `IDENTIFIER` = Your chosen identifier
- `GAMEMODE` = Extracted from the original filename
- `YYYY-MM-DD_HH-MM-SS` = Timestamp when file was processed

---

## Notes

- The script creates and updates a `config.json` file for your settings.
- If you want to build a standalone `.exe`, use [PyInstaller](https://pyinstaller.org/) (see below).
- Primarily tested on FGunZ, unsure if file format is different on other PServers.

---

## Building an Executable (Optional)

1. Install PyInstaller:
   ```
   pip install pyinstaller
   ```
2. Build:
   ```
   pyinstaller --onefile --windowed --icon=icon.ico index.py
   ```
3. The `.exe` will be in the `dist` folder.


---
## Future Planned

- Adding map/lobby names to file name (May rely on Discord Integration from pserver.)
- Ensuring Compatibility with other PServers. (Primarily tested on FGunZ)
- Add Customability to File Format names.

---

## License

MIT License

---

*Created by NurdOfficial™.*