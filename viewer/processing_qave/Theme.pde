/*
Purpose: Define viewer color, typography, and layout constants.
Inputs: Shared playback state, trace-derived models, pane metrics, and user interaction state.
Outputs: Deterministic frame-local rendering updates and synchronized visual state transitions.
Determinism/Timing: Uses timeline phases (pre_gate/apply_gate/settle) and fixed frame progression for reproducible output.
*/

class Theme {
  int[] backgroundTop = new int[] { 8, 14, 23 };
  int[] backgroundBottom = new int[] { 4, 7, 14 };

  int[] panelFill = new int[] { 13, 20, 33 };
  int[] panelStroke = new int[] { 49, 68, 96 };

  int[] textPrimary = new int[] { 230, 236, 246 };
  int[] textSecondary = new int[] { 160, 178, 203 };
  int[] textMuted = new int[] { 118, 134, 156 };

  int[] cyan = new int[] { 69, 211, 255 };
  int[] cyanSoft = new int[] { 97, 188, 255 };
  int[] amber = new int[] { 255, 185, 72 };
  int[] gateIdle = new int[] { 46, 62, 86 };

  int colorBackgroundTop() {
    return color(backgroundTop[0], backgroundTop[1], backgroundTop[2]);
  }

  int colorBackgroundBottom() {
    return color(backgroundBottom[0], backgroundBottom[1], backgroundBottom[2]);
  }

  int colorPanelFill(int alpha) {
    return color(panelFill[0], panelFill[1], panelFill[2], alpha);
  }

  int colorPanelStroke(int alpha) {
    return color(panelStroke[0], panelStroke[1], panelStroke[2], alpha);
  }

  int colorTextPrimary() {
    return color(textPrimary[0], textPrimary[1], textPrimary[2]);
  }

  int colorTextSecondary() {
    return color(textSecondary[0], textSecondary[1], textSecondary[2]);
  }

  int colorTextMuted() {
    return color(textMuted[0], textMuted[1], textMuted[2]);
  }
}

Theme THEME = new Theme();

int phaseColor(String phase) {
  if ("pre_gate".equals(phase)) {
    return color(105, 168, 255);
  }
  if ("apply_gate".equals(phase)) {
    return color(72, 224, 252);
  }
  if ("settle".equals(phase)) {
    return color(255, 194, 94);
  }
  if ("measurement_reveal".equals(phase)) {
    return color(182, 196, 216);
  }
  if ("shot_camera_pullback".equals(phase)) {
    return color(128, 194, 255);
  }
  if ("shot_histogram_project".equals(phase)) {
    return color(124, 232, 214);
  }
  if ("shot_stack".equals(phase)) {
    return color(255, 182, 92);
  }
  return color(182, 196, 216);
}

int amplitudeColor(float phase, float emphasis) {
  float normalized = (phase + PI) / TWO_PI;
  normalized = clampFloat(normalized, 0, 1);

  int c0 = color(75, 215, 255);
  int c1 = color(130, 115, 255);
  int c2 = color(255, 177, 92);

  int blend = normalized < 0.5
    ? lerpColor(c0, c1, normalized * 2.0)
    : lerpColor(c1, c2, (normalized - 0.5) * 2.0);

  float boost = clampFloat(emphasis, 0, 1) * 0.22;
  int boosted = lerpColor(blend, color(255, 255, 255), boost);
  return boosted;
}
