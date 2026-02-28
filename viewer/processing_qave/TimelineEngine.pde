/*
Purpose: Resolve step/phase timeline progression and frame-index state.
Inputs: Shared playback state, trace-derived models, pane metrics, and user interaction state.
Outputs: Deterministic frame-local rendering updates and synchronized visual state transitions.
Determinism/Timing: Uses timeline phases (pre_gate/apply_gate/settle) and fixed frame progression for reproducible output.
*/

class TimelineEngine {
  TraceModel traceModel;
  int frameIndex = 0;
  boolean playing = true;
  float speed = 1.0;
  float speedAccumulator = 0.0;
  boolean loopEnabled = false;
  int loopIn = 0;
  int loopOut = 0;

  TimelineEngine(TraceModel traceModel) {
    setTrace(traceModel);
  }

  void setTrace(TraceModel traceModel) {
    this.traceModel = traceModel;
    frameIndex = 0;
    speedAccumulator = 0;
    loopIn = 0;
    loopOut = max(0, traceModel.totalFrames - 1);
  }

  void setPlaying(boolean playing) {
    this.playing = playing;
  }

  void togglePlaying() {
    playing = !playing;
  }

  void setSpeed(float speed) {
    this.speed = normalizeSpeed(speed);
  }

  void setLoopEnabled(boolean enabled) {
    loopEnabled = enabled;
    if (loopOut < loopIn) {
      loopOut = loopIn;
    }
  }

  void setLoopIn(int newLoopIn) {
    loopIn = clampFrame(newLoopIn);
    if (loopOut < loopIn) {
      loopOut = loopIn;
    }
  }

  void setLoopOut(int newLoopOut) {
    loopOut = clampFrame(newLoopOut);
    if (loopOut < loopIn) {
      loopIn = loopOut;
    }
  }

  void jumpToFrame(int newFrameIndex) {
    frameIndex = clampFrame(newFrameIndex);
  }

  void jumpToStep(int stepIndex) {
    int index = clampInt(stepIndex, 0, max(0, traceModel.stepCount - 1));
    jumpToFrame(index * max(1, traceModel.framesPerStep));
  }

  void stepForward() {
    PlaybackState state = currentFrameState();
    if (traceModel.hasShotReplay() && traceModel.isShotReplayPhase(state.phase)) {
      if ("shot_camera_pullback".equals(state.phase)) {
        jumpToFrame(traceModel.frameForStackShotIndex(0));
      } else if ("shot_stack".equals(state.phase)) {
        int nextShot = state.shotIndex < 0
          ? 0
          : min(max(0, state.shotsTotal - 1), state.shotIndex + 1);
        if (state.shotIndex >= max(0, state.shotsTotal - 1)) {
          jumpToFrame(traceModel.shotProjectTransitionStartFrame());
        } else {
          jumpToFrame(traceModel.frameForStackShotIndex(nextShot));
        }
      } else if ("shot_histogram_project".equals(state.phase)) {
        if (state.shotIndex < 0) {
          jumpToFrame(traceModel.frameForProjectShotIndex(0));
        } else if (state.shotIndex < max(0, state.shotsTotal - 1)) {
          jumpToFrame(traceModel.frameForProjectShotIndex(state.shotIndex + 1));
        } else {
          jumpToFrame(max(0, traceModel.totalFrames - 1));
        }
      }
      return;
    }
    int nextStep = min(max(0, traceModel.stepCount - 1), state.stepIndex + 1);
    jumpToStep(nextStep);
  }

  void stepBackward() {
    PlaybackState state = currentFrameState();
    if (traceModel.hasShotReplay() && traceModel.isShotReplayPhase(state.phase)) {
      if ("shot_histogram_project".equals(state.phase) && state.shotIndex > 0) {
        jumpToFrame(traceModel.frameForProjectShotIndex(state.shotIndex - 1));
      } else if ("shot_histogram_project".equals(state.phase) && state.shotIndex == 0) {
        jumpToFrame(traceModel.shotProjectTransitionStartFrame());
      } else if ("shot_histogram_project".equals(state.phase)) {
        jumpToFrame(traceModel.frameForStackShotIndex(max(0, state.shotsTotal - 1)));
      } else if ("shot_stack".equals(state.phase) && state.shotIndex > 0) {
        jumpToFrame(traceModel.frameForStackShotIndex(state.shotIndex - 1));
      } else if ("shot_stack".equals(state.phase)) {
        jumpToFrame(max(0, traceModel.shotStackStartFrame() - 1));
      } else {
        jumpToFrame(max(0, traceModel.shotReplayStartFrame() - 1));
      }
      return;
    }
    int prevStep = max(0, state.stepIndex - 1);
    jumpToStep(prevStep);
  }

  void advance() {
    if (!playing || traceModel.totalFrames <= 1) {
      return;
    }

    speedAccumulator += speed;
    int increments = floor(speedAccumulator);
    if (increments <= 0) {
      return;
    }
    speedAccumulator -= increments;

    while (increments > 0) {
      incrementFrame();
      increments -= 1;
    }
  }

  PlaybackState currentFrameState() {
    return traceModel.frameState(frameIndex);
  }

  int clampFrame(int value) {
    return clampInt(value, 0, max(0, traceModel.totalFrames - 1));
  }

  void incrementFrame() {
    int next = frameIndex + 1;
    int maxFrame = max(0, traceModel.totalFrames - 1);

    if (loopEnabled) {
      if (next > loopOut) {
        next = loopIn;
      }
    } else if (next > maxFrame) {
      next = maxFrame;
      playing = false;
    }

    frameIndex = clampFrame(next);
  }
}
