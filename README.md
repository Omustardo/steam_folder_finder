# Steam Folder Finder

This script replaces most of a manual process. When looking for savegame data for Steam games, I used to:
1. Find the game id. I found it easiest to go to protondb and search by name, which finds something like https://www.protondb.com/app/1091500 for Cyberpunk 2077. You can also right click on the game in your Steam library, go to Properties and then Installed Files. It shows the App ID. But you can't copy-paste it from that UI for some reason.
2. Find the relevant local parent directory. I have two ssds so it's either in `/home/omustardo/ssd/SteamLibrary/steamapps/compatdata/` or `/home/omustardo/.steam/debian-installation/steamapps/compatdata`. I would look for the subdirectory with the ID that I found in step 1. For example: `/home/omustardo/.steam/debian-installation/steamapps/compatdata/1091500`
3. Use the pc gaming wiki to find the relevant path from there. For https://www.pcgamingwiki.com/wiki/Cyberpunk_2077 it shows `%LOCALAPPDATA%\CD Projekt Red\Cyberpunk 2077` for windows and `<SteamLibrary-folder>/steamapps/compatdata/1091500/pfx/` for linux.
4. The final directory for the Cyberpunk example is: "/home/omustardo/.steam/debian-installation/steamapps/compatdata/1091500/pfx/drive_c/users/steamuser/AppData/Local/CD Projekt Red/Cyberpunk 2077"

# Install

Download the python file. Run it with the paths to your Steam compatdata directories. I recommend making an alias to run it with these paths provided if you plan on doing this regularly.

# Usage

1. Run:
```
python3 steam_folder_finder.py --steam-library="/home/omustardo/ssd/SteamLibrary/steamapps/compatdata" --steam-library="/home/omustardo/.steam/debian-installation/steamapps/compatdata"
```

2. Input your game's name.

3. Double click to open any of the found paths. Paths towards the top are more likely to be the right one. If you see any labeled as "PC Gaming Wiki", use those since they're almost certainly correct.

![Screenshot from 2025-07-06 21-20-24](https://github.com/user-attachments/assets/18db9b81-3156-4550-9ddf-f01308161ceb)

# Implementation

I made this in an hour or two using Claude. https://claude.ai/public/artifacts/2b2ef357-04d6-4d0c-bf42-95323595360e

1. The script retrieves the full catalog of Steam games, which is used for doing searches on name and ID. This is a ~15mb file that is saved to ~/.cache/steam_apps.json. It is re-downloaded if it is over a week old.
2. The user inputs the game name and selects one in the list that appears.
3. The script looks for compadata paths for each provided `--steam-library`, looking at `compatdata/{AppID}/pfx/drive_c/users/steamuser/`. It specifically looks at `%appdata%` directories (Local, Roaming, LocalLow). It looks for keywords from the game name, common save file names/formats, and recent modifications.
4. The script displays potential paths.
