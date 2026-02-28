# Runtime dependencies

QAVE can generate `trace.json` with Python alone. Processing, PeasyCam, and ffmpeg are required only to render frames and encode MP4 or GIF.

## Processing CLI

QAVE runs the viewer using the Processing 4 CLI. It accepts either `processing-java` or `Processing` on your `PATH`.
The bootstrap script pins Processing `4.5.2` portable CLI on Linux x86_64 and prints the executable directory (`.../processing-4.5.2/bin`) for PATH export.

### Linux (x86_64)

```bash
./viewer/scripts/install_processing_cli.sh
eval "$("./viewer/scripts/install_processing_cli.sh --print-export)"
```

Confirm the CLI is available:

```bash
command -v Processing || command -v processing-java
```

### macOS

1. Install Processing 4.
2. Add the Processing CLI directory to your `PATH`. If you installed Processing at `/Applications/Processing.app`, this works for the current shell session:

```bash
export PATH="/Applications/Processing.app/Contents/MacOS:$PATH"
```

3. Confirm it works:

```bash
Processing cli --help
```

### Windows

1. Install Processing 4.
2. Add the directory that contains `Processing.exe` to `PATH` so the `Processing` command is available.
3. Confirm it works by running `Processing cli --help`.
4. Run viewer scripts from Git Bash or WSL2.

## PeasyCam

The viewer requires the PeasyCam Processing sketchbook library.

Install it by running:

```bash
./viewer/scripts/install_processing_peasycam.sh
```

If you are not sure where your sketchbook directory is, open Processing and check Preferences for the configured Sketchbook location.

The installer script reads the sketchbook path from Processing preferences when available. If no preferences are found, it falls back to `~/sketchbook` on Linux and `~/Documents/Processing` on macOS and Windows.

If your sketchbook is in a non-default location, set `QAVE_PROCESSING_SKETCHBOOK` to your sketchbook directory before running the script:

```bash
export QAVE_PROCESSING_SKETCHBOOK="/path/to/sketchbook"
```

If you prefer manual installation, extract the `peasycam/` folder into your Processing sketchbook at `libraries/peasycam/`.

On Windows, run the script in Git Bash, or install PeasyCam manually into your sketchbook. If you run it from WSL2, set `QAVE_PROCESSING_SKETCHBOOK` to your Windows sketchbook path (for example, `/mnt/c/Users/<you>/Documents/Processing`).

## ffmpeg

`ffmpeg` is required to encode MP4 and GIF outputs from rendered PNG frames. Viewer playback of an existing `trace.json` does not require ffmpeg.

### macOS

```bash
brew install ffmpeg
```

### Linux (Debian or Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
```

On other Linux distros, install ffmpeg via your package manager.

### Windows

1. Install ffmpeg.
2. Add the directory that contains `ffmpeg.exe` to `PATH`.
3. Confirm it works by running `ffmpeg -version`.
