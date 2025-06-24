#!/usr/bin/env python3
"""
Create Master VGM Playlist
Creates one huge Spotify playlist containing all VGM tracks from VipVGM.
"""

from vgm_extractor import VipVGMExtractor
from spotify_integration import SpotifyVGMIntegrator
import time
import json
from datetime import datetime


def create_master_vgm_playlist(max_workers: int = 10):
    """Create a master playlist with all VGM tracks

    Args:
        max_workers: Number of concurrent threads for Spotify search (default: 10)
    """
    print("🎮 VGM-Spotify Bridge - Master Playlist Creator")
    print("=" * 60)

    # Initialize extractors
    print("📡 Initializing VGM extractor...")
    vgm_extractor = VipVGMExtractor()

    print("🎵 Initializing Spotify integration...")
    spotify = SpotifyVGMIntegrator()

    # Get all VGM tracks (this will only run once)
    print("\n🎵 Fetching all VGM tracks from VipVGM...")
    all_tracks = vgm_extractor.get_all_tracks()

    if not all_tracks:
        print("❌ No tracks found!")
        return

    print(f"📊 Found {len(all_tracks)} high-quality VGM tracks with composers")
    print(
        f"⏱️  Estimated time: ~{(len(all_tracks) * 0.5) // 60 + 1} minutes with {max_workers} threads (conservative rate limiting)"
    )

    # Convert VGM tracks to the format expected by Spotify integration
    converted_tracks = []
    for track in all_tracks:
        converted_track = {
            "title": track.get("title", ""),
            "composer": track.get("artist", ""),  # VGM uses 'artist' field for composer
            "game": track.get("game", ""),
            "system": "Various",  # We don't have system info in the new format
        }
        converted_tracks.append(converted_track)

    # Create the master playlist
    playlist_name = f"Ultimate VGM Collection - {datetime.now().strftime('%Y-%m-%d')}"

    print(f"\n🎯 Creating master playlist: '{playlist_name}'")

    # Search for tracks and create playlist (now with multithreading!)
    search_results = spotify.search_and_match_tracks(
        converted_tracks, max_workers=max_workers
    )
    found_tracks = search_results["found"]
    not_found_tracks = search_results["not_found"]

    if found_tracks:
        # Create playlist directly with the already-found tracks (no second search!)
        playlist_id = spotify.create_playlist_from_found_tracks(
            playlist_name,
            found_tracks,
            "Ultimate VGM Collection from VipVGM.net - All your favorite video game music in one place!",
        )

        # Save results for analysis
        results = {
            "playlist_id": playlist_id,
            "playlist_name": playlist_name,
            "total_tracks": len(all_tracks),
            "found_count": len(found_tracks),
            "not_found_count": len(not_found_tracks),
            "success_rate": len(found_tracks) / len(all_tracks) * 100,
            "created_at": datetime.now().isoformat(),
            "threads_used": max_workers,
            "found_tracks": found_tracks,
            "not_found_tracks": not_found_tracks,
        }

        # Save detailed results
        results_file = (
            f"vgm_playlist_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n🎉 Master playlist created successfully!")
        print(f"📊 Final Statistics:")
        print(f"   🎵 Playlist: {playlist_name}")
        print(f"   🆔 Playlist ID: {playlist_id}")
        print(
            f"   ✅ Tracks found: {len(found_tracks)}/{len(all_tracks)} ({results['success_rate']:.1f}%)"
        )
        print(f"   ❌ Tracks not found: {len(not_found_tracks)}")
        print(f"   🧵 Threads used: {max_workers}")
        print(f"   📄 Detailed results saved to: {results_file}")

        if playlist_id:
            spotify_url = f"https://open.spotify.com/playlist/{playlist_id}"
            print(f"   🌐 Spotify URL: {spotify_url}")

        return results
    else:
        print("❌ No tracks were found on Spotify!")
        return None


if __name__ == "__main__":
    # You can adjust the number of threads here if needed
    # max_workers=3: Very conservative (safe, ~5-8min)
    # max_workers=5: Conservative (recommended - good balance)
    # max_workers=8: Balanced (might hit some limits)
    # max_workers=10+: Too aggressive (will hit rate limits)

    results = create_master_vgm_playlist(max_workers=8)
    if results:
        print(
            f"\n🎯 Your ultimate VGM playlist is ready with {results['found_count']} tracks!"
        )
