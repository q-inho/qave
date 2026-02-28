/*
Purpose: Render playback controls and interaction affordances.
Inputs: Shared playback state, trace-derived models, pane metrics, and user interaction state.
Outputs: Deterministic frame-local rendering updates and synchronized visual state transitions.
Determinism/Timing: Uses timeline phases (pre_gate/apply_gate/settle) and fixed frame progression for reproducible output.
*/

class RectButton {
  String id;
  String label;
  float x;
  float y;
  float w;
  float h;

  RectButton(String id, String label, float x, float y, float w, float h) {
    this.id = id;
    this.label = label;
    this.x = x;
    this.y = y;
    this.w = w;
    this.h = h;
  }

  boolean contains(float px, float py) {
    return px >= x && px <= x + w && py >= y && py <= y + h;
  }
}

// Class ControlOverlay encapsulates module-specific viewer behavior.
class ControlOverlay {
  PApplet app;
  ArrayList<RectButton> buttons = new ArrayList<RectButton>();

  float panelX;
  float panelY;
  float panelW;
  float panelH;

  float sliderX;
  float sliderY;
  float sliderW;
  float sliderH;

  boolean draggingScrub = false;

  float[] speedOptions = new float[] { 0.25, 0.5, 1.0, 2.0 };

  ControlOverlay(PApplet app) {
    this.app = app;
  }

  void updateLayout() {
    panelX = 16;
    panelW = width - 32;
    panelH = 118;
    panelY = height - panelH - 12;

    buttons.clear();
    float bx = panelX + 14;
    float by = panelY + 14;
    float bw = 88;
    float bh = 28;
    float gap = 8;

    buttons.add(new RectButton("play", "Play/Pause", bx, by, bw, bh));
    bx += bw + gap;
    buttons.add(new RectButton("step_back", "Step -1", bx, by, bw, bh));
    bx += bw + gap;
    buttons.add(new RectButton("step_forward", "Step +1", bx, by, bw, bh));
    bx += bw + gap;
    buttons.add(new RectButton("speed", "Speed", bx, by, bw, bh));
    bx += bw + gap;
    buttons.add(new RectButton("loop", "Loop", bx, by, bw, bh));
    bx += bw + gap;
    buttons.add(new RectButton("loop_in", "Set In", bx, by, bw, bh));
    bx += bw + gap;
    buttons.add(new RectButton("loop_out", "Set Out", bx, by, bw, bh));

    sliderX = panelX + 16;
    sliderY = panelY + 58;
    sliderW = panelW - 32;
    sliderH = 12;
  }

  void render(TimelineEngine timeline, TraceModel traceModel, PlaybackState playback, String recordMode) {
    updateLayout();

    noStroke();
    fill(THEME.colorPanelFill(210));
    rect(panelX, panelY, panelW, panelH, 12);
    stroke(THEME.colorPanelStroke(230));
    noFill();
    strokeWeight(1.1);
    rect(panelX, panelY, panelW, panelH, 12);

    for (RectButton button : buttons) {
      drawButton(button, timeline);
    }

    drawSlider(playback.frameIndex, max(1, traceModel.totalFrames - 1));

    fill(THEME.colorTextSecondary());
    noStroke();
    textAlign(LEFT, TOP);
    textSize(11);
    String status = "Step " + (playback.stepIndex + 1)
      + "/" + traceModel.stepCount
      + " · " + playback.phase
      + " · frame " + (playback.frameIndex + 1)
      + "/" + traceModel.totalFrames;
    text(status, panelX + 16, sliderY + 20);

    textAlign(RIGHT, TOP);
    String loopLabel = timeline.loopEnabled
      ? "Loop: " + timeline.loopIn + " - " + timeline.loopOut
      : "Loop: off";
    String runtimeLabel = "speed " + formatSpeed(timeline.speed) + " · record " + recordMode;
    text(loopLabel + " · " + runtimeLabel, panelX + panelW - 16, sliderY + 20);

    drawShortcutHint();
  }

  void drawButton(RectButton button, TimelineEngine timeline) {
    boolean active = false;
    String label = button.label;

    if ("play".equals(button.id)) {
      active = timeline.playing;
      label = timeline.playing ? "Pause" : "Play";
    } else if ("speed".equals(button.id)) {
      label = "Speed " + formatSpeed(timeline.speed);
    } else if ("loop".equals(button.id)) {
      active = timeline.loopEnabled;
      label = timeline.loopEnabled ? "Loop On" : "Loop Off";
    }

    int fillColor = active ? color(THEME.cyanSoft[0], THEME.cyanSoft[1], THEME.cyanSoft[2], 80) : color(24, 34, 52, 210);
    int strokeColor = active ? color(THEME.cyan[0], THEME.cyan[1], THEME.cyan[2], 220) : THEME.colorPanelStroke(220);

    fill(fillColor);
    stroke(strokeColor);
    strokeWeight(1.0);
    rect(button.x, button.y, button.w, button.h, 8);

    noStroke();
    fill(THEME.colorTextPrimary());
    textAlign(CENTER, CENTER);
    textSize(11);
    text(label, button.x + button.w / 2, button.y + button.h / 2 + 0.5);
  }

  void drawSlider(int frameIndex, int maxFrameIndex) {
    noStroke();
    fill(28, 40, 61, 190);
    rect(sliderX, sliderY, sliderW, sliderH, 6);

    float t = maxFrameIndex <= 0 ? 0 : clampFloat(frameIndex / float(maxFrameIndex), 0, 1);
    fill(THEME.cyanSoft[0], THEME.cyanSoft[1], THEME.cyanSoft[2], 215);
    rect(sliderX, sliderY, sliderW * t, sliderH, 6);

    float knobX = sliderX + sliderW * t;
    noStroke();
    fill(THEME.colorTextPrimary());
    ellipse(knobX, sliderY + sliderH / 2, 13, 13);
  }

  void drawShortcutHint() {
    fill(THEME.colorTextMuted());
    noStroke();
    textAlign(LEFT, TOP);
    textSize(10);
    text(
      "Shortcuts: H toggle controls · Space play/pause · Left/Right step · 1/2/3/4 speed · L loop · [ set in · ] set out · E record mode",
      panelX + 16,
      panelY + panelH - 18
    );
  }

  void handleMousePressed(int mouseX, int mouseY, TimelineEngine timeline, TraceModel traceModel, FrameExporter exporter) {
    updateLayout();

    for (RectButton button : buttons) {
      if (!button.contains(mouseX, mouseY)) {
        continue;
      }
      executeButtonAction(button.id, timeline, traceModel, exporter);
      return;
    }

    if (isOverSlider(mouseX, mouseY)) {
      draggingScrub = true;
      updateScrub(mouseX, timeline, traceModel);
    }
  }

  void handleMouseDragged(int mouseX, TimelineEngine timeline, TraceModel traceModel) {
    if (!draggingScrub) {
      return;
    }
    updateScrub(mouseX, timeline, traceModel);
  }

  void handleMouseReleased() {
    draggingScrub = false;
  }

  boolean isOverSlider(float mx, float my) {
    return mx >= sliderX - 8 && mx <= sliderX + sliderW + 8 && my >= sliderY - 8 && my <= sliderY + sliderH + 8;
  }

  void updateScrub(float mouseX, TimelineEngine timeline, TraceModel traceModel) {
    float t = clampFloat((mouseX - sliderX) / max(1, sliderW), 0, 1);
    int targetFrame = round(t * max(0, traceModel.totalFrames - 1));
    timeline.jumpToFrame(targetFrame);
    timeline.setPlaying(false);
  }

  void executeButtonAction(String id, TimelineEngine timeline, TraceModel traceModel, FrameExporter exporter) {
    if ("play".equals(id)) {
      timeline.togglePlaying();
    } else if ("step_back".equals(id)) {
      timeline.stepBackward();
      timeline.setPlaying(false);
    } else if ("step_forward".equals(id)) {
      timeline.stepForward();
      timeline.setPlaying(false);
    } else if ("speed".equals(id)) {
      timeline.setSpeed(nextSpeed(timeline.speed));
    } else if ("loop".equals(id)) {
      timeline.setLoopEnabled(!timeline.loopEnabled);
    } else if ("loop_in".equals(id)) {
      timeline.setLoopIn(timeline.frameIndex);
    } else if ("loop_out".equals(id)) {
      timeline.setLoopOut(timeline.frameIndex);
    }
  }

  float nextSpeed(float currentSpeed) {
    int currentIndex = 0;
    for (int i = 0; i < speedOptions.length; i += 1) {
      if (abs(speedOptions[i] - currentSpeed) < 1e-6) {
        currentIndex = i;
        break;
      }
    }
    return speedOptions[(currentIndex + 1) % speedOptions.length];
  }

  void handleKeyPressed(char keyValue, int keyCodeValue, TimelineEngine timeline, TraceModel traceModel, FrameExporter exporter) {
    if (keyValue == ' ') {
      timeline.togglePlaying();
      return;
    }

    if (keyCodeValue == LEFT) {
      timeline.stepBackward();
      timeline.setPlaying(false);
      return;
    }

    if (keyCodeValue == RIGHT) {
      timeline.stepForward();
      timeline.setPlaying(false);
      return;
    }

    if (keyValue == '1') {
      timeline.setSpeed(0.25);
      return;
    }
    if (keyValue == '2') {
      timeline.setSpeed(0.5);
      return;
    }
    if (keyValue == '3') {
      timeline.setSpeed(1.0);
      return;
    }
    if (keyValue == '4') {
      timeline.setSpeed(2.0);
      return;
    }

    if (keyValue == 'l' || keyValue == 'L') {
      timeline.setLoopEnabled(!timeline.loopEnabled);
      return;
    }

    if (keyValue == '[') {
      timeline.setLoopIn(timeline.frameIndex);
      return;
    }

    if (keyValue == ']') {
      timeline.setLoopOut(timeline.frameIndex);
      return;
    }

    if (keyValue == 'e' || keyValue == 'E') {
      exporter.cycleMode();
      return;
    }
  }
}
