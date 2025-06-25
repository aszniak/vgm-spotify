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
import json
from datetime import datetime

# Suppress noisy warnings from spotipy and urllib3
logging.getLogger("spotipy").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("root").setLevel(logging.ERROR)

# Load environment variables
load_dotenv("config.env")


class SpotifyVGMIntegrator:
    def __init__(self, market: str = "US", enable_genre_filtering: bool = True):
        """Initialize Spotify client with OAuth"""
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = os.getenv(
            "SPOTIFY_REDIRECT_URI", "http://localhost:8080/callback"
        )

        # Market to use for searches (default: US for consistent VGM results)
        self.market = market
        # Enable/disable genre filtering (can be disabled for faster processing)
        self.enable_genre_filtering = enable_genre_filtering

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
        print(f"🌍 Using market: {self.market} for searches")
        if not self.enable_genre_filtering:
            print("⚡ Genre filtering disabled for faster processing")

        # Thread-safe lock only for results collection
        self._results_lock = threading.Lock()
        # Semaphore to limit concurrent API calls (much more conservative)
        self._api_semaphore = threading.Semaphore(5)  # Only 5 concurrent requests

        # Track genre analysis data
        self.genre_analysis = {
            "tracks_analyzed": 0,
            "genre_distribution": {},
            "vgm_scores": [],
            "rejected_tracks": [],
        }

        # Non-VGM genres to filter out
        self.non_vgm_genres = {
            "christmas",
            "xmas",
            "holiday",
            "pop",
            "rock",
            "country",
            "blues",
            "hip hop",
            "rap",
            "r&b",
            "soul",
            "funk",
            "disco",
            "reggae",
            "ska",
            "latin",
            "salsa",
            "bachata",
            "reggaeton",
            "classical",
            "opera",
            "chamber",
            "orchestra",
            "symphony",
            "punk",
            "indie",
            "alternative",
            "grunge",
            "emo",
            "folk",
            "bluegrass",
            "world",
            "new age",
            "christian",
            "gospel",
            "worship",
            "ccm",
            "adult standards",
            "easy listening",
            "lounge",
            "comedy",
            "spoken word",
            "podcast",
            "children",
            "kids",
            "nursery",
        }

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

                # Use US market for more consistent VGM results (avoids local bias)
                results = self.sp.search(
                    q=query, type="track", limit=limit, market=self.market
                )
                tracks = results["tracks"]["items"]

                if not tracks:
                    return None

                # Filter tracks by genre likelihood (if enabled)
                if self.enable_genre_filtering:
                    vgm_candidates = []
                    for track in tracks:
                        is_vgm, confidence = self._is_likely_vgm(track)
                        if is_vgm:
                            vgm_candidates.append((track, confidence))

                    if not vgm_candidates:
                        # No VGM candidates found
                        print(f"⚠️  No VGM tracks found for query: {query}")
                        return None

                    # Sort by confidence and return the best match
                    vgm_candidates.sort(key=lambda x: x[1], reverse=True)
                    best_track = vgm_candidates[0][0]
                    best_confidence = vgm_candidates[0][1]
                else:
                    # No genre filtering - just return the first track
                    best_track = tracks[0]
                    best_confidence = 0.5  # Default confidence when no filtering

                return {
                    "id": best_track["id"],
                    "name": best_track["name"],
                    "artists": [artist["name"] for artist in best_track["artists"]],
                    "album": best_track["album"]["name"],
                    "uri": best_track["uri"],
                    "external_urls": best_track["external_urls"],
                    "vgm_confidence": best_confidence,  # Add VGM confidence score
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
        """Find best match using fuzzy string matching with genre filtering"""
        best_score = 0
        best_track = None

        for track in tracks:
            # First check if it's likely VGM (if genre filtering enabled)
            if self.enable_genre_filtering:
                is_vgm, genre_confidence = self._is_likely_vgm(track)
                if not is_vgm:
                    continue  # Skip non-VGM tracks
            else:
                genre_confidence = 0.5  # Default confidence when no filtering

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
            # Include genre confidence in the scoring
            total_score = name_score * 0.6 + artist_bonus * 0.3 + genre_confidence * 10

            if (
                total_score > best_score and name_score > 70
            ):  # Raised threshold from 60 to 70
                best_score = total_score
                best_track = {
                    "id": track["id"],
                    "name": track["name"],
                    "artists": [artist["name"] for artist in track["artists"]],
                    "album": track["album"]["name"],
                    "uri": track["uri"],
                    "external_urls": track["external_urls"],
                    "match_score": total_score,
                    "vgm_confidence": genre_confidence,  # Add VGM confidence score
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

    def get_user_playlists(self, limit: int = 50) -> List[Dict]:
        """
        Get current user's playlists

        Args:
            limit: Maximum number of playlists to retrieve

        Returns:
            List of playlist dictionaries
        """
        try:
            playlists = []
            results = self.sp.current_user_playlists(limit=limit)

            while results:
                for playlist in results["items"]:
                    # Only include playlists owned by the current user
                    if playlist["owner"]["id"] == self.user_id:
                        playlists.append(
                            {
                                "id": playlist["id"],
                                "name": playlist["name"],
                                "tracks": playlist["tracks"]["total"],
                                "description": playlist.get("description", ""),
                                "public": playlist["public"],
                                "url": playlist["external_urls"]["spotify"],
                            }
                        )

                # Check if there are more playlists
                if results["next"]:
                    results = self.sp.next(results)
                else:
                    break

            return playlists

        except Exception as e:
            print(f"❌ Error getting playlists: {e}")
            return []

    def delete_playlist(self, playlist_id: str) -> bool:
        """
        Delete (unfollow) a playlist

        Args:
            playlist_id: The Spotify playlist ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Spotify doesn't have a direct delete API, but unfollowing your own playlist deletes it
            self.sp.current_user_unfollow_playlist(playlist_id)
            print(f"✅ Successfully deleted playlist")
            return True

        except Exception as e:
            print(f"❌ Error deleting playlist: {e}")
            return False

    def save_genre_analysis(self, filename: str = "vgm_genre_analysis.json"):
        """
        Save the genre analysis data to a JSON file

        Args:
            filename: Name of the file to save to
        """
        analysis_data = {
            "analysis_date": datetime.now().isoformat(),
            "total_tracks_analyzed": self.genre_analysis["tracks_analyzed"],
            "genre_distribution": dict(
                sorted(
                    self.genre_analysis["genre_distribution"].items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            ),
            "vgm_confidence_scores": sorted(
                self.genre_analysis["vgm_scores"],
                key=lambda x: x["confidence"],
                reverse=True,
            ),
            "rejected_tracks": self.genre_analysis["rejected_tracks"],
            "confidence_summary": {
                "high_confidence_95": len(
                    [
                        s
                        for s in self.genre_analysis["vgm_scores"]
                        if s["confidence"] >= 0.95
                    ]
                ),
                "good_confidence_80": len(
                    [
                        s
                        for s in self.genre_analysis["vgm_scores"]
                        if 0.8 <= s["confidence"] < 0.95
                    ]
                ),
                "medium_confidence_60": len(
                    [
                        s
                        for s in self.genre_analysis["vgm_scores"]
                        if 0.6 <= s["confidence"] < 0.8
                    ]
                ),
                "low_confidence": len(
                    [
                        s
                        for s in self.genre_analysis["vgm_scores"]
                        if s["confidence"] < 0.6
                    ]
                ),
            },
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)

        print(f"\n📊 Genre analysis saved to: {filename}")
        print(f"   - Tracks analyzed: {analysis_data['total_tracks_analyzed']}")
        print(f"   - Unique genres found: {len(analysis_data['genre_distribution'])}")
        print(f"   - Rejected tracks: {len(analysis_data['rejected_tracks'])}")

    def _is_likely_vgm(self, track: Dict) -> Tuple[bool, float]:
        """
        Check if a track is likely video game music based on artist genres

        Returns:
            Tuple of (is_likely_vgm, confidence_score)
        """
        try:
            # Get artist IDs
            artist_ids = [artist["id"] for artist in track.get("artists", [])]
            if not artist_ids:
                return True, 0.5  # No artists, can't tell

            # Fetch artist information with genres
            with self._api_semaphore:
                time.sleep(0.1)  # Rate limiting
                artists_data = self.sp.artists(artist_ids)

            # Collect all genres
            all_genres = []
            artist_names = []
            for artist in artists_data.get("artists", []):
                all_genres.extend(artist.get("genres", []))
                artist_names.append(artist.get("name", "Unknown"))

            # Update genre distribution
            with self._results_lock:
                self.genre_analysis["tracks_analyzed"] += 1
                for genre in all_genres:
                    self.genre_analysis["genre_distribution"][genre] = (
                        self.genre_analysis["genre_distribution"].get(genre, 0) + 1
                    )

            track_info = {
                "name": track.get("name", "Unknown"),
                "artists": artist_names,
                "album": track.get("album", {}).get("name", "Unknown"),
                "genres": all_genres,
            }

            if not all_genres:
                # No genre info, but if it has "soundtrack" or "game" in album name, probably VGM
                album_name = track.get("album", {}).get("name", "").lower()
                if any(
                    keyword in album_name
                    for keyword in ["soundtrack", "ost", "game", "vgm"]
                ):
                    confidence = 0.8
                    with self._results_lock:
                        self.genre_analysis["vgm_scores"].append(
                            {
                                **track_info,
                                "confidence": confidence,
                                "reason": "Album name contains VGM keywords",
                            }
                        )
                    return True, confidence
                confidence = 0.5
                with self._results_lock:
                    self.genre_analysis["vgm_scores"].append(
                        {
                            **track_info,
                            "confidence": confidence,
                            "reason": "No genre info available",
                        }
                    )
                return True, confidence  # No genre info, can't tell for sure

            # Check for VGM-positive indicators
            vgm_indicators = {
                "soundtrack",
                "video game",
                "game",
                "vgm",
                "chiptune",
                "8bit",
                "8-bit",
                "nintendocore",
                "ost",
                "score",
            }

            # Check for Japanese music (often VGM)
            japanese_indicators = {
                "j-pop",
                "jpop",
                "j-rock",
                "jrock",
                "anime",
                "japanese",
            }

            genre_text = " ".join(all_genres).lower()

            # Strong VGM indicators
            if any(indicator in genre_text for indicator in vgm_indicators):
                confidence = 0.95
                with self._results_lock:
                    self.genre_analysis["vgm_scores"].append(
                        {
                            **track_info,
                            "confidence": confidence,
                            "reason": f"Contains VGM genre indicators: {[i for i in vgm_indicators if i in genre_text]}",
                        }
                    )
                return True, confidence

            # Japanese music is often VGM
            if any(indicator in genre_text for indicator in japanese_indicators):
                confidence = 0.8
                with self._results_lock:
                    self.genre_analysis["vgm_scores"].append(
                        {
                            **track_info,
                            "confidence": confidence,
                            "reason": f"Contains Japanese music indicators: {[i for i in japanese_indicators if i in genre_text]}",
                        }
                    )
                return True, confidence

            # Check for non-VGM genres
            for genre in all_genres:
                genre_lower = genre.lower()
                for non_vgm in self.non_vgm_genres:
                    if non_vgm in genre_lower:
                        # Special case: orchestral/classical can be VGM if album suggests it
                        album_name = track.get("album", {}).get("name", "").lower()
                        if any(
                            keyword in album_name
                            for keyword in ["soundtrack", "ost", "game", "vgm"]
                        ):
                            confidence = 0.7
                            with self._results_lock:
                                self.genre_analysis["vgm_scores"].append(
                                    {
                                        **track_info,
                                        "confidence": confidence,
                                        "reason": f"Has non-VGM genre '{genre}' but album suggests VGM",
                                    }
                                )
                            return True, confidence
                        # Track rejected
                        with self._results_lock:
                            self.genre_analysis["rejected_tracks"].append(
                                {
                                    **track_info,
                                    "rejected_for": non_vgm,
                                    "matched_genre": genre,
                                }
                            )
                        return False, 0.1

            # No strong indicators either way
            confidence = 0.6
            with self._results_lock:
                self.genre_analysis["vgm_scores"].append(
                    {
                        **track_info,
                        "confidence": confidence,
                        "reason": "No strong indicators either way",
                    }
                )
            return True, confidence

        except Exception as e:
            print(f"⚠️  Error checking genres: {e}")
            return True, 0.5  # Default to including if error


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
