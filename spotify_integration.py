#!/usr/bin/env python3
"""
Spotify Integration Module
Handles Spotify Web API operations for VGM playlist creation.
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
import re
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import logging

# Suppress noisy warnings from spotipy and urllib3
logging.getLogger("spotipy").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("root").setLevel(logging.ERROR)

# Load environment variables
load_dotenv("config.env")


class SpotifyVGMIntegrator:
    def __init__(self):
        """Initialize Spotify client with OAuth"""
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = os.getenv(
            "SPOTIFY_REDIRECT_URI", "http://localhost:8080/callback"
        )

        if not all([self.client_id, self.client_secret]):
            raise ValueError(
                "Missing Spotify credentials. Please check your .env file."
            )

        # Set up OAuth with playlist modification scope
        scope = "playlist-modify-public playlist-modify-private user-read-private"

        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=scope,
            )
        )

        # Get current user info
        self.user_id = self.sp.current_user()["id"]
        print(f"🎵 Connected to Spotify as: {self.user_id}")

        # Thread-safe lock only for results collection
        self._results_lock = threading.Lock()
        # Semaphore to limit concurrent API calls (much more conservative)
        self._api_semaphore = threading.Semaphore(5)  # Only 5 concurrent requests

    def search_track(
        self, track_name: str, artist: str = "", album: str = "", game_title: str = ""
    ) -> Optional[Dict]:
        """
        Search for a track on Spotify with various strategies

        Args:
            track_name: Name of the track
            artist: Artist/composer name
            album: Album name (often the game title)
            game_title: Game title for alternative searching

        Returns:
            Dict with track information or None if not found
        """

        # Strategy 1: Direct search with artist
        if artist:
            query = f'track:"{track_name}" artist:"{artist}"'
            results = self._search_with_query(query)
            if results:
                return results

        # Strategy 2: Search with game title as album
        if game_title:
            query = f'track:"{track_name}" album:"{game_title}"'
            results = self._search_with_query(query)
            if results:
                return results

        # Strategy 3: Search for game soundtrack
        if game_title:
            query = f'"{track_name}" "{game_title}" soundtrack'
            results = self._search_with_query(query)
            if results:
                return results

        # Strategy 4: Fuzzy search - remove special characters
        clean_track = self._clean_track_name(track_name)
        query = f'"{clean_track}"'
        if artist:
            query += f' "{artist}"'
        results = self._search_with_query(query)
        if results:
            return results

        # Strategy 5: Very broad search
        query = clean_track
        results = self._search_with_query(query, limit=50)
        if results:
            # Use fuzzy matching to find best match
            return self._find_best_fuzzy_match(clean_track, results, artist)

        return None

    def _search_with_query(self, query: str, limit: int = 10) -> Optional[Dict]:
        """Execute Spotify search with given query (conservative rate limiting)"""
        try:
            # Use semaphore to limit concurrent requests
            with self._api_semaphore:
                # Much longer delay to be respectful to the API
                time.sleep(0.2)  # 200ms delay - much more conservative

                results = self.sp.search(q=query, type="track", limit=limit)
                tracks = results["tracks"]["items"]

                if tracks:
                    # Return the first result (most relevant)
                    track = tracks[0]
                    return {
                        "id": track["id"],
                        "name": track["name"],
                        "artists": [artist["name"] for artist in track["artists"]],
                        "album": track["album"]["name"],
                        "uri": track["uri"],
                        "external_urls": track["external_urls"],
                    }

        except Exception as e:
            print(f"❌ Search error for '{query}': {e}")

        return None

    def _clean_track_name(self, track_name: str) -> str:
        """Clean track name for better searching"""
        # Remove common VGM suffixes/prefixes
        cleaned = re.sub(r"\(.*?\)", "", track_name)  # Remove parentheses content
        cleaned = re.sub(r"\[.*?\]", "", cleaned)  # Remove brackets content
        cleaned = re.sub(r"\s*-\s*.*$", "", cleaned)  # Remove everything after dash
        cleaned = cleaned.strip()
        return cleaned

    def _find_best_fuzzy_match(
        self, target_name: str, tracks: List[Dict], target_artist: str = ""
    ) -> Optional[Dict]:
        """Find best match using fuzzy string matching"""
        best_score = 0
        best_track = None

        for track in tracks:
            # Calculate name similarity
            name_score = fuzz.ratio(target_name.lower(), track["name"].lower())

            # Bonus for artist match
            artist_bonus = 0
            if target_artist:
                for artist in track["artists"]:
                    artist_score = fuzz.ratio(
                        target_artist.lower(), artist["name"].lower()
                    )
                    artist_bonus = max(artist_bonus, artist_score)

            # Combined score (name is more important)
            total_score = name_score * 0.7 + artist_bonus * 0.3

            if total_score > best_score and total_score > 60:  # Minimum threshold
                best_score = total_score
                best_track = {
                    "id": track["id"],
                    "name": track["name"],
                    "artists": [artist["name"] for artist in track["artists"]],
                    "album": track["album"]["name"],
                    "uri": track["uri"],
                    "external_urls": track["external_urls"],
                    "match_score": total_score,
                }

        return best_track

    def _search_single_track(self, vgm_track: Dict) -> Tuple[Dict, bool]:
        """Search for a single track (designed for threading)"""
        try:
            spotify_track = self.search_track(
                track_name=vgm_track.get("title", ""),
                artist=vgm_track.get("composer", ""),
                game_title=vgm_track.get("game", ""),
            )

            if spotify_track:
                # Combine VGM metadata with Spotify data
                combined_track = {
                    **vgm_track,  # Original VGM data
                    "spotify": spotify_track,  # Spotify data
                    "matched": True,
                }
                return combined_track, True
            else:
                return {**vgm_track, "matched": False}, False

        except Exception as e:
            print(
                f"❌ Error searching for track '{vgm_track.get('title', 'Unknown')}': {e}"
            )
            return {**vgm_track, "matched": False}, False

    def search_and_match_tracks(
        self, vgm_tracks: List[Dict], max_workers: int = 10
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Search for VGM tracks on Spotify using multithreading

        Args:
            vgm_tracks: List of VGM track dictionaries with keys:
                       'title', 'composer', 'game', 'system'
            max_workers: Maximum number of concurrent threads

        Returns:
            Tuple of (found_tracks, not_found_tracks)
        """
        found_tracks = []
        not_found_tracks = []
        completed_count = 0

        total_tracks = len(vgm_tracks)
        print(
            f"🔍 Searching for {total_tracks} tracks on Spotify using {max_workers} threads..."
        )

        # Create simple progress tracking
        start_time = time.time()

        # Use ThreadPoolExecutor for concurrent processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_track = {
                executor.submit(self._search_single_track, track): track
                for track in vgm_tracks
            }

            # Process completed tasks
            for future in as_completed(future_to_track):
                original_track = future_to_track[future]

                try:
                    result_track, found = future.result()

                    # Thread-safe results update
                    with self._results_lock:
                        completed_count += 1
                        if found:
                            found_tracks.append(result_track)
                        else:
                            not_found_tracks.append(result_track)

                        # Simple progress update every 50 tracks
                        if completed_count % 50 == 0 or completed_count == total_tracks:
                            elapsed = time.time() - start_time
                            rate = completed_count / elapsed if elapsed > 0 else 0
                            eta = (
                                (total_tracks - completed_count) / rate
                                if rate > 0
                                else 0
                            )
                            print(
                                f"🎵 Progress: {completed_count}/{total_tracks} ({completed_count/total_tracks*100:.1f}%) | "
                                f"Found: {len(found_tracks)} | Rate: {rate:.1f} tracks/s | ETA: {eta/60:.1f}min"
                            )

                except Exception as e:
                    print(
                        f"❌ Thread error for track '{original_track.get('title', 'Unknown')}': {e}"
                    )
                    with self._results_lock:
                        completed_count += 1
                        not_found_tracks.append({**original_track, "matched": False})

        print(f"\n📊 Search Results:")
        print(
            f"   ✅ Found: {len(found_tracks)}/{total_tracks} ({len(found_tracks)/total_tracks*100:.1f}%)"
        )
        print(f"   ❌ Not found: {len(not_found_tracks)}")

        return {"found": found_tracks, "not_found": not_found_tracks}

    def create_playlist(
        self, name: str, description: str = "", public: bool = True
    ) -> str:
        """
        Create a new Spotify playlist

        Returns:
            Playlist ID
        """
        try:
            playlist = self.sp.user_playlist_create(
                user=self.user_id, name=name, description=description, public=public
            )

            print(f"✅ Created playlist: {name} (ID: {playlist['id']})")
            return playlist["id"]

        except Exception as e:
            print(f"❌ Error creating playlist '{name}': {e}")
            raise

    def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]) -> bool:
        """Add tracks to a playlist"""
        try:
            # Spotify limits to 100 tracks per request
            chunk_size = 100

            for i in range(0, len(track_uris), chunk_size):
                chunk = track_uris[i : i + chunk_size]
                self.sp.playlist_add_items(playlist_id, chunk)

            print(f"✅ Added {len(track_uris)} tracks to playlist")
            return True

        except Exception as e:
            print(f"❌ Error adding tracks to playlist: {e}")
            return False

    def create_playlist_from_found_tracks(
        self, playlist_name: str, found_tracks: List[Dict], description: str = ""
    ) -> Optional[str]:
        """
        Create a Spotify playlist from already-found tracks (no additional searching)

        Args:
            playlist_name: Name of the playlist to create
            found_tracks: List of tracks that already have Spotify data
            description: Playlist description

        Returns:
            Playlist ID if successful, None otherwise
        """
        try:
            print(
                f"🎵 Creating playlist '{playlist_name}' with {len(found_tracks)} tracks..."
            )

            # Create the playlist
            user_id = self.sp.current_user()["id"]
            playlist = self.sp.user_playlist_create(
                user_id, playlist_name, public=True, description=description
            )
            playlist_id = playlist["id"]

            # Extract Spotify track URIs
            track_uris = []
            for track in found_tracks:
                spotify_data = track.get("spotify", {})
                if spotify_data and "uri" in spotify_data:
                    track_uris.append(spotify_data["uri"])

            print(f"📝 Adding {len(track_uris)} tracks to playlist...")

            # Add tracks in batches (Spotify API limit is 100 per request)
            batch_size = 100
            for i in range(0, len(track_uris), batch_size):
                batch_uris = track_uris[i : i + batch_size]
                self.sp.playlist_add_items(playlist_id, batch_uris)
                print(
                    f"   ✅ Added batch {i//batch_size + 1}/{(len(track_uris)-1)//batch_size + 1}"
                )

            print(f"🎉 Playlist created successfully!")
            return playlist_id

        except Exception as e:
            print(f"❌ Error creating playlist: {e}")
            return None

    def create_vgm_playlist(
        self, playlist_name: str, vgm_tracks: List[Dict], game_name: str = ""
    ) -> str:
        """
        Create a complete VGM playlist from track data

        Returns:
            Playlist ID
        """
        # Search for tracks on Spotify
        found_tracks, not_found = self.search_and_match_tracks(vgm_tracks)

        if not found_tracks:
            print("❌ No tracks found on Spotify!")
            return None

        # Create playlist description
        description = f"Video Game Music playlist"
        if game_name:
            description += f" from {game_name}"
        description += f" • {len(found_tracks)} tracks • Created by VGM-Spotify Bridge"

        # Create the playlist
        playlist_id = self.create_playlist(playlist_name, description)

        # Extract Spotify URIs
        track_uris = [track["spotify"]["uri"] for track in found_tracks]

        # Add tracks to playlist
        success = self.add_tracks_to_playlist(playlist_id, track_uris)

        if success:
            print(
                f"🎉 Successfully created playlist '{playlist_name}' with {len(found_tracks)} tracks!"
            )
            if not_found:
                print(f"⚠️  {len(not_found)} tracks were not found on Spotify")

        return playlist_id


def main():
    """Test the Spotify integration"""
    print("🎵 Testing Spotify Integration...")

    try:
        spotify = SpotifyVGMIntegrator()

        # Test with some sample VGM tracks
        sample_tracks = [
            {
                "title": "Chrono Trigger",
                "composer": "Yasunori Mitsuda",
                "game": "Chrono Trigger",
                "system": "SNES",
            },
            {
                "title": "One Winged Angel",
                "composer": "Nobuo Uematsu",
                "game": "Final Fantasy VII",
                "system": "PlayStation",
            },
        ]

        # Test search functionality
        found, not_found = spotify.search_and_match_tracks(sample_tracks)

        print(f"\n✅ Test completed!")
        print(f"Found {len(found)} tracks, {len(not_found)} not found")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure to create a .env file with your Spotify credentials")


if __name__ == "__main__":
    main()
