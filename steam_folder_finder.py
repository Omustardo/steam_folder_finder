#!/usr/bin/env python3
"""
Steam Game Folder Finder
A GUI tool to find save game folders for Steam games running through Proton on Linux.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import subprocess
import threading
import urllib.request
import urllib.error
from pathlib import Path
import time
import argparse

class SteamGameFinder:
    def __init__(self, steam_libraries=None):
        self.root = tk.Tk()
        self.root.title("Steam Game Folder Finder")
        self.root.geometry("900x700")
        
        # Steam library paths (from CLI args or defaults)
        self.steam_libraries = steam_libraries or [
            "/home/omustardo/ssd/SteamLibrary/steamapps/compatdata/",
            "/home/omustardo/.steam/debian-installation/steamapps/compatdata/"
        ]
        
        # Cache for Steam app list
        self.steam_apps = []
        self.cache_file = os.path.expanduser("~/.cache/steam_apps.json")
        
        self.setup_ui()
        self.load_steam_apps()
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Description section
        desc_frame = ttk.LabelFrame(main_frame, text="About", padding="10")
        desc_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        desc_frame.columnconfigure(0, weight=1)
        
        desc_text = "Find save game folders for Steam games running through Proton on Linux."
        
        ttk.Label(desc_frame, text=desc_text, justify=tk.LEFT).grid(
            row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10)
        )
        
        # Usage instructions
        usage_text = ("Usage: python3 steam_folder_finder.py [--steam-library PATH] [--steam-library PATH2]\n"
                     "Use --steam-library flags to override default Steam library locations.")
        ttk.Label(desc_frame, text=usage_text, justify=tk.LEFT, font=("Courier", 9), 
                 foreground="gray").grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Steam Libraries section with clickable paths
        libs_frame = ttk.LabelFrame(main_frame, text="Steam Library Locations (double-click to open)", padding="10")
        libs_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        libs_frame.columnconfigure(0, weight=1)
        
        # Create a listbox for clickable library paths
        self.libs_listbox = tk.Listbox(libs_frame, height=len(self.steam_libraries), font=("Courier", 9))
        self.libs_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        self.libs_listbox.bind('<Double-1>', self.on_library_double_click)
        
        for lib in self.steam_libraries:
            self.libs_listbox.insert(tk.END, lib)
        
        ttk.Label(libs_frame, text="Double-click any path above to open it in file manager", 
                 font=("Arial", 8), foreground="gray").grid(row=1, column=0, sticky=tk.W)
        
        # Search section
        ttk.Label(main_frame, text="Game Name:", font=("Arial", 10, "bold")).grid(
            row=2, column=0, sticky=tk.W, padx=(0, 10)
        )
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(main_frame, textvariable=self.search_var, width=50)
        self.search_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.search_entry.bind('<KeyRelease>', self.on_search_changed)
        self.search_entry.focus_set()  # Auto-focus the search field
        
        # Results listbox
        ttk.Label(main_frame, text="Found Games:", font=("Arial", 10, "bold")).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=(15, 5)
        )
        
        listbox_frame = ttk.Frame(main_frame)
        listbox_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)
        
        self.results_listbox = tk.Listbox(listbox_frame, height=8)
        self.results_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.results_listbox.bind('<<ListboxSelect>>', self.on_game_selected)  # Auto-find folders on selection
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.results_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.results_listbox.configure(yscrollcommand=scrollbar.set)
        

        
        # Results section
        ttk.Label(main_frame, text="Found Folders:", font=("Arial", 12, "bold")).grid(
            row=5, column=0, columnspan=2, sticky=tk.W, pady=(20, 10)
        )
        
        # Results tree
        self.results_tree = ttk.Treeview(main_frame, columns=("path",), show="tree")
        self.results_tree.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        self.results_tree.bind('<Double-1>', self.on_folder_double_click)  # Double-click to open folder
        
        tree_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        tree_scrollbar.grid(row=4, column=2, sticky=(tk.N, tk.S))
        self.results_tree.configure(yscrollcommand=tree_scrollbar.set)
        

        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Configure grid weights for resizing
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(4, weight=1)
    
    def load_steam_apps(self):
        """Load Steam app list from cache or download from Steam API"""
        self.status_var.set("Loading Steam game list...")
        
        # Try to load from cache first
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    # Check if cache is less than 7 days old
                    if time.time() - data.get('timestamp', 0) < 7 * 24 * 3600:
                        self.steam_apps = data['apps']
                        self.status_var.set(f"Loaded {len(self.steam_apps)} games from cache")
                        return
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Download from Steam API in background
        threading.Thread(target=self.download_steam_apps, daemon=True).start()
    
    def download_steam_apps(self):
        """Download Steam app list from Steam Web API"""
        try:
            self.root.after(0, lambda: self.status_var.set("Downloading Steam game list..."))
            
            url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
            
            with urllib.request.urlopen(url, timeout=30) as response:
                data = json.loads(response.read().decode())
                
            apps = data['applist']['apps']
            
            # Filter out non-games (rough heuristic: games usually have longer names)
            filtered_apps = [app for app in apps if len(app['name']) > 3 and not app['name'].startswith('Steamworks')]
            
            self.steam_apps = filtered_apps
            
            # Cache the results
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            cache_data = {
                'timestamp': time.time(),
                'apps': self.steam_apps
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f)
            
            self.root.after(0, lambda: self.status_var.set(f"Downloaded {len(self.steam_apps)} games"))
            
        except Exception as e:
            error_msg = f"Failed to download game list: {str(e)}"
            self.root.after(0, lambda: self.status_var.set(error_msg))
            print(f"Error downloading Steam apps: {e}")
    
    def refresh_steam_apps(self):
        """Force refresh of Steam app list"""
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        self.steam_apps = []
        self.results_listbox.delete(0, tk.END)
        threading.Thread(target=self.download_steam_apps, daemon=True).start()
    
    def on_search_changed(self, event=None):
        """Handle search input changes"""
        query = self.search_var.get().strip()
        if len(query) < 2:
            self.results_listbox.delete(0, tk.END)
            return
        
        # Fuzzy search through steam apps
        matches = self.fuzzy_search(query, self.steam_apps)
        
        # Filter by installed games (always enabled now)
        matches = self.filter_installed_games(matches)
        
        self.results_listbox.delete(0, tk.END)
        for app in matches[:50]:  # Limit to 50 results
            self.results_listbox.insert(tk.END, f"{app['name']} (ID: {app['appid']})")
    

    
    def filter_installed_games(self, games):
        """Filter games to only those that have compatdata folders (i.e., are installed)"""
        installed_games = []
        
        for game in games:
            app_id = str(game['appid'])
            
            # Check if this game has a compatdata folder in any Steam library
            for library in self.steam_libraries:
                compatdata_path = os.path.join(library, app_id)
                if os.path.exists(compatdata_path):
                    installed_games.append(game)
                    break  # Found in one library, no need to check others
        
        return installed_games
    
    def fuzzy_search(self, query, apps):
        """Simple fuzzy search implementation"""
        query_lower = query.lower()
        matches = []
        
        for app in apps:
            name_lower = app['name'].lower()
            if query_lower in name_lower:
                # Calculate relevance score
                score = 0
                if name_lower.startswith(query_lower):
                    score += 100  # Exact start match
                if query_lower == name_lower:
                    score += 200  # Exact match
                
                # Add word boundary bonus
                words = name_lower.split()
                for word in words:
                    if word.startswith(query_lower):
                        score += 50
                
                matches.append((score, app))
        
        # Sort by relevance score (descending)
        matches.sort(key=lambda x: x[0], reverse=True)
        return [app for score, app in matches]
    
    def on_game_selected(self, event=None):
        """Handle game selection - automatically find folders"""
        selection = self.results_listbox.curselection()
        if selection:
            # Small delay to ensure selection is processed, then find folders
            self.root.after(100, self.find_folders)
    
    def find_folders(self):
        """Find save game folders for selected game"""
        selection = self.results_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a game from the list.")
            return
        
        # Extract app ID from selection
        selected_text = self.results_listbox.get(selection[0])
        try:
            app_id = int(selected_text.split("ID: ")[1].rstrip(")"))
            app_name = selected_text.split(" (ID:")[0]
        except (IndexError, ValueError):
            messagebox.showerror("Error", "Could not parse selected game ID.")
            return
        
        self.status_var.set(f"Searching for {app_name} folders...")
        
        # Clear previous results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        found_folders = []
        
        # Check each Steam library
        for library in self.steam_libraries:
            compatdata_path = os.path.join(library, str(app_id))
            
            if os.path.exists(compatdata_path):
                # Check Local, Roaming, and LocalLow AppData folders
                appdata_paths = [
                    ("AppData/Local", os.path.join(compatdata_path, "pfx", "drive_c", "users", "steamuser", "AppData", "Local")),
                    ("AppData/Roaming", os.path.join(compatdata_path, "pfx", "drive_c", "users", "steamuser", "AppData", "Roaming")),
                    ("AppData/LocalLow", os.path.join(compatdata_path, "pfx", "drive_c", "users", "steamuser", "AppData", "LocalLow"))
                ]
                
                for appdata_type, base_path in appdata_paths:
                    if os.path.exists(base_path):
                        # Show the base AppData folder
                        found_folders.append((appdata_type, base_path))
                        
                        # Look for game-specific folders in this AppData directory
                        self.find_game_folders(base_path, app_name, appdata_type, found_folders)
                
                # Also check some other common locations
                other_paths = [
                    ("Documents", os.path.join(compatdata_path, "pfx", "drive_c", "users", "steamuser", "Documents")),
                    ("My Games", os.path.join(compatdata_path, "pfx", "drive_c", "users", "steamuser", "Documents", "My Games")),
                    ("Saved Games", os.path.join(compatdata_path, "pfx", "drive_c", "users", "steamuser", "Saved Games"))
                ]
                
                for location_type, path in other_paths:
                    if os.path.exists(path):
                        found_folders.append((location_type, path))
                        self.find_game_folders(path, app_name, location_type, found_folders)
        
        # Add results to tree (sort by priority)
        if found_folders:
            # Sort folders by priority: Likely Save Folders first, then by modification time
            def get_folder_priority(folder_item):
                folder_type, path = folder_item
                priority = 0
                
                # Highest priority for likely save folders
                if "Likely Save Folder" in folder_type:
                    priority += 1000
                elif "Game Folder" in folder_type:
                    priority += 100
                elif "Potential" in folder_type:
                    priority += 50
                
                # Add recent modification bonus
                try:
                    mtime = os.path.getmtime(path)
                    days_old = (time.time() - mtime) / (24 * 3600)
                    if days_old < 1:  # Modified in last day
                        priority += 20
                    elif days_old < 7:  # Modified in last week
                        priority += 10
                    elif days_old < 30:  # Modified in last month
                        priority += 5
                except (OSError, PermissionError):
                    pass
                
                return -priority  # Negative for descending sort
            
            found_folders.sort(key=get_folder_priority)
            
            for folder_type, path in found_folders:
                # Add modification time info for better context
                try:
                    mtime = os.path.getmtime(path)
                    days_old = (time.time() - mtime) / (24 * 3600)
                    if days_old < 1:
                        time_info = " (modified today)"
                    elif days_old < 7:
                        time_info = f" (modified {int(days_old)} days ago)"
                    elif days_old < 30:
                        time_info = f" (modified {int(days_old)} days ago)"
                    else:
                        time_info = ""
                except (OSError, PermissionError):
                    time_info = ""
                
                display_text = f"{folder_type}: {os.path.basename(path)}{time_info}"
                item = self.results_tree.insert("", tk.END, text=display_text)
                self.results_tree.set(item, "path", path)
            
            self.status_var.set(f"Found {len(found_folders)} folders for {app_name}")
        else:
            self.results_tree.insert("", tk.END, text="No folders found")
            self.status_var.set(f"No folders found for {app_name}")
    
    def find_game_folders(self, base_path, app_name, location_type, found_folders):
        """Look for game-specific folders with smart pattern matching"""
        try:
            # Get game name variations for matching
            game_words = self.extract_game_keywords(app_name)
            
            for item in os.listdir(base_path):
                item_path = os.path.join(base_path, item)
                if os.path.isdir(item_path):
                    # Check if folder name matches game patterns
                    match_score = self.calculate_folder_match_score(item, game_words, app_name)
                    
                    if match_score > 0:
                        # Check if this folder contains save-like files
                        save_confidence = self.assess_save_folder_confidence(item_path)
                        
                        if save_confidence > 0:
                            folder_desc = f"Game Folder ({location_type})"
                            if save_confidence >= 2:
                                folder_desc = f"Likely Save Folder ({location_type})"
                            
                            found_folders.append((folder_desc, item_path))
                        else:
                            # Still add it as a potential folder if name match is strong
                            if match_score >= 3:
                                found_folders.append((f"Potential Game Folder ({location_type})", item_path))
        
        except PermissionError:
            pass
    
    def extract_game_keywords(self, app_name):
        """Extract meaningful keywords from game name for matching"""
        # Remove common words and split
        common_words = {'the', 'and', 'or', 'of', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'with', 'by'}
        words = []
        
        # Split by common delimiters
        import re
        parts = re.split(r'[:\-\s\(\)]+', app_name.lower())
        
        for part in parts:
            part = part.strip()
            if len(part) > 2 and part not in common_words:
                words.append(part)
        
        return words
    
    def calculate_folder_match_score(self, folder_name, game_words, full_game_name):
        """Calculate how likely a folder is related to the game"""
        folder_lower = folder_name.lower()
        score = 0
        
        # Exact match (case insensitive)
        if folder_lower == full_game_name.lower():
            return 10
        
        # Check for game words in folder name
        for word in game_words:
            if word in folder_lower:
                score += 2
                # Bonus for word boundaries
                if word == folder_lower or folder_lower.startswith(word) or folder_lower.endswith(word):
                    score += 1
        
        # Check for common game folder patterns
        game_patterns = [
            'save', 'saves', 'savegame', 'savegames', 'savedata',
            'config', 'settings', 'profile', 'profiles', 'user',
            'data', 'game', 'local', 'steam'
        ]
        
        for pattern in game_patterns:
            if pattern in folder_lower:
                score += 1
        
        return score
    
    def assess_save_folder_confidence(self, folder_path):
        """Assess how likely a folder contains save games"""
        confidence = 0
        
        try:
            items = os.listdir(folder_path)
            recent_activity_bonus = 0
            
            # Check for recent file modifications (within last 30 days)
            current_time = time.time()
            recent_files = 0
            
            for item in items:
                item_path = os.path.join(folder_path, item)
                item_lower = item.lower()
                
                # Check modification time
                try:
                    mtime = os.path.getmtime(item_path)
                    days_old = (current_time - mtime) / (24 * 3600)
                    if days_old < 30:  # Modified in last 30 days
                        recent_files += 1
                        if days_old < 7:  # Very recent
                            recent_activity_bonus += 2
                        else:
                            recent_activity_bonus += 1
                except (OSError, PermissionError):
                    pass
                
                # Check file extensions
                save_extensions = ['.sav', '.save', '.dat', '.xml', '.json', '.cfg', '.ini', '.sl2', '.ess', '.bak']
                save_patterns = ['save', 'profile', 'config', 'settings', 'user', 'slot', 'progress']
                
                for ext in save_extensions:
                    if item_lower.endswith(ext):
                        confidence += 2
                        break
                
                # Check file name patterns
                for pattern in save_patterns:
                    if pattern in item_lower:
                        confidence += 1
                        break
                
                # Check for numbered save files (save01, slot1, etc.)
                import re
                if re.search(r'(save|slot|profile)\d+', item_lower):
                    confidence += 2
            
            # Add recent activity bonus
            confidence += min(recent_activity_bonus, 5)  # Cap the bonus
            
            # Bonus for reasonable number of files with recent activity
            if 0 < len(items) < 50 and recent_files > 0:
                confidence += 2
                
        except PermissionError:
            pass
        
        return min(confidence, 10)  # Cap at 10
    
    def on_folder_double_click(self, event=None):
        """Handle double-click on folder to open it"""
        selection = self.results_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        path = self.results_tree.set(item, "path")
        
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "Selected folder does not exist.")
            return
        
        try:
            # Open in file manager
            subprocess.run(["xdg-open", path], check=True)
        except subprocess.CalledProcessError:
            try:
                # Fallback to nautilus
                subprocess.run(["nautilus", path], check=True)
            except subprocess.CalledProcessError:
                messagebox.showerror("Error", f"Could not open folder: {path}")
    
    def on_library_double_click(self, event=None):
        """Handle double-click on library path to open it"""
        selection = self.libs_listbox.curselection()
        if not selection:
            return
        
        path = self.libs_listbox.get(selection[0])
        
        if not os.path.exists(path):
            messagebox.showerror("Error", f"Library path does not exist: {path}")
            return
        
        try:
            # Open in file manager
            subprocess.run(["xdg-open", path], check=True)
        except subprocess.CalledProcessError:
            try:
                # Fallback to nautilus
                subprocess.run(["nautilus", path], check=True)
            except subprocess.CalledProcessError:
                messagebox.showerror("Error", f"Could not open folder: {path}")
    
    def refresh_steam_apps(self):
        """Force refresh of Steam app list (kept for potential future use)"""
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        self.steam_apps = []
        self.results_listbox.delete(0, tk.END)
        threading.Thread(target=self.download_steam_apps, daemon=True).start()
    
    def open_selected_folder(self):
        """Open the selected folder in file manager"""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a folder to open.")
            return
        
        item = selection[0]
        path = self.results_tree.set(item, "path")
        
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "Selected folder does not exist.")
            return
        
        try:
            # Open in file manager
            subprocess.run(["xdg-open", path], check=True)
        except subprocess.CalledProcessError:
            try:
                # Fallback to nautilus
                subprocess.run(["nautilus", path], check=True)
            except subprocess.CalledProcessError:
                messagebox.showerror("Error", f"Could not open folder: {path}")
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Find save game folders for Steam games running through Proton on Linux"
    )
    parser.add_argument(
        "--steam-library", 
        action="append", 
        dest="steam_libraries",
        help="Steam library compatdata path (can be used multiple times). "
             "Default: /home/omustardo/ssd/SteamLibrary/steamapps/compatdata/ and "
             "/home/omustardo/.steam/debian-installation/steamapps/compatdata/"
    )
    
    args = parser.parse_args()
    
    # Use provided libraries or fall back to defaults
    steam_libraries = args.steam_libraries
    if steam_libraries:
        # Ensure paths end with compatdata/
        steam_libraries = [
            lib if lib.endswith("compatdata/") else lib.rstrip("/") + "/compatdata/"
            for lib in steam_libraries
        ]
    
    app = SteamGameFinder(steam_libraries)
    app.run()

if __name__ == "__main__":
    main()
