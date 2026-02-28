/*
Purpose: Render amplitude/basis visualizations synchronized to playback frames.
Inputs: Shared playback state, trace-derived models, pane metrics, and user interaction state.
Outputs: Deterministic frame-local rendering updates and synchronized visual state transitions.
Determinism/Timing: Uses timeline phases (pre_gate/apply_gate/settle) and fixed frame progression for reproducible output.
*/

class AmplitudePane {
  PApplet app;
  HashMap<String, AnimationEntity> entities = new HashMap<String, AnimationEntity>();
  ArrayList<String> bases = new ArrayList<String>();

  AmplitudePane(PApplet app) {
    this.app = app;
  }

  void setTrace(TraceModel traceModel) {
    bases.clear();
    entities.clear();

    int limit = min(24, traceModel.allAmplitudeBases.size());
    for (int i = 0; i < limit; i += 1) {
      String basis = traceModel.allAmplitudeBases.get(i);
      bases.add(basis);
      entities.put(
        basis,
        new AnimationEntity(
          new PVector(0, 0, 0),
          new PVector(12, 2, 12),
          new PVector(0.2, 0.2, 0.2),
          0.2,
          0.85,
          0.52,
          0.3
        )
      );
    }
  }

  void render(PanelRect panel, PlaybackState playback, TraceModel traceModel, float revealProgress) {
    if (bases.isEmpty()) {
      return;
    }

    stroke(THEME.colorPanelStroke(220));
    strokeWeight(1.2);
    fill(THEME.colorPanelFill(160));
    rect(panel.x, panel.y, panel.w, panel.h, 10);

    float worldBottom = panel.y + panel.h;
    float barAreaHeight = panel.h * 0.66;
    float baselineY = worldBottom - 28;
    float spacing = bases.size() <= 1 ? 0 : (panel.w - 56) / float(bases.size() - 1);

    for (int i = 0; i < bases.size(); i += 1) {
      String basis = bases.get(i);
      AnimationEntity entity = entities.get(basis);
      AmplitudeSample sample = playback.sample.amplitudes.get(basis);

      float magnitude = sample != null ? sample.magnitude : 0;
      float phase = sample != null ? sample.phase : 0;
      float emphasis = sample != null ? 1 : 0;

      float x = panel.x + 28 + i * spacing;
      float heightValue = 4 + barAreaHeight * magnitude;

      entity.setTarget(
        new PVector(x, baselineY - heightValue / 2, emphasis > 0 ? 18 : 8),
        new PVector(10, heightValue, 10),
        new PVector(magnitude, (phase + PI) / TWO_PI, emphasis)
      );
      entity.update();

      pushMatrix();
      translate(entity.curPos.x, entity.curPos.y, entity.curPos.z);
      noStroke();
      int fillColor = amplitudeColor(phase, emphasis * 0.7);
      fill(fillColor);
      box(entity.curSize.x, entity.curSize.y, entity.curSize.z);

      if (emphasis > 0) {
        noFill();
        stroke(fillColor);
        strokeWeight(1.5);
        box(entity.curSize.x + 2.5, entity.curSize.y + 2.5, entity.curSize.z + 2.5);
      }
      popMatrix();

      int stride = max(1, floor(bases.size() / 8.0));
      if (i % stride == 0) {
        hint(DISABLE_DEPTH_TEST);
        noStroke();
        fill(THEME.colorTextSecondary());
        textAlign(CENTER, TOP);
        textSize(9);
        text(basis, x, baselineY + 8);
        hint(ENABLE_DEPTH_TEST);
      }
    }

    int revealAlpha = round(clampFloat(revealProgress, 0, 1) * 255);
    hint(DISABLE_DEPTH_TEST);
    noStroke();
    fill(THEME.textPrimary[0], THEME.textPrimary[1], THEME.textPrimary[2], revealAlpha);
    textAlign(LEFT, TOP);
    textSize(13);
    text("Amplitude Pane · Top-K", panel.x + 12, panel.y + 10);

    fill(THEME.textSecondary[0], THEME.textSecondary[1], THEME.textSecondary[2], revealAlpha);
    textAlign(RIGHT, TOP);
    text("Tracked bases: " + bases.size(), panel.x + panel.w - 12, panel.y + 10);
    hint(ENABLE_DEPTH_TEST);
  }
}
