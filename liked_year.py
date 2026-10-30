# liked_year.py
# pip install spotipy

import csv
import os
import time
from collections import defaultdict
from datetime import datetime

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# -------------------------
# SETTINGS
# -------------------------

REDIRECT_URI = "http://127.0.0.1:8888/callback"

SCOPES = (
    "user-library-read",
    "user-library-modify",
    "playlist-read-private",
    "playlist-modify-private",
    "playlist-modify-public",
)

# "date_added" groups by the year you liked the song.
# "release_year" groups by the song/album release year.
GROUP_BY = "date_added"

# Important safety switches.
MAKE_PLAYLISTS = True
DELETE_FROM_LIKED_SONGS = True

CSV_BACKUP = "spotify_liked_backup.csv"

# -------------------------
# AUTH
# -------------------------

os.environ.setdefault("SPOTIPY_REDIRECT_URI", REDIRECT_URI)

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        scope=SCOPES,
        open_browser=True
    )
)

me = sp.current_user()["id"]
current_year = str(datetime.now().year)

# -------------------------
# HELPERS
# -------------------------

def saved_tracks():
    offset = 0
    while True:
        result = sp.current_user_saved_tracks(limit=50, offset=offset)
        items = result.get("items") or []

        if not items:
            break

        for item in items:
            yield item

        offset += len(items)

        # Spotify saved-tracks pagination is capped around 10,000 tracks.
        # You have ~4,000, so this is fine.
        if offset >= 10000:
            print("Stopped fetching at the Spotify API pagination cap.")
            break

        time.sleep(0.3)


def find_playlist(name):
    offset = 0

    while True:
        result = sp.current_user_playlists(limit=50, offset=offset)
        items = result.get("items") or []

        for playlist in items:
            if playlist.get("name") == name:
                return playlist.get("id")

        if len(items) < 50:
            break

        offset += 50
        time.sleep(0.2)

    return None


def get_playlist_track_ids(playlist_id):
    ids = set()
    offset = 0

    while True:
        result = sp.playlist_items(
            playlist_id,
            limit=100,
            offset=offset,
            additional_types=["track"]
        )

        items = result.get("items") or []

        if not items:
            break

        for item in items:
            track = item.get("track")
            if track and track.get("id"):
                ids.add(track["id"])

        if len(items) < 100:
            break

        offset += 100
        time.sleep(0.2)

    return ids


# -------------------------
# READ LIKED SONGS
# -------------------------

print("Fetching Liked Songs...")

old_songs_by_year = defaultdict(list)
export_rows = []

for item in saved_tracks():
    track = item.get("track") or {}
    track_id = track.get("id")

    if not track_id:
        continue

    added_at = item.get("added_at") or ""
    album = track.get("album") or {}

    if GROUP_BY == "release_year":
        year = (album.get("release_date") or "")[:4]
    else:
        year = added_at[:4]

    if not year:
        continue

    export_rows.append([
        year,
        added_at,
        track_id,
        track.get("name") or "",
        album.get("name") or "",
    ])

    # Keep current year in Liked Songs.
    if year != current_year:
        old_songs_by_year[year].append(track_id)

print(f"Finished scanning saved tracks.")

# -------------------------
# BACKUP
# -------------------------

if CSV_BACKUP:
    with open(CSV_BACKUP, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "group_year",
            "added_at",
            "spotify_track_id",
            "track",
            "album"
        ])
        writer.writerows(export_rows)

    print(f"Exported {len(export_rows)} saved tracks to {CSV_BACKUP}")

# Deduplicate old IDs per year.
safe_songs_by_year = {
    year: list(dict.fromkeys(ids))
    for year, ids in old_songs_by_year.items()
}

# -------------------------
# CREATE YEARLY PLAYLISTS
# -------------------------

if MAKE_PLAYLISTS:
    for year, track_ids in sorted(safe_songs_by_year.items()):
        playlist_name = f"Liked Songs {year}"

        playlist_id = find_playlist(playlist_name)

        if not playlist_id:
            print(f"Creating playlist: {playlist_name}")
            created = sp.current_user_playlist_create(
                playlist_name,
#                public=False,
                description=f"Songs added to Liked Songs in {year}"
            )
            playlist_id = created["id"]
            time.sleep(0.4)

        print(f"Checking existing tracks in: {playlist_name}")
        existing_ids = get_playlist_track_ids(playlist_id)

        to_add = [
            track_id for track_id in track_ids
            if track_id not in existing_ids
        ]

        added_ok = []

        for i in range(0, len(to_add), 100):
            chunk = to_add[i:i + 100]

            try:
                sp.playlist_add_items(playlist_id, chunk)
                added_ok.extend(chunk)
            except Exception as e:
                print(f"Failed to add a chunk of songs to {playlist_name}: {e}")

            time.sleep(0.6)

        verified = list(dict.fromkeys(list(existing_ids.intersection(track_ids)) + added_ok))
        safe_songs_by_year[year] = verified

        print(f"{playlist_name}: verified {len(verified)} songs in playlist.")

else:
    print("MAKE_PLAYLISTS=False: playlists will not be created.")

# -------------------------
# OPTIONAL: REMOVE OLD SONGS FROM LIKED SONGS
# -------------------------

chunk_size = 40

if DELETE_FROM_LIKED_SONGS:
    ids_to_delete = []

    for ids in safe_songs_by_year.values():
        ids_to_delete.extend(ids)

    ids_to_delete = list(dict.fromkeys(ids_to_delete))

    print("")
    print(f"About to remove {len(ids_to_delete)} songs from Liked Songs.")
    print("These songs should already be in yearly playlists.")

    for i in range(0, len(ids_to_delete), chunk_size):
        chunk = ids_to_delete[i:i + chunk_size]

        try:
            sp.current_user_saved_tracks_delete(chunk)
            print(f"Removed {len(chunk)} songs from Liked Songs.")
        except Exception as e:
            print(f"Failed to delete chunk: {e}")

        time.sleep(1.5)

else:
    print("")
    print("DELETE_FROM_LIKED_SONGS=False: no songs were removed from Liked Songs.")
