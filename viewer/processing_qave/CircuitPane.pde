/*
Purpose: Render the circuit lane and synchronized gate pointer state.
Inputs: Shared playback state, trace-derived models, pane metrics, and user interaction state.
Outputs: Deterministic frame-local rendering updates and synchronized visual state transitions.
Determinism/Timing: Uses timeline phases (pre_gate/apply_gate/settle) and fixed frame progression for reproducible output.
*/

class CircuitPane {
  PApplet app;
  ArrayList<AnimationEntity> entities = new ArrayList<AnimationEntity>();

  CircuitPane(PApplet app) {
    this.app = app;
  }

  void setTrace(TraceModel traceModel) {
    entities.clear();
    for (int i = 0; i < traceModel.stepCount; i += 1) {
      AnimationEntity entity = new AnimationEntity(
        new PVector(i * 10, 0, 0),
        new PVector(20, 20, 4),
        new PVector(0.1, 0.2, 0.3),
        0.23,
        0.8,
        0.5,
        0.28
      );
      entities.add(entity);
    }
  }

  void render(PanelRect panel, PlaybackState playback, TraceModel traceModel, float revealProgress) {
    if (entities.isEmpty()) {
      return;
    }

    stroke(THEME.colorPanelStroke(220));
    strokeWeight(1.2);
    fill(THEME.colorPanelFill(165));
    rect(panel.x, panel.y, panel.w, panel.h, 10);

    float laneY = panel.y + panel.h * 0.58;
    stroke(THEME.colorTextSecondary());
    strokeWeight(2.0);
    line(panel.x + 30, laneY, panel.x + panel.w - 30, laneY);

    int gateCount = entities.size();
    float spacing = gateCount <= 1 ? 0 : (panel.w - 70) / float(gateCount - 1);
    int active = clampInt(playback.stepIndex, 0, gateCount - 1);
    int activePhaseColor = phaseColor(playback.phase);

    for (int i = 0; i < gateCount; i += 1) {
      AnimationEntity entity = entities.get(i);
      float x = panel.x + 35 + i * spacing;
      boolean isActive = i == active;
      float pulse = isActive ? 1.0 + 0.14 * sin(playback.frameIndex * 0.15) : 1.0;

      entity.setTarget(
        new PVector(
          x,
          laneY + (isActive ? -18 : 0),
          isActive ? 14 : 2
        ),
        new PVector(
          18 * pulse,
          isActive ? 28 * pulse : 20,
          isActive ? 12 : 6
        ),
        new PVector(
          isActive ? 1.0 : 0.2,
          isActive ? 0.7 : 0.25,
          isActive ? 0.4 : 0.3
        )
      );
      entity.update();

      pushMatrix();
      translate(entity.curPos.x, entity.curPos.y, entity.curPos.z);
      noStroke();
      if (isActive) {
        fill(activePhaseColor);
      } else {
        fill(THEME.gateIdle[0], THEME.gateIdle[1], THEME.gateIdle[2], 220);
      }
      box(entity.curSize.x, entity.curSize.y, entity.curSize.z);

      if (isActive) {
        stroke(activePhaseColor);
        noFill();
        strokeWeight(1.6);
        box(entity.curSize.x + 3, entity.curSize.y + 3, entity.curSize.z + 3);
      }
      popMatrix();

      hint(DISABLE_DEPTH_TEST);
      fill(isActive ? THEME.colorTextPrimary() : THEME.colorTextSecondary());
      noStroke();
      textAlign(CENTER, CENTER);
      textSize(isActive ? 13 : 11);
      text(traceModel.steps.get(i).gateLabel, x, panel.y + panel.h * 0.18);
      hint(ENABLE_DEPTH_TEST);
    }

    float cursorX = panel.x + 35 + active * spacing;
    stroke(activePhaseColor);
    strokeWeight(2.2);
    line(cursorX, laneY - 32, cursorX, laneY + 34);

    int revealAlpha = round(clampFloat(revealProgress, 0, 1) * 255);
    hint(DISABLE_DEPTH_TEST);
    noStroke();
    fill(THEME.textPrimary[0], THEME.textPrimary[1], THEME.textPrimary[2], revealAlpha);
    textAlign(LEFT, TOP);
    textSize(13);
    text("Circuit Lane · Step " + (active + 1) + "/" + traceModel.stepCount, panel.x + 12, panel.y + 10);

    fill(THEME.textSecondary[0], THEME.textSecondary[1], THEME.textSecondary[2], revealAlpha);
    textAlign(RIGHT, TOP);
    text("Phase: " + playback.phase, panel.x + panel.w - 12, panel.y + 10);
    hint(ENABLE_DEPTH_TEST);
  }
}
