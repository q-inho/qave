/*
Purpose: Define trace data models consumed by renderer panes and timeline playback.
Inputs: Shared playback state, trace-derived models, pane metrics, and user interaction state.
Outputs: Deterministic frame-local rendering updates and synchronized visual state transitions.
Determinism/Timing: Uses timeline phases (pre_gate/apply_gate/settle) and fixed frame progression for reproducible output.
*/

class PhaseWindow {
  String phase;
  int startFrame;
  int endFrame;

  PhaseWindow(String phase, int startFrame, int endFrame) {
    this.phase = phase;
    this.startFrame = startFrame;
    this.endFrame = endFrame;
  }
}

// Class AmplitudeSample encapsulates module-specific viewer behavior.
class AmplitudeSample {
  String basis;
  float magnitude;
  float phase;

  AmplitudeSample(String basis, float magnitude, float phase) {
    this.basis = basis;
    this.magnitude = magnitude;
    this.phase = phase;
  }
}

// Class ProbabilitySample encapsulates module-specific viewer behavior.
class ProbabilitySample {
  String basis;
  float probability;

  ProbabilitySample(String basis, float probability) {
    this.basis = basis;
    this.probability = probability;
  }
}

// Class ReducedDensitySample encapsulates module-specific viewer behavior.
class ReducedDensitySample {
  int[] qubits;
  String qubitKey;
  float[][] real;
  float[][] imag;

  ReducedDensitySample(int[] qubits, float[][] real, float[][] imag) {
    this.qubits = qubits;
    this.qubitKey = buildQubitKey(qubits);
    this.real = real;
    this.imag = imag;
  }

  String buildQubitKey(int[] qubits) {
    if (qubits == null || qubits.length == 0) {
      return "";
    }
    StringBuilder builder = new StringBuilder();
    for (int i = 0; i < qubits.length; i += 1) {
      if (i > 0) {
        builder.append(",");
      }
      builder.append(qubits[i]);
    }
    return builder.toString();
  }
}

// Class GateMatrixSample encapsulates module-specific viewer behavior.
class GateMatrixSample {
  String gateName;
  int[] qubits;
  String qubitKey;
  float[][] real;
  float[][] imag;

  GateMatrixSample(String gateName, int[] qubits, float[][] real, float[][] imag) {
    this.gateName = gateName;
    this.qubits = qubits;
    this.qubitKey = buildQubitKey(qubits);
    this.real = real;
    this.imag = imag;
  }

  String buildQubitKey(int[] qubits) {
    if (qubits == null || qubits.length == 0) {
      return "";
    }
    StringBuilder builder = new StringBuilder();
    for (int i = 0; i < qubits.length; i += 1) {
      if (i > 0) {
        builder.append(",");
      }
      builder.append(qubits[i]);
    }
    return builder.toString();
  }
}

// Class EvolutionSample encapsulates module-specific viewer behavior.
class EvolutionSample {
  int sampleIndex;
  String phase;
  float tNormalized;
  String stateHash;
  HashMap<String, AmplitudeSample> amplitudes = new HashMap<String, AmplitudeSample>();
  HashMap<String, ProbabilitySample> probabilities = new HashMap<String, ProbabilitySample>();
  ArrayList<ReducedDensitySample> reducedDensityBlocks = new ArrayList<ReducedDensitySample>();
  GateMatrixSample gateMatrix;

  EvolutionSample(int sampleIndex, String phase, float tNormalized, String stateHash) {
    this.sampleIndex = sampleIndex;
    this.phase = phase;
    this.tNormalized = tNormalized;
    this.stateHash = stateHash;
  }
}

// Class FrameSample encapsulates module-specific viewer behavior.
class FrameSample {
  String phase;
  float tNormalized;
  String stateHash;
  HashMap<String, AmplitudeSample> amplitudes = new HashMap<String, AmplitudeSample>();
  HashMap<String, ProbabilitySample> probabilities = new HashMap<String, ProbabilitySample>();
  ArrayList<ReducedDensitySample> reducedDensityBlocks = new ArrayList<ReducedDensitySample>();
  GateMatrixSample gateMatrix;

  FrameSample(String phase, float tNormalized, String stateHash) {
    this.phase = phase;
    this.tNormalized = tNormalized;
    this.stateHash = stateHash;
  }
}

// Class TraceStep encapsulates module-specific viewer behavior.
class TraceStep {
  int index;
  String operationId;
  String operationName = "";
  boolean isMeasurement = false;
  int[] operationQubits = new int[0];
  int[] operationControls = new int[0];
  int[] operationTargets = new int[0];
  String gateLabel;
  ArrayList<PhaseWindow> phaseWindows = new ArrayList<PhaseWindow>();
  HashMap<String, AmplitudeSample> amplitudes = new HashMap<String, AmplitudeSample>();
  HashMap<String, ProbabilitySample> probabilities = new HashMap<String, ProbabilitySample>();
  ArrayList<EvolutionSample> evolutionSamples = new ArrayList<EvolutionSample>();
  String gateStartHash = "";
  String gateEndHash = "";
}

// Class ShotReplayTimeline encapsulates module-specific viewer behavior.
class ShotReplayTimeline {
  int cameraPullbackFrames = 36;
  int histogramProjectFrames = 60;
  int framesPerShot = 6;
}

// Class ShotReplayOutcome encapsulates module-specific viewer behavior.
class ShotReplayOutcome {
  String label;
  float probability;
  String stateHash;

  ShotReplayOutcome(String label, float probability, String stateHash) {
    this.label = label;
    this.probability = probability;
    this.stateHash = stateHash != null ? stateHash : "";
  }
}

// Class ShotReplayState encapsulates module-specific viewer behavior.
class ShotReplayState {
  String label;
  String stateHash;
  HashMap<String, AmplitudeSample> amplitudes = new HashMap<String, AmplitudeSample>();
  ArrayList<ReducedDensitySample> reducedDensityBlocks = new ArrayList<ReducedDensitySample>();

  ShotReplayState(String label, String stateHash) {
    this.label = label;
    this.stateHash = stateHash != null ? stateHash : "";
  }
}

// Class ShotReplayEvent encapsulates module-specific viewer behavior.
class ShotReplayEvent {
  int shotIndex;
  String outcomeLabel;
  String stateHash;

  ShotReplayEvent(int shotIndex, String outcomeLabel, String stateHash) {
    this.shotIndex = shotIndex;
    this.outcomeLabel = outcomeLabel != null ? outcomeLabel : "";
    this.stateHash = stateHash != null ? stateHash : "";
  }
}

// Class MeasurementShotReplay encapsulates module-specific viewer behavior.
class MeasurementShotReplay {
  int sourceStepIndex = 0;
  int[] measuredQubits = new int[0];
  int[] measuredClassicalTargets = new int[0];
  int shotsTotal = 0;
  int samplingSeed = 0;
  ShotReplayTimeline timeline = new ShotReplayTimeline();
  ArrayList<ShotReplayOutcome> outcomes = new ArrayList<ShotReplayOutcome>();
  ArrayList<ShotReplayEvent> shotEvents = new ArrayList<ShotReplayEvent>();
  HashMap<String, ShotReplayState> outcomeStatesByLabel = new HashMap<String, ShotReplayState>();
  HashMap<String, ShotReplayState> outcomeStatesByHash = new HashMap<String, ShotReplayState>();
}

// Class PlaybackState encapsulates module-specific viewer behavior.
class PlaybackState {
  int frameIndex;
  int stepIndex;
  int localFrame;
  String phase;
  float stepProgress;
  float phaseProgress;
  float gateProgressGlobal;
  float timelineProgressGlobal;
  boolean inShotReplay;
  int shotIndex;
  int shotsTotal;
  String shotOutcomeLabel;
  float shotProgress;
  String shotBeat;
  float shotBeatProgress;
  TraceStep step;
  FrameSample sample;

  PlaybackState(
    int frameIndex,
    int stepIndex,
    int localFrame,
    String phase,
    float stepProgress,
    float phaseProgress,
    float gateProgressGlobal,
    float timelineProgressGlobal,
    boolean inShotReplay,
    int shotIndex,
    int shotsTotal,
    String shotOutcomeLabel,
    float shotProgress,
    String shotBeat,
    float shotBeatProgress,
    TraceStep step,
    FrameSample sample
  ) {
    this.frameIndex = frameIndex;
    this.stepIndex = stepIndex;
    this.localFrame = localFrame;
    this.phase = phase;
    this.stepProgress = stepProgress;
    this.phaseProgress = phaseProgress;
    this.gateProgressGlobal = gateProgressGlobal;
    this.timelineProgressGlobal = timelineProgressGlobal;
    this.inShotReplay = inShotReplay;
    this.shotIndex = shotIndex;
    this.shotsTotal = shotsTotal;
    this.shotOutcomeLabel = shotOutcomeLabel != null ? shotOutcomeLabel : "";
    this.shotProgress = shotProgress;
    this.shotBeat = shotBeat != null ? shotBeat : "";
    this.shotBeatProgress = clampFloat(shotBeatProgress, 0.0, 1.0);
    this.step = step;
    this.sample = sample;
  }
}

// Class TraceModel encapsulates module-specific viewer behavior.
class TraceModel {
  int fps = TARGET_FPS;
  int framesPerStep = 1;
  int totalFrames = 1;
  int gateFrameCount = 1;
  int stepCount = 0;
  String timelineId = "viewer_timeline";
  boolean hasMeasurementStep = false;
  String measurementMode = "collapse";
  String selectedOutcome = "";
  float selectedOutcomeProbability = 0.0;
  int measurementRevealFrames = 48;
  MeasurementShotReplay measurementShotReplay = null;
  int shotCameraPullbackFrames = 0;
  int shotHistogramProjectFrames = 0;
  int shotStackFrames = 0;
  int shotProjectFrames = 0;
  int shotBaseFramesPerShot = 0;
  int shotExtendedFramesPerShot = 0;
  int shotReplayFrameCount = 0;
  final float SHOT_STACK_BEAT_LOCK_FRACTION = 0.15;
  final float SHOT_STACK_BEAT_EMIT_FRACTION = 0.35;
  final float SHOT_STACK_BEAT_COLLAPSE_FRACTION = 0.30;
  final float SHOT_STACK_BEAT_SETTLE_FRACTION = 0.20;
  final String SHOT_STACK_BEAT_LOCK = "lock_density";
  final String SHOT_STACK_BEAT_EMIT = "emit";
  final String SHOT_STACK_BEAT_COLLAPSE = "collapse";
  final String SHOT_STACK_BEAT_SETTLE = "stack_settle";

  ArrayList<String> syncGroups = new ArrayList<String>();
  ArrayList<TraceStep> steps = new ArrayList<TraceStep>();
  ArrayList<String> allAmplitudeBases = new ArrayList<String>();
  ArrayList<String> allProbabilityBases = new ArrayList<String>();

  float amplitudeMax = 1.0;
  float probabilityMax = 1.0;

  PlaybackState frameState(int requestedFrame) {
    int clampedFrame = clampInt(requestedFrame, 0, max(0, totalFrames - 1));
    int framePerStep = max(1, framesPerStep);
    float timelineProgressGlobal = totalFrames <= 1
      ? 1.0
      : clampFloat(clampedFrame / float(max(1, totalFrames - 1)), 0.0, 1.0);

    int postGateOffset = gateFrameCount;
    int finalStepIndex = max(0, stepCount - 1);
    TraceStep finalStep = steps.get(finalStepIndex);

    if (hasMeasurementReveal() && clampedFrame >= postGateOffset && clampedFrame < postGateOffset + measurementRevealFrames) {
      int revealFrame = clampedFrame - postGateOffset;
      float revealProgress = measurementRevealFrames <= 1
        ? 1.0
        : clampFloat(revealFrame / float(max(1, measurementRevealFrames - 1)), 0.0, 1.0);
      FrameSample revealSample = resolveSampleForStep(finalStep, 1.0, "measurement_reveal");
      return new PlaybackState(
        clampedFrame,
        finalStepIndex,
        max(0, framePerStep - 1),
        "measurement_reveal",
        1.0,
        revealProgress,
        1.0,
        timelineProgressGlobal,
        false,
        -1,
        0,
        "",
        0.0,
        "",
        0.0,
        finalStep,
        revealSample
      );
    }

    postGateOffset += hasMeasurementReveal() ? measurementRevealFrames : 0;
    if (hasShotReplay() && clampedFrame >= postGateOffset) {
      int localReplayFrame = clampedFrame - postGateOffset;
      int replayShotCount = max(1, measurementShotReplay.shotsTotal);
      int shotPhaseEnd = shotCameraPullbackFrames;
      int stackPhaseEnd = shotCameraPullbackFrames + shotStackFrames;
      int projectTransitionEnd = stackPhaseEnd + shotHistogramProjectFrames;

      if (localReplayFrame < shotPhaseEnd) {
        float phaseProgress = shotCameraPullbackFrames <= 1
          ? 1.0
          : clampFloat(localReplayFrame / float(max(1, shotCameraPullbackFrames - 1)), 0.0, 1.0);
        FrameSample sample = resolveShotReplayHoldSample("shot_camera_pullback");
        sample.probabilities = resolveShotReplayProbabilities(-1, 0.0, false);
        return new PlaybackState(
          clampedFrame,
          finalStepIndex,
          max(0, framePerStep - 1),
          "shot_camera_pullback",
          1.0,
          phaseProgress,
          1.0,
          timelineProgressGlobal,
          true,
          -1,
          measurementShotReplay.shotsTotal,
          "",
          0.0,
          "",
          0.0,
          finalStep,
          sample
        );
      }

      if (localReplayFrame < stackPhaseEnd) {
        int stackFrame = max(0, localReplayFrame - shotCameraPullbackFrames);
        int framesPerShot = max(1, shotExtendedFramesPerShot);
        int shotIndex = min(replayShotCount - 1, stackFrame / framesPerShot);
        int shotLocalFrame = max(0, stackFrame - shotIndex * framesPerShot);
        float shotProgress = framesPerShot <= 1
          ? 1.0
          : clampFloat(shotLocalFrame / float(max(1, framesPerShot - 1)), 0.0, 1.0);
        String shotBeat = resolveShotStackBeat(shotProgress);
        float shotBeatProgress = resolveShotStackBeatProgress(shotProgress, shotBeat);
        ShotReplayEvent event = resolveShotReplayEvent(shotIndex);
        String shotOutcomeLabel = event != null ? event.outcomeLabel : "";
        FrameSample sample = resolveShotReplayEventFrameSample(shotIndex, "shot_stack");
        sample.probabilities = resolveShotReplayProbabilities(-1, 0.0, false);
        return new PlaybackState(
          clampedFrame,
          finalStepIndex,
          max(0, framePerStep - 1),
          "shot_stack",
          1.0,
          shotProgress,
          1.0,
          timelineProgressGlobal,
          true,
          shotIndex,
          measurementShotReplay.shotsTotal,
          shotOutcomeLabel,
          shotProgress,
          shotBeat,
          shotBeatProgress,
          finalStep,
          sample
        );
      }

      if (localReplayFrame < projectTransitionEnd) {
        int transitionFrame = max(0, localReplayFrame - stackPhaseEnd);
        float phaseProgress = shotHistogramProjectFrames <= 1
          ? 1.0
          : clampFloat(transitionFrame / float(max(1, shotHistogramProjectFrames - 1)), 0.0, 1.0);
        FrameSample sample = resolveShotReplayEventFrameSample(replayShotCount - 1, "shot_histogram_project");
        sample.probabilities = resolveShotReplayProbabilities(-1, 0.0, false);
        return new PlaybackState(
          clampedFrame,
          finalStepIndex,
          max(0, framePerStep - 1),
          "shot_histogram_project",
          1.0,
          phaseProgress,
          1.0,
          timelineProgressGlobal,
          true,
          -1,
          measurementShotReplay.shotsTotal,
          "",
          0.0,
          "",
          0.0,
          finalStep,
          sample
        );
      }

      int projectFrame = max(0, localReplayFrame - projectTransitionEnd);
      int framesPerShot = max(1, shotExtendedFramesPerShot);
      int shotIndex = min(replayShotCount - 1, projectFrame / framesPerShot);
      int shotLocalFrame = max(0, projectFrame - shotIndex * framesPerShot);
      float shotProgress = framesPerShot <= 1
        ? 1.0
        : clampFloat(shotLocalFrame / float(max(1, framesPerShot - 1)), 0.0, 1.0);
      ShotReplayEvent event = resolveShotReplayEvent(shotIndex);
      String shotOutcomeLabel = event != null ? event.outcomeLabel : "";
      FrameSample sample = resolveShotReplayEventFrameSample(shotIndex, "shot_histogram_project");
      sample.probabilities = resolveShotReplayProbabilities(shotIndex, shotProgress, true);
      return new PlaybackState(
        clampedFrame,
        finalStepIndex,
        max(0, framePerStep - 1),
        "shot_histogram_project",
        1.0,
        shotProgress,
        1.0,
        timelineProgressGlobal,
        true,
        shotIndex,
        measurementShotReplay.shotsTotal,
        shotOutcomeLabel,
        shotProgress,
        "",
        0.0,
        finalStep,
        sample
      );
    }

    int gateFrame = clampInt(clampedFrame, 0, max(0, gateFrameCount - 1));
    float gateProgressGlobal = gateFrameCount <= 1
      ? 1.0
      : clampFloat(gateFrame / float(max(1, gateFrameCount - 1)), 0.0, 1.0);
    int stepIndex = min(max(0, stepCount - 1), gateFrame / framePerStep);
    int localFrame = gateFrame - stepIndex * framePerStep;
    TraceStep step = steps.get(stepIndex);
    String phase = findPhaseAtFrame(localFrame, step.phaseWindows);
    PhaseWindow activePhaseWindow = findActivePhaseWindow(localFrame, step.phaseWindows);

    float stepProgress = 0.0;
    if (framePerStep > 1) {
      stepProgress = clampFloat(localFrame / float(framePerStep - 1), 0.0, 1.0);
    }
    float phaseProgress = stepProgress;
    if (activePhaseWindow != null) {
      int phaseFrames = max(0, activePhaseWindow.endFrame - activePhaseWindow.startFrame);
      if (phaseFrames <= 1) {
        phaseProgress = 1.0;
      } else {
        phaseProgress = clampFloat(
          (localFrame - activePhaseWindow.startFrame) / float(phaseFrames - 1),
          0.0,
          1.0
        );
      }
    }

    FrameSample sample = resolveSampleForStep(step, stepProgress, phase);
    return new PlaybackState(
      clampedFrame,
      stepIndex,
      localFrame,
      phase,
      stepProgress,
      phaseProgress,
      gateProgressGlobal,
      timelineProgressGlobal,
      false,
      -1,
      0,
      "",
      0.0,
      "",
      0.0,
      step,
      sample
    );
  }

  boolean hasMeasurementReveal() {
    return hasMeasurementStep
      && "collapse".equals(measurementMode)
      && selectedOutcome != null
      && selectedOutcome.length() > 0
      && measurementRevealFrames > 0;
  }

  boolean hasShotReplay() {
    return measurementShotReplay != null
      && measurementShotReplay.timeline != null
      && measurementShotReplay.shotsTotal > 0
      && measurementShotReplay.timeline.framesPerShot > 0
      && measurementShotReplay.shotEvents != null
      && !measurementShotReplay.shotEvents.isEmpty();
  }

  void finalizeFrameCounts() {
    gateFrameCount = max(1, stepCount * max(1, framesPerStep));
    shotCameraPullbackFrames = 0;
    shotHistogramProjectFrames = 0;
    shotStackFrames = 0;
    shotProjectFrames = 0;
    shotBaseFramesPerShot = 0;
    shotExtendedFramesPerShot = 0;
    shotReplayFrameCount = 0;
    if (hasShotReplay()) {
      shotCameraPullbackFrames = max(1, measurementShotReplay.timeline.cameraPullbackFrames);
      shotBaseFramesPerShot = max(1, measurementShotReplay.timeline.framesPerShot);
      shotExtendedFramesPerShot = shotBaseFramesPerShot + 4;
      shotStackFrames = max(1, measurementShotReplay.shotsTotal * shotExtendedFramesPerShot);
      shotHistogramProjectFrames = max(1, measurementShotReplay.timeline.histogramProjectFrames);
      shotProjectFrames = max(1, measurementShotReplay.shotsTotal * shotExtendedFramesPerShot);
      shotReplayFrameCount = shotCameraPullbackFrames
        + shotStackFrames
        + shotHistogramProjectFrames
        + shotProjectFrames;
    }
    totalFrames = gateFrameCount
      + (hasMeasurementReveal() ? measurementRevealFrames : 0)
      + shotReplayFrameCount;
  }

  int shotReplayStartFrame() {
    return gateFrameCount + (hasMeasurementReveal() ? measurementRevealFrames : 0);
  }

  int shotStackStartFrame() {
    return shotReplayStartFrame() + shotCameraPullbackFrames;
  }

  int frameForShotIndex(int shotIndex) {
    return frameForStackShotIndex(shotIndex);
  }

  int shotProjectTransitionStartFrame() {
    return shotStackStartFrame() + shotStackFrames;
  }

  int shotProjectStartFrame() {
    return shotProjectTransitionStartFrame() + shotHistogramProjectFrames;
  }

  int frameForStackShotIndex(int shotIndex) {
    if (!hasShotReplay()) {
      return clampInt(stepCount * max(1, framesPerStep) - 1, 0, max(0, totalFrames - 1));
    }
    int clampedShot = clampInt(shotIndex, 0, max(0, measurementShotReplay.shotsTotal - 1));
    int frame = shotStackStartFrame() + clampedShot * max(1, shotExtendedFramesPerShot);
    return clampInt(frame, 0, max(0, totalFrames - 1));
  }

  int frameForProjectShotIndex(int shotIndex) {
    if (!hasShotReplay()) {
      return clampInt(stepCount * max(1, framesPerStep) - 1, 0, max(0, totalFrames - 1));
    }
    int clampedShot = clampInt(shotIndex, 0, max(0, measurementShotReplay.shotsTotal - 1));
    int frame = shotProjectStartFrame() + clampedShot * max(1, shotExtendedFramesPerShot);
    return clampInt(frame, 0, max(0, totalFrames - 1));
  }

  boolean isShotReplayPhase(String phase) {
    return "shot_camera_pullback".equals(phase)
      || "shot_histogram_project".equals(phase)
      || "shot_stack".equals(phase);
  }

  ShotReplayEvent resolveShotReplayEvent(int shotIndex) {
    if (!hasShotReplay() || shotIndex < 0 || shotIndex >= measurementShotReplay.shotEvents.size()) {
      return null;
    }
    return measurementShotReplay.shotEvents.get(shotIndex);
  }

  FrameSample resolveShotReplayHoldSample(String phase) {
    int finalStepIndex = clampInt(
      measurementShotReplay != null ? measurementShotReplay.sourceStepIndex : stepCount - 1,
      0,
      max(0, stepCount - 1)
    );
    TraceStep finalStep = steps.get(finalStepIndex);
    FrameSample hold = resolveSampleForStep(finalStep, 1.0, phase);
    if (hold != null) {
      return hold;
    }
    return fallbackSample(finalStep, phase, 1.0);
  }

  int resolveShotReplayVisualSourceStepIndex() {
    if (steps == null || steps.isEmpty()) {
      return -1;
    }
    int sourceStepIndex = clampInt(
      measurementShotReplay != null ? measurementShotReplay.sourceStepIndex : stepCount - 1,
      0,
      max(0, steps.size() - 1)
    );
    TraceStep sourceStep = steps.get(sourceStepIndex);
    if (isMeasurementLikeStep(sourceStep) && sourceStepIndex > 0) {
      return sourceStepIndex - 1;
    }
    return sourceStepIndex;
  }

  FrameSample resolveShotReplayVisualSourceSample(String phase) {
    if (measurementShotReplay == null || steps == null || steps.isEmpty()) {
      return resolveShotReplayHoldSample(phase);
    }
    int visualSourceStepIndex = resolveShotReplayVisualSourceStepIndex();
    if (visualSourceStepIndex < 0 || visualSourceStepIndex >= steps.size()) {
      return resolveShotReplayHoldSample(phase);
    }
    TraceStep sourceStep = steps.get(visualSourceStepIndex);
    EvolutionSample sourceEvolution = resolveLatestSettleEvolutionSample(sourceStep);
    if (sourceEvolution != null) {
      return copySample(sourceEvolution, phase, sourceEvolution.tNormalized);
    }
    return resolveShotReplayHoldSample(phase);
  }

  FrameSample resolveShotReplayFrameSample(ShotReplayEvent event, float shotProgress, String phase) {
    if (event == null || measurementShotReplay == null) {
      return resolveShotReplayHoldSample(phase);
    }

    ShotReplayState replayState = resolveShotReplayStateForEvent(event);
    if (replayState == null) {
      return resolveShotReplayHoldSample(phase);
    }

    FrameSample sample = new FrameSample(phase, clampFloat(shotProgress, 0.0, 1.0), replayState.stateHash);
    for (String key : replayState.amplitudes.keySet()) {
      AmplitudeSample src = replayState.amplitudes.get(key);
      sample.amplitudes.put(key, new AmplitudeSample(src.basis, src.magnitude, src.phase));
    }
    sample.reducedDensityBlocks = copyReducedDensityBlocks(replayState.reducedDensityBlocks);
    return sample;
  }

  FrameSample resolveShotReplaySourceSample(String phase) {
    return resolveShotReplayVisualSourceSample(phase);
  }

  FrameSample resolveShotReplayEventFrameSample(int shotIndex, String phase) {
    if (!hasShotReplay()) {
      return resolveShotReplayHoldSample(phase);
    }
    int clampedShotIndex = clampInt(shotIndex, 0, max(0, measurementShotReplay.shotEvents.size() - 1));
    ShotReplayEvent event = resolveShotReplayEvent(clampedShotIndex);
    return resolveShotReplayFrameSample(event, 1.0, phase);
  }

  ShotReplayState resolveShotReplayStateForEvent(ShotReplayEvent event) {
    if (event == null) {
      return null;
    }
    return resolveShotReplayState(event.stateHash, event.outcomeLabel);
  }

  ShotReplayState resolveShotReplayState(String stateHash, String outcomeLabel) {
    if (measurementShotReplay == null) {
      return null;
    }
    String safeHash = stateHash != null ? stateHash : "";
    if (safeHash.length() > 0) {
      ShotReplayState byHash = measurementShotReplay.outcomeStatesByHash.get(safeHash);
      if (byHash != null) {
        return byHash;
      }
    }
    String safeLabel = outcomeLabel != null ? outcomeLabel : "";
    if (safeLabel.length() > 0) {
      ShotReplayState byLabel = measurementShotReplay.outcomeStatesByLabel.get(safeLabel);
      if (byLabel != null) {
        return byLabel;
      }
    }
    return null;
  }

  EvolutionSample resolveLatestSettleEvolutionSample(TraceStep sourceStep) {
    if (sourceStep == null || sourceStep.evolutionSamples == null || sourceStep.evolutionSamples.isEmpty()) {
      return null;
    }

    EvolutionSample latestSettle = null;
    for (EvolutionSample sample : sourceStep.evolutionSamples) {
      if (sample == null || !"settle".equals(sample.phase)) {
        continue;
      }
      if (latestSettle == null) {
        latestSettle = sample;
        continue;
      }
      boolean later = sample.tNormalized > latestSettle.tNormalized;
      boolean tieLaterIndex = abs(sample.tNormalized - latestSettle.tNormalized) <= 1e-6
        && sample.sampleIndex > latestSettle.sampleIndex;
      if (later || tieLaterIndex) {
        latestSettle = sample;
      }
    }

    if (latestSettle != null) {
      return latestSettle;
    }
    return sourceStep.evolutionSamples.get(sourceStep.evolutionSamples.size() - 1);
  }

  boolean isMeasurementLikeStep(TraceStep step) {
    if (step == null) {
      return false;
    }
    if (step.isMeasurement) {
      return true;
    }
    String opName = step.operationName != null ? step.operationName.toLowerCase() : "";
    if ("measure".equals(opName) || "measurement".equals(opName)) {
      return true;
    }
    String opId = step.operationId != null ? step.operationId.toLowerCase() : "";
    return opId.contains("measure");
  }

  String resolveShotStackBeat(float shotProgress) {
    float p = clampFloat(shotProgress, 0.0, 1.0);
    float lockEnd = clampFloat(SHOT_STACK_BEAT_LOCK_FRACTION, 0.0, 1.0);
    float emitEnd = clampFloat(lockEnd + SHOT_STACK_BEAT_EMIT_FRACTION, 0.0, 1.0);
    float collapseEnd = clampFloat(emitEnd + SHOT_STACK_BEAT_COLLAPSE_FRACTION, 0.0, 1.0);
    float settleEnd = clampFloat(collapseEnd + SHOT_STACK_BEAT_SETTLE_FRACTION, 0.0, 1.0);

    if (p < lockEnd) {
      return SHOT_STACK_BEAT_LOCK;
    }
    if (p < emitEnd) {
      return SHOT_STACK_BEAT_EMIT;
    }
    if (p < collapseEnd) {
      return SHOT_STACK_BEAT_COLLAPSE;
    }
    if (p < settleEnd) {
      return SHOT_STACK_BEAT_SETTLE;
    }
    return SHOT_STACK_BEAT_SETTLE;
  }

  float resolveShotStackBeatProgress(float shotProgress, String shotBeat) {
    float p = clampFloat(shotProgress, 0.0, 1.0);
    float lockEnd = clampFloat(SHOT_STACK_BEAT_LOCK_FRACTION, 0.0, 1.0);
    float emitEnd = clampFloat(lockEnd + SHOT_STACK_BEAT_EMIT_FRACTION, 0.0, 1.0);
    float collapseEnd = clampFloat(emitEnd + SHOT_STACK_BEAT_COLLAPSE_FRACTION, 0.0, 1.0);
    float settleEnd = clampFloat(collapseEnd + SHOT_STACK_BEAT_SETTLE_FRACTION, 0.0, 1.0);

    if (SHOT_STACK_BEAT_LOCK.equals(shotBeat)) {
      return clampFloat(p / max(1e-5, lockEnd), 0.0, 1.0);
    }
    if (SHOT_STACK_BEAT_EMIT.equals(shotBeat)) {
      return clampFloat((p - lockEnd) / max(1e-5, emitEnd - lockEnd), 0.0, 1.0);
    }
    if (SHOT_STACK_BEAT_COLLAPSE.equals(shotBeat)) {
      return clampFloat((p - emitEnd) / max(1e-5, collapseEnd - emitEnd), 0.0, 1.0);
    }
    return clampFloat((p - collapseEnd) / max(1e-5, settleEnd - collapseEnd), 0.0, 1.0);
  }

  HashMap<String, ProbabilitySample> resolveShotReplayProbabilities(int shotIndex, float shotProgress) {
    return resolveShotReplayProbabilities(shotIndex, shotProgress, true);
  }

  HashMap<String, ProbabilitySample> resolveShotReplayProbabilities(int shotIndex, float shotProgress, boolean projectEnabled) {
    HashMap<String, ProbabilitySample> probabilities = new HashMap<String, ProbabilitySample>();
    if (!hasShotReplay()) {
      return probabilities;
    }

    HashMap<String, Float> counts = new HashMap<String, Float>();
    for (ShotReplayOutcome outcome : measurementShotReplay.outcomes) {
      counts.put(outcome.label, 0.0);
    }

    if (projectEnabled) {
      int completedShots = clampInt(shotIndex, 0, measurementShotReplay.shotEvents.size());
      for (int i = 0; i < completedShots; i += 1) {
        ShotReplayEvent event = measurementShotReplay.shotEvents.get(i);
        float value = counts.containsKey(event.outcomeLabel) ? counts.get(event.outcomeLabel) : 0.0;
        counts.put(event.outcomeLabel, value + 1.0);
      }

      if (shotIndex >= 0 && shotIndex < measurementShotReplay.shotEvents.size()) {
        ShotReplayEvent active = measurementShotReplay.shotEvents.get(shotIndex);
        float value = counts.containsKey(active.outcomeLabel) ? counts.get(active.outcomeLabel) : 0.0;
        counts.put(active.outcomeLabel, value + clampFloat(shotProgress, 0.0, 1.0));
      }
    }

    float safeTotal = max(1.0, measurementShotReplay.shotsTotal);
    for (ShotReplayOutcome outcome : measurementShotReplay.outcomes) {
      float count = counts.containsKey(outcome.label) ? counts.get(outcome.label) : 0.0;
      probabilities.put(
        outcome.label,
        new ProbabilitySample(outcome.label, clampFloat(count / safeTotal, 0.0, 1.0))
      );
    }

    return probabilities;
  }

  ArrayList<String> shotReplayOutcomeLabels() {
    ArrayList<String> labels = new ArrayList<String>();
    if (!hasShotReplay()) {
      return labels;
    }
    for (ShotReplayOutcome outcome : measurementShotReplay.outcomes) {
      if (outcome != null && outcome.label != null && outcome.label.length() > 0) {
        labels.add(outcome.label);
      }
    }
    return labels;
  }

  String findPhaseAtFrame(int localFrame, ArrayList<PhaseWindow> windows) {
    for (PhaseWindow window : windows) {
      if (localFrame >= window.startFrame && localFrame < window.endFrame) {
        return window.phase;
      }
    }
    if (windows.isEmpty()) {
      return "apply_gate";
    }
    return windows.get(windows.size() - 1).phase;
  }

  PhaseWindow findActivePhaseWindow(int localFrame, ArrayList<PhaseWindow> windows) {
    if (windows == null || windows.isEmpty()) {
      return null;
    }
    for (PhaseWindow window : windows) {
      if (localFrame >= window.startFrame && localFrame < window.endFrame) {
        return window;
      }
    }
    return windows.get(windows.size() - 1);
  }

  FrameSample resolveSampleForStep(TraceStep step, float tNormalized, String phase) {
    if (step.evolutionSamples == null || step.evolutionSamples.isEmpty()) {
      return fallbackSample(step, phase, tNormalized);
    }

    ArrayList<EvolutionSample> samples = step.evolutionSamples;
    if (samples.size() == 1) {
      return copySample(samples.get(0), phase, tNormalized);
    }

    int upper = 0;
    while (upper < samples.size() && samples.get(upper).tNormalized < tNormalized) {
      upper += 1;
    }

    FrameSample resolved = null;
    if (upper <= 0) {
      resolved = copySample(samples.get(0), phase, tNormalized);
    } else if (upper >= samples.size()) {
      resolved = copySample(samples.get(samples.size() - 1), phase, tNormalized);
    } else {
      int lower = upper - 1;
      EvolutionSample a = samples.get(lower);
      EvolutionSample b = samples.get(upper);

      float span = max(1e-8, b.tNormalized - a.tNormalized);
      float alpha = clampFloat((tNormalized - a.tNormalized) / span, 0.0, 1.0);

      if (alpha <= 1e-6) {
        resolved = copySample(a, phase, tNormalized);
      } else if (alpha >= 1.0 - 1e-6) {
        resolved = copySample(b, phase, tNormalized);
      } else {
        resolved = interpolateSamples(a, b, alpha, phase, tNormalized);
      }
    }

    EvolutionSample matrixSource = resolveNearestEvolutionSample(step, tNormalized, phase);
    if (matrixSource != null) {
      resolved.reducedDensityBlocks = copyReducedDensityBlocks(matrixSource.reducedDensityBlocks);
      resolved.gateMatrix = copyGateMatrixSample(matrixSource.gateMatrix);
    }
    return resolved;
  }

  FrameSample fallbackSample(TraceStep step, String phase, float tNormalized) {
    String hash = step.gateEndHash.length() > 0 ? step.gateEndHash : step.gateStartHash;
    FrameSample sample = new FrameSample(phase, tNormalized, hash);

    for (String key : step.amplitudes.keySet()) {
      AmplitudeSample src = step.amplitudes.get(key);
      sample.amplitudes.put(key, new AmplitudeSample(src.basis, src.magnitude, src.phase));
    }

    for (String key : step.probabilities.keySet()) {
      ProbabilitySample src = step.probabilities.get(key);
      sample.probabilities.put(key, new ProbabilitySample(src.basis, src.probability));
    }

    return sample;
  }

  FrameSample copySample(EvolutionSample source, String phase, float tNormalized) {
    FrameSample sample = new FrameSample(phase, tNormalized, source.stateHash);

    for (String key : source.amplitudes.keySet()) {
      AmplitudeSample src = source.amplitudes.get(key);
      sample.amplitudes.put(key, new AmplitudeSample(src.basis, src.magnitude, src.phase));
    }

    for (String key : source.probabilities.keySet()) {
      ProbabilitySample src = source.probabilities.get(key);
      sample.probabilities.put(key, new ProbabilitySample(src.basis, src.probability));
    }

    for (ReducedDensitySample block : source.reducedDensityBlocks) {
      ReducedDensitySample copied = copyReducedDensityBlock(block);
      if (copied != null) {
        sample.reducedDensityBlocks.add(copied);
      }
    }

    sample.gateMatrix = copyGateMatrixSample(source.gateMatrix);

    return sample;
  }

  FrameSample interpolateSamples(
    EvolutionSample a,
    EvolutionSample b,
    float alpha,
    String phase,
    float tNormalized
  ) {
    FrameSample out = new FrameSample(phase, tNormalized, alpha < 0.5 ? a.stateHash : b.stateHash);

    HashSet<String> amplitudeKeys = new HashSet<String>();
    amplitudeKeys.addAll(a.amplitudes.keySet());
    amplitudeKeys.addAll(b.amplitudes.keySet());

    for (String key : amplitudeKeys) {
      AmplitudeSample aValue = a.amplitudes.get(key);
      AmplitudeSample bValue = b.amplitudes.get(key);

      float aMagnitude = aValue != null ? aValue.magnitude : 0.0;
      float bMagnitude = bValue != null ? bValue.magnitude : 0.0;
      float aPhase = aValue != null ? aValue.phase : (bValue != null ? bValue.phase : 0.0);
      float bPhase = bValue != null ? bValue.phase : aPhase;

      out.amplitudes.put(
        key,
        new AmplitudeSample(
          key,
          lerp(aMagnitude, bMagnitude, alpha),
          interpolateAngle(aPhase, bPhase, alpha)
        )
      );
    }

    HashSet<String> probabilityKeys = new HashSet<String>();
    probabilityKeys.addAll(a.probabilities.keySet());
    probabilityKeys.addAll(b.probabilities.keySet());

    for (String key : probabilityKeys) {
      ProbabilitySample aValue = a.probabilities.get(key);
      ProbabilitySample bValue = b.probabilities.get(key);

      float aProbability = aValue != null ? aValue.probability : 0.0;
      float bProbability = bValue != null ? bValue.probability : 0.0;
      out.probabilities.put(
        key,
        new ProbabilitySample(key, clampFloat(lerp(aProbability, bProbability, alpha), 0.0, 1.0))
      );
    }

    out.reducedDensityBlocks = interpolateDensityBlocks(a.reducedDensityBlocks, b.reducedDensityBlocks, alpha);
    out.gateMatrix = interpolateGateMatrixSamples(a.gateMatrix, b.gateMatrix, alpha);
    return out;
  }

  FrameSample interpolateFrameSamples(
    FrameSample a,
    FrameSample b,
    float alpha,
    String phase,
    float tNormalized
  ) {
    if (a == null && b == null) {
      return null;
    }
    if (a == null) {
      return copyFrameSample(b, phase, tNormalized);
    }
    if (b == null) {
      return copyFrameSample(a, phase, tNormalized);
    }

    float safeAlpha = clampFloat(alpha, 0.0, 1.0);
    FrameSample out = new FrameSample(phase, tNormalized, safeAlpha < 0.5 ? a.stateHash : b.stateHash);

    HashSet<String> amplitudeKeys = new HashSet<String>();
    amplitudeKeys.addAll(a.amplitudes.keySet());
    amplitudeKeys.addAll(b.amplitudes.keySet());
    for (String key : amplitudeKeys) {
      AmplitudeSample aValue = a.amplitudes.get(key);
      AmplitudeSample bValue = b.amplitudes.get(key);
      float aMagnitude = aValue != null ? aValue.magnitude : 0.0;
      float bMagnitude = bValue != null ? bValue.magnitude : 0.0;
      float aPhase = aValue != null ? aValue.phase : (bValue != null ? bValue.phase : 0.0);
      float bPhase = bValue != null ? bValue.phase : aPhase;
      out.amplitudes.put(
        key,
        new AmplitudeSample(
          key,
          lerp(aMagnitude, bMagnitude, safeAlpha),
          interpolateAngle(aPhase, bPhase, safeAlpha)
        )
      );
    }

    HashSet<String> probabilityKeys = new HashSet<String>();
    probabilityKeys.addAll(a.probabilities.keySet());
    probabilityKeys.addAll(b.probabilities.keySet());
    for (String key : probabilityKeys) {
      ProbabilitySample aValue = a.probabilities.get(key);
      ProbabilitySample bValue = b.probabilities.get(key);
      float aProbability = aValue != null ? aValue.probability : 0.0;
      float bProbability = bValue != null ? bValue.probability : 0.0;
      out.probabilities.put(
        key,
        new ProbabilitySample(key, clampFloat(lerp(aProbability, bProbability, safeAlpha), 0.0, 1.0))
      );
    }

    out.reducedDensityBlocks = interpolateDensityBlocks(a.reducedDensityBlocks, b.reducedDensityBlocks, safeAlpha);
    out.gateMatrix = interpolateGateMatrixSamples(a.gateMatrix, b.gateMatrix, safeAlpha);
    return out;
  }

  FrameSample copyFrameSample(FrameSample source, String phase, float tNormalized) {
    if (source == null) {
      return null;
    }
    FrameSample copy = new FrameSample(phase, tNormalized, source.stateHash);
    for (String key : source.amplitudes.keySet()) {
      AmplitudeSample src = source.amplitudes.get(key);
      copy.amplitudes.put(key, new AmplitudeSample(src.basis, src.magnitude, src.phase));
    }
    for (String key : source.probabilities.keySet()) {
      ProbabilitySample src = source.probabilities.get(key);
      copy.probabilities.put(key, new ProbabilitySample(src.basis, src.probability));
    }
    copy.reducedDensityBlocks = copyReducedDensityBlocks(source.reducedDensityBlocks);
    copy.gateMatrix = copyGateMatrixSample(source.gateMatrix);
    return copy;
  }

  ArrayList<ReducedDensitySample> copyReducedDensityBlocks(ArrayList<ReducedDensitySample> blocks) {
    ArrayList<ReducedDensitySample> copied = new ArrayList<ReducedDensitySample>();
    if (blocks == null) {
      return copied;
    }
    for (ReducedDensitySample block : blocks) {
      ReducedDensitySample cloned = copyReducedDensityBlock(block);
      if (cloned != null) {
        copied.add(cloned);
      }
    }
    return copied;
  }

  EvolutionSample resolveNearestEvolutionSample(TraceStep step, float tNormalized, String phase) {
    if (step == null || step.evolutionSamples == null || step.evolutionSamples.isEmpty()) {
      return null;
    }

    EvolutionSample best = null;
    float bestScore = Float.MAX_VALUE;
    for (EvolutionSample candidate : step.evolutionSamples) {
      float phasePenalty = candidate.phase.equals(phase) ? 0.0 : 1.0;
      float score = phasePenalty * 2.0 + abs(candidate.tNormalized - tNormalized);
      if (best == null || score < bestScore) {
        best = candidate;
        bestScore = score;
      }
    }
    return best;
  }

  EvolutionSample resolvePreviousEvolutionSample(TraceStep step, EvolutionSample reference) {
    if (step == null || reference == null || step.evolutionSamples == null || step.evolutionSamples.isEmpty()) {
      return null;
    }
    ArrayList<EvolutionSample> samples = step.evolutionSamples;
    for (int i = 0; i < samples.size(); i += 1) {
      if (samples.get(i) == reference) {
        if (i == 0) {
          return reference;
        }
        return samples.get(i - 1);
      }
    }
    return reference;
  }

  ArrayList<ReducedDensitySample> interpolateDensityBlocks(
    ArrayList<ReducedDensitySample> aBlocks,
    ArrayList<ReducedDensitySample> bBlocks,
    float alpha
  ) {
    HashMap<String, ReducedDensitySample> aByKey = new HashMap<String, ReducedDensitySample>();
    HashMap<String, ReducedDensitySample> bByKey = new HashMap<String, ReducedDensitySample>();

    for (ReducedDensitySample block : aBlocks) {
      aByKey.put(block.qubitKey, block);
    }
    for (ReducedDensitySample block : bBlocks) {
      bByKey.put(block.qubitKey, block);
    }

    HashSet<String> allKeys = new HashSet<String>();
    allKeys.addAll(aByKey.keySet());
    allKeys.addAll(bByKey.keySet());

    ArrayList<ReducedDensitySample> merged = new ArrayList<ReducedDensitySample>();
    for (String key : allKeys) {
      ReducedDensitySample aBlock = aByKey.get(key);
      ReducedDensitySample bBlock = bByKey.get(key);

      if (aBlock == null) {
        ReducedDensitySample copied = copyReducedDensityBlock(bBlock);
        if (copied != null) {
          merged.add(copied);
        }
        continue;
      }
      if (bBlock == null) {
        ReducedDensitySample copied = copyReducedDensityBlock(aBlock);
        if (copied != null) {
          merged.add(copied);
        }
        continue;
      }

      if (aBlock.real.length != bBlock.real.length || aBlock.real.length == 0) {
        merged.add(alpha < 0.5 ? copyReducedDensityBlock(aBlock) : copyReducedDensityBlock(bBlock));
        continue;
      }

      int rows = aBlock.real.length;
      int cols = aBlock.real[0].length;
      float[][] real = new float[rows][cols];
      float[][] imag = new float[rows][cols];

      for (int row = 0; row < rows; row += 1) {
        for (int col = 0; col < cols; col += 1) {
          real[row][col] = lerp(aBlock.real[row][col], bBlock.real[row][col], alpha);
          imag[row][col] = lerp(aBlock.imag[row][col], bBlock.imag[row][col], alpha);
        }
      }

      merged.add(new ReducedDensitySample(aBlock.qubits, real, imag));
    }

    return merged;
  }

  ReducedDensitySample copyReducedDensityBlock(ReducedDensitySample source) {
    if (source == null) {
      return null;
    }

    int[] qubits = new int[source.qubits.length];
    arrayCopy(source.qubits, qubits);

    int rows = source.real.length;
    int cols = rows > 0 ? source.real[0].length : 0;
    float[][] real = new float[rows][cols];
    float[][] imag = new float[rows][cols];

    for (int row = 0; row < rows; row += 1) {
      for (int col = 0; col < cols; col += 1) {
        real[row][col] = source.real[row][col];
        imag[row][col] = source.imag[row][col];
      }
    }

    return new ReducedDensitySample(qubits, real, imag);
  }

  GateMatrixSample copyGateMatrixSample(GateMatrixSample source) {
    if (source == null) {
      return null;
    }

    int[] qubits = new int[source.qubits.length];
    arrayCopy(source.qubits, qubits);

    int rows = source.real.length;
    int cols = rows > 0 ? source.real[0].length : 0;
    float[][] real = new float[rows][cols];
    float[][] imag = new float[rows][cols];

    for (int row = 0; row < rows; row += 1) {
      for (int col = 0; col < cols; col += 1) {
        real[row][col] = source.real[row][col];
        imag[row][col] = source.imag[row][col];
      }
    }

    return new GateMatrixSample(source.gateName, qubits, real, imag);
  }

  GateMatrixSample interpolateGateMatrixSamples(GateMatrixSample a, GateMatrixSample b, float alpha) {
    if (a == null && b == null) {
      return null;
    }
    if (a == null) {
      return copyGateMatrixSample(b);
    }
    if (b == null) {
      return copyGateMatrixSample(a);
    }

    if (!sameMatrixShape(a, b) || !a.gateName.equals(b.gateName) || !a.qubitKey.equals(b.qubitKey)) {
      return alpha < 0.5 ? copyGateMatrixSample(a) : copyGateMatrixSample(b);
    }

    int rows = a.real.length;
    int cols = a.real[0].length;
    float[][] real = new float[rows][cols];
    float[][] imag = new float[rows][cols];
    for (int row = 0; row < rows; row += 1) {
      for (int col = 0; col < cols; col += 1) {
        real[row][col] = lerp(a.real[row][col], b.real[row][col], alpha);
        imag[row][col] = lerp(a.imag[row][col], b.imag[row][col], alpha);
      }
    }

    int[] qubits = new int[a.qubits.length];
    arrayCopy(a.qubits, qubits);
    return new GateMatrixSample(a.gateName, qubits, real, imag);
  }

  boolean sameMatrixShape(GateMatrixSample a, GateMatrixSample b) {
    if (a.real.length == 0 || b.real.length == 0 || a.real.length != b.real.length) {
      return false;
    }

    if (a.real[0].length == 0 || b.real[0].length == 0 || a.real[0].length != b.real[0].length) {
      return false;
    }

    for (int row = 0; row < a.real.length; row += 1) {
      if (a.real[row].length != b.real[row].length || a.imag[row].length != b.imag[row].length) {
        return false;
      }
    }

    return true;
  }

  float interpolateAngle(float a, float b, float alpha) {
    float delta = b - a;
    while (delta > PI) {
      delta -= TWO_PI;
    }
    while (delta < -PI) {
      delta += TWO_PI;
    }
    return a + delta * alpha;
  }
}
