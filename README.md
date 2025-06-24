# 🎮 VGM-Spotify Bridge

A Python tool that creates ultimate Spotify playlists from the entire VipVGM.net video game music collection. Automatically searches for and matches 1,700+ VGM tracks on Spotify using intelligent fuzzy matching and multithreaded processing.

## ✨ Features

- **🎵 Complete VGM Collection**: Extracts 1,779 high-quality VGM tracks from VipVGM.net
- **🚀 Fast Multithreaded Search**: Uses concurrent API calls to process tracks in ~5-6 minutes
- **🧠 Intelligent Matching**: Multiple search strategies with fuzzy matching for maximum success rate
- **📊 Detailed Results**: Comprehensive JSON reports with found/not-found tracks and statistics
- **🔄 Rate Limit Handling**: Smart rate limiting and automatic retry mechanisms
- **🎯 One-Click Playlists**: Creates ready-to-use Spotify playlists automatically

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
2. Search for each track on Spotify using 8 concurrent threads
3. Create a Spotify playlist with all found tracks
4. Generate detailed results in JSON format

### Expected Results

- **Processing Time**: ~5-6 minutes
- **Success Rate**: ~85-90% of tracks found on Spotify
- **Final Playlist**: 1,400-1,600 tracks ready to play!

## 📁 Project Structure

```
vgm-spotify/
├── create_master_playlist.py   # Main script - creates ultimate playlist
├── vgm_extractor.py           # Extracts tracks from VipVGM roster.json
├── spotify_integration.py     # Spotify API integration with threading
├── requirements.txt           # Python dependencies
├── config.env.example        # Configuration template
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

## ⚙️ Configuration Options

You can adjust threading performance in `create_master_playlist.py`:

```python
# Conservative (safe, ~8min)
results = create_master_vgm_playlist(max_workers=3)

# Balanced (recommended, ~5-6min)
results = create_master_vgm_playlist(max_workers=5)

# Aggressive (faster but may hit rate limits)
results = create_master_vgm_playlist(max_workers=8)
```

## 📊 Output

The script generates:

- **Spotify Playlist**: Directly added to your account
- **JSON Report**: Detailed results with statistics and track data
- **Console Output**: Real-time progress and final summary

Example output:

```
🔍 Searching for 1779 tracks on Spotify using 8 threads...
🎵 Progress: 850/1779 (47.8%) | Found: 789 | Rate: 8.2 tracks/s | ETA: 1.9min
🎉 Master playlist created successfully!
✅ Tracks found: 1456/1779 (81.8%)
🌐 Spotify URL: https://open.spotify.com/playlist/abc123xyz
```

## 🚨 Important Notes

- **First Run**: May require browser authentication for Spotify OAuth
- **Rate Limits**: Script automatically handles Spotify API rate limits
- **Large Dataset**: Processing 1,700+ tracks takes several minutes
- **Internet Required**: Needs stable connection for API calls

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
