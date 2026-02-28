/*
Purpose: Load and validate trace JSON assets for deterministic playback.
Inputs: Shared playback state, trace-derived models, pane metrics, and user interaction state.
Outputs: Deterministic frame-local rendering updates and synchronized visual state transitions.
Determinism/Timing: Uses timeline phases (pre_gate/apply_gate/settle) and fixed frame progression for reproducible output.
*/

class TraceLoaderResult {
  boolean ok;
  TraceModel model;
  String errorMessage;

  TraceLoaderResult(boolean ok, TraceModel model, String errorMessage) {
    this.ok = ok;
    this.model = model;
    this.errorMessage = errorMessage;
  }
}

// Class TraceLoader encapsulates module-specific viewer behavior.
class TraceLoader {
  final String[] requiredKeys = new String[] { "steps", "timeline", "observable_snapshots", "view_sync_groups" };
  PApplet app;

  TraceLoader(PApplet app) {
    this.app = app;
  }

  TraceLoaderResult load(String tracePath) {
    Path resolvedPath = resolveTracePath(tracePath);
    if (resolvedPath == null) {
      return new TraceLoaderResult(false, null, "Unable to find trace file: " + tracePath);
    }

    JSONObject raw = loadJson(resolvedPath);
    if (raw == null) {
      return new TraceLoaderResult(false, null, "Invalid JSON at: " + resolvedPath.toString());
    }

    ArrayList<String> missing = missingKeys(raw);
    if (!missing.isEmpty()) {
      return new TraceLoaderResult(
        false,
        null,
        "Trace is missing required keys: " + join(missing.toArray(new String[0]), ", ")
      );
    }

    JSONArray stepsArray = arrayOrNull(raw, "steps");
    JSONArray snapshotsArray = arrayOrNull(raw, "observable_snapshots");
    if (stepsArray == null || stepsArray.size() == 0) {
      return new TraceLoaderResult(false, null, "Trace.steps must be a non-empty array.");
    }
    if (snapshotsArray == null || snapshotsArray.size() == 0) {
      return new TraceLoaderResult(false, null, "Trace.observable_snapshots must be a non-empty array.");
    }

    JSONObject timelineObj = objectOrNull(raw, "timeline");
    if (timelineObj == null) {
      return new TraceLoaderResult(false, null, "Trace.timeline must be an object.");
    }

    int stepCount = min(stepsArray.size(), snapshotsArray.size());
    if (stepCount <= 0) {
      return new TraceLoaderResult(false, null, "No overlapping steps between steps and observable_snapshots.");
    }

    TraceModel model = new TraceModel();
    float frameDurationMs = 1000.0 / TARGET_FPS;
    float defaultStepDurationMs = floatOrDefault(timelineObj, "default_step_duration_ms", 800.0);
    model.framesPerStep = max(1, round(defaultStepDurationMs / frameDurationMs));
    model.stepCount = stepCount;
    model.gateFrameCount = max(1, stepCount * model.framesPerStep);
    model.totalFrames = model.gateFrameCount;
    model.timelineId = stringOrDefault(timelineObj, "timeline_id", "viewer_timeline");

    JSONArray syncGroups = arrayOrNull(raw, "view_sync_groups");
    if (syncGroups != null) {
      for (int i = 0; i < syncGroups.size(); i += 1) {
        String value = stringOrDefault(syncGroups, i, "");
        if (value.length() > 0) {
          model.syncGroups.add(value);
        }
      }
    }

    String measurementModelError = parseMeasurementModel(raw, model);
    if (measurementModelError.length() > 0) {
      return new TraceLoaderResult(false, null, measurementModelError);
    }
    parseMeasurementShotReplay(raw, model);

    TreeSet<String> amplitudeBases = new TreeSet<String>();
    TreeSet<String> probabilityBases = new TreeSet<String>();

    for (int i = 0; i < stepCount; i += 1) {
      JSONObject stepObj = objectOrDefault(stepsArray, i);
      JSONObject snapshotObj = objectOrDefault(snapshotsArray, i);

      TraceStep step = new TraceStep();
      step.index = i;
      step.operationId = stringOrDefault(stepObj, "operation_id", "step_" + i);
      step.operationName = stringOrDefault(stepObj, "operation_name", "");
      step.operationQubits = parseIntArray(arrayOrNull(stepObj, "operation_qubits"));
      step.operationControls = parseIntArray(arrayOrNull(stepObj, "operation_controls"));
      step.operationTargets = parseIntArray(arrayOrNull(stepObj, "operation_targets"));
      step.gateLabel = parseGateLabel(step.operationId);
      step.phaseWindows = normalizePhaseWindows(arrayOrNull(stepObj, "phase_windows"), model.framesPerStep);
      JSONObject measurementObj = objectOrNull(stepObj, "measurement");
      if (measurementObj != null && boolOrDefault(measurementObj, "is_measurement", false)) {
        step.isMeasurement = true;
        model.hasMeasurementStep = true;
      }

      JSONObject boundary = objectOrNull(stepObj, "boundary_checkpoint");
      if (boundary != null) {
        step.gateStartHash = stringOrDefault(boundary, "gate_start_hash", "");
        step.gateEndHash = stringOrDefault(boundary, "gate_end_hash", "");
      }

      parseTopKIntoMap(arrayOrNull(snapshotObj, "top_k_amplitudes"), step.amplitudes, amplitudeBases, model);
      parseHistogramIntoMap(arrayOrNull(snapshotObj, "measurement_histogram"), step.probabilities, probabilityBases, model);

      step.evolutionSamples = parseEvolutionSamples(arrayOrNull(stepObj, "evolution_samples"));
      if (!step.evolutionSamples.isEmpty()) {
        for (EvolutionSample sample : step.evolutionSamples) {
          for (String basis : sample.amplitudes.keySet()) {
            amplitudeBases.add(basis);
            model.amplitudeMax = max(model.amplitudeMax, sample.amplitudes.get(basis).magnitude);
          }
          for (String basis : sample.probabilities.keySet()) {
            probabilityBases.add(basis);
            model.probabilityMax = max(model.probabilityMax, sample.probabilities.get(basis).probability);
          }
        }
      }

      model.steps.add(step);
    }
    if (model.measurementShotReplay != null) {
      for (ShotReplayOutcome outcome : model.measurementShotReplay.outcomes) {
        if (outcome != null && outcome.label != null && outcome.label.length() > 0) {
          probabilityBases.add(outcome.label);
          model.probabilityMax = max(model.probabilityMax, 1.0);
        }
      }
    }

    for (String basis : amplitudeBases) {
      model.allAmplitudeBases.add(basis);
    }
    for (String basis : probabilityBases) {
      model.allProbabilityBases.add(basis);
    }

    if (model.allProbabilityBases.isEmpty()) {
      for (String basis : model.allAmplitudeBases) {
        model.allProbabilityBases.add(basis);
      }
    }

    model.finalizeFrameCounts();

    return new TraceLoaderResult(true, model, "");
  }

  String parseMeasurementModel(JSONObject raw, TraceModel model) {
    JSONObject measurementObj = objectOrNull(raw, "measurement_model");
    if (measurementObj == null) {
      return "";
    }

    model.measurementMode = stringOrDefault(measurementObj, "mode", "collapse");
    if (!"collapse".equals(model.measurementMode)) {
      return "Unsupported measurement_model.mode '" + model.measurementMode + "'. Only 'collapse' is supported.";
    }
    model.selectedOutcome = stringOrDefault(measurementObj, "selected_outcome", "");
    model.selectedOutcomeProbability = 0.0;

    if (model.selectedOutcome.length() == 0) {
      return "";
    }

    JSONArray outcomes = arrayOrNull(measurementObj, "outcomes");
    if (outcomes == null) {
      return "";
    }

    for (int i = 0; i < outcomes.size(); i += 1) {
      JSONObject item = objectOrDefault(outcomes, i);
      String label = stringOrDefault(item, "label", "");
      if (!model.selectedOutcome.equals(label)) {
        continue;
      }
      model.selectedOutcomeProbability = clampFloat(floatOrDefault(item, "probability", 0), 0, 1);
      break;
    }
    return "";
  }

  void parseMeasurementShotReplay(JSONObject raw, TraceModel model) {
    JSONObject replayObj = objectOrNull(raw, "measurement_shot_replay");
    if (replayObj == null) {
      model.measurementShotReplay = null;
      return;
    }

    MeasurementShotReplay replay = new MeasurementShotReplay();
    replay.sourceStepIndex = max(0, intOrDefault(replayObj, "source_step_index", 0));
    replay.measuredQubits = parseIntArray(arrayOrNull(replayObj, "measured_qubits"));
    replay.measuredClassicalTargets = parseIntArray(arrayOrNull(replayObj, "measured_classical_targets"));
    replay.shotsTotal = max(0, intOrDefault(replayObj, "shots_total", 0));
    replay.samplingSeed = intOrDefault(replayObj, "sampling_seed", 0);

    JSONObject timelineObj = objectOrNull(replayObj, "timeline");
    if (timelineObj != null) {
      replay.timeline.cameraPullbackFrames = max(1, intOrDefault(timelineObj, "camera_pullback_frames", 36));
      replay.timeline.histogramProjectFrames = max(1, intOrDefault(timelineObj, "histogram_project_frames", 60));
      replay.timeline.framesPerShot = max(1, intOrDefault(timelineObj, "frames_per_shot", 6));
    }

    JSONArray outcomes = arrayOrNull(replayObj, "outcomes");
    if (outcomes != null) {
      for (int i = 0; i < outcomes.size(); i += 1) {
        JSONObject item = objectOrDefault(outcomes, i);
        String label = stringOrDefault(item, "label", "");
        if (label.length() == 0) {
          continue;
        }
        float probability = clampFloat(floatOrDefault(item, "probability", 0), 0, 1);
        String stateHash = stringOrDefault(item, "state_hash", "");
        replay.outcomes.add(new ShotReplayOutcome(label, probability, stateHash));
      }
    }

    JSONArray outcomeStates = arrayOrNull(replayObj, "outcome_states");
    if (outcomeStates != null) {
      for (int i = 0; i < outcomeStates.size(); i += 1) {
        JSONObject item = objectOrDefault(outcomeStates, i);
        String label = stringOrDefault(item, "label", "");
        String stateHash = stringOrDefault(item, "state_hash", "");
        if (label.length() == 0 || stateHash.length() == 0) {
          continue;
        }

        ShotReplayState state = new ShotReplayState(label, stateHash);
        JSONArray topK = arrayOrNull(item, "top_k_amplitudes");
        if (topK != null) {
          for (int j = 0; j < topK.size(); j += 1) {
            JSONObject ampObj = objectOrDefault(topK, j);
            String basis = stringOrDefault(ampObj, "basis", "");
            if (basis.length() == 0) {
              continue;
            }
            float magnitude = clampFloat(floatOrDefault(ampObj, "magnitude", 0), 0, 1);
            float phase = floatOrDefault(ampObj, "phase", 0);
            state.amplitudes.put(basis, new AmplitudeSample(basis, magnitude, phase));
            model.amplitudeMax = max(model.amplitudeMax, magnitude);
          }
        }
        state.reducedDensityBlocks = parseReducedDensityBlocks(arrayOrNull(item, "reduced_density_blocks"));

        replay.outcomeStatesByLabel.put(label, state);
        replay.outcomeStatesByHash.put(stateHash, state);
      }
    }

    JSONArray events = arrayOrNull(replayObj, "shot_events");
    if (events != null) {
      for (int i = 0; i < events.size(); i += 1) {
        JSONObject item = objectOrDefault(events, i);
        int shotIndex = max(0, intOrDefault(item, "shot_index", i));
        String outcomeLabel = stringOrDefault(item, "outcome_label", "");
        String stateHash = stringOrDefault(item, "state_hash", "");
        if (outcomeLabel.length() == 0 || stateHash.length() == 0) {
          continue;
        }
        replay.shotEvents.add(new ShotReplayEvent(shotIndex, outcomeLabel, stateHash));
      }
    }

    Collections.sort(replay.shotEvents, new Comparator<ShotReplayEvent>() {
      public int compare(ShotReplayEvent a, ShotReplayEvent b) {
        return a.shotIndex - b.shotIndex;
      }
    });

    ArrayList<ShotReplayEvent> validatedEvents = new ArrayList<ShotReplayEvent>();
    for (ShotReplayEvent event : replay.shotEvents) {
      boolean hasHashState = replay.outcomeStatesByHash.containsKey(event.stateHash);
      boolean hasLabelState = replay.outcomeStatesByLabel.containsKey(event.outcomeLabel);
      if (hasHashState || hasLabelState) {
        validatedEvents.add(event);
      }
    }
    replay.shotEvents = validatedEvents;

    if (replay.shotsTotal <= 0) {
      replay.shotsTotal = replay.shotEvents.size();
    }
    if (replay.shotsTotal <= 0 || replay.outcomes.isEmpty() || replay.shotEvents.isEmpty()) {
      model.measurementShotReplay = null;
      return;
    }

    model.measurementShotReplay = replay;
  }

  Path resolveTracePath(String rawPath) {
    String candidate = rawPath;
    if (candidate == null || candidate.trim().length() == 0) {
      candidate = "data/trace.json";
    }

    Path direct = Paths.get(candidate);
    if (direct.isAbsolute() && Files.exists(direct)) {
      return direct;
    }

    if (!direct.isAbsolute() && Files.exists(direct)) {
      return direct.toAbsolutePath();
    }

    Path sketchRelative = Paths.get(app.sketchPath(candidate));
    if (Files.exists(sketchRelative)) {
      return sketchRelative;
    }

    return null;
  }

  JSONObject loadJson(Path path) {
    try {
      byte[] data = Files.readAllBytes(path);
      String text = new String(data, StandardCharsets.UTF_8);
      return app.parseJSONObject(text);
    }
    catch (Exception ignored) {
      return null;
    }
  }

  ArrayList<String> missingKeys(JSONObject raw) {
    ArrayList<String> missing = new ArrayList<String>();
    for (String key : requiredKeys) {
      if (raw == null || !raw.hasKey(key)) {
        missing.add(key);
      }
    }
    return missing;
  }

  ArrayList<PhaseWindow> normalizePhaseWindows(JSONArray phaseWindows, int framesPerStep) {
    ArrayList<PhaseWindow> windows = new ArrayList<PhaseWindow>();

    if (phaseWindows != null) {
      for (int i = 0; i < phaseWindows.size(); i += 1) {
        JSONObject item = objectOrDefault(phaseWindows, i);
        String phase = stringOrDefault(item, "phase", "apply_gate");
        float startNorm = clampFloat(floatOrDefault(item, "t_start", 0), 0, 1);
        float endNorm = clampFloat(floatOrDefault(item, "t_end", 1), 0, 1);

        int startFrame = clampInt(round(startNorm * framesPerStep), 0, framesPerStep);
        int endFrame = clampInt(round(endNorm * framesPerStep), 0, framesPerStep);
        if (endFrame <= startFrame) {
          endFrame = min(framesPerStep, startFrame + 1);
        }
        windows.add(new PhaseWindow(phase, startFrame, endFrame));
      }
    }

    if (windows.isEmpty()) {
      windows.add(new PhaseWindow("apply_gate", 0, framesPerStep));
    }

    Collections.sort(windows, new Comparator<PhaseWindow>() {
      public int compare(PhaseWindow a, PhaseWindow b) {
        return a.startFrame - b.startFrame;
      }
    });

    windows.get(0).startFrame = 0;
    windows.get(windows.size() - 1).endFrame = framesPerStep;

    for (int i = 1; i < windows.size(); i += 1) {
      PhaseWindow prev = windows.get(i - 1);
      PhaseWindow cur = windows.get(i);
      cur.startFrame = max(cur.startFrame, prev.startFrame);
      if (cur.endFrame <= cur.startFrame) {
        cur.endFrame = min(framesPerStep, cur.startFrame + 1);
      }
    }

    return windows;
  }

  void parseTopKIntoMap(
    JSONArray topK,
    HashMap<String, AmplitudeSample> target,
    TreeSet<String> bases,
    TraceModel model
  ) {
    if (topK == null) {
      return;
    }

    for (int index = 0; index < topK.size(); index += 1) {
      JSONObject item = objectOrDefault(topK, index);
      String basis = stringOrDefault(item, "basis", "");
      if (basis.length() == 0) {
        continue;
      }
      float magnitude = clampFloat(floatOrDefault(item, "magnitude", 0), 0, 1);
      float phase = floatOrDefault(item, "phase", 0);
      target.put(basis, new AmplitudeSample(basis, magnitude, phase));
      bases.add(basis);
      model.amplitudeMax = max(model.amplitudeMax, magnitude);
    }
  }

  void parseHistogramIntoMap(
    JSONArray histogram,
    HashMap<String, ProbabilitySample> target,
    TreeSet<String> bases,
    TraceModel model
  ) {
    if (histogram == null) {
      return;
    }

    for (int index = 0; index < histogram.size(); index += 1) {
      JSONObject item = objectOrDefault(histogram, index);
      String outcome = stringOrDefault(item, "outcome", "");
      if (outcome.length() == 0) {
        continue;
      }
      float probability = clampFloat(floatOrDefault(item, "probability", 0), 0, 1);
      target.put(outcome, new ProbabilitySample(outcome, probability));
      bases.add(outcome);
      model.probabilityMax = max(model.probabilityMax, probability);
    }
  }

  ArrayList<EvolutionSample> parseEvolutionSamples(JSONArray samplesArray) {
    ArrayList<EvolutionSample> samples = new ArrayList<EvolutionSample>();
    if (samplesArray == null) {
      return samples;
    }

    for (int i = 0; i < samplesArray.size(); i += 1) {
      JSONObject item = objectOrDefault(samplesArray, i);
      int sampleIndex = int(floatOrDefault(item, "sample_index", i));
      String phase = stringOrDefault(item, "phase", "apply_gate");
      float tNormalized = clampFloat(floatOrDefault(item, "t_normalized", 0), 0, 1);
      String stateHash = stringOrDefault(item, "state_hash", "");

      EvolutionSample sample = new EvolutionSample(sampleIndex, phase, tNormalized, stateHash);
      JSONArray topK = arrayOrNull(item, "top_k_amplitudes");
      if (topK != null) {
        for (int j = 0; j < topK.size(); j += 1) {
          JSONObject ampItem = objectOrDefault(topK, j);
          String basis = stringOrDefault(ampItem, "basis", "");
          if (basis.length() == 0) {
            continue;
          }
          float magnitude = clampFloat(floatOrDefault(ampItem, "magnitude", 0), 0, 1);
          float phaseValue = floatOrDefault(ampItem, "phase", 0);
          sample.amplitudes.put(basis, new AmplitudeSample(basis, magnitude, phaseValue));
        }
      }

      JSONArray histogram = arrayOrNull(item, "measurement_histogram");
      if (histogram != null) {
        for (int j = 0; j < histogram.size(); j += 1) {
          JSONObject histItem = objectOrDefault(histogram, j);
          String outcome = stringOrDefault(histItem, "outcome", "");
          if (outcome.length() == 0) {
            continue;
          }
          float probability = clampFloat(floatOrDefault(histItem, "probability", 0), 0, 1);
          sample.probabilities.put(outcome, new ProbabilitySample(outcome, probability));
        }
      }

      sample.reducedDensityBlocks = parseReducedDensityBlocks(arrayOrNull(item, "reduced_density_blocks"));
      sample.gateMatrix = parseGateMatrixSample(objectOrNull(item, "gate_matrix"));
      samples.add(sample);
    }

    Collections.sort(samples, new Comparator<EvolutionSample>() {
      public int compare(EvolutionSample a, EvolutionSample b) {
        if (a.tNormalized < b.tNormalized) {
          return -1;
        }
        if (a.tNormalized > b.tNormalized) {
          return 1;
        }
        return a.sampleIndex - b.sampleIndex;
      }
    });

    return samples;
  }

  ArrayList<ReducedDensitySample> parseReducedDensityBlocks(JSONArray blocksArray) {
    ArrayList<ReducedDensitySample> blocks = new ArrayList<ReducedDensitySample>();
    if (blocksArray == null) {
      return blocks;
    }

    for (int i = 0; i < blocksArray.size(); i += 1) {
      JSONObject blockObj = objectOrDefault(blocksArray, i);
      int[] qubits = parseIntArray(arrayOrNull(blockObj, "qubits"));
      float[][] real = parseMatrix(arrayOrNull(blockObj, "real"));
      float[][] imag = parseMatrix(arrayOrNull(blockObj, "imag"));

      if (real.length == 0 || imag.length == 0 || real.length != imag.length) {
        continue;
      }

      int cols = real[0].length;
      boolean rectangular = cols > 0;
      for (int row = 0; row < real.length; row += 1) {
        if (real[row].length != cols || imag[row].length != cols) {
          rectangular = false;
          break;
        }
      }
      if (!rectangular) {
        continue;
      }

      blocks.add(new ReducedDensitySample(qubits, real, imag));
    }

    return blocks;
  }

  GateMatrixSample parseGateMatrixSample(JSONObject gateMatrixObj) {
    if (gateMatrixObj == null) {
      return null;
    }

    String gateName = stringOrDefault(gateMatrixObj, "gate_name", "");
    int[] qubits = parseIntArray(arrayOrNull(gateMatrixObj, "qubits"));
    float[][] real = parseMatrix(arrayOrNull(gateMatrixObj, "real"));
    float[][] imag = parseMatrix(arrayOrNull(gateMatrixObj, "imag"));

    if (real.length == 0 || imag.length == 0 || real.length != imag.length) {
      return null;
    }

    int cols = real[0].length;
    if (cols <= 0) {
      return null;
    }
    for (int row = 0; row < real.length; row += 1) {
      if (real[row].length != cols || imag[row].length != cols) {
        return null;
      }
    }

    return new GateMatrixSample(gateName, qubits, real, imag);
  }

  int[] parseIntArray(JSONArray arr) {
    if (arr == null || arr.size() == 0) {
      return new int[0];
    }

    int[] values = new int[arr.size()];
    for (int i = 0; i < arr.size(); i += 1) {
      try {
        values[i] = arr.getInt(i);
      }
      catch (Exception ignored) {
        try {
          values[i] = int(parseFloatArg(arr.getString(i), 0));
        }
        catch (Exception ignoredAgain) {
          values[i] = 0;
        }
      }
    }
    return values;
  }

  float[][] parseMatrix(JSONArray rows) {
    if (rows == null || rows.size() == 0) {
      return new float[0][0];
    }

    float[][] matrix = new float[rows.size()][];
    for (int r = 0; r < rows.size(); r += 1) {
      JSONArray row = null;
      try {
        row = rows.getJSONArray(r);
      }
      catch (Exception ignored) {
      }

      if (row == null) {
        matrix[r] = new float[0];
        continue;
      }

      matrix[r] = new float[row.size()];
      for (int c = 0; c < row.size(); c += 1) {
        try {
          matrix[r][c] = row.getFloat(c);
        }
        catch (Exception ignored) {
          matrix[r][c] = parseFloatArg(row.getString(c), 0);
        }
      }
    }

    return matrix;
  }

  JSONArray arrayOrNull(JSONObject obj, String key) {
    if (obj == null || !obj.hasKey(key)) {
      return null;
    }
    try {
      return obj.getJSONArray(key);
    }
    catch (Exception ignored) {
      return null;
    }
  }

  JSONObject objectOrNull(JSONObject obj, String key) {
    if (obj == null || !obj.hasKey(key)) {
      return null;
    }
    try {
      return obj.getJSONObject(key);
    }
    catch (Exception ignored) {
      return null;
    }
  }

  JSONObject objectOrDefault(JSONArray arr, int index) {
    if (arr == null || index < 0 || index >= arr.size()) {
      return new JSONObject();
    }
    try {
      return arr.getJSONObject(index);
    }
    catch (Exception ignored) {
      return new JSONObject();
    }
  }

  String stringOrDefault(JSONObject obj, String key, String fallback) {
    if (obj == null || !obj.hasKey(key)) {
      return fallback;
    }
    try {
      String value = obj.getString(key);
      return value != null ? value : fallback;
    }
    catch (Exception ignored) {
      return fallback;
    }
  }

  String stringOrDefault(JSONArray arr, int index, String fallback) {
    if (arr == null || index < 0 || index >= arr.size()) {
      return fallback;
    }
    try {
      String value = arr.getString(index);
      return value != null ? value : fallback;
    }
    catch (Exception ignored) {
      return fallback;
    }
  }

  float floatOrDefault(JSONObject obj, String key, float fallback) {
    if (obj == null || !obj.hasKey(key)) {
      return fallback;
    }
    try {
      return obj.getFloat(key);
    }
    catch (Exception ignored) {
      try {
        return float(obj.getString(key));
      }
      catch (Exception ignoredAgain) {
        return fallback;
      }
    }
  }

  int intOrDefault(JSONObject obj, String key, int fallback) {
    if (obj == null || !obj.hasKey(key)) {
      return fallback;
    }
    try {
      return obj.getInt(key);
    }
    catch (Exception ignored) {
      try {
        return round(obj.getFloat(key));
      }
      catch (Exception ignoredAgain) {
        return parseIntArg(stringOrDefault(obj, key, str(fallback)), fallback);
      }
    }
  }

  boolean boolOrDefault(JSONObject obj, String key, boolean fallback) {
    if (obj == null || !obj.hasKey(key)) {
      return fallback;
    }
    try {
      return obj.getBoolean(key);
    }
    catch (Exception ignored) {
      String raw = stringOrDefault(obj, key, fallback ? "true" : "false");
      return "true".equalsIgnoreCase(raw);
    }
  }
}
