/*
Purpose: Export deterministic frame sequences for offline encoding.
Inputs: Shared playback state, trace-derived models, pane metrics, and user interaction state.
Outputs: Deterministic frame-local rendering updates and synchronized visual state transitions.
Determinism/Timing: Uses timeline phases (pre_gate/apply_gate/settle) and fixed frame progression for reproducible output.
*/

class FrameExporter {
  PApplet app;
  String mode = "none";
  HashSet<Integer> exportedFrames = new HashSet<Integer>();
  int exportCount = 0;

  FrameExporter(PApplet app) {
    this.app = app;
    ensureExportDirectory();
  }

  void setMode(String mode) {
    this.mode = normalizeRecordMode(mode);
    exportedFrames.clear();
    exportCount = 0;
    if (!"none".equals(this.mode)) {
      ensureExportDirectory();
      if (!resetFramesDirectoryOnDisk()) {
        String framePath = app.sketchPath("exports/frames");
        println("FrameExporter warning: failed to reset frame directory: " + framePath);
        println("FrameExporter warning: aborting recording startup to avoid mixed frame outputs.");
        throw new RuntimeException("FrameExporter: unable to prepare exports/frames");
      }
    }
  }

  String mode() {
    return mode;
  }

  void cycleMode() {
    if ("none".equals(mode)) {
      setMode("loop");
    } else if ("loop".equals(mode)) {
      setMode("full");
    } else {
      setMode("none");
    }
  }

  void maybeExport(PlaybackState playback, TimelineEngine timeline, TraceModel traceModel) {
    if ("none".equals(mode)) {
      return;
    }

    if (!timeline.playing) {
      return;
    }

    int frame = playback.frameIndex;
    if ("loop".equals(mode)) {
      if (!timeline.loopEnabled) {
        return;
      }
      if (frame < timeline.loopIn || frame > timeline.loopOut) {
        return;
      }
    }

    if (exportedFrames.contains(frame)) {
      return;
    }

    String filename = "exports/frames/frame-" + app.nf(exportCount, 6) + ".png";
    app.saveFrame(filename);
    exportedFrames.add(frame);
    exportCount += 1;
  }

  void ensureExportDirectory() {
    try {
      Path exportPath = Paths.get(app.sketchPath("exports"));
      Path framePath = Paths.get(app.sketchPath("exports/frames"));
      Files.createDirectories(exportPath);
      Files.createDirectories(framePath);
    }
    catch (Exception ignored) {
    }
  }

  boolean resetFramesDirectoryOnDisk() {
    Path framesPath = Paths.get(app.sketchPath("exports/frames"));
    try {
      deleteRecursively(framesPath.toFile());
      Files.createDirectories(framesPath);
    }
    catch (Exception e) {
      println("FrameExporter warning: reset failed for " + framesPath + " (" + e.getMessage() + ")");
      return false;
    }
    if (!verifyFramesDirectoryWritable(framesPath)) {
      println("FrameExporter warning: directory is not writable after reset: " + framesPath);
      return false;
    }
    return true;
  }

  boolean verifyFramesDirectoryWritable(Path framesPath) {
    try {
      if (!Files.exists(framesPath) || !Files.isDirectory(framesPath) || !Files.isWritable(framesPath)) {
        return false;
      }
      Path probePath = framesPath.resolve(".qave_write_probe_" + app.nf((int)(System.nanoTime() & 0x7fffffff), 10));
      Files.write(probePath, new byte[] { 0x51 });
      Files.deleteIfExists(probePath);
      return true;
    }
    catch (Exception ignored) {
      return false;
    }
  }

  void deleteRecursively(java.io.File path) {
    if (path == null || !path.exists()) {
      return;
    }
    if (path.isDirectory()) {
      java.io.File[] children = path.listFiles();
      if (children != null) {
        for (java.io.File child : children) {
          deleteRecursively(child);
        }
      }
    }
    path.delete();
  }
}
