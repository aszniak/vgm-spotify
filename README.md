# 🎮 VGM-Spotify Bridge

Create Spotify playlists from VipVGM.net's collection of video game music!

## 🚀 Features

- 🎵 Extracts high-quality VGM tracks from VipVGM.net (1,779 tracks!)
- 🔍 Smart track matching on Spotify with fuzzy search
- 🎯 **Intelligent genre filtering** to avoid non-VGM tracks (Christmas, pop, country, etc.)
- 🎮 Preserves legitimate VGM genres (electronic, techno, metal, jazz, orchestral)
- 🌍 Location-independent search (uses US market by default)
- ⚡ Multithreaded processing for faster playlist creation
- 📊 Detailed progress tracking and results reporting
- 📈 Genre analysis reports for transparency
- 🗑️ Playlist management tools (delete unwanted playlists)
- 🎨 Beautiful console output with emojis

## 📋 Prerequisites

- Python 3.8 or higher
- Spotify Premium account (free accounts work too, but Premium is recommended)
- Spotify Developer Application (free)

## 🛠️ Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Spotify API Setup

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications)
2. Create a new app
3. Copy your Client ID and Client Secret
4. Set redirect URI to: `http://localhost:8080/callback`

### 3. Configuration

```bash
cp config.env.example config.env
# Edit config.env with your Spotify credentials
```

Your `config.env` should look like:

```
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://localhost:8080/callback
```

## 🚀 Usage

### Create Ultimate VGM Playlist

```bash
python3 create_master_playlist.py
```

This will:

1. Extract all VGM tracks from VipVGM.net (1,779 tracks)
2. Search for each track on Spotify using intelligent genre filtering
3. Use 3 concurrent threads for safe, reliable processing
4. Create a Spotify playlist with all found tracks
5. Generate detailed results and genre analysis in JSON format

### Expected Results

- **Processing Time**: ~8-10 minutes (with genre filtering for quality)
- **Success Rate**: ~85-90% of tracks found on Spotify
- **Final Playlist**: 1,400-1,600 high-quality VGM tracks ready to play!
- **Bonus**: Genre analysis report to understand track filtering

## 📁 Project Structure

```
vgm-spotify/
├── create_master_playlist.py   # Main script - creates ultimate playlist
├── vgm_extractor.py           # Extracts tracks from VipVGM roster.json
├── spotify_integration.py     # Spotify API integration with threading + genre filtering
├── delete_playlist.py         # Utility to delete Spotify playlists
├── requirements.txt           # Python dependencies
├── config.env.example        # Configuration template
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

## ⚙️ Configuration Options

You can adjust threading performance in `create_master_playlist.py`:

```python
# Conservative (safe, ~10min) - Default
results = create_master_vgm_playlist(max_workers=3)

# Balanced (faster, ~8min) - May encounter some rate limits
results = create_master_vgm_playlist(max_workers=5)

# Aggressive (fastest, ~5-6min) - Higher chance of rate limits
results = create_master_vgm_playlist(max_workers=8)
```

### Additional Tools

**Delete unwanted playlists:**

```bash
python3 delete_playlist.py
```

- Interactive tool to view and delete your Spotify playlists
- Useful for cleaning up test playlists

## 📊 Output

The script generates:

- **Spotify Playlist**: Directly added to your account
- **JSON Report**: Detailed results with statistics and track data
- **Console Output**: Real-time progress and final summary

Example output:

```
🔍 Searching for 1779 tracks on Spotify using 3 threads...
🎵 Progress: 850/1779 (47.8%) | Found: 789 | Rate: 2.9 tracks/s | ETA: 5.3min
⚠️  No VGM tracks found for query: "Jingle Bells Christmas"
🎉 Master playlist created successfully!
✅ Tracks found: 1456/1779 (81.8%)
📊 Genre analysis saved to: vgm_genre_analysis_20231215_143022.json
🌐 Spotify URL: https://open.spotify.com/playlist/abc123xyz
```

## 🚨 Important Notes

- **First Run**: May require browser authentication for Spotify OAuth
- **Rate Limits**: Script automatically handles Spotify API rate limits
- **Large Dataset**: Processing 1,700+ tracks takes several minutes
- **Internet Required**: Needs stable connection for API calls
- **Genre Filtering**: Enabled by default for quality - filters out Christmas, pop, country music
- **Processing Speed**: Quality over speed - genre filtering adds time but improves results

## 🎯 Why This Project?

VipVGM.net hosts an incredible collection of video game music, but there was no easy way to enjoy it on modern streaming platforms. This bridge solves that by:

1. **Automating Discovery**: No manual track searching
2. **Maximizing Matches**: Advanced search strategies find obscure tracks
3. **Saving Time**: What would take days manually happens in minutes
4. **Creating Value**: Transform a database into a playable playlist

## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests! Some ideas:

- Additional streaming platform support (Apple Music, YouTube Music)
- Enhanced matching algorithms
- Playlist organization by genre/console/era
- GUI interface

## 📄 License

This project is for educational and personal use. Respect VipVGM.net's terms of service and Spotify's API guidelines.

---

**Happy listening! 🎵🎮**
