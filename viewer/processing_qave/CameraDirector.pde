/*
Purpose: Resolve camera pose, focus, and distance for deterministic scene framing.
Inputs: Shared playback state, trace-derived models, pane metrics, and user interaction state.
Outputs: Deterministic frame-local rendering updates and synchronized visual state transitions.
Determinism/Timing: Uses timeline phases (pre_gate/apply_gate/settle) and fixed frame progression for reproducible output.
*/

class CameraPoseState {
  float rotateXDeg;
  float rotateYDeg;
  float rotateZDeg;
  float zoom;
  float panXNorm;
  float panYNorm;

  CameraPoseState(
    float rotateXDeg,
    float rotateYDeg,
    float rotateZDeg,
    float zoom,
    float panXNorm,
    float panYNorm
  ) {
    this.rotateXDeg = rotateXDeg;
    this.rotateYDeg = rotateYDeg;
    this.rotateZDeg = rotateZDeg;
    this.zoom = zoom;
    this.panXNorm = panXNorm;
    this.panYNorm = panYNorm;
  }
}

// Class ProjectedSpan encapsulates module-specific viewer behavior.
class ProjectedSpan {
  float width;
  float height;
  float depth;

  ProjectedSpan(float width, float height, float depth) {
    this.width = max(1.0, width);
    this.height = max(1.0, height);
    this.depth = max(1.0, depth);
  }
}

// Class OccupancyEnvelope encapsulates module-specific viewer behavior.
class OccupancyEnvelope {
  float minW;
  float maxW;
  float minH;
  float maxH;

  OccupancyEnvelope(float minW, float maxW, float minH, float maxH) {
    this.minW = minW;
    this.maxW = maxW;
    this.minH = minH;
    this.maxH = maxH;
  }
}

// Class CameraDirector encapsulates module-specific viewer behavior.
class CameraDirector {
  PApplet app;
  PeasyCam cam;

  final CameraPoseState LOCKED_CONV_POSE = new CameraPoseState(0.0, -20.0, 0.0, 1.00, 0.0, 0.0);
  final CameraPoseState DRIFT_PRIMARY = new CameraPoseState(0.22, 0.16, 0.26, 0.010, 0.0032, 0.0022);
  final CameraPoseState DRIFT_SECONDARY = new CameraPoseState(0.08, 0.06, 0.10, 0.004, 0.0013, 0.0011);
  final CameraPoseState SHOT_PULLBACK_POSE = new CameraPoseState(40, -10.0, 0.0, 3., 0.0, 0.0);
  final CameraPoseState SHOT_STACK_POSE = new CameraPoseState(20, -10.0, 0.0, 3, 0.0, -0.1);
  final CameraPoseState SHOT_DRIFT_PRIMARY = new CameraPoseState(0.14, 0.09, 0.08, 0.0035, 0.0011, 0.0007);
  final CameraPoseState SHOT_DRIFT_SECONDARY = new CameraPoseState(0.05, 0.03, 0.04, 0.0015, 0.0006, 0.0004);
  final CameraPoseState SHOT_STACK_BREATH = new CameraPoseState(0.20, 0.0, 0.10, 0.012, 0.0012, 0.0010);
  final float SHOT_PROJECT_CAMERA_HOLD_FRACTION = 0.50;
  final float SHOT_QUBIT_MIN_HIST_GAP = 14.0;
  final float SHOT_QUBIT_HIST_GAP_CUBE_MULT = 0.95;
  final float SHOT_REPLAY_LAYER_GAP_SCALE = 10.0;
  final float SHOT_QUBIT_CUBE_SIZE_RATIO = 0.64;
  final float SHOT_QUBIT_CUBE_MIN_SIZE = 8.0;
  final float SHOT_QUBIT_CUBE_MAX_SIZE = 26.0;
  final float SHOT_REPLAY_DEPTH_BLEND = 0.30;
  final int SHOT_STACK_SOFT_CAP_LINEAR_LAYERS = 24;
  final float SHOT_STACK_TAIL_COMPRESS_RATIO = 0.28;
  final float SHOT_STACK_DEPTH_BASE_MULT = 0.58;
  final float SHOT_STACK_DEPTH_BASE_MIN = 5.0;
  final float SHOT_STACK_DEPTH_BASE_MAX = 18.0;

  final float LOOKAT_CENTER_DAMP = 0.18;
  final float LOOKAT_DEPTH_DAMP = 0.18;
  final float LOOKAT_DISTANCE_DAMP = 0.16;
  final float ROTATION_DAMP = 0.14;
  final float ZOOM_DAMP = 0.14;
  final float PAN_DAMP = 0.16;
  final int FRAME_JUMP_REANCHOR_THRESHOLD = 3;

  final float OCCUPANCY_MIN_W = 0.42;
  final float OCCUPANCY_MAX_W = 0.50;
  final float OCCUPANCY_MIN_H = 0.46;
  final float OCCUPANCY_MAX_H = 0.56;
  final float REPLAY_OCC_PULLBACK_MIN_W = 0.46;
  final float REPLAY_OCC_PULLBACK_MAX_W = 0.60;
  final float REPLAY_OCC_PULLBACK_MIN_H = 0.34;
  final float REPLAY_OCC_PULLBACK_MAX_H = 0.56;
  final float REPLAY_OCC_STACK_MIN_W = 0.40;
  final float REPLAY_OCC_STACK_MAX_W = 0.52;
  final float REPLAY_OCC_STACK_MIN_H = 0.28;
  final float REPLAY_OCC_STACK_MAX_H = 0.46;
  final float REPLAY_DISTANCE_SOLVE_BIAS = 0.22;

  boolean smoothingInitialized = false;
  float smoothedCenterX = 0.0;
  float smoothedCenterY = 0.0;
  float smoothedCenterZ = 0.0;
  double smoothedDistance = 0.0;
  float smoothedRotateXDeg = 0.0;
  float smoothedRotateYDeg = 0.0;
  float smoothedRotateZDeg = 0.0;
  float smoothedZoom = 1.0;
  float smoothedPanXNorm = 0.0;
  float smoothedPanYNorm = 0.0;
  int lastFrameIndex = -1;
  TraceModel lastTraceModel = null;

  CameraDirector(PApplet app, PeasyCam cam) {
    this.app = app;
    this.cam = cam;
  }

  void configure() {
    cam.setActive(false);
    cam.setMinimumDistance(180);
    cam.setMaximumDistance(12000);
    resetSmoothing();
  }

  void resetSmoothing() {
    smoothingInitialized = false;
    smoothedCenterX = 0.0;
    smoothedCenterY = 0.0;
    smoothedCenterZ = 0.0;
    smoothedDistance = 0.0;
    smoothedRotateXDeg = 0.0;
    smoothedRotateYDeg = 0.0;
    smoothedRotateZDeg = 0.0;
    smoothedZoom = 1.0;
    smoothedPanXNorm = 0.0;
    smoothedPanYNorm = 0.0;
    lastFrameIndex = -1;
  }

  void apply(PlaybackState playback, MatrixViewMetrics metrics, TraceModel traceModel) {
    if (playback == null || metrics == null) {
      return;
    }

    if (traceModel != lastTraceModel) {
      resetSmoothing();
      lastTraceModel = traceModel;
    }

    CameraPoseState targetPose = resolvePose(playback);
    float targetFocusZ = resolveFocusZ(playback, metrics);
    boolean frameJumped = detectFrameJump(playback.frameIndex);
    if (!smoothingInitialized || frameJumped) {
      anchorToPose(targetPose, metrics, playback, traceModel, targetFocusZ);
    } else {
      smoothPoseTowards(targetPose);
      smoothLookAt(metrics, playback, traceModel, targetFocusZ);
    }

    cam.lookAt(smoothedCenterX, smoothedCenterY, smoothedCenterZ, smoothedDistance, 0);
    cam.setRotations(
      radians(smoothedRotateXDeg),
      radians(smoothedRotateYDeg),
      radians(smoothedRotateZDeg)
    );
  }

  boolean detectFrameJump(int frameIndex) {
    if (lastFrameIndex < 0) {
      lastFrameIndex = frameIndex;
      return false;
    }

    int delta = abs(frameIndex - lastFrameIndex);
    lastFrameIndex = frameIndex;
    return delta > FRAME_JUMP_REANCHOR_THRESHOLD;
  }

  void anchorToPose(
    CameraPoseState pose,
    MatrixViewMetrics metrics,
    PlaybackState playback,
    TraceModel traceModel,
    float targetFocusZ
  ) {
    smoothedRotateXDeg = pose.rotateXDeg;
    smoothedRotateYDeg = pose.rotateYDeg;
    smoothedRotateZDeg = pose.rotateZDeg;
    smoothedZoom = pose.zoom;
    smoothedPanXNorm = pose.panXNorm;
    smoothedPanYNorm = pose.panYNorm;

    smoothedCenterX = metrics.centerX + smoothedPanXNorm * metrics.matrixW;
    smoothedCenterY = metrics.centerY + smoothedPanYNorm * metrics.matrixH;
    smoothedCenterZ = targetFocusZ;
    smoothedDistance = resolveDistance(metrics, smoothedPose(), playback, traceModel, smoothedCenterZ);
    smoothingInitialized = true;
  }

  void smoothPoseTowards(CameraPoseState pose) {
    smoothedRotateXDeg = lerp(smoothedRotateXDeg, pose.rotateXDeg, ROTATION_DAMP);
    smoothedRotateYDeg = lerp(smoothedRotateYDeg, pose.rotateYDeg, ROTATION_DAMP);
    smoothedRotateZDeg = lerp(smoothedRotateZDeg, pose.rotateZDeg, ROTATION_DAMP);
    smoothedZoom = lerp(smoothedZoom, pose.zoom, ZOOM_DAMP);
    smoothedPanXNorm = lerp(smoothedPanXNorm, pose.panXNorm, PAN_DAMP);
    smoothedPanYNorm = lerp(smoothedPanYNorm, pose.panYNorm, PAN_DAMP);
  }

  void smoothLookAt(MatrixViewMetrics metrics, PlaybackState playback, TraceModel traceModel, float targetFocusZ) {
    float targetCenterX = metrics.centerX + smoothedPanXNorm * metrics.matrixW;
    float targetCenterY = metrics.centerY + smoothedPanYNorm * metrics.matrixH;
    double targetDistance = resolveDistance(metrics, smoothedPose(), playback, traceModel, targetFocusZ);

    smoothedCenterX = lerp(smoothedCenterX, targetCenterX, LOOKAT_CENTER_DAMP);
    smoothedCenterY = lerp(smoothedCenterY, targetCenterY, LOOKAT_CENTER_DAMP);
    smoothedCenterZ = lerp(smoothedCenterZ, targetFocusZ, LOOKAT_DEPTH_DAMP);
    smoothedDistance += (targetDistance - smoothedDistance) * LOOKAT_DISTANCE_DAMP;
  }

  CameraPoseState smoothedPose() {
    return new CameraPoseState(
      smoothedRotateXDeg,
      smoothedRotateYDeg,
      smoothedRotateZDeg,
      smoothedZoom,
      smoothedPanXNorm,
      smoothedPanYNorm
    );
  }

  CameraPoseState resolvePose(PlaybackState playback) {
    if (playback == null) {
      return resolveGatePose(0.0);
    }

    CameraPoseState gatePose = resolveGatePose(playback.timelineProgressGlobal);
    if ("shot_camera_pullback".equals(playback.phase)) {
      return lerpPose(gatePose, SHOT_STACK_POSE, easeInOutSine01(playback.phaseProgress));
    }
    if ("shot_histogram_project".equals(playback.phase)) {
      if (playback.shotIndex < 0) {
        CameraPoseState drifted = addPose(SHOT_STACK_POSE, resolveShotStackDrift(playback.timelineProgressGlobal));
        float alpha = resolveShotProjectMoveAlpha(playback.phaseProgress);
        return lerpPose(drifted, SHOT_STACK_POSE, alpha);
      }
      return SHOT_STACK_POSE;
    }
    if ("shot_stack".equals(playback.phase)) {
      CameraPoseState drifted = addPose(SHOT_STACK_POSE, resolveShotStackDrift(playback.timelineProgressGlobal));
      return addPose(drifted, resolveShotStackBreath(playback.shotProgress));
    }
    return gatePose;
  }

  float resolveFocusZ(PlaybackState playback, MatrixViewMetrics metrics) {
    if (playback == null || metrics == null || !playback.inShotReplay) {
      return 0.0;
    }

    float qubitFocusZ = shotReplayQubitFrontZ(metrics);
    float histogramFocusZ = shotReplayHistogramFrontZ(metrics);
    if ("shot_camera_pullback".equals(playback.phase)) {
      return lerp(0.0, qubitFocusZ, easeInOutSine01(playback.phaseProgress));
    }
    if ("shot_histogram_project".equals(playback.phase)) {
      if (playback.shotIndex < 0) {
        float alpha = resolveShotProjectMoveAlpha(playback.phaseProgress);
        return lerp(qubitFocusZ, histogramFocusZ, alpha);
      }
      return histogramFocusZ;
    }
    if ("shot_stack".equals(playback.phase)) {
      return qubitFocusZ;
    }
    return qubitFocusZ;
  }

  float resolveShotProjectMoveAlpha(float phaseProgress) {
    float eased = easeInOutSine01(phaseProgress);
    if (eased <= SHOT_PROJECT_CAMERA_HOLD_FRACTION) {
      return 0.0;
    }
    float denom = max(1e-5, 1.0 - SHOT_PROJECT_CAMERA_HOLD_FRACTION);
    return clampFloat((eased - SHOT_PROJECT_CAMERA_HOLD_FRACTION) / denom, 0.0, 1.0);
  }

  CameraPoseState resolveGatePose(float timelineProgressGlobal) {
    float t = clampFloat(timelineProgressGlobal, 0.0, 1.0);
    float theta = TWO_PI * t;
    float primary = sin(theta);
    float secondary = sin(theta * 2.0);

    CameraPoseState drift = new CameraPoseState(
      DRIFT_PRIMARY.rotateXDeg * primary + DRIFT_SECONDARY.rotateXDeg * secondary,
      DRIFT_PRIMARY.rotateYDeg * primary + DRIFT_SECONDARY.rotateYDeg * secondary,
      DRIFT_PRIMARY.rotateZDeg * primary + DRIFT_SECONDARY.rotateZDeg * secondary,
      DRIFT_PRIMARY.zoom * primary + DRIFT_SECONDARY.zoom * secondary,
      DRIFT_PRIMARY.panXNorm * primary + DRIFT_SECONDARY.panXNorm * secondary,
      DRIFT_PRIMARY.panYNorm * primary + DRIFT_SECONDARY.panYNorm * secondary
    );
    return addPose(LOCKED_CONV_POSE, drift);
  }

  CameraPoseState resolveShotStackDrift(float timelineProgressGlobal) {
    float t = clampFloat(timelineProgressGlobal, 0.0, 1.0);
    float theta = TWO_PI * t;
    float primary = sin(theta);
    float secondary = sin(theta * 2.0 + HALF_PI * 0.5);
    return new CameraPoseState(
      SHOT_DRIFT_PRIMARY.rotateXDeg * primary + SHOT_DRIFT_SECONDARY.rotateXDeg * secondary,
      SHOT_DRIFT_PRIMARY.rotateYDeg * primary + SHOT_DRIFT_SECONDARY.rotateYDeg * secondary,
      SHOT_DRIFT_PRIMARY.rotateZDeg * primary + SHOT_DRIFT_SECONDARY.rotateZDeg * secondary,
      SHOT_DRIFT_PRIMARY.zoom * primary + SHOT_DRIFT_SECONDARY.zoom * secondary,
      SHOT_DRIFT_PRIMARY.panXNorm * primary + SHOT_DRIFT_SECONDARY.panXNorm * secondary,
      SHOT_DRIFT_PRIMARY.panYNorm * primary + SHOT_DRIFT_SECONDARY.panYNorm * secondary
    );
  }

  CameraPoseState resolveShotStackBreath(float shotProgress) {
    float pulse = sin(PI * clampFloat(shotProgress, 0.0, 1.0));
    return new CameraPoseState(
      SHOT_STACK_BREATH.rotateXDeg * pulse,
      SHOT_STACK_BREATH.rotateYDeg * pulse,
      SHOT_STACK_BREATH.rotateZDeg * pulse,
      SHOT_STACK_BREATH.zoom * pulse,
      SHOT_STACK_BREATH.panXNorm * pulse,
      SHOT_STACK_BREATH.panYNorm * pulse
    );
  }

  float easeInOutSine01(float value) {
    float x = clampFloat(value, 0.0, 1.0);
    return -(cos(PI * x) - 1.0) * 0.5;
  }

  CameraPoseState lerpPose(CameraPoseState a, CameraPoseState b, float t) {
    float alpha = clampFloat(t, 0.0, 1.0);
    return new CameraPoseState(
      lerp(a.rotateXDeg, b.rotateXDeg, alpha),
      lerp(a.rotateYDeg, b.rotateYDeg, alpha),
      lerp(a.rotateZDeg, b.rotateZDeg, alpha),
      lerp(a.zoom, b.zoom, alpha),
      lerp(a.panXNorm, b.panXNorm, alpha),
      lerp(a.panYNorm, b.panYNorm, alpha)
    );
  }

  double resolveDistance(
    MatrixViewMetrics metrics,
    CameraPoseState pose,
    PlaybackState playback,
    TraceModel traceModel,
    float focusZ
  ) {
    float depthBudget = max(1.0, metrics.stackDepthEstimate);
    if (playback != null && playback.inShotReplay) {
      depthBudget = max(depthBudget, resolveReplayDepthBudget(metrics, playback, traceModel, focusZ));
    }
    ProjectedSpan projectedSpan = resolveProjectedSpan(metrics, pose, depthBudget);
    float aspect = max(0.1, app.width / float(max(1, app.height)));
    float vFov = PI / 3.0;
    float hFov = 2.0 * atan(tan(vFov * 0.5) * aspect);
    float tanHFov = max(1e-4, tan(hFov * 0.5));
    float tanVFov = max(1e-4, tan(vFov * 0.5));
    OccupancyEnvelope occupancy = resolveOccupancyEnvelope(playback);

    float depthSafety = projectedSpan.depth * 0.08;
    float halfW = max(6.0, projectedSpan.width * 0.5 + depthSafety);
    float halfH = max(6.0, projectedSpan.height * 0.5 + depthSafety);

    float lowerW = halfW / max(1e-4, occupancy.maxW * tanHFov);
    float upperW = halfW / max(1e-4, occupancy.minW * tanHFov);
    float lowerH = halfH / max(1e-4, occupancy.maxH * tanVFov);
    float upperH = halfH / max(1e-4, occupancy.minH * tanVFov);

    float lower = max(lowerW, lowerH);
    float upper = min(upperW, upperH);
    boolean replayPhase = playback != null
      && ("shot_camera_pullback".equals(playback.phase)
        || "shot_histogram_project".equals(playback.phase)
        || "shot_stack".equals(playback.phase));
    float solveBias = replayPhase ? REPLAY_DISTANCE_SOLVE_BIAS : 0.5;
    float solvedDistance = lower <= upper ? lerp(lower, upper, solveBias) : lower;
    float safeZoom = max(0.6, pose.zoom);
    double adjustedDistance = solvedDistance / safeZoom;
    return Math.max(180.0, Math.min(12000.0, adjustedDistance));
  }

  OccupancyEnvelope resolveOccupancyEnvelope(PlaybackState playback) {
    if (playback == null) {
      return new OccupancyEnvelope(OCCUPANCY_MIN_W, OCCUPANCY_MAX_W, OCCUPANCY_MIN_H, OCCUPANCY_MAX_H);
    }
    if ("shot_camera_pullback".equals(playback.phase)) {
      return new OccupancyEnvelope(
        REPLAY_OCC_PULLBACK_MIN_W,
        REPLAY_OCC_PULLBACK_MAX_W,
        REPLAY_OCC_PULLBACK_MIN_H,
        REPLAY_OCC_PULLBACK_MAX_H
      );
    }
    if ("shot_histogram_project".equals(playback.phase)) {
      if (isProjectionShotLockPhase(playback)) {
        return replayStackOccupancyEnvelope();
      }
      float alpha = resolveShotProjectMoveAlpha(playback.phaseProgress);
      return new OccupancyEnvelope(
        lerp(REPLAY_OCC_PULLBACK_MIN_W, REPLAY_OCC_STACK_MIN_W, alpha),
        lerp(REPLAY_OCC_PULLBACK_MAX_W, REPLAY_OCC_STACK_MAX_W, alpha),
        lerp(REPLAY_OCC_PULLBACK_MIN_H, REPLAY_OCC_STACK_MIN_H, alpha),
        lerp(REPLAY_OCC_PULLBACK_MAX_H, REPLAY_OCC_STACK_MAX_H, alpha)
      );
    }
    if ("shot_stack".equals(playback.phase)) {
      return replayStackOccupancyEnvelope();
    }
    return new OccupancyEnvelope(OCCUPANCY_MIN_W, OCCUPANCY_MAX_W, OCCUPANCY_MIN_H, OCCUPANCY_MAX_H);
  }

  boolean isProjectionShotLockPhase(PlaybackState playback) {
    return playback != null
      && "shot_histogram_project".equals(playback.phase)
      && playback.shotIndex >= 0;
  }

  OccupancyEnvelope replayStackOccupancyEnvelope() {
    return new OccupancyEnvelope(
      REPLAY_OCC_STACK_MIN_W,
      REPLAY_OCC_STACK_MAX_W,
      REPLAY_OCC_STACK_MIN_H,
      REPLAY_OCC_STACK_MAX_H
    );
  }

  float resolveReplayDepthBudget(MatrixViewMetrics metrics, PlaybackState playback, TraceModel traceModel, float focusZ) {
    float matrixFrontZ = shotReplayMatrixFrontZ(metrics);
    float qubitFrontZ = shotReplayQubitFrontZ(metrics);
    float histogramFrontZ = shotReplayHistogramFrontZ(metrics);
    int shotsTotal = playback != null ? max(0, playback.shotsTotal) : 0;
    if (shotsTotal <= 0 && traceModel != null && traceModel.measurementShotReplay != null) {
      shotsTotal = max(0, traceModel.measurementShotReplay.shotsTotal);
    }
    float stackBackOffset = shotReplayEffectiveMaxDepthOffset(metrics, shotsTotal);
    float stackBackZ = qubitFrontZ - stackBackOffset;
    float margin = max(12.0, metrics.cubeSize * 0.90);
    float replayMinZ = min(0.0, min(matrixFrontZ - margin, stackBackZ - margin));
    float replayMaxZ = max(histogramFrontZ + margin, qubitFrontZ + margin);
    float replaySpan = max(1.0, replayMaxZ - replayMinZ);
    float extentFromFocus = max(abs(focusZ - replayMinZ), abs(replayMaxZ - focusZ));
    float symmetricSpan = max(1.0, extentFromFocus * 2.0);
    float blendedSpan = lerp(replaySpan, symmetricSpan, SHOT_REPLAY_DEPTH_BLEND);
    float replayDepth = blendedSpan + margin;
    return max(metrics.stackDepthEstimate, replayDepth);
  }

  float shotReplayMatrixFrontZ(MatrixViewMetrics metrics) {
    if (metrics == null) {
      return 8.0;
    }
    return 1.10 + metrics.cubeSize * 0.92;
  }

  float shotReplayLayerGap(MatrixViewMetrics metrics) {
    if (metrics == null) {
      return SHOT_QUBIT_MIN_HIST_GAP * SHOT_REPLAY_LAYER_GAP_SCALE;
    }
    float baseGap = max(SHOT_QUBIT_MIN_HIST_GAP, metrics.cubeSize * SHOT_QUBIT_HIST_GAP_CUBE_MULT);
    return baseGap * SHOT_REPLAY_LAYER_GAP_SCALE;
  }

  float shotReplayQubitFrontZ(MatrixViewMetrics metrics) {
    return shotReplayMatrixFrontZ(metrics) + shotReplayLayerGap(metrics);
  }

  float shotReplayHistogramFrontZ(MatrixViewMetrics metrics) {
    return shotReplayQubitFrontZ(metrics) + shotReplayLayerGap(metrics);
  }

  float shotReplayDepthBaseStep(MatrixViewMetrics metrics) {
    if (metrics == null) {
      return SHOT_STACK_DEPTH_BASE_MIN;
    }
    return clampFloat(
      metrics.cubeSize * SHOT_STACK_DEPTH_BASE_MULT,
      SHOT_STACK_DEPTH_BASE_MIN,
      SHOT_STACK_DEPTH_BASE_MAX
    );
  }

  float shotReplayDepthOffset(MatrixViewMetrics metrics, float age) {
    float safeAge = max(0.0, age);
    float baseStep = shotReplayDepthBaseStep(metrics);
    float linearAge = min(float(SHOT_STACK_SOFT_CAP_LINEAR_LAYERS), safeAge);
    float tailAge = max(0.0, safeAge - float(SHOT_STACK_SOFT_CAP_LINEAR_LAYERS));
    return linearAge * baseStep + tailAge * baseStep * SHOT_STACK_TAIL_COMPRESS_RATIO;
  }

  float shotReplayQubitCubeSide(MatrixViewMetrics metrics) {
    if (metrics == null) {
      return SHOT_QUBIT_CUBE_MIN_SIZE;
    }
    return clampFloat(
      metrics.cubeSize * SHOT_QUBIT_CUBE_SIZE_RATIO,
      SHOT_QUBIT_CUBE_MIN_SIZE,
      SHOT_QUBIT_CUBE_MAX_SIZE
    );
  }

  float shotReplayBaseCubeDepth(MatrixViewMetrics metrics) {
    float cubeSide = shotReplayQubitCubeSide(metrics);
    return clampFloat(
      cubeSide * 0.92,
      SHOT_QUBIT_CUBE_MIN_SIZE * 0.85,
      SHOT_QUBIT_CUBE_MAX_SIZE * 0.96
    );
  }

  float shotReplayDensityRenderedFrontZ(MatrixViewMetrics metrics) {
    if (metrics == null) {
      return 1.10 + 52.0 + 0.35;
    }
    return 1.10 + metrics.cubeSize + 0.35;
  }

  float shotReplaySpawnFrontGap(MatrixViewMetrics metrics) {
    float cubeSide = shotReplayQubitCubeSide(metrics);
    return clampFloat(cubeSide * 0.16, 2.4, 7.0);
  }

  float shotReplayFrontSafeMaxDepthOffset(MatrixViewMetrics metrics) {
    float qubitFrontZ = shotReplayQubitFrontZ(metrics);
    float densityFrontZ = shotReplayDensityRenderedFrontZ(metrics);
    float spawnGap = shotReplaySpawnFrontGap(metrics);
    float minLayerCenterZ = densityFrontZ + spawnGap + shotReplayBaseCubeDepth(metrics) * 0.5;
    return max(0.0, qubitFrontZ - minLayerCenterZ);
  }

  float shotReplayEffectiveMaxDepthOffset(MatrixViewMetrics metrics, int shotsTotal) {
    float rawMaxOffset = shotReplayDepthOffset(metrics, max(0.0, float(shotsTotal - 1)));
    float frontSafeMaxOffset = shotReplayFrontSafeMaxDepthOffset(metrics);
    return min(rawMaxOffset, frontSafeMaxOffset);
  }

  ProjectedSpan resolveProjectedSpan(MatrixViewMetrics metrics, CameraPoseState pose, float depthBudget) {
    float rx = radians(pose.rotateXDeg);
    float ry = radians(pose.rotateYDeg);
    float rz = radians(pose.rotateZDeg);
    float cosX = cos(rx);
    float sinX = sin(rx);
    float cosY = cos(ry);
    float sinY = sin(ry);
    float cosZ = cos(rz);
    float sinZ = sin(rz);
    float halfW = metrics.matrixW * 0.5;
    float halfH = metrics.matrixH * 0.5;
    float halfD = max(1.0, depthBudget * 0.5);

    float minX = Float.POSITIVE_INFINITY;
    float maxX = Float.NEGATIVE_INFINITY;
    float minY = Float.POSITIVE_INFINITY;
    float maxY = Float.NEGATIVE_INFINITY;
    float minZ = Float.POSITIVE_INFINITY;
    float maxZ = Float.NEGATIVE_INFINITY;

    for (int sx = -1; sx <= 1; sx += 2) {
      for (int sy = -1; sy <= 1; sy += 2) {
        for (int sz = -1; sz <= 1; sz += 2) {
          float x = sx * halfW;
          float y = sy * halfH;
          float z = sz * halfD;

          float xx = x;
          float yx = y * cosX - z * sinX;
          float zx = y * sinX + z * cosX;

          float xy = xx * cosY + zx * sinY;
          float yy = yx;
          float zy = -xx * sinY + zx * cosY;

          float xz = xy * cosZ - yy * sinZ;
          float yz = xy * sinZ + yy * cosZ;

          minX = min(minX, xz);
          maxX = max(maxX, xz);
          minY = min(minY, yz);
          maxY = max(maxY, yz);
          minZ = min(minZ, zy);
          maxZ = max(maxZ, zy);
        }
      }
    }
    return new ProjectedSpan(
      max(12.0, maxX - minX),
      max(12.0, maxY - minY),
      max(2.0, maxZ - minZ)
    );
  }

  CameraPoseState addPose(CameraPoseState base, CameraPoseState delta) {
    return new CameraPoseState(
      base.rotateXDeg + delta.rotateXDeg,
      base.rotateYDeg + delta.rotateYDeg,
      base.rotateZDeg + delta.rotateZDeg,
      base.zoom + delta.zoom,
      base.panXNorm + delta.panXNorm,
      base.panYNorm + delta.panYNorm
    );
  }
}
