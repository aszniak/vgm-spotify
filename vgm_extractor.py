#!/usr/bin/env python3
"""
VipVGM Track Extractor
Extracts track information from VipVGM's roster.json endpoint.
"""

import requests
import json
from typing import List, Dict, Optional
from urllib.parse import urljoin


class VipVGMExtractor:
    def __init__(self):
        self.base_url = "https://www.vipvgm.net/"
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "VGM-Spotify-Bridge/1.0 (Contact: github.com/your-repo)"}
        )

    def get_tracks_from_json_api(self) -> List[Dict]:
        """
        Extract tracks from VipVGM's roster.json endpoint.
        This is the official data source with 2000+ tracks.
        """
        print("🎵 Fetching tracks from VipVGM roster.json...")

        json_url = urljoin(self.base_url, "roster.json")

        try:
            print(f"🔍 Requesting: {json_url}")
            response = self.session.get(json_url, timeout=30)
            response.raise_for_status()

            print(f"✅ Successfully fetched JSON data ({len(response.content)} bytes)")

            # Parse JSON
            data = response.json()

            if "tracks" not in data:
                print("❌ No 'tracks' field found in JSON response")
                return []

            tracks_data = data["tracks"]
            print(f"📊 Found {len(tracks_data)} tracks in roster")

            tracks = []
            for track_data in tracks_data:
                # Convert VipVGM format to our standard format
                track = {
                    "id": track_data.get("id"),
                    "title": track_data.get("title", "").strip(),
                    "artist": track_data.get("comp", "").strip(),  # composer
                    "game": track_data.get("game", "").strip(),
                    "file": track_data.get("file", "").strip(),
                }

                # Only add tracks with title and artist (for better Spotify matching)
                if track["title"] and track["artist"]:
                    tracks.append(track)
                else:
                    print(f"⚠️ Skipping track without title or artist: {track}")

            print(f"📊 Successfully processed {len(tracks)} valid tracks")

            # Show sample tracks
            if tracks:
                print("\n🎵 Sample tracks:")
                for i, track in enumerate(tracks[:3]):
                    print(f"   {i+1}. {track['title']} - {track['artist']}")
                    print(f"      Game: {track['game']}")
                    print(f"      File: {track['file']}")
                    print()

            return tracks

        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching roster.json: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {e}")
            return []
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return []

    def get_all_tracks(self) -> List[Dict]:
        """Get all tracks using the JSON API method"""
        return self.get_tracks_from_json_api()

    def search_tracks(
        self, query: str = "", game: str = "", artist: str = ""
    ) -> List[Dict]:
        """
        Search tracks by query, game, or artist
        """
        all_tracks = self.get_all_tracks()

        if not any([query, game, artist]):
            return all_tracks

        filtered_tracks = []
        query_lower = query.lower() if query else ""
        game_lower = game.lower() if game else ""
        artist_lower = artist.lower() if artist else ""

        for track in all_tracks:
            # Check if track matches search criteria
            matches = True

            if query:
                matches = matches and (
                    query_lower in track.get("title", "").lower()
                    or query_lower in track.get("artist", "").lower()
                    or query_lower in track.get("game", "").lower()
                )

            if game:
                matches = matches and game_lower in track.get("game", "").lower()

            if artist:
                matches = matches and artist_lower in track.get("artist", "").lower()

            if matches:
                filtered_tracks.append(track)

        print(f"🔍 Found {len(filtered_tracks)} tracks matching search criteria")
        return filtered_tracks

    def get_track_stats(self) -> Dict:
        """Get statistics about the track collection"""
        tracks = self.get_all_tracks()

        if not tracks:
            return {}

        games = set()
        artists = set()

        for track in tracks:
            if track.get("game"):
                games.add(track["game"])
            if track.get("artist"):
                artists.add(track["artist"])

        return {
            "total_tracks": len(tracks),
            "unique_games": len(games),
            "unique_artists": len(artists),
            "sample_games": sorted(list(games))[:10],
            "sample_artists": sorted(list(artists))[:10],
        }


def main():
    """Test the VipVGM extractor"""
    extractor = VipVGMExtractor()

    print("🎮 VipVGM Track Extractor Test")
    print("=" * 50)

    # Test basic track extraction
    tracks = extractor.get_all_tracks()
    print(f"\n📊 Total tracks found: {len(tracks)}")

    if tracks:
        print("\n🎵 First 5 tracks:")
        for i, track in enumerate(tracks[:5]):
            print(f"  {i+1}. {track['title']} - {track['artist']}")
            print(f"     Game: {track['game']}")

    # Get collection statistics
    stats = extractor.get_track_stats()
    if stats:
        print(f"\n📈 Collection Statistics:")
        print(f"  Total tracks: {stats['total_tracks']}")
        print(f"  Unique games: {stats['unique_games']}")
        print(f"  Unique artists: {stats['unique_artists']}")

        print(f"\n🎮 Sample games:")
        for game in stats["sample_games"]:
            print(f"  - {game}")

    # Test search functionality
    print(f"\n🔍 Testing search for 'Mario':")
    mario_tracks = extractor.search_tracks(query="Mario")
    for track in mario_tracks[:3]:
        print(f"  - {track['title']} ({track['game']})")


if __name__ == "__main__":
    main()
