# spotify_cleaner
Organize liked songs into yearly playlists

## How to
1. Add Spotify Developer App (https://developer.spotify.com/)
   - Redirect URI: http://127.0.0.1:8888/callback
   - APIs used: Check Web API
2. Prepare environment
   - Download spotipy (E.g. python3 -m pip install spotipy --use-feature=2020-resolver)
   - `export SPOTIPY_CLIENT_ID="GET_FROM_WEB_UI"`
   - `export SPOTIPY_CLIENT_SECRET="GET_FROM_WEB_UI"`
3. Run!
   - ` python liked_year.py`
   - Only keep `DELETE_FROM_LIKED_SONGS=TRUE` if you're okay deleting the added songs from your Liked Songs
