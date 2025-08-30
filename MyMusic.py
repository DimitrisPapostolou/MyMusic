from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QSlider, QFileDialog, QListWidgetItem,
    QLineEdit, QStackedWidget, QInputDialog, QMenu, QScrollArea, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, QUrl, QByteArray
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QIcon, QPixmap
import random
import json
import os
from mutagen.id3 import ID3, APIC

DATA_FILE = "playlists.json"


class SpotifyClone(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spotify Clone")
        self.resize(1100, 650)

        # ===== MEDIA PLAYER =====
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.5)

        # ===== DATA =====
        self.library_songs = []
        self.playlists = {}
        self.current_song_list = []
        self.current_index = -1
        self.current_duration = 0
        self.is_slider_dragging = False
        self.repeat_one = False
        self.shuffle = False

        # ===== ROOT LAYOUT =====
        root = QHBoxLayout(self)

        # ===== SIDEBAR =====
        sidebar = QVBoxLayout()
        title = QLabel("MyMusic")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; padding: 12px;")

        btn_home = QPushButton("Home")
        btn_search = QPushButton("Search")
        btn_library = QPushButton("Your Library")
        btn_playlists = QPushButton("Playlists")
        btn_add = QPushButton("➕ Add Songs")

        btn_home.clicked.connect(lambda: self.switch_page(0))
        btn_search.clicked.connect(lambda: self.switch_page(1))
        btn_library.clicked.connect(lambda: self.switch_page(2))
        btn_playlists.clicked.connect(lambda: self.switch_page(3))
        btn_add.clicked.connect(self.add_songs)

        for b in (btn_home, btn_search, btn_library, btn_playlists, btn_add):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setMinimumHeight(34)

        sidebar.addWidget(title)
        sidebar.addWidget(btn_home)
        sidebar.addWidget(btn_search)
        sidebar.addWidget(btn_library)
        sidebar.addWidget(btn_playlists)
        sidebar.addStretch(1)
        sidebar.addWidget(btn_add)

        sidebar_wrap = QWidget()
        sidebar_wrap.setLayout(sidebar)
        sidebar_wrap.setFixedWidth(200)

        # ===== MAIN AREA =====
        self.pages = QStackedWidget()

        # --- HOME PAGE ---
        home_page = QWidget()
        hl = QVBoxLayout(home_page)
        hl.setContentsMargins(10, 10, 10, 10)
        hl.setSpacing(15)

        welcome_label = QLabel("🎵 Welcome to MyMusic\nAdd songs, create playlists and enjoy!")
        welcome_label.setStyleSheet("font-size: 16px; padding: 5px;")
        hl.addWidget(welcome_label)

        # Scroll area for playlists
        playlist_scroll = QScrollArea()
        playlist_scroll.setWidgetResizable(True)
        playlist_container = QWidget()
        self.home_playlists_grid = QGridLayout(playlist_container)
        self.home_playlists_grid.setSpacing(20)
        playlist_scroll.setWidget(playlist_container)
        hl.addWidget(QLabel("Your Playlists"))
        hl.addWidget(playlist_scroll, stretch=1)

        # Scroll area for songs
        songs_scroll = QScrollArea()
        songs_scroll.setWidgetResizable(True)
        songs_container = QWidget()
        self.home_songs_grid = QGridLayout(songs_container)
        self.home_songs_grid.setSpacing(20)
        songs_scroll.setWidget(songs_container)
        hl.addWidget(QLabel("Recently Added Songs"))
        hl.addWidget(songs_scroll, stretch=1)

        # --- SEARCH PAGE ---
        search_page = QWidget()
        sl = QVBoxLayout(search_page)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search for songs...")
        self.search_results = QListWidget()
        self.search_bar.textChanged.connect(self.filter_songs)
        self.search_results.itemDoubleClicked.connect(self.play_selected_song)
        sl.addWidget(self.search_bar)
        sl.addWidget(self.search_results)

        # --- LIBRARY PAGE ---
        library_page = QWidget()
        ll = QVBoxLayout(library_page)
        self.library_list = QListWidget()
        self.library_list.itemDoubleClicked.connect(self.play_selected_song)
        self.library_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.library_list.customContextMenuRequested.connect(self.show_library_menu)
        ll.addWidget(QLabel("Your Library"))
        ll.addWidget(self.library_list)

        # --- PLAYLISTS PAGE ---
        playlists_page = QWidget()
        pl = QVBoxLayout(playlists_page)

        self.playlist_list = QListWidget()
        self.playlist_list.itemClicked.connect(self.show_playlist_songs)

        self.playlist_songs = QListWidget()
        self.playlist_songs.itemDoubleClicked.connect(self.play_selected_song)

        new_playlist_btn = QPushButton("➕ New Playlist")
        new_playlist_btn.clicked.connect(self.create_playlist)

        self.shuffle_btn = QPushButton("🔀 Shuffle Off")
        self.shuffle_btn.clicked.connect(self.toggle_shuffle)

        self.repeat_btn = QPushButton("🔁 Repeat Off")
        self.repeat_btn.clicked.connect(self.toggle_repeat)

        pl.addWidget(QLabel("Playlists"))
        pl.addWidget(self.playlist_list, stretch=1)
        pl.addWidget(new_playlist_btn)
        pl.addWidget(QLabel("Songs in Playlist"))
        pl.addWidget(self.playlist_songs, stretch=2)
        pl.addWidget(self.shuffle_btn)
        pl.addWidget(self.repeat_btn)

        # Add pages
        self.pages.addWidget(home_page)
        self.pages.addWidget(search_page)
        self.pages.addWidget(library_page)
        self.pages.addWidget(playlists_page)

        # ===== PLAYER BAR =====
        player_bar = QHBoxLayout()
        self.album_art = QLabel()
        self.album_art.setFixedSize(64, 64)
        self.album_art.setStyleSheet("border: 1px solid #333; background-color: #222;")
        self.album_art.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.prev_btn = QPushButton("⏮")
        self.play_btn = QPushButton("▶")
        self.pause_btn = QPushButton("⏸")
        self.next_btn = QPushButton("⏭")

        for b in (self.prev_btn, self.play_btn, self.pause_btn, self.next_btn):
            b.setFixedWidth(48)
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        self.progress = QSlider(Qt.Orientation.Horizontal)
        self.progress.setRange(0, 100)
        self.progress.sliderPressed.connect(lambda: setattr(self, 'is_slider_dragging', True))
        self.progress.sliderReleased.connect(lambda: setattr(self, 'is_slider_dragging', False))
        self.progress.sliderMoved.connect(self.seek_position)

        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(50)
        self.volume.valueChanged.connect(lambda v: self.audio.setVolume(v / 100))

        player_bar.addWidget(self.album_art)
        player_bar.addWidget(self.prev_btn)
        player_bar.addWidget(self.play_btn)
        player_bar.addWidget(self.pause_btn)
        player_bar.addWidget(self.next_btn)
        player_bar.addSpacing(16)
        player_bar.addWidget(QLabel("Progress"))
        player_bar.addWidget(self.progress, stretch=1)
        player_bar.addSpacing(16)
        player_bar.addWidget(QLabel("Vol"))
        player_bar.addWidget(self.volume)

        # ===== MAIN WRAP =====
        main_wrap = QVBoxLayout()
        main_wrap.addWidget(self.pages, stretch=1)
        main_wrap.addLayout(player_bar)

        # Add to root
        root.addWidget(sidebar_wrap)
        root.addLayout(main_wrap, stretch=1)

        # Styling
        self.setStyleSheet("""
            QWidget { background: #111; color: #eee; }
            QListWidget, QSlider, QLineEdit { background: #181818; border: none; }
            QPushButton { background: #222; border: 1px solid #333; border-radius: 6px; padding: 6px 10px; }
            QPushButton:hover { background: #2a2a2a; }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background: #333; }
            QLineEdit { padding: 6px; color: white; }
        """)

        # Connect player signals
        self.play_btn.clicked.connect(self.play)
        self.pause_btn.clicked.connect(self.pause)
        self.next_btn.clicked.connect(self.next_song)
        self.prev_btn.clicked.connect(self.prev_song)
        self.player.positionChanged.connect(self.update_slider)
        self.player.durationChanged.connect(lambda dur: setattr(self, 'current_duration', dur))
        self.player.mediaStatusChanged.connect(self.handle_media_finished)

        # Load saved playlists and refresh home
        self.load_playlists()
        self.refresh_home()

    # ===== FACTORY METHODS =====
    def enterEventFactory(self, btn):
        def enter(event):
            btn.setVisible(True)
        return enter

    def leaveEventFactory(self, btn):
        def leave(event):
            btn.setVisible(False)
        return leave

    # ===== HOME PAGE REFRESH =====
    def refresh_home(self):
        # Clear previous widgets
        for layout in [self.home_playlists_grid, self.home_songs_grid]:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        # Show playlists
        col, row = 0, 0
        for playlist_name, songs in self.playlists.items():
            frame = QFrame()
            frame.setMinimumSize(160, 160)
            frame.setMaximumSize(200, 200)
            frame.setStyleSheet("QFrame { background-color: #222; border-radius: 8px; }")
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(5,5,5,5)
            layout.setSpacing(5)

            # Playlist name
            name_label = QLabel(playlist_name)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(name_label)

            play_btn = QPushButton("▶")
            play_btn.setFixedSize(32, 32)
            play_btn.setStyleSheet("QPushButton { background-color: #1db954; border-radius: 16px; color: white; }")
            play_btn.setVisible(False)
            layout.addWidget(play_btn, alignment=Qt.AlignmentFlag.AlignCenter)

            frame.enterEvent = self.enterEventFactory(play_btn)
            frame.leaveEvent = self.leaveEventFactory(play_btn)

            def play_playlist_factory(songs_list):
                def play_playlist():
                    if songs_list:
                        self.current_song_list = songs_list
                        self.current_index = 0
                        self.play_current_song()
                return play_playlist
            play_btn.clicked.connect(play_playlist_factory(songs))

            self.home_playlists_grid.addWidget(frame, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1

        # Show songs
        col, row = 0, 0
        for song_path in self.library_songs[:8]:
            frame = QFrame()
            frame.setMinimumSize(140, 140)
            frame.setMaximumSize(180, 180)
            frame.setStyleSheet("QFrame { background-color: #222; border-radius: 8px; }")
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(5,5,5,5)
            layout.setSpacing(5)

            name_label = QLabel(os.path.basename(song_path))
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(name_label)

            play_btn = QPushButton("▶")
            play_btn.setFixedSize(28, 28)
            play_btn.setStyleSheet("QPushButton { background-color: #1db954; border-radius: 14px; color: white; }")
            play_btn.setVisible(False)
            layout.addWidget(play_btn, alignment=Qt.AlignmentFlag.AlignCenter)

            frame.enterEvent = self.enterEventFactory(play_btn)
            frame.leaveEvent = self.leaveEventFactory(play_btn)

            def play_song_factory(path):
                def play_song():
                    self.current_song_list = [path]
                    self.current_index = 0
                    self.play_current_song()
                return play_song
            play_btn.clicked.connect(play_song_factory(song_path))

            self.home_songs_grid.addWidget(frame, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1

    # ===== DATA METHODS =====
    def save_playlists(self):
        data = {"library": self.library_songs, "playlists": self.playlists}
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def load_playlists(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.library_songs = data.get("library", [])
                self.playlists = data.get("playlists", {})

        self.library_list.clear()
        for song in self.library_songs:
            self.library_list.addItem(QListWidgetItem(os.path.basename(song)))

        self.playlist_list.clear()
        for playlist_name in self.playlists:
            self.playlist_list.addItem(playlist_name)

        self.filter_songs()

    # ===== NAVIGATION =====
    def switch_page(self, index):
        self.pages.setCurrentIndex(index)

    # ===== LIBRARY =====
    def add_songs(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Add audio files", "", "Audio Files (*.mp3 *.wav *.flac);;All Files (*)")
        for p in paths:
            if p not in self.library_songs:
                self.library_songs.append(p)
        self.save_playlists()
        self.load_playlists()
        self.refresh_home()

    def show_library_menu(self, pos):
        item = self.library_list.itemAt(pos)
        if not item: return
        menu = QMenu()
        add_to_playlist = menu.addAction("Add to Playlist")
        action = menu.exec(self.library_list.mapToGlobal(pos))
        if action == add_to_playlist:
            self.add_song_to_playlist(item.text())

    # ===== SEARCH =====
    def filter_songs(self):
        query = self.search_bar.text().lower()
        self.search_results.clear()
        for song in self.library_songs:
            if query in song.lower():
                self.search_results.addItem(os.path.basename(song))

    # ===== PLAYLISTS =====
    def create_playlist(self):
        name, ok = QInputDialog.getText(self, "New Playlist", "Playlist name:")
        if ok and name and name not in self.playlists:
            self.playlists[name] = []
            self.save_playlists()
            self.load_playlists()
            self.refresh_home()

    def add_song_to_playlist(self, song_name):
        if not self.playlists: return
        playlist_names = list(self.playlists.keys())
        name, ok = QInputDialog.getItem(self, "Add to Playlist", "Choose playlist:", playlist_names, 0, False)
        if ok and name:
            # match full path
            full_path = next((s for s in self.library_songs if os.path.basename(s) == song_name), None)
            if full_path and full_path not in self.playlists[name]:
                self.playlists[name].append(full_path)
                self.save_playlists()
                self.load_playlists()
                self.refresh_home()

    def show_playlist_songs(self, item):
        name = item.text()
        self.playlist_songs.clear()
        self.current_song_list = self.playlists.get(name, [])
        for song in self.current_song_list:
            self.playlist_songs.addItem(QListWidgetItem(os.path.basename(song)))

    # ===== PLAYER =====
    def play_selected_song(self, item):
        song_name = item.text()
        full_path = next((s for s in self.library_songs if os.path.basename(s) == song_name), None)
        if full_path:
            self.current_song_list = [full_path]
            self.current_index = 0
            self.play_current_song()

    def play_current_song(self):
        if 0 <= self.current_index < len(self.current_song_list):
            song_path = self.current_song_list[self.current_index]
            self.player.setSource(QUrl.fromLocalFile(song_path))
            self.player.play()

    # ===== PLAYER CONTROLS =====
    def play(self): self.player.play()
    def pause(self): self.player.pause()
    def prev_song(self):
        if self.shuffle:
            self.current_index = random.randint(0, len(self.current_song_list)-1)
        else:
            self.current_index -= 1
            if self.current_index < 0:
                self.current_index = len(self.current_song_list)-1
        self.play_current_song()

    def next_song(self):
        if self.shuffle:
            self.current_index = random.randint(0, len(self.current_song_list)-1)
        else:
            self.current_index += 1
            if self.current_index >= len(self.current_song_list):
                self.current_index = 0
        self.play_current_song()

    def update_slider(self, pos):
        if not self.is_slider_dragging and self.current_duration > 0:
            self.progress.setValue(int(pos * 100 / self.current_duration))

    def seek_position(self, val):
        if self.current_duration > 0:
            new_pos = int((val / 100) * self.current_duration)
            self.player.setPosition(new_pos)

    def toggle_repeat(self):
        self.repeat_one = not self.repeat_one
        self.repeat_btn.setText("🔁 Repeat On" if self.repeat_one else "🔁 Repeat Off")

    def toggle_shuffle(self):
        self.shuffle = not self.shuffle
        self.shuffle_btn.setText("🔀 Shuffle On" if self.shuffle else "🔀 Shuffle Off")

    def handle_media_finished(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.repeat_one:
                self.player.setPosition(0)
                self.player.play()
            else:
                self.next_song()


# ---- RUN APP ----
if __name__ == "__main__":
    app = QApplication([])
    win = SpotifyClone()
    win.show()
    app.exec()
