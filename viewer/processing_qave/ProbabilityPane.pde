/*
Purpose: Render probability bars and measurement distributions per frame.
Inputs: Shared playback state, trace-derived models, pane metrics, and user interaction state.
Outputs: Deterministic frame-local rendering updates and synchronized visual state transitions.
Determinism/Timing: Uses timeline phases (pre_gate/apply_gate/settle) and fixed frame progression for reproducible output.
*/

class ProbabilityPane {
  PApplet app;
  HashMap<String, AnimationEntity> entities = new HashMap<String, AnimationEntity>();
  ArrayList<String> bases = new ArrayList<String>();

  ProbabilityPane(PApplet app) {
    this.app = app;
  }

  void setTrace(TraceModel traceModel) {
    bases.clear();
    entities.clear();

    int limit = min(24, traceModel.allProbabilityBases.size());
    for (int i = 0; i < limit; i += 1) {
      String basis = traceModel.allProbabilityBases.get(i);
      bases.add(basis);
      entities.put(
        basis,
        new AnimationEntity(
          new PVector(0, 0, 0),
          new PVector(10, 2, 10),
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

    HashSet<String> amplitudeHighlights = new HashSet<String>(playback.sample.amplitudes.keySet());

    float worldBottom = panel.y + panel.h;
    float barAreaHeight = panel.h * 0.66;
    float baselineY = worldBottom - 24;
    float spacing = bases.size() <= 1 ? 0 : (panel.w - 56) / float(bases.size() - 1);

    for (int i = 0; i < bases.size(); i += 1) {
      String basis = bases.get(i);
      AnimationEntity entity = entities.get(basis);

      ProbabilitySample sample = playback.sample.probabilities.get(basis);
      float probability = sample != null ? sample.probability : 0;
      boolean highlight = amplitudeHighlights.contains(basis);

      float x = panel.x + 28 + i * spacing;
      float heightValue = 4 + barAreaHeight * probability;

      entity.setTarget(
        new PVector(x, baselineY - heightValue / 2, highlight ? 14 : 6),
        new PVector(9, heightValue, 9),
        new PVector(probability, highlight ? 1 : 0, 0.3)
      );
      entity.update();

      pushMatrix();
      translate(entity.curPos.x, entity.curPos.y, entity.curPos.z);
      noStroke();
      int fillColor = highlight
        ? color(THEME.amber[0], THEME.amber[1], THEME.amber[2], 240)
        : color(THEME.cyan[0], THEME.cyan[1], THEME.cyan[2], 205);
      fill(fillColor);
      box(entity.curSize.x, entity.curSize.y, entity.curSize.z);

      if (highlight) {
        noFill();
        stroke(fillColor);
        strokeWeight(1.4);
        box(entity.curSize.x + 2, entity.curSize.y + 2, entity.curSize.z + 2);
      }
      popMatrix();

      int stride = max(1, floor(bases.size() / 8.0));
      if (i % stride == 0) {
        hint(DISABLE_DEPTH_TEST);
        noStroke();
        fill(THEME.colorTextSecondary());
        textAlign(CENTER, TOP);
        textSize(9);
        text(basis, x, baselineY + 6);
        hint(ENABLE_DEPTH_TEST);
      }
    }

    int revealAlpha = round(clampFloat(revealProgress, 0, 1) * 255);
    hint(DISABLE_DEPTH_TEST);
    noStroke();
    fill(THEME.textPrimary[0], THEME.textPrimary[1], THEME.textPrimary[2], revealAlpha);
    textAlign(LEFT, TOP);
    textSize(13);
    text("Probability Pane", panel.x + 12, panel.y + 10);

    fill(THEME.textSecondary[0], THEME.textSecondary[1], THEME.textSecondary[2], revealAlpha);
    textAlign(RIGHT, TOP);
    text("Phase-linked highlights: " + amplitudeHighlights.size(), panel.x + panel.w - 12, panel.y + 10);
    hint(ENABLE_DEPTH_TEST);
  }
}
