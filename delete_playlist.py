#!/usr/bin/env python3
"""
Delete Spotify Playlists
Interactive tool to view and delete Spotify playlists
"""

from spotify_integration import SpotifyVGMIntegrator
import sys


def main():
    """Main function to delete playlists"""
    print("🗑️  Spotify Playlist Manager")
    print("=" * 40)

    # Initialize Spotify client
    try:
        spotify = SpotifyVGMIntegrator()
    except Exception as e:
        print(f"❌ Error connecting to Spotify: {e}")
        return

    # Get user's playlists
    print("\n📋 Fetching your playlists...")
    playlists = spotify.get_user_playlists(limit=50)

    if not playlists:
        print("No playlists found!")
        return

    # Filter VGM playlists
    vgm_playlists = [
        p for p in playlists if "VGM" in p["name"] or "Ultimate VGM" in p["name"]
    ]

    if vgm_playlists:
        print(f"\n🎮 Found {len(vgm_playlists)} VGM playlist(s):")
        for i, playlist in enumerate(vgm_playlists):
            print(f"\n{i+1}. {playlist['name']}")
            print(f"   Tracks: {playlist['tracks']}")
            print(f"   ID: {playlist['id']}")
            print(f"   URL: {playlist['url']}")

    # Show all playlists
    print(f"\n📋 All your playlists ({len(playlists)} total):")
    for i, playlist in enumerate(playlists):
        print(f"\n{i+1}. {playlist['name']}")
        print(f"   Tracks: {playlist['tracks']}")
        if playlist["description"]:
            print(f"   Description: {playlist['description'][:60]}...")

    # Ask which to delete
    print("\n" + "=" * 40)
    print("Enter the number of the playlist to delete (or 'q' to quit):")

    while True:
        choice = input("\n> ").strip()

        if choice.lower() == "q":
            print("👋 Exiting without deleting anything.")
            break

        try:
            index = int(choice) - 1
            if 0 <= index < len(playlists):
                selected = playlists[index]

                # Confirm deletion
                print(f"\n⚠️  Are you sure you want to delete '{selected['name']}'?")
                print(f"   This playlist has {selected['tracks']} tracks.")
                confirm = input("Type 'yes' to confirm: ").strip().lower()

                if confirm == "yes":
                    if spotify.delete_playlist(selected["id"]):
                        print(f"✅ Deleted '{selected['name']}'")
                    else:
                        print(f"❌ Failed to delete '{selected['name']}'")
                else:
                    print("❌ Deletion cancelled.")

                # Ask if they want to delete another
                another = input("\nDelete another playlist? (y/n): ").strip().lower()
                if another != "y":
                    break
            else:
                print("❌ Invalid number. Please try again.")

        except ValueError:
            print("❌ Please enter a valid number or 'q' to quit.")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
