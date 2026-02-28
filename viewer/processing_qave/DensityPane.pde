/*
Purpose: Render density-matrix layers and phase-aligned scene cues.
Inputs: Shared playback state, trace-derived models, pane metrics, and user interaction state.
Outputs: Deterministic frame-local rendering updates and synchronized visual state transitions.
Determinism/Timing: Uses timeline phases (pre_gate/apply_gate/settle) and fixed frame progression for reproducible output.
*/

class DensityPane {
  PApplet app;

  DensityPane(PApplet app) {
    this.app = app;
  }

  void setTrace(TraceModel traceModel) {
  }

  void render(PanelRect panel, PlaybackState playback, TraceModel traceModel, float revealProgress) {
    stroke(THEME.colorPanelStroke(220));
    strokeWeight(1.2);
    fill(THEME.colorPanelFill(160));
    rect(panel.x, panel.y, panel.w, panel.h, 10);

    ReducedDensitySample block = selectPreferredBlock(playback.sample);
    if (block == null || block.real == null || block.real.length == 0) {
      hint(DISABLE_DEPTH_TEST);
      noStroke();
      fill(THEME.colorTextSecondary());
      textAlign(CENTER, CENTER);
      textSize(12);
      text("No reduced density block in current sample", panel.x + panel.w / 2, panel.y + panel.h / 2);
      hint(ENABLE_DEPTH_TEST);
      drawHeader(panel, playback, revealProgress, "(none)");
      return;
    }

    int dim = block.real.length;
    float availableW = panel.w - 72;
    float availableH = panel.h - 64;
    float cell = min(availableW / max(1, dim), availableH / max(1, dim));
    float matrixW = cell * dim;
    float matrixH = cell * dim;
    float startX = panel.x + (panel.w - matrixW) * 0.5;
    float startY = panel.y + 36 + (availableH - matrixH) * 0.5;

    hint(DISABLE_DEPTH_TEST);
    noStroke();

    for (int row = 0; row < dim; row += 1) {
      for (int col = 0; col < dim; col += 1) {
        float realValue = block.real[row][col];
        float imagValue = block.imag[row][col];
        fill(densityColor(realValue));
        rect(startX + col * cell, startY + row * cell, cell, cell);

        float edgeAlpha = clampFloat(abs(imagValue), 0.0, 1.0) * 180.0;
        if (edgeAlpha > 6.0) {
          noFill();
          stroke(THEME.cyan[0], THEME.cyan[1], THEME.cyan[2], edgeAlpha);
          strokeWeight(1.1);
          rect(startX + col * cell, startY + row * cell, cell, cell);
          noStroke();
        }

        if (dim <= 4) {
          fill(THEME.colorTextPrimary());
          textAlign(CENTER, CENTER);
          textSize(10);
          text(nfc(realValue, 2), startX + col * cell + cell / 2, startY + row * cell + cell / 2);
        }
      }
    }

    stroke(THEME.colorPanelStroke(230));
    noFill();
    strokeWeight(1.0);
    rect(startX, startY, matrixW, matrixH);

    noStroke();
    fill(THEME.colorTextMuted());
    textAlign(LEFT, CENTER);
    textSize(10);
    text("Im parts shown as cyan edge intensity", panel.x + 12, panel.y + panel.h - 14);

    drawHeader(panel, playback, revealProgress, qubitLabel(block.qubits));
    hint(ENABLE_DEPTH_TEST);
  }

  void drawHeader(PanelRect panel, PlaybackState playback, float revealProgress, String qubitLabel) {
    int revealAlpha = round(clampFloat(revealProgress, 0, 1) * 255);
    noStroke();
    fill(THEME.textPrimary[0], THEME.textPrimary[1], THEME.textPrimary[2], revealAlpha);
    textAlign(LEFT, TOP);
    textSize(13);
    text("Density Pane", panel.x + 12, panel.y + 10);

    fill(THEME.textSecondary[0], THEME.textSecondary[1], THEME.textSecondary[2], revealAlpha);
    textAlign(RIGHT, TOP);
    text("Block: " + qubitLabel + " · phase " + playback.phase, panel.x + panel.w - 12, panel.y + 10);
  }

  String qubitLabel(int[] qubits) {
    if (qubits == null || qubits.length == 0) {
      return "none";
    }

    StringBuilder builder = new StringBuilder();
    builder.append("[");
    for (int i = 0; i < qubits.length; i += 1) {
      if (i > 0) {
        builder.append(",");
      }
      builder.append(qubits[i]);
    }
    builder.append("]");
    return builder.toString();
  }

  ReducedDensitySample selectPreferredBlock(FrameSample sample) {
    if (sample == null || sample.reducedDensityBlocks == null || sample.reducedDensityBlocks.isEmpty()) {
      return null;
    }

    ReducedDensitySample largestBlock = null;
    int largestSpan = -1;
    for (ReducedDensitySample block : sample.reducedDensityBlocks) {
      if (block == null || !isRectangular(block.real, block.imag)) {
        continue;
      }
      int span = block != null && block.qubits != null ? block.qubits.length : 0;
      if (span > largestSpan) {
        largestSpan = span;
        largestBlock = block;
      }
    }
    if (largestBlock != null) {
      return largestBlock;
    }

    for (ReducedDensitySample block : sample.reducedDensityBlocks) {
      if (block != null && "0,1".equals(block.qubitKey)) {
        return block;
      }
    }

    for (ReducedDensitySample block : sample.reducedDensityBlocks) {
      if (block != null && "0".equals(block.qubitKey)) {
        return block;
      }
    }

    return sample.reducedDensityBlocks.get(0);
  }

  int densityColor(float value) {
    float clamped = clampFloat(value, -1.0, 1.0);
    float t = (clamped + 1.0) * 0.5;

    int neg = color(THEME.amber[0], THEME.amber[1], THEME.amber[2], 210);
    int zero = color(36, 52, 78, 220);
    int pos = color(THEME.cyan[0], THEME.cyan[1], THEME.cyan[2], 220);

    if (t < 0.5) {
      return lerpColor(neg, zero, t * 2.0);
    }
    return lerpColor(zero, pos, (t - 0.5) * 2.0);
  }

  boolean isRectangular(float[][] real, float[][] imag) {
    if (real == null || imag == null || real.length == 0 || imag.length == 0 || real.length != imag.length) {
      return false;
    }
    int cols = real[0].length;
    if (cols <= 0) {
      return false;
    }
    for (int row = 0; row < real.length; row += 1) {
      if (real[row].length != cols || imag[row].length != cols) {
        return false;
      }
    }
    return true;
  }
}
