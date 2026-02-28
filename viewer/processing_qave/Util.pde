/*
Purpose: Provide shared utility helpers used across viewer panes and systems.
Inputs: Shared playback state, trace-derived models, pane metrics, and user interaction state.
Outputs: Deterministic frame-local rendering updates and synchronized visual state transitions.
Determinism/Timing: Uses timeline phases (pre_gate/apply_gate/settle) and fixed frame progression for reproducible output.
*/

class PanelRect {
  float x;
  float y;
  float w;
  float h;

  PanelRect(float x, float y, float w, float h) {
    this.x = x;
    this.y = y;
    this.w = w;
    this.h = h;
  }
}

// Class RuntimeConfig encapsulates module-specific viewer behavior.
class RuntimeConfig {
  String tracePath = "data/trace.json";
  boolean autoplay = true;
  float speed = 1.0;
  int maxFrames = 0;
  boolean maxFramesSpecified = false;
  String recordMode = "none";
  int width = 1920;
  int height = 1080;
  int fps = 60;

  RuntimeConfig fromSources(PApplet app) {
    RuntimeConfig config = new RuntimeConfig();
    ArrayList<String> cliArgs = collectCliArgs(app);
    config.applyTokens(cliArgs);
    config.applyFallbacks();
    config.speed = normalizeSpeed(config.speed);
    config.recordMode = normalizeRecordMode(config.recordMode);
    if (config.maxFrames < 0) {
      config.maxFrames = 0;
    }
    return config;
  }

  ArrayList<String> collectCliArgs(PApplet app) {
    ArrayList<String> values = new ArrayList<String>();

    for (String fieldName : new String[] { "args", "passedArgs" }) {
      try {
        java.lang.reflect.Field field = PApplet.class.getDeclaredField(fieldName);
        field.setAccessible(true);
        Object raw = field.get(app);
        if (raw instanceof String[]) {
          String[] arr = (String[])raw;
          for (String item : arr) {
            if (item != null && item.length() > 0) {
              values.add(item.trim());
            }
          }
        }
      }
      catch (Exception ignored) {
      }
    }

    if (!values.isEmpty()) {
      return values;
    }

    String envArgs = System.getenv("QAVE_ARGS");
    if (envArgs != null && envArgs.trim().length() > 0) {
      String[] tokens = PApplet.splitTokens(envArgs, " ");
      for (String token : tokens) {
        if (token != null && token.length() > 0) {
          values.add(token.trim());
        }
      }
    }

    return values;
  }

  void applyTokens(ArrayList<String> tokens) {
    for (int i = 0; i < tokens.size(); i += 1) {
      String token = tokens.get(i);

      if (token.equals("--trace") && i + 1 < tokens.size()) {
        tracePath = tokens.get(i + 1);
        i += 1;
      } else if (token.startsWith("--trace=")) {
        tracePath = token.substring("--trace=".length());
      } else if (token.equals("--autoplay") && i + 1 < tokens.size()) {
        autoplay = parseBoolArg(tokens.get(i + 1), autoplay);
        i += 1;
      } else if (token.startsWith("--autoplay=")) {
        autoplay = parseBoolArg(token.substring("--autoplay=".length()), autoplay);
      } else if (token.equals("--speed") && i + 1 < tokens.size()) {
        speed = parseFloatArg(tokens.get(i + 1), speed);
        i += 1;
      } else if (token.startsWith("--speed=")) {
        speed = parseFloatArg(token.substring("--speed=".length()), speed);
      } else if (token.equals("--max-frames") && i + 1 < tokens.size()) {
        maxFrames = parseIntArg(tokens.get(i + 1), maxFrames);
        maxFramesSpecified = true;
        i += 1;
      } else if (token.startsWith("--max-frames=")) {
        maxFrames = parseIntArg(token.substring("--max-frames=".length()), maxFrames);
        maxFramesSpecified = true;
      } else if (token.equals("--record") && i + 1 < tokens.size()) {
        recordMode = tokens.get(i + 1);
        i += 1;
      } else if (token.startsWith("--record=")) {
        recordMode = token.substring("--record=".length());
      } else if (token.equals("--width") && i + 1 < tokens.size()) {
        width = parseIntArg(tokens.get(i + 1), width);
        i += 1;
      } else if (token.startsWith("--width=")) {
        width = parseIntArg(token.substring("--width=".length()), width);
      } else if (token.equals("--height") && i + 1 < tokens.size()) {
        height = parseIntArg(tokens.get(i + 1), height);
        i += 1;
      } else if (token.startsWith("--height=")) {
        height = parseIntArg(token.substring("--height=".length()), height);
      } else if (token.equals("--fps") && i + 1 < tokens.size()) {
        fps = parseIntArg(tokens.get(i + 1), fps);
        i += 1;
      } else if (token.startsWith("--fps=")) {
        fps = parseIntArg(token.substring("--fps=".length()), fps);
      }
    }
  }

  void applyFallbacks() {
    if (tracePath == null || tracePath.trim().length() == 0) {
      tracePath = fallbackString(System.getProperty("qave.trace"), System.getenv("QAVE_TRACE"), tracePath);
    }

    autoplay = fallbackBoolean(System.getProperty("qave.autoplay"), System.getenv("QAVE_AUTOPLAY"), autoplay);

    String speedValue = fallbackString(System.getProperty("qave.speed"), System.getenv("QAVE_SPEED"), null);
    if (speedValue != null) {
      speed = parseFloatArg(speedValue, speed);
    }

    String maxFramesValue = fallbackString(System.getProperty("qave.max_frames"), System.getenv("QAVE_MAX_FRAMES"), null);
    if (maxFramesValue != null) {
      maxFrames = parseIntArg(maxFramesValue, maxFrames);
      maxFramesSpecified = true;
    }

    String recordValue = fallbackString(System.getProperty("qave.record"), System.getenv("QAVE_RECORD"), null);
    if (recordValue != null) {
      recordMode = recordValue;
    }

    String widthValue = fallbackString(System.getProperty("qave.width"), System.getenv("QAVE_WIDTH"), null);
    if (widthValue != null) {
      width = parseIntArg(widthValue, width);
    }
    String heightValue = fallbackString(System.getProperty("qave.height"), System.getenv("QAVE_HEIGHT"), null);
    if (heightValue != null) {
      height = parseIntArg(heightValue, height);
    }
    String fpsValue = fallbackString(System.getProperty("qave.fps"), System.getenv("QAVE_FPS"), null);
    if (fpsValue != null) {
      fps = parseIntArg(fpsValue, fps);
    }

    width = max(320, width);
    height = max(240, height);
    fps = max(1, fps);
  }
}

String fallbackString(String first, String second, String defaultValue) {
  if (first != null && first.trim().length() > 0) {
    return first.trim();
  }
  if (second != null && second.trim().length() > 0) {
    return second.trim();
  }
  return defaultValue;
}

boolean fallbackBoolean(String first, String second, boolean defaultValue) {
  if (first != null && first.trim().length() > 0) {
    return parseBoolArg(first, defaultValue);
  }
  if (second != null && second.trim().length() > 0) {
    return parseBoolArg(second, defaultValue);
  }
  return defaultValue;
}

float normalizeSpeed(float value) {
  float[] supported = new float[] { 0.25, 0.5, 1.0, 2.0 };
  float selected = supported[0];
  float bestDistance = abs(value - selected);
  for (int i = 1; i < supported.length; i += 1) {
    float candidate = supported[i];
    float distance = abs(value - candidate);
    if (distance < bestDistance) {
      bestDistance = distance;
      selected = candidate;
    }
  }
  return selected;
}

String normalizeRecordMode(String mode) {
  if (mode == null) {
    return "none";
  }
  String normalized = mode.toLowerCase(Locale.US).trim();
  if (normalized.equals("none") || normalized.equals("loop") || normalized.equals("full")) {
    return normalized;
  }
  return "none";
}

boolean parseBoolArg(String value, boolean fallback) {
  if (value == null) {
    return fallback;
  }
  String normalized = value.trim().toLowerCase(Locale.US);
  if (normalized.equals("true") || normalized.equals("1") || normalized.equals("yes") || normalized.equals("on")) {
    return true;
  }
  if (normalized.equals("false") || normalized.equals("0") || normalized.equals("no") || normalized.equals("off")) {
    return false;
  }
  return fallback;
}

float parseFloatArg(String value, float fallback) {
  if (value == null || value.trim().length() == 0) {
    return fallback;
  }
  try {
    return Float.parseFloat(value.trim());
  }
  catch (Exception ignored) {
    return fallback;
  }
}

int parseIntArg(String value, int fallback) {
  if (value == null || value.trim().length() == 0) {
    return fallback;
  }
  try {
    return Integer.parseInt(value.trim());
  }
  catch (Exception ignored) {
    return fallback;
  }
}

float clampFloat(float value, float minValue, float maxValue) {
  return max(minValue, min(maxValue, value));
}

int clampInt(int value, int minValue, int maxValue) {
  return max(minValue, min(maxValue, value));
}

String parseGateLabel(String operationId) {
  if (operationId == null || operationId.length() == 0) {
    return "GATE";
  }
  String[] parts = operationId.split("_");
  if (parts.length == 0) {
    return operationId.toUpperCase(Locale.US);
  }
  return parts[parts.length - 1].toUpperCase(Locale.US);
}

String formatSpeed(float speed) {
  return nf(speed, 0, speed < 1.0 ? 2 : 1) + "x";
}
