/*
Purpose: Bootstrap the Processing viewer application and orchestrate pane lifecycle.
Inputs: Shared playback state, trace-derived models, pane metrics, and user interaction state.
Outputs: Deterministic frame-local rendering updates and synchronized visual state transitions.
Determinism/Timing: Uses timeline phases (pre_gate/apply_gate/settle) and fixed frame progression for reproducible output.
*/

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Locale;
import java.util.TreeSet;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import processing.core.PApplet;
import peasy.*;

int TARGET_FPS = 60;
int WINDOW_WIDTH = 1920;
int WINDOW_HEIGHT = 1080;

RuntimeConfig config;
RuntimeConfig startupConfig;
TraceLoader loader;
TraceModel traceModel;
TimelineEngine timeline;
MatrixEvolutionPane matrixEvolutionPane;
ControlOverlay controlOverlay;
FrameExporter frameExporter;
PeasyCam cam;
CameraDirector cameraDirector;

String fatalError = "";
float revealProgress = 0.0;
int drawCounter = 0;
boolean hudVisible = false;

void settings() {
  startupConfig = new RuntimeConfig().fromSources(this);
  WINDOW_WIDTH = startupConfig.width;
  WINDOW_HEIGHT = startupConfig.height;
  TARGET_FPS = startupConfig.fps;
  size(WINDOW_WIDTH, WINDOW_HEIGHT, P3D);
  smooth(8);
}

void setup() {
  frameRate(TARGET_FPS);
  surface.setTitle("QAVE Processing Timeline Viewer");
  textFont(createFont("SansSerif", 12, true));

  cam = new PeasyCam(this, width * 0.5, height * 0.62, 0, max(width, height) * 0.74);
  cameraDirector = new CameraDirector(this, cam);
  cameraDirector.configure();

  config = startupConfig != null ? startupConfig : new RuntimeConfig().fromSources(this);
  loader = new TraceLoader(this);
  controlOverlay = new ControlOverlay(this);
  frameExporter = new FrameExporter(this);
  frameExporter.setMode(config.recordMode);

  TraceLoaderResult result = loader.load(config.tracePath);
  if (!result.ok) {
    fatalError = result.errorMessage;
    println("Trace load failed: " + fatalError);
    return;
  }

  initializeRuntime(result.model);
}

void initializeRuntime(TraceModel model) {
  traceModel = model;
  if ("full".equals(config.recordMode) && !config.maxFramesSpecified) {
    config.maxFrames = max(1, traceModel.totalFrames);
    println("Auto --max-frames set to totalFrames=" + config.maxFrames + " for --record full");
  }
  timeline = new TimelineEngine(traceModel);
  timeline.setPlaying(config.autoplay);
  timeline.setSpeed(config.speed);

  matrixEvolutionPane = new MatrixEvolutionPane(this);
  matrixEvolutionPane.setTrace(traceModel);
  if (cameraDirector != null) {
    cameraDirector.resetSmoothing();
  }
}

boolean hasRuntime() {
  return traceModel != null && timeline != null;
}

void draw() {
  drawCounter += 1;
  background(0);

  if (!hasRuntime()) {
    if (cam != null) {
      cam.beginHUD();
    }
    drawFatalPanel(fatalError.length() > 0 ? fatalError : "Trace model unavailable.");
    if (cam != null) {
      cam.endHUD();
    }
    maybeExitOnMaxFrames();
    return;
  }

  revealProgress = min(1.0, revealProgress + 0.018);
  PlaybackState playback = timeline.currentFrameState();

  float margin = 6;
  float reservedBottom = hudVisible ? 136 : 8;
  float innerW = width - margin * 2.0;
  float usableH = max(280, height - margin * 2.0 - reservedBottom);
  PanelRect matrixRect = new PanelRect(margin, margin, innerW, usableH);
  MatrixViewMetrics metrics = matrixEvolutionPane.computeViewMetrics(matrixRect, playback);

  if (cameraDirector != null) {
    cameraDirector.apply(playback, metrics, traceModel);
  }
  matrixEvolutionPane.renderWorld(matrixRect, playback, traceModel, metrics);

  if (cam != null) {
    cam.beginHUD();
  }
  matrixEvolutionPane.renderHud(matrixRect, playback, traceModel, revealProgress);
  if (hudVisible) {
    controlOverlay.render(timeline, traceModel, playback, frameExporter.mode());
  }
  if (cam != null) {
    cam.endHUD();
  }

  frameExporter.maybeExport(playback, timeline, traceModel);
  timeline.advance();
  maybeExitOnMaxFrames();
}

void drawBackgroundGradient() {
  noStroke();
  int steps = 30;
  for (int i = 0; i < steps; i += 1) {
    float t = i / float(max(1, steps - 1));
    int c = lerpColor(THEME.colorBackgroundTop(), THEME.colorBackgroundBottom(), t);
    fill(c);
    float y = t * height;
    rect(0, y, width, height / float(steps) + 2);
  }
}

void drawFatalPanel(String message) {
  fill(THEME.colorPanelFill(230));
  stroke(THEME.colorPanelStroke(220));
  strokeWeight(1.2);
  rect(40, 40, width - 80, height - 80, 12);

  fill(THEME.colorTextPrimary());
  noStroke();
  textAlign(LEFT, TOP);
  textSize(18);
  text("Trace Load Error", 64, 64);

  textSize(13);
  fill(THEME.colorTextSecondary());
  textLeading(20);
  text(message, 64, 96, width - 128, height - 140);

  textSize(12);
  fill(THEME.colorTextMuted());
		  text(
		    "Expected keys: steps, timeline, observable_snapshots, view_sync_groups\\n"
		    + "Optional matrix key: steps[*].evolution_samples[*].gate_matrix\\n"
		    + "Generate traces via Python API (package-first): see docs/tutorials/ghz3_with_QAVE.ipynb.",
		    64,
		    height - 120,
		    width - 128,
		    80
		  );
	}

void maybeExitOnMaxFrames() {
  if (config.maxFrames > 0 && drawCounter >= config.maxFrames) {
    println("Reached --max-frames " + config.maxFrames + ", exiting.");
    exit();
  }
}

void mousePressed() {
  if (!hasRuntime() || !hudVisible) {
    return;
  }
  controlOverlay.handleMousePressed(mouseX, mouseY, timeline, traceModel, frameExporter);
}

void mouseDragged() {
  if (!hasRuntime() || !hudVisible) {
    return;
  }
  controlOverlay.handleMouseDragged(mouseX, timeline, traceModel);
}

void mouseReleased() {
  if (!hudVisible) {
    return;
  }
  controlOverlay.handleMouseReleased();
}

void keyPressed() {
  if (!hasRuntime()) {
    return;
  }
  if (key == 'h' || key == 'H') {
    hudVisible = !hudVisible;
    if (!hudVisible) {
      controlOverlay.handleMouseReleased();
    }
    return;
  }
  controlOverlay.handleKeyPressed(key, keyCode, timeline, traceModel, frameExporter);
}
