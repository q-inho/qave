/*
Purpose: Render volumetric matrix evolution and in-gate sample transitions.
Inputs: Shared playback state, trace-derived models, pane metrics, and user interaction state.
Outputs: Deterministic frame-local rendering updates and synchronized visual state transitions.
Determinism/Timing: Uses timeline phases (pre_gate/apply_gate/settle) and fixed frame progression for reproducible output.
*/

float easeInOutCirc01(float value) {
  float x = clampFloat(value, 0.0, 1.0);
  if (x < 0.5) {
    return (1.0 - sqrt(max(0.0, 1.0 - pow(2.0 * x, 2.0)))) * 0.5;
  }
  return (sqrt(max(0.0, 1.0 - pow(-2.0 * x + 2.0, 2.0))) + 1.0) * 0.5;
}

float easeInOutSine01(float value) {
  float x = clampFloat(value, 0.0, 1.0);
  return -(cos(PI * x) - 1.0) * 0.5;
}

float smoothstep01(float value) {
  float x = clampFloat(value, 0.0, 1.0);
  return x * x * (3.0 - 2.0 * x);
}

// Class MatrixCellEntity encapsulates module-specific viewer behavior.
class MatrixCellEntity {
  PVector orgPos;
  PVector curPos;
  PVector trgPos;

  PVector orgSize;
  PVector curSize;
  PVector trgSize;

  PVector curValue;
  PVector trgValue;

  int frameStart;
  int frameDuration;

  MatrixCellEntity(PVector pos, PVector size, PVector value, int frameStart, int frameDuration) {
    orgPos = pos.copy();
    curPos = pos.copy();
    trgPos = pos.copy();

    orgSize = size.copy();
    curSize = size.copy();
    trgSize = size.copy();

    curValue = value.copy();
    trgValue = value.copy();

    this.frameStart = frameStart;
    this.frameDuration = max(1, frameDuration);
  }

  void setTarget(PVector pos, PVector size, PVector value, int frameIndex, int duration) {
    if (targetChanged(pos, size)) {
      orgPos.set(curPos);
      trgPos.set(pos);
      orgSize.set(curSize);
      trgSize.set(size);
      frameStart = frameIndex;
      frameDuration = max(1, duration);
    }
    trgValue.set(value);
  }

  void update(int frameIndex) {
    float t = frameDuration <= 0
      ? 1.0
      : clampFloat((frameIndex - frameStart) / float(max(1, frameDuration)), 0.0, 1.0);
    float easing = easeInOutCirc01(t);

    curPos = PVector.lerp(orgPos, trgPos, easing);
    curSize = PVector.lerp(orgSize, trgSize, easing);
    curValue.add(PVector.sub(trgValue, curValue).mult(0.2));

    if (!isFinite(curPos)) {
      curPos.set(trgPos);
    }
    if (!isFinite(curSize)) {
      curSize.set(trgSize);
    }
    if (!isFinite(curValue)) {
      curValue.set(trgValue);
    }
  }

  void snapTo(PVector pos, PVector size, PVector value, int frameIndex) {
    orgPos.set(pos);
    curPos.set(pos);
    trgPos.set(pos);
    orgSize.set(size);
    curSize.set(size);
    trgSize.set(size);
    curValue.set(value);
    trgValue.set(value);
    frameStart = frameIndex;
    frameDuration = 1;
  }

  boolean targetChanged(PVector pos, PVector size) {
    return PVector.dist(trgPos, pos) > 0.05 || PVector.dist(trgSize, size) > 0.05;
  }

  boolean isFinite(PVector v) {
    return !Float.isNaN(v.x)
      && !Float.isNaN(v.y)
      && !Float.isNaN(v.z)
      && !Float.isInfinite(v.x)
      && !Float.isInfinite(v.y)
      && !Float.isInfinite(v.z);
  }
}

// Class GateActorEntity encapsulates module-specific viewer behavior.
class GateActorEntity {
  PVector orgPos;
  PVector curPos;
  PVector trgPos;

  PVector orgSize;
  PVector curSize;
  PVector trgSize;

  PVector curValue;
  PVector trgValue;

  int frameStart;
  int frameDuration;

  GateActorEntity(PVector pos, PVector size, PVector value, int frameStart, int frameDuration) {
    orgPos = pos.copy();
    curPos = pos.copy();
    trgPos = pos.copy();

    orgSize = size.copy();
    curSize = size.copy();
    trgSize = size.copy();

    curValue = value.copy();
    trgValue = value.copy();

    this.frameStart = frameStart;
    this.frameDuration = max(1, frameDuration);
  }

  void setTarget(PVector pos, PVector size, PVector value, int frameIndex, int duration) {
    if (targetChanged(pos, size)) {
      orgPos.set(curPos);
      trgPos.set(pos);
      orgSize.set(curSize);
      trgSize.set(size);
      frameStart = frameIndex;
      frameDuration = max(1, duration);
    }
    trgValue.set(value);
  }

  void update(int frameIndex) {
    float t = frameDuration <= 0
      ? 1.0
      : clampFloat((frameIndex - frameStart) / float(max(1, frameDuration)), 0.0, 1.0);
    float easing = easeInOutCirc01(t);

    curPos = PVector.lerp(orgPos, trgPos, easing);
    curSize = PVector.lerp(orgSize, trgSize, easing);
    curValue.add(PVector.sub(trgValue, curValue).mult(0.2));

    if (!isFinite(curPos)) {
      curPos.set(trgPos);
    }
    if (!isFinite(curSize)) {
      curSize.set(trgSize);
    }
    if (!isFinite(curValue)) {
      curValue.set(trgValue);
    }
  }

  boolean targetChanged(PVector pos, PVector size) {
    return PVector.dist(trgPos, pos) > 0.05 || PVector.dist(trgSize, size) > 0.05;
  }

  boolean isFinite(PVector v) {
    return !Float.isNaN(v.x)
      && !Float.isNaN(v.y)
      && !Float.isNaN(v.z)
      && !Float.isInfinite(v.x)
      && !Float.isInfinite(v.y)
      && !Float.isInfinite(v.z);
  }
}

// Class ShotHistogramLabelSprite encapsulates module-specific viewer behavior.
class ShotHistogramLabelSprite {
  String label;
  float screenX;
  float screenY;
  float alpha;
  boolean active;

  ShotHistogramLabelSprite(String label, float screenX, float screenY, float alpha, boolean active) {
    this.label = label != null ? label : "";
    this.screenX = screenX;
    this.screenY = screenY;
    this.alpha = clampFloat(alpha, 0.0, 1.0);
    this.active = active;
  }
}

// Class ShotQubitLabelSprite encapsulates module-specific viewer behavior.
class ShotQubitLabelSprite {
  String label;
  float screenX;
  float screenY;
  float alpha;
  boolean active;

  ShotQubitLabelSprite(String label, float screenX, float screenY, float alpha, boolean active) {
    this.label = label != null ? label : "";
    this.screenX = screenX;
    this.screenY = screenY;
    this.alpha = clampFloat(alpha, 0.0, 1.0);
    this.active = active;
  }
}

// Class MatrixViewMetrics encapsulates module-specific viewer behavior.
class MatrixViewMetrics {
  int rows;
  int cols;

  float centerX;
  float centerY;
  float pitch;
  float cubeSize;
  float matrixW;
  float matrixH;
  float stackDepthEstimate;
  boolean valid;
  String message;

  MatrixViewMetrics(
    int rows,
    int cols,
    float centerX,
    float centerY,
    float pitch,
    float cubeSize,
    float matrixW,
    float matrixH,
    float stackDepthEstimate,
    boolean valid,
    String message
  ) {
    this.rows = max(1, rows);
    this.cols = max(1, cols);
    this.centerX = centerX;
    this.centerY = centerY;
    this.pitch = max(1.0, pitch);
    this.cubeSize = max(2.0, cubeSize);
    this.matrixW = max(2.0, matrixW);
    this.matrixH = max(2.0, matrixH);
    this.stackDepthEstimate = max(1.0, stackDepthEstimate);
    this.valid = valid;
    this.message = message != null ? message : "";
  }

  float localXForIndex(int col) {
    return (col - (cols - 1) * 0.5) * pitch;
  }

  float localYForIndex(int row) {
    return (row - (rows - 1) * 0.5) * pitch;
  }
}

// Class StoryBeat encapsulates module-specific viewer behavior.
class StoryBeat {
  String phase;
  String beat;
  float phaseProgress;
  float beatProgress;
  boolean actorVisible;
  float actorIntensity;
  float scanProgress;

  StoryBeat(
    String phase,
    String beat,
    float phaseProgress,
    float beatProgress,
    boolean actorVisible,
    float actorIntensity,
    float scanProgress
  ) {
    this.phase = phase;
    this.beat = beat;
    this.phaseProgress = phaseProgress;
    this.beatProgress = beatProgress;
    this.actorVisible = actorVisible;
    this.actorIntensity = actorIntensity;
    this.scanProgress = scanProgress;
  }
}

// Class CellDeltaSample encapsulates module-specific viewer behavior.
class CellDeltaSample {
  int row;
  int col;
  float delta;
  float localX;
  float localY;
  int rank;

  CellDeltaSample(int row, int col, float delta, float localX, float localY) {
    this.row = row;
    this.col = col;
    this.delta = delta;
    this.localX = localX;
    this.localY = localY;
    this.rank = -1;
  }
}

// Class CellInfluenceMap encapsulates module-specific viewer behavior.
class CellInfluenceMap {
  int rows;
  int cols;
  int total;
  float maxDelta = 0.0;
  int[][] rankLookup;
  float[][] normalizedDelta;
  ArrayList<CellDeltaSample> ranked = new ArrayList<CellDeltaSample>();

  CellInfluenceMap(int rows, int cols) {
    this.rows = max(1, rows);
    this.cols = max(1, cols);
    this.total = this.rows * this.cols;
    rankLookup = new int[this.rows][this.cols];
    normalizedDelta = new float[this.rows][this.cols];
    for (int r = 0; r < this.rows; r += 1) {
      for (int c = 0; c < this.cols; c += 1) {
        rankLookup[r][c] = -1;
        normalizedDelta[r][c] = 0.0;
      }
    }
  }

  void addCell(int row, int col, float delta, float localX, float localY) {
    ranked.add(new CellDeltaSample(row, col, max(0.0, delta), localX, localY));
  }

  void finalizeMap() {
    if (ranked.isEmpty()) {
      return;
    }

    Collections.sort(ranked, new Comparator<CellDeltaSample>() {
      public int compare(CellDeltaSample a, CellDeltaSample b) {
        int byDelta = Float.compare(b.delta, a.delta);
        if (byDelta != 0) {
          return byDelta;
        }
        if (a.row != b.row) {
          return a.row - b.row;
        }
        return a.col - b.col;
      }
    });

    maxDelta = 0.0;
    for (int i = 0; i < ranked.size(); i += 1) {
      CellDeltaSample sample = ranked.get(i);
      sample.rank = i;
      maxDelta = max(maxDelta, sample.delta);
    }
    float safeMax = max(maxDelta, 1e-9);
    for (CellDeltaSample sample : ranked) {
      rankLookup[sample.row][sample.col] = sample.rank;
      normalizedDelta[sample.row][sample.col] = clampFloat(sample.delta / safeMax, 0.0, 1.0);
    }
  }

  float normalizedDeltaAt(int row, int col) {
    if (row < 0 || col < 0 || row >= rows || col >= cols) {
      return 0.0;
    }
    return normalizedDelta[row][col];
  }

  int rankAt(int row, int col) {
    if (row < 0 || col < 0 || row >= rows || col >= cols) {
      return -1;
    }
    return rankLookup[row][col];
  }

  int activeCount(StoryBeat beat) {
    if (!beat.actorVisible || total <= 0) {
      return 0;
    }
    if ("enter".equals(beat.beat)) {
      return 1;
    }
    if ("scan".equals(beat.beat)) {
      float p = clampFloat(beat.scanProgress, 0.0, 1.0);
      int count = 1 + floor(p * max(0, total - 1));
      return clampInt(count, 1, total);
    }
    if ("exit".equals(beat.beat)) {
      return total;
    }
    return 0;
  }

  float frontierIndex(StoryBeat beat) {
    if (total <= 0) {
      return 0.0;
    }
    if ("enter".equals(beat.beat)) {
      return lerp(-0.8, 0.0, easeInOutCirc01(beat.beatProgress));
    }
    if ("scan".equals(beat.beat)) {
      return clampFloat(beat.scanProgress, 0.0, 1.0) * max(0, total - 1);
    }
    if ("exit".equals(beat.beat)) {
      return lerp(max(0, total - 1), max(0, total - 1) + 0.8, easeInOutCirc01(beat.beatProgress));
    }
    return -1.0;
  }

  PVector centroidForTopK(int k) {
    if (ranked.isEmpty()) {
      return new PVector(0, 0, 0);
    }
    int count = clampInt(k, 1, ranked.size());
    float sx = 0.0;
    float sy = 0.0;
    for (int i = 0; i < count; i += 1) {
      CellDeltaSample sample = ranked.get(i);
      sx += sample.localX;
      sy += sample.localY;
    }
    return new PVector(sx / count, sy / count, 0);
  }

  PVector actorTarget(StoryBeat beat, MatrixViewMetrics geometry) {
    if (ranked.isEmpty()) {
      return new PVector(0, 0, 0);
    }

    CellDeltaSample first = ranked.get(0);
    CellDeltaSample last = ranked.get(ranked.size() - 1);
    PVector firstPos = new PVector(first.localX, first.localY, 0);
    PVector lastPos = new PVector(last.localX, last.localY, 0);
    PVector startOff = firstPos.copy().add(new PVector(-geometry.pitch * 1.7, -geometry.pitch * 1.1, 0));
    PVector endOff = lastPos.copy().add(new PVector(geometry.pitch * 1.7, geometry.pitch * 1.1, 0));

    if ("enter".equals(beat.beat)) {
      float t = easeInOutCirc01(beat.beatProgress);
      return PVector.lerp(startOff, centroidForTopK(1), t);
    }

    if ("scan".equals(beat.beat)) {
      return centroidForTopK(activeCount(beat));
    }

    if ("exit".equals(beat.beat)) {
      float t = easeInOutCirc01(beat.beatProgress);
      return PVector.lerp(centroidForTopK(total), endOff, t);
    }

    return centroidForTopK(1);
  }

  float influenceForCell(int row, int col, StoryBeat beat) {
    if (!beat.actorVisible || row < 0 || col < 0 || row >= rows || col >= cols) {
      return 0.0;
    }
    int rank = rankLookup[row][col];
    if (rank < 0) {
      return 0.0;
    }

    float frontier = frontierIndex(beat);
    float width = max(1.0, total * 0.12);
    float distance = abs(rank - frontier);
    float frontierInfluence = smoothstep01(clampFloat(1.0 - distance / width, 0.0, 1.0));
    float writtenInfluence = rank <= frontier ? 0.38 : 0.0;
    float deltaWeight = 0.60 + 0.40 * normalizedDeltaAt(row, col);
    float base = max(frontierInfluence, writtenInfluence);
    return clampFloat(base * deltaWeight * beat.actorIntensity, 0.0, 1.0);
  }
}

// Class DensityLayerFrame encapsulates module-specific viewer behavior.
class DensityLayerFrame {
  int stepIndex;
  int age;
  String phase;
  float[][] real;
  float[][] imag;
  String stateHash;
  boolean isActive;

  DensityLayerFrame(
    int stepIndex,
    int age,
    String phase,
    float[][] real,
    float[][] imag,
    String stateHash,
    boolean isActive
  ) {
    this.stepIndex = stepIndex;
    this.age = age;
    this.phase = phase;
    this.real = real;
    this.imag = imag;
    this.stateHash = stateHash;
    this.isActive = isActive;
  }
}

// Class DensityRenderMode encapsulates module-specific viewer behavior.
class DensityRenderMode {
  static final int RAW = 0;
  static final int ADAPTIVE_LOD = 1;
}

// Class LodTileSample encapsulates module-specific viewer behavior.
class LodTileSample {
  int rowStart;
  int rowEnd;
  int colStart;
  int colEnd;
  float magnitudeRms;
  float phaseAngle;
  float deltaAvg;
  float diagWeight;

  LodTileSample(
    int rowStart,
    int rowEnd,
    int colStart,
    int colEnd,
    float magnitudeRms,
    float phaseAngle,
    float deltaAvg,
    float diagWeight
  ) {
    this.rowStart = rowStart;
    this.rowEnd = rowEnd;
    this.colStart = colStart;
    this.colEnd = colEnd;
    this.magnitudeRms = magnitudeRms;
    this.phaseAngle = phaseAngle;
    this.deltaAvg = deltaAvg;
    this.diagWeight = diagWeight;
  }
}

// Class LodDensityGrid encapsulates module-specific viewer behavior.
class LodDensityGrid {
  int rows;
  int cols;
  LodTileSample[][] tiles;
  float[][] real;
  float[][] imag;
  float[][] mag;
  float[][] phase;
  float[][] delta;
  float[][] diag;
  boolean valid;

  LodDensityGrid(int rows, int cols) {
    this.rows = max(1, rows);
    this.cols = max(1, cols);
    this.tiles = new LodTileSample[this.rows][this.cols];
    this.real = new float[this.rows][this.cols];
    this.imag = new float[this.rows][this.cols];
    this.mag = new float[this.rows][this.cols];
    this.phase = new float[this.rows][this.cols];
    this.delta = new float[this.rows][this.cols];
    this.diag = new float[this.rows][this.cols];
    this.valid = false;
  }
}

// Class CircuitLensRenderKind encapsulates module-specific viewer behavior.
class CircuitLensRenderKind {
  static final int SINGLE = 0;
  static final int CONTROL_TARGET = 1;
  static final int SWAP = 2;
  static final int MEASURE = 3;
  static final int GENERIC_MULTI = 4;
  static final int IDLE_UNKNOWN = 5;
}

// Class CircuitLensGateSpec encapsulates module-specific viewer behavior.
class CircuitLensGateSpec {
  int stepIndex;
  String gateToken;
  String rawGateName;
  String operationId;
  int[] qubits;
  int[] controlQubits;
  int[] targetQubits;
  int renderKind;

  CircuitLensGateSpec(
    int stepIndex,
    String gateToken,
    String rawGateName,
    String operationId,
    int[] qubits,
    int[] controlQubits,
    int[] targetQubits,
    int renderKind
  ) {
    this.stepIndex = stepIndex;
    this.gateToken = gateToken != null ? gateToken : "U";
    this.rawGateName = rawGateName != null ? rawGateName : "";
    this.operationId = operationId != null ? operationId : "";
    this.qubits = qubits != null ? qubits : new int[0];
    this.controlQubits = controlQubits != null ? controlQubits : new int[0];
    this.targetQubits = targetQubits != null ? targetQubits : new int[0];
    this.renderKind = renderKind;
  }
}

// Class ComplexEntry encapsulates module-specific viewer behavior.
class ComplexEntry {
  float re;
  float im;

  ComplexEntry(float re, float im) {
    this.re = re;
    this.im = im;
  }

  float magnitude() {
    return sqrt(re * re + im * im);
  }

  float phase() {
    return atan2(im, re);
  }
}

// Class DecompositionTerm encapsulates module-specific viewer behavior.
class DecompositionTerm {
  int srcRow;
  int srcCol;
  float re;
  float im;
  float weight;
  float phase;

  DecompositionTerm(int srcRow, int srcCol, float re, float im) {
    this.srcRow = srcRow;
    this.srcCol = srcCol;
    this.re = re;
    this.im = im;
    this.weight = sqrt(re * re + im * im);
    this.phase = atan2(im, re);
  }
}

// Class DecompositionOverlayState encapsulates module-specific viewer behavior.
class DecompositionOverlayState {
  boolean active = false;
  String reason = "";
  int targetRow = 0;
  int targetCol = 0;
  float error = 0.0;
  float maxWeight = 0.0;
  ArrayList<DecompositionTerm> terms = new ArrayList<DecompositionTerm>();
}

// Class ShotSourceCell encapsulates module-specific viewer behavior.
class ShotSourceCell {
  int row;
  int col;
  float localX;
  float localY;
  int basisIndex;
  int basisDim;
  float weight;
  String basisLabel;
  String stateHash;
  String outcomeLabel;
  String blockKey;

  ShotSourceCell(
    int row,
    int col,
    float localX,
    float localY,
    int basisIndex,
    int basisDim,
    float weight,
    String basisLabel,
    String stateHash,
    String outcomeLabel,
    String blockKey
  ) {
    this.row = row;
    this.col = col;
    this.localX = localX;
    this.localY = localY;
    this.basisIndex = basisIndex;
    this.basisDim = basisDim;
    this.weight = weight;
    this.basisLabel = basisLabel != null ? basisLabel : "";
    this.stateHash = stateHash != null ? stateHash : "";
    this.outcomeLabel = outcomeLabel != null ? outcomeLabel : "";
    this.blockKey = blockKey != null ? blockKey : "";
  }
}

// Class MatrixEvolutionPane encapsulates module-specific viewer behavior.
class MatrixEvolutionPane {
  PApplet app;
  HashMap<String, MatrixCellEntity> rhoEntities = new HashMap<String, MatrixCellEntity>();
  HashMap<String, MatrixCellEntity> shotQubitEntities = new HashMap<String, MatrixCellEntity>();
  HashMap<String, MatrixCellEntity> shotHistogramEntities = new HashMap<String, MatrixCellEntity>();
  HashMap<String, ShotSourceCell> shotSourceCellCache = new HashMap<String, ShotSourceCell>();
  ArrayList<ShotQubitLabelSprite> shotQubitLabelSprites = new ArrayList<ShotQubitLabelSprite>();
  ArrayList<ShotHistogramLabelSprite> shotHistogramLabelSprites = new ArrayList<ShotHistogramLabelSprite>();
  HashMap<String, ReducedDensitySample> initGroundBlockCache = new HashMap<String, ReducedDensitySample>();
  GateActorEntity gateActor;
  float globalRhoMagnitudeMax = 1.0;
  String initLayerStateHash = "synthetic_ground";
  ReducedDensitySample hudRho = null;
  String hudMissingMessage = "";
  boolean hudMatrixValid = true;
  int hudVisibleLayerCount = 0;
  int hudAvailableLayerCount = 0;
  int hudLayerCap = 0;
  String hudRenderModeLabel = "raw";
  String hudContextLabel = "Context: unavailable";
  String hudCircuitLabel = "Circuit: unavailable";
  boolean hudDecompositionActive = false;
  String hudDecompositionLabel = "";
  String hudDecompositionReason = "";
  String hudShotResponsibleSourceLabel = "";
  int hudShotActiveContributorQubit = -1;
  int hudShotActiveContributorCount = -1;
  ArrayList<CircuitLensGateSpec> circuitLensSpecs = new ArrayList<CircuitLensGateSpec>();
  int circuitLensQubitCount = 1;
  int circuitLensMaxQubitIndex = 0;
  final int INIT_LAYER_STEP_INDEX = -1;
  final String INIT_LAYER_PHASE = "pre_gate";
  final float MIN_SCALE = 1e-6;
  final int RAW_DETAIL_MAX_DIM = 8;
  final int LOD_GRID_DIM_SMALL = 12;
  final int LOD_GRID_DIM_MEDIUM = 16;
  final int LOD_GRID_DIM_LARGE = 24;
  final float MAG_GAMMA = 0.55;
  final float MAG_EPS = 1e-6;
  final float OFFDIAG_FADE = 0.35;
  final float STACK_DEPTH_STEP_MULT = 0.62;
  final float STACK_DEPTH_STEP_MIN = 12.0;
  final float STACK_DEPTH_STEP_MAX = 48.0;
  final float STACK_NO_OVERLAP_MULT = 0.96;
  final float STACK_NO_OVERLAP_MARGIN = 1.0;
  final float STACK_DRIFT_DECAY = 0.86;
  final float LAYER_ALPHA_DECAY_PER_AGE = 0.045;
  final float LAYER_SCALE_DECAY_PER_AGE = 0.012;
  final float MATRIX_CELL_FILL_RATIO = 0.90;
  final float CIRCUIT_LENS_GATE_PITCH_PX = 36.0;
  final float CIRCUIT_LENS_ACTIVE_ANCHOR_RATIO = 0.50;
  final float CIRCUIT_LENS_CULL_MARGIN_PX = 18.0;
  final int DECOMP_TOP_K = 5;
  final float DECOMP_EPS = 1e-8;
  final float DECOMP_UNITARY_EPS = 2e-3;
  final float DECOMP_MARKER_Z = 7.4;
  final float DECOMP_TARGET_Z = 8.0;
  final float SHOT_PROJECT_CAMERA_HOLD_FRACTION = 0.50;
  final float SHOT_PROJECT_PULSE_FRACTION = 0.34;
  final float SHOT_PROJECT_SPAN_RATIO = 0.86;
  final float SHOT_PROJECT_MIN_BAR_H = 2.0;
  final float SHOT_QUBIT_LAYER_SPAN_RATIO = 0.52;
  final float SHOT_QUBIT_CUBE_SIZE_RATIO = 0.64;
  final float SHOT_QUBIT_CUBE_MIN_SIZE = 8.0;
  final float SHOT_QUBIT_CUBE_MAX_SIZE = 26.0;
  final float SHOT_QUBIT_CUBOID_MIN_DEPTH = 2.0;
  final float SHOT_QUBIT_CUBOID_DEPTH_BLEND = 1.0;
  final float SHOT_QUBIT_STACK_DEPTH_MULTIPLIER = 1.5;
  final float SHOT_QUBIT_MIN_HIST_GAP = 14.0;
  final float SHOT_QUBIT_HIST_GAP_CUBE_MULT = 0.95;
  final float SHOT_REPLAY_LAYER_GAP_SCALE = 10.0;
  final float SHOT_QUBIT_STACK_PULSE_MIN = 0.35;
  final float SHOT_QUBIT_STACK_PULSE_MAX = 1.0;
  final int SHOT_QUBIT_BIT_0_GRAY = 84;
  final int SHOT_QUBIT_BIT_1_GRAY = 244;
  final int SHOT_QUBIT_BIT_UNKNOWN_GRAY = 164;
  final int SHOT_QUBIT_EDGE_GRAY_BOOST_BASE = 20;
  final int SHOT_QUBIT_EDGE_GRAY_BOOST_ACTIVE = 34;
  final float SHOT_QUBIT_HISTORICAL_LUMA_DIM_MIN = 0.52;
  final float SHOT_QUBIT_HISTORICAL_ALPHA_DIM_MIN = 0.40;
  final int SHOT_STACK_SOFT_CAP_LINEAR_LAYERS = 24;
  final float SHOT_STACK_TAIL_COMPRESS_RATIO = 0.28;
  final float SHOT_STACK_DEPTH_BASE_MULT = 0.58;
  final float SHOT_STACK_DEPTH_BASE_MIN = 5.0;
  final float SHOT_STACK_DEPTH_BASE_MAX = 18.0;
  final float SHOT_QUBIT_LABEL_Y_OFFSET = 10.0;
  final float SHOT_LABEL_MIN_GAP_PX = 24.0;
  final float SHOT_LABEL_STAGGER_PX = 12.0;
  final float SHOT_LABEL_BASE_Y_OFFSET = 8.0;
  final int SHOT_EMISSION_SOURCE_TOP_K = 6;
  final float SHOT_EMISSION_MIN_PROBABILITY = 1e-6;
  final float SHOT_EMISSION_CONTRIBUTOR_THRESHOLD = 1e-7;
  final float SHOT_DENSITY_RELAY_BAND = 0.24;
  final float SHOT_DENSITY_RELAY_MIN_ALPHA = 24.0;
  final float SHOT_DENSITY_RELAY_MAX_ALPHA = 178.0;
  final float SHOT_DENSITY_RELAY_MIN_STROKE = 0.6;
  final float SHOT_DENSITY_RELAY_MAX_STROKE = 2.0;
  final float SHOT_SOURCE_DIM_STACK = 1.00;
  final float SHOT_SOURCE_DIM_PROJECT = 1.00;
  final float SHOT_SOURCE_HIGHLIGHT_ALPHA_MIN = 110.0;
  final float SHOT_SOURCE_HIGHLIGHT_ALPHA_MAX = 255.0;

  MatrixEvolutionPane(PApplet app) {
    this.app = app;
  }

  void setTrace(TraceModel traceModel) {
    rhoEntities.clear();
    shotQubitEntities.clear();
    shotHistogramEntities.clear();
    shotSourceCellCache.clear();
    shotQubitLabelSprites.clear();
    shotHistogramLabelSprites.clear();
    initGroundBlockCache.clear();
    gateActor = null;
    initLayerStateHash = resolveInitialLayerStateHash(traceModel);
    hudRho = null;
    hudMissingMessage = "";
    hudMatrixValid = true;
    hudVisibleLayerCount = 0;
    hudAvailableLayerCount = 0;
    hudLayerCap = 0;
    hudRenderModeLabel = "raw";
    hudContextLabel = "Context: unavailable";
    hudCircuitLabel = "Circuit: unavailable";
    hudDecompositionActive = false;
    hudDecompositionLabel = "";
    hudDecompositionReason = "";
    hudShotResponsibleSourceLabel = "";
    hudShotActiveContributorQubit = -1;
    hudShotActiveContributorCount = -1;
    circuitLensSpecs.clear();
    circuitLensQubitCount = 1;
    circuitLensMaxQubitIndex = 0;
    globalRhoMagnitudeMax = computeGlobalRhoMagnitude(traceModel);
    buildCircuitLensSpecs(traceModel);
  }

  MatrixViewMetrics computeViewMetrics(PanelRect panel, PlaybackState playback) {
    ReducedDensitySample block = selectPreferredBlock(playback != null ? playback.sample : null);
    int rows = 4;
    int cols = 4;
    boolean valid = false;
    String message = "No reduced density block for this sample.";
    if (block != null && isRectangular(block.real, block.imag)) {
      rows = max(1, block.real.length);
      cols = max(1, block.real[0].length);
      valid = true;
      message = "";
    } else if (block != null) {
      message = "Malformed reduced density block in trace payload.";
    }

    float targetMatrixW = clampFloat(panel.w * 0.58, panel.w * 0.55, panel.w * 0.62);
    float targetMatrixH = clampFloat(panel.h * 0.34, panel.h * 0.30, panel.h * 0.38);
    float padW = max(18.0, panel.w * 0.03);
    float padH = max(14.0, panel.h * 0.04);

    float maxStageW = max(32.0, panel.w - padW * 2.0);
    float maxStageH = max(32.0, panel.h - padH * 2.0);
    float desiredW = min(targetMatrixW, maxStageW);
    float desiredH = min(targetMatrixH, maxStageH);

    float pitchW = desiredW / max(1.0, cols);
    float pitchH = desiredH / max(1.0, rows);
    float pitch = clampFloat(min(pitchW, pitchH), 30.0, 170.0);
    float cubeSize = max(8.0, pitch * MATRIX_CELL_FILL_RATIO);

    float matrixW = cols * pitch;
    float matrixH = rows * pitch;
    float centerX = panel.x + panel.w * 0.5;
    float centerY = panel.y + panel.h * 0.54;
    int estimatedLayerCount = resolveEstimatedLayerCount(playback);
    float stackDepthEstimate = resolveStackDepthBudget(matrixW, matrixH, cubeSize, estimatedLayerCount);

    return new MatrixViewMetrics(
      rows,
      cols,
      centerX,
      centerY,
      pitch,
      cubeSize,
      matrixW,
      matrixH,
      stackDepthEstimate,
      valid,
      message
    );
  }

  void renderWorld(PanelRect panel, PlaybackState playback, TraceModel traceModel, MatrixViewMetrics metrics) {
    EvolutionSample activeSample = null;
    ReducedDensitySample activeRho = null;
    if ("measurement_reveal".equals(playback.phase)) {
      activeSample = resolveSettleEvolutionSample(playback.step);
      activeRho = selectPreferredBlock(activeSample);
    } else {
      activeSample = traceModel.resolveNearestEvolutionSample(
        playback.step,
        playback.stepProgress,
        playback.phase
      );
      activeRho = selectPreferredBlock(playback.sample);
      if (activeRho == null) {
        activeRho = selectPreferredBlock(activeSample);
      }
    }
    hudRho = activeRho;

    EvolutionSample previousSample = traceModel.resolvePreviousEvolutionSample(playback.step, activeSample);
    ReducedDensitySample previousRho = selectPreferredBlock(previousSample);

    String activeStateHash = "";
    if (activeSample != null) {
      activeStateHash = activeSample.stateHash;
    } else if (playback.sample != null) {
      activeStateHash = playback.sample.stateHash;
    }

    ArrayList<DensityLayerFrame> layers = resolveLayerFrames(playback, traceModel, activeRho, activeStateHash);
    hudVisibleLayerCount = layers.size();
    boolean showActiveLayer = shouldRenderActiveGateLayer(playback);
    hudAvailableLayerCount = playback != null ? playback.stepIndex + (showActiveLayer ? 2 : 1) : 0;
    hudLayerCap = hudAvailableLayerCount;

    hudMatrixValid = renderMatrixStage(
      panel,
      metrics,
      layers,
      activeRho,
      previousRho != null ? previousRho.real : null,
      previousRho != null ? previousRho.imag : null,
      playback,
      traceModel,
      playback.phase,
      playback.phaseProgress,
      playback.frameIndex,
      playback.step,
      metrics != null ? metrics.message : "No reduced density block for this sample."
    );
  }

  void renderHud(PanelRect panel, PlaybackState playback, TraceModel traceModel, float revealProgress) {
    if (!hudMatrixValid) {
      drawMissingBlockMessage(panel, hudMissingMessage);
    }
    drawMinimalCaption(panel, playback, traceModel, revealProgress, hudRho);
    drawShotReplayQubitLabels(panel, playback);
    drawShotReplayHistogramLabels(panel, playback);
  }

  boolean renderMatrixStage(
    PanelRect panel,
    MatrixViewMetrics geometry,
    ArrayList<DensityLayerFrame> layers,
    ReducedDensitySample activeBlock,
    float[][] previousReal,
    float[][] previousImag,
    PlaybackState playback,
    TraceModel traceModel,
    String phase,
    float phaseProgress,
    int frameIndex,
    TraceStep step,
    String missingMessage
  ) {
    hudDecompositionActive = false;
    hudDecompositionLabel = "";
    hudDecompositionReason = "";
    hudShotResponsibleSourceLabel = "";

    DensityLayerFrame activeLayer = null;
    if (layers != null) {
      for (DensityLayerFrame layer : layers) {
        if (layer != null && layer.isActive) {
          activeLayer = layer;
          break;
        }
      }
      if (activeLayer == null && !layers.isEmpty()) {
        activeLayer = layers.get(layers.size() - 1);
      }
    }

    boolean valid = geometry != null
      && geometry.valid
      && activeLayer != null
      && isRectangular(activeLayer.real, activeLayer.imag);
    if (!valid) {
      pruneStaleRhoEntities(new HashSet<String>());
      pruneStaleShotQubitEntities(new HashSet<String>());
      shotQubitLabelSprites.clear();
      pruneStaleShotHistogramEntities(new HashSet<String>());
      shotHistogramLabelSprites.clear();
      hudMissingMessage = missingMessage;
      hudRenderModeLabel = "full-history/raw";
      hudContextLabel = "Context: unavailable";
      hudCircuitLabel = "Circuit: unavailable";
      hudDecompositionReason = "inactive: unavailable";
      return false;
    }
    hudMissingMessage = "";

    int fullRows = activeLayer.real.length;
    int fullCols = activeLayer.real[0].length;
    hudRenderModeLabel = "full-history/raw";
    hudCircuitLabel = circuitLensLabel(playback);

    ArrayList<DensityLayerFrame> renderLayers = new ArrayList<DensityLayerFrame>();
    for (DensityLayerFrame layer : layers) {
      if (layer == null || !isRectangular(layer.real, layer.imag)) {
        continue;
      }
      renderLayers.add(layer);
    }

    DensityLayerFrame activeRenderLayer = null;
    for (DensityLayerFrame layer : renderLayers) {
      if (layer != null && layer.isActive) {
        activeRenderLayer = layer;
        break;
      }
    }
    if (activeRenderLayer == null && !renderLayers.isEmpty()) {
      activeRenderLayer = renderLayers.get(renderLayers.size() - 1);
    }
    if (activeRenderLayer == null || !isRectangular(activeRenderLayer.real, activeRenderLayer.imag)) {
      pruneStaleRhoEntities(new HashSet<String>());
      pruneStaleShotQubitEntities(new HashSet<String>());
      shotQubitLabelSprites.clear();
      pruneStaleShotHistogramEntities(new HashSet<String>());
      shotHistogramLabelSprites.clear();
      hudMissingMessage = missingMessage;
      hudDecompositionReason = "inactive: unavailable";
      return false;
    }

    float[][] activeReal = activeRenderLayer.real;
    float[][] activeImag = activeRenderLayer.imag;
    int rows = activeReal.length;
    int cols = activeReal[0].length;
    hudContextLabel = "Context: full " + cols + "x" + rows;

    boolean revealPhase = "measurement_reveal".equals(phase);
    StoryBeat beat = resolveStoryBeat(phase, phaseProgress);
    CellInfluenceMap influenceMap = buildCellInfluenceMap(activeReal, activeImag, previousReal, previousImag, geometry);
    DecompositionOverlayState decompositionState = resolveDecompositionOverlay(
      playback,
      activeBlock,
      rows,
      cols,
      influenceMap,
      beat
    );
    hudDecompositionActive = decompositionState.active;
    hudDecompositionReason = decompositionState.reason != null ? decompositionState.reason : "";
    if (decompositionState.active) {
      hudDecompositionLabel =
        "Decomp: cell ["
        + decompositionState.targetRow
        + ","
        + decompositionState.targetCol
        + "], top"
        + decompositionState.terms.size()
        + ", err="
        + nf(decompositionState.error, 1, 4);
    }
    int motionDuration = durationForBeat(beat, step);
    float revealDim = revealPhase ? (1.0 - 0.58 * easeInOutCirc01(phaseProgress)) : 1.0;
    boolean shotSourcePhase = playback != null
      && playback.inShotReplay
      && ("shot_stack".equals(playback.phase)
        || ("shot_histogram_project".equals(playback.phase) && playback.shotIndex >= 0));
    ShotSourceCell shotSourceCell = shotSourcePhase
      ? resolveShotReplayResponsibleSourceCell(playback, traceModel, geometry)
      : null;
    hudShotResponsibleSourceLabel = shotSourceCell != null ? shotSourceCell.basisLabel : "";
    boolean actorEnabled = beat.actorVisible && !revealPhase && influenceMap.maxDelta > 1e-6;
    float frontier = influenceMap.frontierIndex(beat);
    int sourceSetCount = clampInt(max(2, round(influenceMap.total * 0.15)), 2, min(influenceMap.total, 6));
    int reachedCount = clampInt(1 + floor(frontier), 0, influenceMap.total);
    int targetSetCount = clampInt(max(2, round(influenceMap.total * 0.16)), 2, min(influenceMap.total, 7));
    float depthStep = resolveGuaranteedDepthStep(geometry.cubeSize);
    float lateralBudgetX = resolveStackLateralBudgetX(geometry, renderLayers.size());
    float lateralBudgetY = resolveStackLateralBudgetY(geometry, renderLayers.size());
    float stagePlaneZ = resolveStagePlaneZ(renderLayers, geometry, rows, cols, depthStep);
    HashSet<String> renderedEntityKeys = new HashSet<String>();

    pushMatrix();
    translate(geometry.centerX, geometry.centerY, -22);

    renderStageSurface(geometry, stagePlaneZ);
    if (actorEnabled) {
      updateGateActor(geometry, influenceMap, beat, frameIndex, motionDuration);
    }

    for (DensityLayerFrame layer : renderLayers) {
      if (layer == null || !isRectangular(layer.real, layer.imag)) {
        continue;
      }
      if (layer.real.length != rows || layer.real[0].length != cols) {
        continue;
      }

      int age = max(0, layer.age);
      float driftNorm = 1.0 - pow(STACK_DRIFT_DECAY, age);
      float layerAlpha = clampFloat(1.0 - age * LAYER_ALPHA_DECAY_PER_AGE, 0.26, 1.0);
      float layerScaleAttenuation = clampFloat(1.0 - age * LAYER_SCALE_DECAY_PER_AGE, 0.72, 1.0);
      float layerZOffset = -age * depthStep;
      float layerXOffset = -driftNorm * lateralBudgetX;
      float layerYOffset = driftNorm * lateralBudgetY;
      boolean activeLayerVisual = layer.isActive && actorEnabled;

      for (int row = 0; row < rows; row += 1) {
        for (int col = 0; col < cols; col += 1) {
          float localX = geometry.localXForIndex(col) + layerXOffset;
          float localY = geometry.localYForIndex(row) + layerYOffset;
          float actorInfluence = activeLayerVisual ? influenceMap.influenceForCell(row, col, beat) : 0.0;

          float re = layer.real[row][col];
          float im = layer.imag[row][col];
          float magnitude = sqrt(re * re + im * im);
          float normalizedMagnitude = clampFloat(magnitude / max(globalRhoMagnitudeMax, MIN_SCALE), 0.0, 1.0);
          float phaseAngle = atan2(im, re);

          float deltaComplex = 0.0;
          boolean changed = false;
          float normalizedDelta = 0.0;
          if (layer.isActive) {
            float prevRe = matrixValue(previousReal, row, col, re);
            float prevIm = matrixValue(previousImag, row, col, im);
            float diffRe = re - prevRe;
            float diffIm = im - prevIm;
            deltaComplex = sqrt(diffRe * diffRe + diffIm * diffIm);
            normalizedDelta = influenceMap.normalizedDeltaAt(row, col);
            changed = deltaComplex > 0.004 || normalizedDelta > 0.08;
          }

          float cubeScale = (0.92 + 0.08 * actorInfluence) * layerScaleAttenuation;
          float cubeSide = geometry.cubeSize * cubeScale;
          float lift = 1.10 + cubeSide * 0.5 + actorInfluence * 0.35 + layerZOffset;

          String key = "rho:" + layer.stepIndex + ":" + row + ":" + col;
          renderedEntityKeys.add(key);
          MatrixCellEntity entity = rhoEntities.get(key);
          if (entity == null) {
            entity = new MatrixCellEntity(
              new PVector(localX, localY, lift),
              new PVector(cubeSide, cubeSide, cubeSide),
              new PVector(normalizedMagnitude, (phaseAngle + PI) / TWO_PI, deltaComplex),
              frameIndex,
              motionDuration
            );
            rhoEntities.put(key, entity);
          }

          entity.setTarget(
            new PVector(localX, localY, lift),
            new PVector(cubeSide, cubeSide, cubeSide),
            new PVector(normalizedMagnitude, (phaseAngle + PI) / TWO_PI, deltaComplex),
            frameIndex,
            motionDuration
          );
          entity.update(frameIndex);

          float diagWeight = 1.0;
          float diagonalAlpha = lerp(OFFDIAG_FADE, 1.0, clampFloat(diagWeight, 0.0, 1.0));

          float luminanceBoost = layer.isActive ? actorInfluence * 0.09 : 0.0;
          int fillColor = applyLuminanceDim(luminanceColor(entity.curValue.x + luminanceBoost), revealDim);
          fillColor = applyAlphaDim(fillColor, layerAlpha * diagonalAlpha);
          int edgeColor = phaseEdgeColor(entity.curValue.y, changed, actorInfluence, normalizedDelta);
          edgeColor = applyAlphaDim(edgeColor, revealDim * layerAlpha * diagonalAlpha);
          boolean replaySourceLayer = shotSourcePhase && layer.isActive && shotSourceCell != null;
          boolean sourceCellActive = replaySourceLayer && row == shotSourceCell.row && col == shotSourceCell.col;
          if (replaySourceLayer && !sourceCellActive) {
            float dimFactor = "shot_stack".equals(playback.phase) ? SHOT_SOURCE_DIM_STACK : SHOT_SOURCE_DIM_PROJECT;
            fillColor = applyLuminanceDim(fillColor, dimFactor);
            fillColor = applyAlphaDim(fillColor, dimFactor);
            edgeColor = applyAlphaDim(edgeColor, dimFactor);
          }
          drawCubeCell(entity, fillColor, edgeColor, changed, actorInfluence, activeLayerVisual);
          if (sourceCellActive) {
            drawShotReplaySourceCellHighlight(entity, playback);
          }
          if (activeLayerVisual) {
            int rank = influenceMap.rankAt(row, col);
            boolean inSourceSet = rank >= 0 && rank < sourceSetCount;
            boolean inActiveFrontier = rank >= 0 && abs(rank - frontier) <= max(1.0, influenceMap.total * 0.10);
            boolean inTargetSet = rank >= 0
              && reachedCount > 0
              && rank < reachedCount
              && rank >= max(0, reachedCount - targetSetCount);
            drawHandoffCellOverlay(entity, inSourceSet, inActiveFrontier, inTargetSet, actorInfluence, beat);
          }
        }
      }
    }

    if (decompositionState.active) {
      drawDecompositionOverlay(geometry, decompositionState, revealDim);
    }
    drawShotReplayDensityRelayPulse(geometry, playback, renderLayers);
    drawShotReplayQubitLayer(geometry, playback, renderLayers, traceModel, frameIndex);
    drawShotReplayHistogram(geometry, playback, traceModel, frameIndex);

    rectMode(CORNER);
    popMatrix();
    pruneStaleRhoEntities(renderedEntityKeys);
    return true;
  }

  void drawShotReplayQubitLayer(
    MatrixViewMetrics geometry,
    PlaybackState playback,
    ArrayList<DensityLayerFrame> renderLayers,
    TraceModel traceModel,
    int frameIndex
  ) {
    if (geometry == null || playback == null || traceModel == null || !playback.inShotReplay || !traceModel.hasShotReplay()) {
      pruneStaleShotQubitEntities(new HashSet<String>());
      shotQubitLabelSprites.clear();
      hudShotActiveContributorQubit = -1;
      hudShotActiveContributorCount = -1;
      return;
    }

    int[] displayQubits = resolveReplayDisplayQubits(traceModel);
    if (displayQubits.length == 0) {
      pruneStaleShotQubitEntities(new HashSet<String>());
      shotQubitLabelSprites.clear();
      hudShotActiveContributorQubit = -1;
      hudShotActiveContributorCount = -1;
      return;
    }
    hudShotActiveContributorQubit = -1;
    hudShotActiveContributorCount = -1;
    if ("shot_camera_pullback".equals(playback.phase)) {
      pruneStaleShotQubitEntities(new HashSet<String>());
      shotQubitLabelSprites.clear();
      return;
    }

    float qubitFrontZ = shotReplayQubitFrontZ(geometry);
    float histogramFrontZ = shotReplayHistogramFrontZ(geometry);
    float qubitFinalY = 0.0;
    float span = geometry.matrixW * SHOT_QUBIT_LAYER_SPAN_RATIO;
    float spacing = displayQubits.length <= 1 ? 0.0 : span / float(displayQubits.length - 1);
    float cubeSide = clampFloat(
      geometry.cubeSize * SHOT_QUBIT_CUBE_SIZE_RATIO,
      SHOT_QUBIT_CUBE_MIN_SIZE,
      SHOT_QUBIT_CUBE_MAX_SIZE
    );
    float baseCubeDepth = clampFloat(cubeSide * 0.92, SHOT_QUBIT_CUBE_MIN_SIZE * 0.85, SHOT_QUBIT_CUBE_MAX_SIZE * 0.96);

    float spreadAlpha = 1.0;
    float phaseAlpha = 1.0;
    if ("shot_camera_pullback".equals(playback.phase)) {
      spreadAlpha = easeInOutCirc01(playback.phaseProgress);
      phaseAlpha = clampFloat(0.15 + 0.85 * spreadAlpha, 0.0, 1.0);
    } else if ("shot_histogram_project".equals(playback.phase) && playback.shotIndex < 0) {
      spreadAlpha = 1.0;
      phaseAlpha = clampFloat(0.70 + 0.30 * playback.phaseProgress, 0.0, 1.0);
    }
    float histogramRevealAlpha = resolveShotHistogramRevealAlpha(playback);

    String currentOutcomeLabel = resolveReplayOutcomeLabel(playback, traceModel);
    String previousOutcomeLabel = resolvePreviousReplayOutcomeLabel(playback, traceModel, currentOutcomeLabel);
    boolean stackPhase = "shot_stack".equals(playback.phase);
    boolean projectPhase = "shot_histogram_project".equals(playback.phase);
    boolean projectionSubPhase = projectPhase && playback.shotIndex >= 0;
    String shotBeat = stackPhase ? playback.shotBeat : "";
    float shotBeatProgress = stackPhase ? clampFloat(playback.shotBeatProgress, 0.0, 1.0) : 0.0;
    boolean beatLock = stackPhase && "lock_density".equals(shotBeat);
    boolean beatEmit = stackPhase && "emit".equals(shotBeat);
    boolean beatCollapse = stackPhase && "collapse".equals(shotBeat);
    boolean beatSettle = stackPhase && "stack_settle".equals(shotBeat);
    boolean beatEmitOrCollapse = beatEmit || beatCollapse;
    ShotSourceCell responsibleSourceCell = stackPhase
      ? resolveShotReplayResponsibleSourceCell(playback, traceModel, geometry)
      : null;
    float beatLinkAlpha = 0.0;
    if (beatEmit) {
      beatLinkAlpha = 0.45 + 0.55 * easeInOutCirc01(shotBeatProgress);
    } else if (beatCollapse) {
      beatLinkAlpha = 1.00 - 0.20 * easeInOutCirc01(shotBeatProgress);
    }
    float stackMorph = stackPhase ? easeInOutCirc01(playback.shotProgress) : 1.0;
    float stackPulse = stackPhase || projectionSubPhase
      ? lerp(SHOT_QUBIT_STACK_PULSE_MIN, SHOT_QUBIT_STACK_PULSE_MAX, sin(PI * clampFloat(playback.shotProgress, 0.0, 1.0)))
      : 0.0;

    int shotsTotal = max(0, playback.shotsTotal);
    int stackHead = -1;
    if (stackPhase) {
      stackHead = playback.shotIndex >= 0 ? clampInt(playback.shotIndex, 0, max(0, shotsTotal - 1)) : -1;
    } else if (projectPhase) {
      stackHead = shotsTotal > 0 ? shotsTotal - 1 : -1;
    }
    boolean hasStackLayers = stackHead >= 0;
    float maxStackCuboidDepth = resolveShotReplayMaxStackCuboidDepth(baseCubeDepth);
    float effectiveMaxDepthOffset = resolveShotReplayEffectiveMaxDepthOffset(
      geometry,
      shotsTotal,
      qubitFrontZ,
      cubeSide,
      maxStackCuboidDepth
    );
    float shotCuboidDepth = resolveShotReplayCuboidDepth(
      shotsTotal,
      baseCubeDepth,
      maxStackCuboidDepth,
      effectiveMaxDepthOffset
    );
    float previewSpawnCenterZ = resolveShotReplaySpawnCenterZ(geometry, baseCubeDepth, cubeSide);
    int activeProjectionShot = projectionSubPhase ? clampInt(playback.shotIndex, 0, max(0, shotsTotal - 1)) : -1;
    String activeProjectionLabel = projectionSubPhase
      ? resolveActiveProjectionHistogramLabel(playback, traceModel)
      : "";

    HashMap<String, Float> histogramXByLabel = new HashMap<String, Float>();
    ArrayList<String> histogramLabels = traceModel.shotReplayOutcomeLabels();
    if (histogramLabels == null || histogramLabels.isEmpty()) {
      histogramLabels = new ArrayList<String>();
      if (playback.sample != null && playback.sample.probabilities != null) {
        histogramLabels.addAll(playback.sample.probabilities.keySet());
      }
    }
    Collections.sort(histogramLabels);
    for (int labelIndex = 0; labelIndex < histogramLabels.size(); labelIndex += 1) {
      String label = histogramLabels.get(labelIndex);
      float finalX = histogramLabels.size() <= 1
        ? 0.0
        : -(geometry.matrixW * SHOT_PROJECT_SPAN_RATIO) * 0.5
          + labelIndex * ((geometry.matrixW * SHOT_PROJECT_SPAN_RATIO) / float(histogramLabels.size() - 1));
      float phasedX = resolveShotHistogramXAtPhase(playback, finalX);
      histogramXByLabel.put(label, phasedX);
    }
    String linkedLabel = activeProjectionLabel.length() > 0 ? activeProjectionLabel : currentOutcomeLabel;
    float linkedHistogramX = histogramXByLabel.containsKey(linkedLabel)
      ? histogramXByLabel.get(linkedLabel)
      : 0.0;
    ReducedDensitySample sourceDensityBlock = stackPhase ? selectPreferredBlock(playback.sample) : null;
    if (stackPhase && sourceDensityBlock == null) {
      sourceDensityBlock = resolveShotReplaySourceDensityBlock(traceModel);
    }
    boolean showProjectionLinks = projectionSubPhase && histogramRevealAlpha > 1e-5;
    float linkAlpha = showProjectionLinks
      ? clampFloat(120.0 + 110.0 * stackPulse, 0.0, 230.0) * histogramRevealAlpha
      : 0.0;

    HashSet<String> renderedKeys = new HashSet<String>();
    ArrayList<ShotQubitLabelSprite> labelSprites = new ArrayList<ShotQubitLabelSprite>();
    boolean hasDensityLayers = renderLayers != null && !renderLayers.isEmpty();

    if (!hasStackLayers) {
      for (int i = 0; i < displayQubits.length; i += 1) {
        int qubit = displayQubits[i];
        int measuredBitIndex = measurementBitIndexForQubit(traceModel, qubit);
        int currentBit = decodeOutcomeBitForMeasuredIndex(currentOutcomeLabel, measuredBitIndex);
        float bitValue = currentBit >= 0 ? float(currentBit) : 0.5;

        float finalX = displayQubits.length <= 1 ? 0.0 : -span * 0.5 + i * spacing;
        float x = lerp(0.0, finalX, spreadAlpha);
        float y = qubitFinalY;
        float z = lerp(previewSpawnCenterZ, qubitFrontZ, spreadAlpha);
        String key = "qbit:preview:" + qubit;
        renderedKeys.add(key);
        MatrixCellEntity entity = shotQubitEntities.get(key);
        PVector targetPos = new PVector(x, y, z);
        PVector targetSize = new PVector(cubeSide, cubeSide, baseCubeDepth);
        PVector targetValue = new PVector(bitValue, currentBit >= 0 ? 1.0 : 0.0, 0.0);
        if (entity == null) {
          entity = new MatrixCellEntity(targetPos, targetSize, targetValue, frameIndex, 14);
          shotQubitEntities.put(key, entity);
        }
        entity.setTarget(targetPos, targetSize, targetValue, frameIndex, 14);
        entity.update(frameIndex);
        int fillColor = resolveShotQubitFillColor(currentBit, entity.curValue.x, false, 1.0, phaseAlpha);
        int edgeColor = resolveShotQubitEdgeColor(currentBit, entity.curValue.x, false, 1.0, phaseAlpha, 0.0);
        drawCubeCell(entity, fillColor, edgeColor, false, 0.0, false);
      }
    } else {
      for (int shotLayerIndex = 0; shotLayerIndex <= stackHead; shotLayerIndex += 1) {
        ShotReplayEvent layerEvent = traceModel.resolveShotReplayEvent(shotLayerIndex);
        String layerOutcome = layerEvent != null ? layerEvent.outcomeLabel : "";
        String layerPrevOutcome = layerOutcome;
        if (stackPhase && shotLayerIndex == stackHead) {
          ShotReplayEvent prevEvent = traceModel.resolveShotReplayEvent(stackHead - 1);
          if (prevEvent != null && prevEvent.outcomeLabel != null && prevEvent.outcomeLabel.length() > 0) {
            layerPrevOutcome = prevEvent.outcomeLabel;
          } else if (previousOutcomeLabel != null && previousOutcomeLabel.length() > 0) {
            layerPrevOutcome = previousOutcomeLabel;
          }
        }

        float layerAge = resolveShotReplayVisualAge(shotsTotal, shotLayerIndex);
        float depthOffset = resolveShotReplaySlotDepthOffset(shotsTotal, shotLayerIndex, effectiveMaxDepthOffset);
        boolean activeStackLayer = stackPhase && shotLayerIndex == stackHead;
        boolean activeProjectionLayer = projectionSubPhase && shotLayerIndex == activeProjectionShot;
        boolean activeLayer = activeStackLayer || activeProjectionLayer;
        float layerPulse = activeLayer
          ? lerp(SHOT_QUBIT_STACK_PULSE_MIN, SHOT_QUBIT_STACK_PULSE_MAX, sin(PI * clampFloat(playback.shotProgress, 0.0, 1.0)))
          : 0.0;
        float ageAlpha = clampFloat(1.0 - layerAge * 0.015, 0.24, 1.0);

        for (int i = 0; i < displayQubits.length; i += 1) {
          int qubit = displayQubits[i];
          int measuredBitIndex = measurementBitIndexForQubit(traceModel, qubit);
          int currentBit = decodeOutcomeBitForMeasuredIndex(layerOutcome, measuredBitIndex);
          int previousBit = decodeOutcomeBitForMeasuredIndex(layerPrevOutcome, measuredBitIndex);
          if (previousBit < 0 && currentBit >= 0) {
            previousBit = currentBit;
          }
          if (currentBit < 0 && previousBit >= 0) {
            currentBit = previousBit;
          }

          float prevBitValue = previousBit >= 0 ? float(previousBit) : 0.5;
          float currBitValue = currentBit >= 0 ? float(currentBit) : prevBitValue;
          float sourceBitValue = resolveShotReplayMarginalP1ForQubit(sourceDensityBlock, qubit);
          if (sourceBitValue < 0.0) {
            sourceBitValue = lerp(prevBitValue, currBitValue, stackMorph);
          }
          sourceBitValue = clampFloat(sourceBitValue, 0.0, 1.0);

          float finalX = displayQubits.length <= 1 ? 0.0 : -span * 0.5 + i * spacing;
          float slotX = finalX;
          float slotY = qubitFinalY;
          float slotZ = qubitFrontZ - depthOffset;
          String contributorBeat = beatCollapse ? "collapse" : "emit";
          float contributorBeatProgress = beatCollapse ? shotBeatProgress : 0.0;
          ArrayList<CellDeltaSample> fallbackSourceCells = activeStackLayer
            ? resolveShotReplayEmissionSourceCellsForQubit(
              geometry,
              sourceDensityBlock,
              qubit,
              currentBit,
              contributorBeat,
              contributorBeatProgress,
              SHOT_EMISSION_SOURCE_TOP_K
            )
            : new ArrayList<CellDeltaSample>();
          ArrayList<CellDeltaSample> qubitSourceCells = activeStackLayer
            ? resolveShotReplayEmissionCellsForShotSourceCell(responsibleSourceCell, currentBit)
            : new ArrayList<CellDeltaSample>();
          if (qubitSourceCells.isEmpty()) {
            qubitSourceCells = fallbackSourceCells;
          }

          PVector originPos = !qubitSourceCells.isEmpty()
            ? resolveShotReplayContributorAnchor(geometry, qubitSourceCells, cubeSide, shotCuboidDepth)
            : resolveShotReplayDensityFallbackOrigin(geometry, slotX, slotY, cubeSide, shotCuboidDepth);
          PVector slotPos = new PVector(slotX, slotY, slotZ);
          float x = slotX;
          float y = slotY;
          float z = slotZ;
          float bitValue = currBitValue;
          float emissionTravelProgress = clampFloat(stackMorph, 0.0, 1.0);
          if (activeStackLayer) {
            float travelAlpha = resolveShotReplayStackTravelAlpha(shotBeat, shotBeatProgress, stackMorph);
            emissionTravelProgress = travelAlpha;
            if (beatLock) {
              bitValue = prevBitValue;
            } else if (beatEmit) {
              float emitMorph = easeInOutCirc01(shotBeatProgress);
              bitValue = lerp(prevBitValue, sourceBitValue, emitMorph);
            } else if (beatCollapse) {
              float collapseMorph = easeInOutCirc01(shotBeatProgress);
              bitValue = lerp(sourceBitValue, currBitValue, collapseMorph);
            } else if (beatSettle) {
              bitValue = currBitValue;
            } else {
              bitValue = lerp(prevBitValue, currBitValue, stackMorph);
            }
            PVector travelPos = PVector.lerp(originPos, slotPos, clampFloat(travelAlpha, 0.0, 1.0));
            x = travelPos.x;
            y = travelPos.y;
            z = travelPos.z;
            if (beatLock) {
              y += cubeSide * 0.03 * sin(PI * clampFloat(shotBeatProgress, 0.0, 1.0));
            }
          }
          bitValue = clampFloat(bitValue, 0.0, 1.0);

          String key = "qbit:" + shotLayerIndex + ":" + qubit;
          renderedKeys.add(key);
          MatrixCellEntity entity = shotQubitEntities.get(key);
          PVector targetPos = new PVector(x, y, z);
          PVector targetSize = new PVector(cubeSide, cubeSide, shotCuboidDepth);
          PVector targetValue = new PVector(bitValue, currentBit >= 0 ? 1.0 : 0.0, layerAge);
          if (entity == null) {
            entity = new MatrixCellEntity(targetPos, targetSize, targetValue, frameIndex, 10);
            shotQubitEntities.put(key, entity);
          }
          entity.snapTo(targetPos, targetSize, targetValue, frameIndex);

          if (activeStackLayer && beatEmitOrCollapse && !qubitSourceCells.isEmpty()) {
            drawShotReplayDensityToQubitLinks(
              geometry,
              entity,
              qubitSourceCells,
              cubeSide,
              shotCuboidDepth,
              beatLinkAlpha,
              layerPulse,
              emissionTravelProgress
            );
          }

          int fillColor = resolveShotQubitFillColor(currentBit, entity.curValue.x, activeLayer, ageAlpha, phaseAlpha);
          int edgeColor = resolveShotQubitEdgeColor(
            currentBit,
            entity.curValue.x,
            activeLayer,
            ageAlpha,
            phaseAlpha,
            activeLayer ? layerPulse : 0.0
          );
          boolean changed = activeStackLayer && previousBit >= 0 && currentBit >= 0 && previousBit != currentBit;
          drawCubeCell(entity, fillColor, edgeColor, changed, activeLayer ? layerPulse : 0.0, activeLayer);

          if (activeStackLayer && hudShotActiveContributorQubit < 0) {
            hudShotActiveContributorQubit = qubit;
            hudShotActiveContributorCount = qubitSourceCells.size();
          }

          if (showProjectionLinks && activeProjectionLayer) {
            stroke(232, 222, 196, linkAlpha);
            strokeWeight(1.0 + 1.2 * layerPulse);
            line(
              entity.curPos.x,
              entity.curPos.y - cubeSide * 0.18,
              entity.curPos.z + shotCuboidDepth * 0.54,
              linkedHistogramX,
              0.0,
              histogramFrontZ - 0.25
            );
            noStroke();
          }

          if (activeLayer && hasDensityLayers) {
            float labelWorldX = entity.curPos.x;
            float labelWorldY = entity.curPos.y - cubeSide * 0.62;
            float labelWorldZ = entity.curPos.z + shotCuboidDepth * 0.58;
            if (activeStackLayer && stackPhase) {
              labelWorldX = slotX;
              labelWorldY = slotY - cubeSide * 0.62;
              labelWorldZ = slotZ + shotCuboidDepth * 0.58;
            }
            float labelX = screenX(labelWorldX, labelWorldY, labelWorldZ);
            float labelY = screenY(labelWorldX, labelWorldY, labelWorldZ);
            if (Float.isFinite(labelX) && Float.isFinite(labelY)) {
              float labelAlpha = clampFloat(0.55 + 0.45 * (phaseAlpha * ageAlpha), 0.0, 1.0);
              labelSprites.add(
                new ShotQubitLabelSprite("q" + qubit, labelX, labelY, labelAlpha, true)
              );
            }
          }
        }
      }
    }

    shotQubitLabelSprites.clear();
    shotQubitLabelSprites.addAll(labelSprites);
    pruneStaleShotQubitEntities(renderedKeys);
  }

  float resolveShotReplayStackTravelAlpha(String shotBeat, float shotBeatProgress, float fallbackAlpha) {
    String beat = shotBeat != null ? shotBeat : "";
    float progress = clampFloat(shotBeatProgress, 0.0, 1.0);
    if ("lock_density".equals(beat)) {
      return 0.0;
    }
    if ("emit".equals(beat)) {
      return lerp(0.0, 0.72, easeInOutCirc01(progress));
    }
    if ("collapse".equals(beat)) {
      return lerp(0.72, 1.0, easeInOutCirc01(progress));
    }
    if ("stack_settle".equals(beat)) {
      return 1.0;
    }
    return clampFloat(fallbackAlpha, 0.0, 1.0);
  }

  PVector resolveShotReplayDensityFallbackOrigin(
    MatrixViewMetrics geometry,
    float slotX,
    float slotY,
    float cubeSide,
    float shotCuboidDepth
  ) {
    float sourceZ = shotReplayMatrixFrontZ(geometry) + max(0.9, geometry.cubeSize * 0.20);
    float zNudge = clampFloat(max(cubeSide, shotCuboidDepth) * 0.06, 0.14, 1.0);
    return new PVector(slotX, slotY, sourceZ + zNudge);
  }

  float resolveShotDensityRelayFront(String shotBeat, float shotBeatProgress) {
    String beat = shotBeat != null ? shotBeat : "";
    float progress = clampFloat(shotBeatProgress, 0.0, 1.0);
    if ("lock_density".equals(beat)) {
      return 0.0;
    }
    if ("emit".equals(beat)) {
      return 0.5 * easeInOutCirc01(progress);
    }
    if ("collapse".equals(beat)) {
      return 0.5 + 0.5 * easeInOutCirc01(progress);
    }
    if ("stack_settle".equals(beat)) {
      return 1.0;
    }
    return 0.0;
  }

  void drawShotReplayDensityRelayPulse(
    MatrixViewMetrics geometry,
    PlaybackState playback,
    ArrayList<DensityLayerFrame> renderLayers
  ) {
    if (geometry == null || playback == null || renderLayers == null || renderLayers.isEmpty()) {
      return;
    }
    if (!"shot_stack".equals(playback.phase)) {
      return;
    }

    String shotBeat = playback.shotBeat != null ? playback.shotBeat : "";
    if (!"emit".equals(shotBeat) && !"collapse".equals(shotBeat)) {
      return;
    }

    ArrayList<DensityLayerFrame> orderedLayers = new ArrayList<DensityLayerFrame>();
    for (DensityLayerFrame layer : renderLayers) {
      if (layer != null && isRectangular(layer.real, layer.imag)) {
        orderedLayers.add(layer);
      }
    }
    if (orderedLayers.isEmpty()) {
      return;
    }
    Collections.sort(orderedLayers, new Comparator<DensityLayerFrame>() {
      public int compare(DensityLayerFrame a, DensityLayerFrame b) {
        if (a.age != b.age) {
          return b.age - a.age;
        }
        return a.stepIndex - b.stepIndex;
      }
    });

    float relayFront = resolveShotDensityRelayFront(shotBeat, playback.shotBeatProgress);
    float safeBand = max(0.02, SHOT_DENSITY_RELAY_BAND);
    int layerCount = orderedLayers.size();
    float depthStep = resolveGuaranteedDepthStep(geometry.cubeSize);
    float lateralBudgetX = resolveStackLateralBudgetX(geometry, layerCount);
    float lateralBudgetY = resolveStackLateralBudgetY(geometry, layerCount);
    float pulseGlobal = sin(PI * clampFloat(playback.shotProgress, 0.0, 1.0));

    pushStyle();
    rectMode(CENTER);
    noFill();
    for (int i = 0; i < layerCount; i += 1) {
      DensityLayerFrame layer = orderedLayers.get(i);
      float layerNorm = layerCount <= 1 ? 1.0 : i / float(max(1, layerCount - 1));
      float distance = abs(layerNorm - relayFront);
      if (distance > safeBand) {
        continue;
      }

      float activation = clampFloat(1.0 - distance / safeBand, 0.0, 1.0);
      activation = smoothstep01(activation);
      float alphaValue = lerp(SHOT_DENSITY_RELAY_MIN_ALPHA, SHOT_DENSITY_RELAY_MAX_ALPHA, activation);
      float strokeValue = lerp(SHOT_DENSITY_RELAY_MIN_STROKE, SHOT_DENSITY_RELAY_MAX_STROKE, activation);
      float phasePulse = 0.82 + 0.18 * pulseGlobal;

      int age = max(0, layer.age);
      float driftNorm = 1.0 - pow(STACK_DRIFT_DECAY, age);
      float layerXOffset = -driftNorm * lateralBudgetX;
      float layerYOffset = driftNorm * lateralBudgetY;
      float layerScaleAttenuation = clampFloat(1.0 - age * LAYER_SCALE_DECAY_PER_AGE, 0.72, 1.0);
      float cubeSide = geometry.cubeSize * 0.92 * layerScaleAttenuation;
      float layerZOffset = -age * depthStep;
      float frontZ = 1.10 + cubeSide + layerZOffset + 0.24;
      float outlineW = geometry.matrixW + geometry.pitch * (0.22 + 0.10 * activation);
      float outlineH = geometry.matrixH + geometry.pitch * (0.22 + 0.10 * activation);

      stroke(236, 229, 206, clampFloat(alphaValue * phasePulse, 0.0, 255.0));
      strokeWeight(strokeValue);
      pushMatrix();
      translate(layerXOffset, layerYOffset, frontZ);
      rect(0, 0, outlineW, outlineH, 2.0);
      stroke(246, 240, 214, clampFloat((alphaValue + 18.0) * phasePulse, 0.0, 255.0));
      strokeWeight(max(0.5, strokeValue * 0.72));
      float railY = outlineH * 0.5 + 1.2;
      line(-outlineW * 0.5, railY, 0.0, outlineW * 0.5, railY, 0.0);
      popMatrix();
    }
    popStyle();
  }

  float shotReplayMatrixFrontZ(MatrixViewMetrics geometry) {
    if (geometry == null) {
      return 8.0;
    }
    return 1.10 + geometry.cubeSize * 0.92;
  }

  float shotReplayLayerGap(MatrixViewMetrics geometry) {
    if (geometry == null) {
      return SHOT_QUBIT_MIN_HIST_GAP * SHOT_REPLAY_LAYER_GAP_SCALE;
    }
    float baseGap = max(SHOT_QUBIT_MIN_HIST_GAP, geometry.cubeSize * SHOT_QUBIT_HIST_GAP_CUBE_MULT);
    return baseGap * SHOT_REPLAY_LAYER_GAP_SCALE;
  }

  float shotReplayHistogramFrontZ(MatrixViewMetrics geometry) {
    return shotReplayQubitFrontZ(geometry) + shotReplayLayerGap(geometry);
  }

  float shotReplayQubitFrontZ(MatrixViewMetrics geometry) {
    return shotReplayMatrixFrontZ(geometry) + shotReplayLayerGap(geometry);
  }

  float resolveShotReplayBaseDepthStep(MatrixViewMetrics geometry) {
    if (geometry == null) {
      return SHOT_STACK_DEPTH_BASE_MIN;
    }
    return clampFloat(
      geometry.cubeSize * SHOT_STACK_DEPTH_BASE_MULT,
      SHOT_STACK_DEPTH_BASE_MIN,
      SHOT_STACK_DEPTH_BASE_MAX
    );
  }

  float resolveShotReplayDepthOffset(MatrixViewMetrics geometry, float age) {
    float safeAge = max(0.0, age);
    float baseStep = resolveShotReplayBaseDepthStep(geometry);
    float linearAge = min(float(SHOT_STACK_SOFT_CAP_LINEAR_LAYERS), safeAge);
    float tailAge = max(0.0, safeAge - float(SHOT_STACK_SOFT_CAP_LINEAR_LAYERS));
    return linearAge * baseStep + tailAge * baseStep * SHOT_STACK_TAIL_COMPRESS_RATIO;
  }

  float resolveShotReplayMaxDepthOffset(MatrixViewMetrics geometry, int shotsTotal) {
    return resolveShotReplayDepthOffset(geometry, max(0.0, float(shotsTotal - 1)));
  }

  float resolveShotReplaySlotDepthOffset(int shotsTotal, int shotLayerIndex, float maxDepthOffset) {
    if (shotsTotal <= 1) {
      return 0.0;
    }
    int clampedShot = clampInt(shotLayerIndex, 0, max(0, shotsTotal - 1));
    int slotFromFront = max(0, shotsTotal - 1 - clampedShot);
    float slotRatio = slotFromFront / float(max(1, shotsTotal - 1));
    return max(0.0, maxDepthOffset) * slotRatio;
  }

  float resolveShotReplayVisualAge(int shotsTotal, int shotLayerIndex) {
    if (shotsTotal <= 1) {
      return 0.0;
    }
    int clampedShot = clampInt(shotLayerIndex, 0, max(0, shotsTotal - 1));
    return max(0, shotsTotal - 1 - clampedShot);
  }

  float resolveShotReplayFrontSafeMaxDepthOffset(
    MatrixViewMetrics geometry,
    float qubitFrontZ,
    float cubeSide,
    float clearanceDepth
  ) {
    float densityFrontZ = resolveShotReplayDensityRenderedFrontZ(geometry);
    float spawnGap = resolveShotReplaySpawnFrontGap(geometry, cubeSide);
    float minLayerCenterZ = densityFrontZ + spawnGap + max(0.0, clearanceDepth) * 0.5;
    return max(0.0, qubitFrontZ - minLayerCenterZ);
  }

  float resolveShotReplayEffectiveMaxDepthOffset(
    MatrixViewMetrics geometry,
    int shotsTotal,
    float qubitFrontZ,
    float cubeSide,
    float clearanceDepth
  ) {
    float rawMaxOffset = resolveShotReplayMaxDepthOffset(geometry, shotsTotal);
    float frontSafeMaxOffset = resolveShotReplayFrontSafeMaxDepthOffset(
      geometry,
      qubitFrontZ,
      cubeSide,
      clearanceDepth
    );
    return min(rawMaxOffset, frontSafeMaxOffset);
  }

  float resolveShotReplayMaxStackCuboidDepth(float baseCubeDepth) {
    float safeBaseDepth = max(0.0, baseCubeDepth);
    float maxStackDepth = safeBaseDepth * SHOT_QUBIT_STACK_DEPTH_MULTIPLIER;
    return max(SHOT_QUBIT_CUBOID_MIN_DEPTH, maxStackDepth);
  }

  float resolveShotReplayCuboidDepth(
    int shotsTotal,
    float baseCubeDepth,
    float maxStackCuboidDepth,
    float maxDepthOffset
  ) {
    float safeBaseDepth = max(0.0, baseCubeDepth);
    float safeMaxStackDepth = max(SHOT_QUBIT_CUBOID_MIN_DEPTH, maxStackCuboidDepth);
    int safeShots = max(1, shotsTotal);
    float safeMaxOffset = max(0.0, maxDepthOffset);
    float pillarDepth = max(safeBaseDepth, safeMaxOffset + safeBaseDepth);
    float scaledDepth = pillarDepth / float(safeShots);
    float blendedDepth = lerp(safeBaseDepth, scaledDepth, clampFloat(SHOT_QUBIT_CUBOID_DEPTH_BLEND, 0.0, 1.0));
    float elongatedDepth = blendedDepth * SHOT_QUBIT_STACK_DEPTH_MULTIPLIER;
    return clampFloat(elongatedDepth, SHOT_QUBIT_CUBOID_MIN_DEPTH, safeMaxStackDepth);
  }

  float resolveShotReplaySpawnFrontGap(MatrixViewMetrics geometry, float cubeSide) {
    if (geometry == null) {
      return clampFloat(max(0.0, cubeSide) * 0.16, 2.4, 7.0);
    }
    float safeCubeSide = max(0.0, cubeSide);
    return clampFloat(safeCubeSide * 0.16, 2.4, 7.0);
  }

  float resolveShotReplayDensityRenderedFrontZ(MatrixViewMetrics geometry) {
    if (geometry == null) {
      return 1.10 + 52.0 + 0.35;
    }
    // Active density front bound: lift(1.10 + cubeSide*0.5 + actorLift) + half cubeSide.
    // For actorLift=0.35 and cubeSide~=geometry.cubeSize, front ~= 1.10 + cubeSize + 0.35.
    return 1.10 + geometry.cubeSize + 0.35;
  }

  float resolveShotReplaySpawnCenterZ(MatrixViewMetrics geometry, float cuboidDepth, float cubeSide) {
    float densityFrontZ = resolveShotReplayDensityRenderedFrontZ(geometry);
    float spawnGap = resolveShotReplaySpawnFrontGap(geometry, cubeSide);
    return densityFrontZ + spawnGap + max(0.0, cuboidDepth) * 0.5;
  }

  float resolveShotProjectMoveAlpha(float phaseProgress) {
    float eased = easeInOutSine01(phaseProgress);
    if (eased <= SHOT_PROJECT_CAMERA_HOLD_FRACTION) {
      return 0.0;
    }
    float denom = max(1e-5, 1.0 - SHOT_PROJECT_CAMERA_HOLD_FRACTION);
    return clampFloat((eased - SHOT_PROJECT_CAMERA_HOLD_FRACTION) / denom, 0.0, 1.0);
  }

  float resolveShotHistogramRevealAlpha(PlaybackState playback) {
    if (playback == null) {
      return 0.0;
    }
    if ("shot_camera_pullback".equals(playback.phase)) {
      return 0.0;
    }
    if ("shot_stack".equals(playback.phase)) {
      return 0.0;
    }
    if ("shot_histogram_project".equals(playback.phase)) {
      if (playback.shotIndex >= 0) {
        return 1.0;
      }
      return resolveShotProjectMoveAlpha(playback.phaseProgress);
    }
    return 0.0;
  }

  float resolveShotHistogramXAtPhase(PlaybackState playback, float finalX) {
    if (playback == null) {
      return finalX;
    }
    if ("shot_camera_pullback".equals(playback.phase)) {
      return 0.0;
    }
    if ("shot_stack".equals(playback.phase)) {
      return 0.0;
    }
    if ("shot_histogram_project".equals(playback.phase)) {
      if (playback.shotIndex >= 0) {
        return finalX;
      }
      float moveAlpha = resolveShotProjectMoveAlpha(playback.phaseProgress);
      if (moveAlpha <= 1e-5 || moveAlpha < SHOT_PROJECT_PULSE_FRACTION) {
        return 0.0;
      }
      float spreadAlpha = smoothstep01(
        (moveAlpha - SHOT_PROJECT_PULSE_FRACTION) / max(1e-5, (1.0 - SHOT_PROJECT_PULSE_FRACTION))
      );
      return lerp(0.0, finalX, spreadAlpha);
    }
    return finalX;
  }

  int[] resolveReplayDisplayQubits(TraceModel traceModel) {
    if (traceModel == null || traceModel.measurementShotReplay == null) {
      return new int[0];
    }
    int[] measured = traceModel.measurementShotReplay.measuredQubits;
    if (measured == null || measured.length == 0) {
      return new int[0];
    }
    ArrayList<Integer> unique = new ArrayList<Integer>();
    for (int value : measured) {
      if (value < 0) {
        continue;
      }
      boolean exists = false;
      for (int existing : unique) {
        if (existing == value) {
          exists = true;
          break;
        }
      }
      if (!exists) {
        unique.add(value);
      }
    }
    Collections.sort(unique);
    int[] sorted = new int[unique.size()];
    for (int i = 0; i < unique.size(); i += 1) {
      sorted[i] = unique.get(i);
    }
    return sorted;
  }

  int measurementBitIndexForQubit(TraceModel traceModel, int qubit) {
    if (traceModel == null || traceModel.measurementShotReplay == null) {
      return -1;
    }
    int[] measured = traceModel.measurementShotReplay.measuredQubits;
    if (measured == null || measured.length == 0) {
      return -1;
    }
    for (int i = 0; i < measured.length; i += 1) {
      if (measured[i] == qubit) {
        return i;
      }
    }
    return -1;
  }

  String resolveReplayOutcomeLabel(PlaybackState playback, TraceModel traceModel) {
    if (playback != null && playback.shotOutcomeLabel != null && playback.shotOutcomeLabel.length() > 0) {
      return playback.shotOutcomeLabel;
    }
    String byStateHash = resolveOutcomeLabelForStateHash(
      playback != null && playback.sample != null ? playback.sample.stateHash : "",
      traceModel
    );
    if (byStateHash.length() > 0) {
      return byStateHash;
    }
    if (traceModel != null && traceModel.selectedOutcome != null && traceModel.selectedOutcome.length() > 0) {
      return traceModel.selectedOutcome;
    }
    return "";
  }

  String resolveActiveProjectionHistogramLabel(PlaybackState playback, TraceModel traceModel) {
    if (playback == null || traceModel == null || !"shot_histogram_project".equals(playback.phase) || playback.shotIndex < 0) {
      return "";
    }
    if (playback.shotOutcomeLabel != null && playback.shotOutcomeLabel.length() > 0) {
      return playback.shotOutcomeLabel;
    }
    if (traceModel.hasShotReplay()) {
      int clampedShotIndex = clampInt(playback.shotIndex, 0, max(0, traceModel.measurementShotReplay.shotEvents.size() - 1));
      ShotReplayEvent activeEvent = traceModel.resolveShotReplayEvent(clampedShotIndex);
      if (activeEvent != null && activeEvent.outcomeLabel != null && activeEvent.outcomeLabel.length() > 0) {
        return activeEvent.outcomeLabel;
      }
    }
    return resolveReplayOutcomeLabel(playback, traceModel);
  }

  String resolvePreviousReplayOutcomeLabel(
    PlaybackState playback,
    TraceModel traceModel,
    String fallback
  ) {
    String safeFallback = fallback != null ? fallback : "";
    if (playback == null || traceModel == null || !traceModel.hasShotReplay() || playback.shotIndex <= 0) {
      return safeFallback;
    }
    ShotReplayEvent event = traceModel.resolveShotReplayEvent(playback.shotIndex - 1);
    if (event != null && event.outcomeLabel != null && event.outcomeLabel.length() > 0) {
      return event.outcomeLabel;
    }
    return safeFallback;
  }

  String resolveOutcomeLabelForStateHash(String stateHash, TraceModel traceModel) {
    if (traceModel == null || traceModel.measurementShotReplay == null || stateHash == null || stateHash.length() == 0) {
      return "";
    }
    ShotReplayState state = traceModel.measurementShotReplay.outcomeStatesByHash.get(stateHash);
    if (state != null && state.label != null && state.label.length() > 0) {
      return state.label;
    }
    for (ShotReplayOutcome outcome : traceModel.measurementShotReplay.outcomes) {
      if (outcome == null || outcome.label == null || outcome.label.length() == 0) {
        continue;
      }
      if (outcome.stateHash != null && outcome.stateHash.equals(stateHash)) {
        return outcome.label;
      }
    }
    return "";
  }

  int decodeOutcomeBitForMeasuredIndex(String outcomeLabel, int measuredBitIndex) {
    if (outcomeLabel == null || outcomeLabel.length() == 0 || measuredBitIndex < 0) {
      return -1;
    }
    int charIndex = outcomeLabel.length() - 1 - measuredBitIndex;
    if (charIndex < 0 || charIndex >= outcomeLabel.length()) {
      return -1;
    }
    char bit = outcomeLabel.charAt(charIndex);
    if (bit == '0') {
      return 0;
    }
    if (bit == '1') {
      return 1;
    }
    return -1;
  }

  ReducedDensitySample resolveShotReplaySourceDensityBlock(TraceModel traceModel) {
    if (traceModel == null || !traceModel.hasShotReplay()) {
      return null;
    }
    FrameSample sourceSample = traceModel.resolveShotReplaySourceSample("shot_stack");
    return selectPreferredBlock(sourceSample);
  }

  boolean isShotReplaySourcePhase(PlaybackState playback) {
    if (playback == null || !playback.inShotReplay) {
      return false;
    }
    if ("shot_stack".equals(playback.phase)) {
      return playback.shotIndex >= 0;
    }
    if ("shot_histogram_project".equals(playback.phase)) {
      return playback.shotIndex >= 0;
    }
    return false;
  }

  ShotReplayState resolveShotReplayStateForEvent(
    TraceModel traceModel,
    ShotReplayEvent event
  ) {
    if (traceModel == null || event == null || traceModel.measurementShotReplay == null) {
      return null;
    }
    ShotReplayState byHash = traceModel.measurementShotReplay.outcomeStatesByHash.get(event.stateHash);
    if (byHash != null) {
      return byHash;
    }
    return traceModel.measurementShotReplay.outcomeStatesByLabel.get(event.outcomeLabel);
  }

  String formatBasisLabel(int basisIndex, int width) {
    int safeWidth = max(1, width);
    String raw = Integer.toBinaryString(max(0, basisIndex));
    if (raw.length() > safeWidth) {
      raw = raw.substring(raw.length() - safeWidth);
    }
    StringBuilder builder = new StringBuilder();
    for (int i = raw.length(); i < safeWidth; i += 1) {
      builder.append("0");
    }
    builder.append(raw);
    return "|" + builder.toString() + ">";
  }

  ShotSourceCell materializeShotSourceCell(ShotSourceCell sourceCell, MatrixViewMetrics geometry) {
    if (sourceCell == null || geometry == null) {
      return sourceCell;
    }
    int safeDim = max(1, sourceCell.basisDim);
    int[] coordinates = resolveShotReplayDiagonalCellCoordinates(geometry, safeDim, sourceCell.basisIndex);
    int row = coordinates[0];
    int col = coordinates[1];
    return new ShotSourceCell(
      row,
      col,
      geometry.localXForIndex(col),
      geometry.localYForIndex(row),
      sourceCell.basisIndex,
      safeDim,
      sourceCell.weight,
      sourceCell.basisLabel,
      sourceCell.stateHash,
      sourceCell.outcomeLabel,
      sourceCell.blockKey
    );
  }

  String shotSourceCacheKey(ShotReplayEvent event, ReducedDensitySample block, int dim) {
    String stateHash = event != null && event.stateHash != null ? event.stateHash : "";
    String outcomeLabel = event != null && event.outcomeLabel != null ? event.outcomeLabel : "";
    String blockKey = block != null && block.qubitKey != null ? block.qubitKey : "";
    return stateHash + "|" + outcomeLabel + "|" + blockKey + "|" + dim;
  }

  ShotSourceCell resolveShotReplayResponsibleSourceCell(
    PlaybackState playback,
    TraceModel traceModel,
    MatrixViewMetrics geometry
  ) {
    if (playback == null || traceModel == null || geometry == null || !isShotReplaySourcePhase(playback)) {
      return null;
    }
    if (!traceModel.hasShotReplay() || playback.shotIndex < 0) {
      return null;
    }

    ShotReplayEvent event = traceModel.resolveShotReplayEvent(playback.shotIndex);
    if (event == null) {
      return null;
    }
    ShotReplayState replayState = resolveShotReplayStateForEvent(traceModel, event);
    if (replayState == null) {
      return null;
    }

    ReducedDensitySample block = selectPreferredBlock(replayState.reducedDensityBlocks);
    if (block == null || !isRectangular(block.real, block.imag)) {
      return null;
    }
    int dim = min(block.real.length, block.real[0].length);
    if (dim <= 0) {
      return null;
    }

    String cacheKey = shotSourceCacheKey(event, block, dim);
    ShotSourceCell cached = shotSourceCellCache.get(cacheKey);
    if (cached != null) {
      return materializeShotSourceCell(cached, geometry);
    }

    int bestBasis = -1;
    float bestWeight = -1.0;
    float tieEps = 1e-7;
    for (int basis = 0; basis < dim; basis += 1) {
      float diagonal = max(0.0, matrixValue(block.real, basis, basis, 0.0));
      if (diagonal > bestWeight + tieEps) {
        bestWeight = diagonal;
        bestBasis = basis;
        continue;
      }
      if (abs(diagonal - bestWeight) <= tieEps && (bestBasis < 0 || basis < bestBasis)) {
        bestBasis = basis;
        bestWeight = diagonal;
      }
    }
    if (bestBasis < 0) {
      return null;
    }

    int safeWidth = block.qubits != null && block.qubits.length > 0
      ? block.qubits.length
      : max(1, round(log(max(1, dim)) / log(2)));
    int[] coordinates = resolveShotReplayDiagonalCellCoordinates(geometry, dim, bestBasis);
    int row = coordinates[0];
    int col = coordinates[1];
    ShotSourceCell resolved = new ShotSourceCell(
      row,
      col,
      geometry.localXForIndex(col),
      geometry.localYForIndex(row),
      bestBasis,
      dim,
      max(SHOT_EMISSION_MIN_PROBABILITY, bestWeight),
      formatBasisLabel(bestBasis, safeWidth),
      event.stateHash,
      event.outcomeLabel,
      block.qubitKey
    );
    shotSourceCellCache.put(cacheKey, resolved);
    return resolved;
  }

  ArrayList<CellDeltaSample> resolveShotReplayEmissionCellsForShotSourceCell(
    ShotSourceCell sourceCell,
    int sampledBit
  ) {
    ArrayList<CellDeltaSample> sources = new ArrayList<CellDeltaSample>();
    if (sourceCell == null) {
      return sources;
    }
    CellDeltaSample contributor = new CellDeltaSample(
      sourceCell.row,
      sourceCell.col,
      max(SHOT_EMISSION_MIN_PROBABILITY, sourceCell.weight),
      sourceCell.localX,
      sourceCell.localY
    );
    contributor.rank = sampledBit;
    sources.add(contributor);
    return sources;
  }

  float resolveShotReplayMarginalP1ForQubit(ReducedDensitySample sourceBlock, int qubit) {
    if (sourceBlock == null || !isRectangular(sourceBlock.real, sourceBlock.imag) || sourceBlock.qubits == null) {
      return -1.0;
    }
    int qubitBitIndex = -1;
    for (int i = 0; i < sourceBlock.qubits.length; i += 1) {
      if (sourceBlock.qubits[i] == qubit) {
        qubitBitIndex = i;
        break;
      }
    }
    if (qubitBitIndex < 0) {
      return -1.0;
    }

    int dim = min(sourceBlock.real.length, sourceBlock.real[0].length);
    if (dim <= 0) {
      return -1.0;
    }

    float trace = 0.0;
    float p1 = 0.0;
    for (int basis = 0; basis < dim; basis += 1) {
      float diag = max(0.0, matrixValue(sourceBlock.real, basis, basis, 0.0));
      trace += diag;
      if (((basis >> qubitBitIndex) & 1) == 1) {
        p1 += diag;
      }
    }

    if (trace <= 1e-8) {
      return 0.5;
    }
    return clampFloat(p1 / trace, 0.0, 1.0);
  }

  ArrayList<CellDeltaSample> resolveShotReplayEmissionSourceCellsForQubit(
    MatrixViewMetrics geometry,
    ReducedDensitySample sourceBlock,
    int qubit,
    int sampledBit,
    String shotBeat,
    float shotBeatProgress,
    int maxCells
  ) {
    ArrayList<CellDeltaSample> sources = new ArrayList<CellDeltaSample>();
    if (geometry == null || sourceBlock == null || !isRectangular(sourceBlock.real, sourceBlock.imag) || sourceBlock.qubits == null) {
      return sources;
    }

    if ("lock_density".equals(shotBeat) || "stack_settle".equals(shotBeat)) {
      return sources;
    }
    if (!"emit".equals(shotBeat) && !"collapse".equals(shotBeat)) {
      return sources;
    }

    int qubitBitIndex = -1;
    for (int i = 0; i < sourceBlock.qubits.length; i += 1) {
      if (sourceBlock.qubits[i] == qubit) {
        qubitBitIndex = i;
        break;
      }
    }
    if (qubitBitIndex < 0) {
      return sources;
    }

    int dim = min(sourceBlock.real.length, sourceBlock.real[0].length);
    if (dim <= 0) {
      return sources;
    }

    float trace = 0.0;
    for (int basis = 0; basis < dim; basis += 1) {
      trace += max(0.0, matrixValue(sourceBlock.real, basis, basis, 0.0));
    }
    if (trace <= SHOT_EMISSION_CONTRIBUTOR_THRESHOLD) {
      return sources;
    }

    ArrayList<CellDeltaSample> bitZero = new ArrayList<CellDeltaSample>();
    ArrayList<CellDeltaSample> bitOne = new ArrayList<CellDeltaSample>();
    for (int basis = 0; basis < dim; basis += 1) {
      float diag = max(0.0, matrixValue(sourceBlock.real, basis, basis, 0.0));
      float probability = diag / trace;
      if (probability <= SHOT_EMISSION_CONTRIBUTOR_THRESHOLD) {
        continue;
      }

      int[] cell = resolveShotReplayDiagonalCellCoordinates(geometry, dim, basis);
      int row = cell[0];
      int col = cell[1];
      float localX = geometry.localXForIndex(col);
      float localY = geometry.localYForIndex(row);
      CellDeltaSample candidate = new CellDeltaSample(row, col, probability, localX, localY);
      int basisBit = (basis >> qubitBitIndex) & 1;
      candidate.rank = basisBit;
      if (basisBit == 1) {
        bitOne.add(candidate);
      } else {
        bitZero.add(candidate);
      }
    }

    bitZero = dedupeShotReplayEmissionCells(bitZero);
    bitOne = dedupeShotReplayEmissionCells(bitOne);
    if (bitZero.isEmpty() && bitOne.isEmpty()) {
      return sources;
    }

    int safeMaxCells = clampInt(maxCells, 0, max(0, bitZero.size() + bitOne.size()));
    if (safeMaxCells <= 0) {
      return sources;
    }

    int takeZero = 0;
    int takeOne = 0;
    if (!bitZero.isEmpty() && !bitOne.isEmpty()) {
      int targetPerPartition = safeMaxCells / 2;
      takeZero = min(bitZero.size(), targetPerPartition);
      takeOne = min(bitOne.size(), targetPerPartition);
      if ((safeMaxCells % 2) == 1) {
        int spareZero = max(0, bitZero.size() - takeZero);
        int spareOne = max(0, bitOne.size() - takeOne);
        if (spareZero >= spareOne && spareZero > 0) {
          takeZero += 1;
        } else if (spareOne > 0) {
          takeOne += 1;
        }
      }
    } else if (!bitZero.isEmpty()) {
      takeZero = min(bitZero.size(), safeMaxCells);
    } else {
      takeOne = min(bitOne.size(), safeMaxCells);
    }
    int remaining = max(0, safeMaxCells - (takeZero + takeOne));
    while (remaining > 0) {
      boolean added = false;
      if (bitZero.size() > takeZero) {
        takeZero += 1;
        remaining -= 1;
        added = true;
      }
      if (remaining <= 0) {
        break;
      }
      if (bitOne.size() > takeOne) {
        takeOne += 1;
        remaining -= 1;
        added = true;
      }
      if (!added) {
        break;
      }
    }

    for (int i = 0; i < takeZero; i += 1) {
      sources.add(bitZero.get(i));
    }
    for (int i = 0; i < takeOne; i += 1) {
      sources.add(bitOne.get(i));
    }

    float collapseT = clampFloat(shotBeatProgress, 0.0, 1.0);
    float sampledWeight = 1.0;
    float otherWeight = 1.0;
    if ("collapse".equals(shotBeat)) {
      sampledWeight = clampFloat(0.82 + 0.28 * collapseT, 0.0, 1.2);
      otherWeight = clampFloat(1.0 - 0.92 * collapseT, 0.06, 1.0);
    }

    ArrayList<CellDeltaSample> weighted = new ArrayList<CellDeltaSample>();
    for (CellDeltaSample source : sources) {
      if (source == null) {
        continue;
      }
      int sourceBit = source.rank == 1 ? 1 : 0;
      float beatWeight = 1.0;
      if ("collapse".equals(shotBeat) && (sampledBit == 0 || sampledBit == 1)) {
        beatWeight = sourceBit == sampledBit ? sampledWeight : otherWeight;
      }
      float weightedDelta = source.delta * beatWeight;
      if (weightedDelta <= SHOT_EMISSION_CONTRIBUTOR_THRESHOLD) {
        continue;
      }
      CellDeltaSample adjusted = new CellDeltaSample(source.row, source.col, weightedDelta, source.localX, source.localY);
      adjusted.rank = source.rank;
      weighted.add(adjusted);
    }

    weighted = dedupeShotReplayEmissionCells(weighted);
    Collections.sort(weighted, new Comparator<CellDeltaSample>() {
      public int compare(CellDeltaSample a, CellDeltaSample b) {
        int byProb = Float.compare(b.delta, a.delta);
        if (byProb != 0) {
          return byProb;
        }
        if (a.row != b.row) {
          return a.row - b.row;
        }
        return a.col - b.col;
      }
    });

    int capped = clampInt(safeMaxCells, 0, weighted.size());
    if (capped <= 0 || capped >= weighted.size()) {
      return weighted;
    }

    ArrayList<CellDeltaSample> trimmed = new ArrayList<CellDeltaSample>();
    for (int i = 0; i < capped; i += 1) {
      trimmed.add(weighted.get(i));
    }
    return trimmed;
  }

  int[] resolveShotReplayDiagonalCellCoordinates(MatrixViewMetrics geometry, int dim, int basisIndex) {
    int safeBasis = clampInt(basisIndex, 0, max(0, dim - 1));
    int row;
    int col;
    if (dim == geometry.rows && dim == geometry.cols) {
      row = safeBasis;
      col = safeBasis;
    } else {
      float normalized = dim <= 1 ? 0.0 : safeBasis / float(max(1, dim - 1));
      row = clampInt(round(normalized * max(0, geometry.rows - 1)), 0, max(0, geometry.rows - 1));
      col = clampInt(round(normalized * max(0, geometry.cols - 1)), 0, max(0, geometry.cols - 1));
    }
    return new int[] { row, col };
  }

  ArrayList<CellDeltaSample> dedupeShotReplayEmissionCells(ArrayList<CellDeltaSample> sources) {
    ArrayList<CellDeltaSample> deduped = new ArrayList<CellDeltaSample>();
    if (sources == null || sources.isEmpty()) {
      return deduped;
    }

    HashMap<String, CellDeltaSample> byCell = new HashMap<String, CellDeltaSample>();
    for (CellDeltaSample source : sources) {
      if (source == null) {
        continue;
      }
      String key = source.row + ":" + source.col;
      CellDeltaSample aggregate = byCell.get(key);
      if (aggregate == null) {
        aggregate = new CellDeltaSample(source.row, source.col, max(0.0, source.delta), source.localX, source.localY);
        aggregate.rank = source.rank;
        byCell.put(key, aggregate);
      } else {
        aggregate.delta += max(0.0, source.delta);
      }
    }

    for (String key : byCell.keySet()) {
      CellDeltaSample sample = byCell.get(key);
      if (sample != null && sample.delta > SHOT_EMISSION_CONTRIBUTOR_THRESHOLD) {
        deduped.add(sample);
      }
    }

    Collections.sort(deduped, new Comparator<CellDeltaSample>() {
      public int compare(CellDeltaSample a, CellDeltaSample b) {
        int byProb = Float.compare(b.delta, a.delta);
        if (byProb != 0) {
          return byProb;
        }
        if (a.row != b.row) {
          return a.row - b.row;
        }
        return a.col - b.col;
      }
    });
    return deduped;
  }

  PVector resolveShotReplayContributorAnchor(
    MatrixViewMetrics geometry,
    ArrayList<CellDeltaSample> sourceCells,
    float cubeSide,
    float shotCuboidDepth
  ) {
    float sourceZ = shotReplayMatrixFrontZ(geometry) + max(0.9, geometry.cubeSize * 0.20);
    float zNudge = clampFloat(max(cubeSide, shotCuboidDepth) * 0.06, 0.14, 1.0);
    if (sourceCells == null || sourceCells.isEmpty()) {
      return new PVector(0.0, 0.0, sourceZ + zNudge);
    }

    float tieEps = 1e-7;
    CellDeltaSample best = null;
    float bestDelta = -1.0;
    for (CellDeltaSample source : sourceCells) {
      if (source == null) {
        continue;
      }
      float weight = max(0.0, source.delta);
      if (weight <= SHOT_EMISSION_CONTRIBUTOR_THRESHOLD) {
        continue;
      }
      if (best == null) {
        best = source;
        bestDelta = weight;
        continue;
      }
      if (weight > bestDelta + tieEps) {
        best = source;
        bestDelta = weight;
        continue;
      }
      if (abs(weight - bestDelta) <= tieEps) {
        if (source.row < best.row || (source.row == best.row && source.col < best.col)) {
          best = source;
          bestDelta = weight;
        }
      }
    }

    if (best == null) {
      CellDeltaSample first = sourceCells.get(0);
      if (first == null) {
        return new PVector(0.0, 0.0, sourceZ + zNudge);
      }
      return new PVector(first.localX, first.localY, sourceZ + zNudge);
    }
    return new PVector(best.localX, best.localY, sourceZ + zNudge);
  }

  void drawShotReplayDensityToQubitLinks(
    MatrixViewMetrics geometry,
    MatrixCellEntity qubitEntity,
    ArrayList<CellDeltaSample> sourceCells,
    float cubeSide,
    float shotCuboidDepth,
    float beatAlpha,
    float pulse,
    float travelProgress
  ) {
    if (geometry == null || qubitEntity == null || sourceCells == null || sourceCells.isEmpty()) {
      return;
    }
    float safeBeatAlpha = clampFloat(beatAlpha, 0.0, 1.0);
    if (safeBeatAlpha <= 1e-5) {
      return;
    }

    float safePulse = clampFloat(pulse, 0.0, 1.0);
    float safeTravel = clampFloat(travelProgress, 0.0, 1.0);
    float sourceZ = shotReplayMatrixFrontZ(geometry) + max(0.9, geometry.cubeSize * 0.20);
    float targetY = qubitEntity.curPos.y - cubeSide * 0.12;
    float targetZ = qubitEntity.curPos.z + shotCuboidDepth * 0.52;
    float maxWeight = max(SHOT_EMISSION_MIN_PROBABILITY, sourceCells.get(0).delta);

    for (CellDeltaSample source : sourceCells) {
      if (source == null) {
        continue;
      }
      float weight = clampFloat(source.delta / maxWeight, 0.0, 1.0);
      float alpha = clampFloat((120.0 + 220.0 * weight) * safeBeatAlpha, 0.0, 255.0);
      stroke(244, 232, 206, alpha);
      strokeWeight(1.20 + 1.80 * weight + 0.80 * safePulse);
      line(
        source.localX,
        source.localY,
        sourceZ,
        qubitEntity.curPos.x,
        targetY,
        targetZ
      );

      noStroke();
      float spark = 1.20 + 2.20 * weight;
      fill(255, 238, 204, alpha * 0.72);
      pushMatrix();
      translate(source.localX, source.localY, sourceZ + 0.25);
      box(spark, spark, spark);
      popMatrix();

      float markerT = clampFloat(safeTravel, 0.0, 1.0);
      float markerX = lerp(source.localX, qubitEntity.curPos.x, markerT);
      float markerY = lerp(source.localY, targetY, markerT);
      float markerZ = lerp(sourceZ, targetZ, markerT);
      float markerSize = 1.40 + 2.60 * weight + 0.90 * safePulse;
      fill(255, 246, 219, clampFloat(alpha * (0.74 + 0.22 * safePulse), 0.0, 255.0));
      pushMatrix();
      translate(markerX, markerY, markerZ + 0.12);
      box(markerSize, markerSize, markerSize);
      popMatrix();
    }

    noStroke();
  }

  void drawShotReplaySourceCellHighlight(MatrixCellEntity entity, PlaybackState playback) {
    if (entity == null || playback == null) {
      return;
    }
    float phasePulse = "shot_stack".equals(playback.phase)
      ? sin(PI * clampFloat(playback.shotProgress, 0.0, 1.0))
      : easeInOutCirc01(playback.shotProgress);
    float safePulse = clampFloat(phasePulse, 0.0, 1.0);
    float alpha = lerp(SHOT_SOURCE_HIGHLIGHT_ALPHA_MIN, SHOT_SOURCE_HIGHLIGHT_ALPHA_MAX, safePulse);
    float lift = entity.curPos.z + entity.curSize.z * 0.52 + 0.2;

    pushStyle();
    noFill();
    stroke(255, 238, 196, alpha);
    strokeWeight(1.6 + 1.1 * safePulse);
    pushMatrix();
    translate(entity.curPos.x, entity.curPos.y, lift);
    box(
      entity.curSize.x * (1.10 + 0.07 * safePulse),
      entity.curSize.y * (1.10 + 0.07 * safePulse),
      max(1.2, entity.curSize.z * 0.16)
    );
    popMatrix();

    noStroke();
    fill(255, 245, 214, min(255, alpha * 0.78));
    pushMatrix();
    translate(entity.curPos.x, entity.curPos.y, lift + 0.22);
    float marker = 1.8 + 1.9 * safePulse;
    box(marker, marker, marker);
    popMatrix();
    popStyle();
  }

  void drawShotReplayHistogram(MatrixViewMetrics geometry, PlaybackState playback, TraceModel traceModel, int frameIndex) {
    if (geometry == null || playback == null || playback.sample == null || !playback.inShotReplay) {
      pruneStaleShotQubitEntities(new HashSet<String>());
      shotQubitLabelSprites.clear();
      pruneStaleShotHistogramEntities(new HashSet<String>());
      shotHistogramLabelSprites.clear();
      return;
    }

    HashMap<String, ProbabilitySample> histogram = playback.sample.probabilities;
    if (histogram == null || histogram.isEmpty()) {
      pruneStaleShotQubitEntities(new HashSet<String>());
      shotQubitLabelSprites.clear();
      pruneStaleShotHistogramEntities(new HashSet<String>());
      shotHistogramLabelSprites.clear();
      return;
    }

    ArrayList<String> labels = new ArrayList<String>(histogram.keySet());
    Collections.sort(labels);
    if (labels.isEmpty()) {
      pruneStaleShotQubitEntities(new HashSet<String>());
      shotQubitLabelSprites.clear();
      pruneStaleShotHistogramEntities(new HashSet<String>());
      shotHistogramLabelSprites.clear();
      return;
    }

    float histogramRevealAlpha = resolveShotHistogramRevealAlpha(playback);
    if (histogramRevealAlpha <= 1e-5) {
      pruneStaleShotHistogramEntities(new HashSet<String>());
      shotHistogramLabelSprites.clear();
      return;
    }

    float phaseAlpha = clampFloat(histogramRevealAlpha, 0.0, 1.0);
    if ("shot_histogram_project".equals(playback.phase) && playback.shotIndex < 0) {
      float moveAlpha = resolveShotProjectMoveAlpha(playback.phaseProgress);
      phaseAlpha = clampFloat((0.35 + 0.65 * moveAlpha) * histogramRevealAlpha, 0.0, 1.0);
    }

    float span = geometry.matrixW * SHOT_PROJECT_SPAN_RATIO;
    float spacing = labels.size() <= 1 ? 0.0 : span / float(labels.size() - 1);
    float barW = labels.size() <= 1
      ? clampFloat(geometry.matrixW * 0.32, 10.0, 42.0)
      : clampFloat(spacing * 0.56, 4.0, 18.0);
    float barDepth = clampFloat(geometry.cubeSize * 0.42, 6.0, 20.0);
    float baselineY = 0.0;
    float frontZ = shotReplayHistogramFrontZ(geometry);
    float maxBarHeight = geometry.matrixH * 0.46;
    float labelAlpha = shotReplayHistogramLabelAlpha(playback) * histogramRevealAlpha;
    float labelYLocal = baselineY + max(geometry.cubeSize * 0.38, 6.0);
    float labelZLocal = frontZ + barDepth * 0.62;

    HashSet<String> renderedKeys = new HashSet<String>();
    ArrayList<ShotHistogramLabelSprite> labelSprites = new ArrayList<ShotHistogramLabelSprite>();
    float activeBarX = 0.0;
    float activeBarHeight = 0.0;
    boolean hasActiveBar = false;
    boolean projectionShotPhase = "shot_histogram_project".equals(playback.phase) && playback.shotIndex >= 0;
    String activeProjectionLabel = projectionShotPhase
      ? resolveActiveProjectionHistogramLabel(playback, traceModel)
      : "";

    for (int i = 0; i < labels.size(); i += 1) {
      String label = labels.get(i);
      ProbabilitySample sample = histogram.get(label);
      float probability = sample != null ? clampFloat(sample.probability, 0.0, 1.0) : 0.0;

      float baseHeight = max(SHOT_PROJECT_MIN_BAR_H, maxBarHeight * probability);
      float displayHeight = baseHeight;
      float finalX = labels.size() <= 1 ? 0.0 : -span * 0.5 + i * spacing;
      float x = resolveShotHistogramXAtPhase(playback, finalX);
      float pulseBump = 0.0;
      if ("shot_histogram_project".equals(playback.phase) && playback.shotIndex < 0) {
        float moveAlpha = resolveShotProjectMoveAlpha(playback.phaseProgress);
        if (moveAlpha < SHOT_PROJECT_PULSE_FRACTION) {
          float pulseAlpha = clampFloat(
            moveAlpha / max(1e-5, SHOT_PROJECT_PULSE_FRACTION),
            0.0,
            1.0
          );
          pulseBump = sin(PI * pulseAlpha) * geometry.cubeSize * 0.18;
        }
      }
      if ("shot_histogram_project".equals(playback.phase) && playback.shotIndex < 0) {
        displayHeight = lerp(SHOT_PROJECT_MIN_BAR_H, baseHeight, 0.52 * phaseAlpha);
        displayHeight += pulseBump;
      }

      float y = baselineY - displayHeight * 0.5;
      String key = "hist:" + label;
      renderedKeys.add(key);
      MatrixCellEntity entity = shotHistogramEntities.get(key);
      if (entity == null) {
        entity = new MatrixCellEntity(
          new PVector(x, y, frontZ),
          new PVector(barW, displayHeight, barDepth),
          new PVector(probability, 0.0, 0.0),
          frameIndex,
          16
        );
        shotHistogramEntities.put(key, entity);
      }

      PVector targetPos = new PVector(x, y, frontZ);
      PVector targetSize = new PVector(barW, displayHeight, barDepth);
      PVector targetValue = new PVector(probability, 0.0, 0.0);
      if (projectionShotPhase) {
        entity.snapTo(targetPos, targetSize, targetValue, frameIndex);
      } else {
        entity.setTarget(targetPos, targetSize, targetValue, frameIndex, 16);
        entity.update(frameIndex);
      }

      boolean activeShotLabel = projectionShotPhase
        && activeProjectionLabel.length() > 0
        && activeProjectionLabel.equals(label);
      int baseColor = activeShotLabel
        ? color(THEME.amber[0], THEME.amber[1], THEME.amber[2], 242 * phaseAlpha)
        : color(THEME.cyan[0], THEME.cyan[1], THEME.cyan[2], 186 * phaseAlpha);
      int edgeColor = activeShotLabel
        ? color(255, 240, 192, 220 * phaseAlpha)
        : color(208, 236, 255, 150 * phaseAlpha);

      drawCubeCell(entity, baseColor, edgeColor, activeShotLabel, activeShotLabel ? 0.9 : 0.35, false);
      if (labelAlpha > 0.0) {
        float labelScreenX = screenX(entity.curPos.x, labelYLocal, labelZLocal);
        float labelScreenY = screenY(entity.curPos.x, labelYLocal, labelZLocal);
        if (Float.isFinite(labelScreenX) && Float.isFinite(labelScreenY)) {
          labelSprites.add(
            new ShotHistogramLabelSprite(label, labelScreenX, labelScreenY, labelAlpha, activeShotLabel)
          );
        }
      }
      if (activeShotLabel) {
        activeBarX = x;
        activeBarHeight = displayHeight;
        hasActiveBar = true;
      }
    }

    if ("shot_histogram_project".equals(playback.phase) && playback.shotIndex >= 0 && hasActiveBar) {
      float pulse = easeInOutCirc01(playback.shotProgress);
      float targetY = baselineY - max(6.0, activeBarHeight * (0.55 + 0.45 * pulse));
      float markerZ = frontZ + 0.36;
      float markerArm = 1.8 + 2.8 * pulse;
      stroke(255, 224, 138, 170 + 70 * pulse);
      strokeWeight(1.0 + 1.2 * pulse);
      line(activeBarX - markerArm, targetY, markerZ, activeBarX + markerArm, targetY, markerZ);
      line(activeBarX, targetY - markerArm * 0.65, markerZ, activeBarX, targetY + markerArm * 0.65, markerZ);
      noStroke();
      fill(255, 232, 165, 120 + 110 * pulse);
      pushMatrix();
      translate(activeBarX, targetY, frontZ + 0.55);
      box(2.2 + 1.8 * pulse, 2.2 + 1.8 * pulse, 2.2 + 1.8 * pulse);
      popMatrix();
    }

    shotHistogramLabelSprites.clear();
    shotHistogramLabelSprites.addAll(labelSprites);
    pruneStaleShotHistogramEntities(renderedKeys);
  }

  void pruneStaleShotQubitEntities(HashSet<String> renderedKeys) {
    if (renderedKeys == null) {
      shotQubitEntities.clear();
      return;
    }

    ArrayList<String> staleKeys = new ArrayList<String>();
    for (String key : shotQubitEntities.keySet()) {
      if (!renderedKeys.contains(key)) {
        staleKeys.add(key);
      }
    }
    for (String key : staleKeys) {
      shotQubitEntities.remove(key);
    }
  }

  void pruneStaleShotHistogramEntities(HashSet<String> renderedKeys) {
    if (renderedKeys == null) {
      shotHistogramEntities.clear();
      return;
    }

    ArrayList<String> staleKeys = new ArrayList<String>();
    for (String key : shotHistogramEntities.keySet()) {
      if (!renderedKeys.contains(key)) {
        staleKeys.add(key);
      }
    }
    for (String key : staleKeys) {
      shotHistogramEntities.remove(key);
    }
  }

  float shotReplayHistogramLabelAlpha(PlaybackState playback) {
    if (playback == null) {
      return 0.0;
    }
    if ("shot_camera_pullback".equals(playback.phase)) {
      return 0.0;
    }
    if ("shot_stack".equals(playback.phase)) {
      return 0.0;
    }
    if ("shot_histogram_project".equals(playback.phase)) {
      if (playback.shotIndex >= 0) {
        return 1.0;
      }
      float moveAlpha = resolveShotProjectMoveAlpha(playback.phaseProgress);
      if (moveAlpha <= SHOT_PROJECT_PULSE_FRACTION) {
        return 0.0;
      }
      float spreadProgress = (moveAlpha - SHOT_PROJECT_PULSE_FRACTION) / max(1e-5, 1.0 - SHOT_PROJECT_PULSE_FRACTION);
      return smoothstep01(spreadProgress);
    }
    return 0.0;
  }

  void drawShotReplayQubitLabels(PanelRect panel, PlaybackState playback) {
    if (panel == null || playback == null || shotQubitLabelSprites.isEmpty()) {
      return;
    }

    ArrayList<ShotQubitLabelSprite> sprites = new ArrayList<ShotQubitLabelSprite>(shotQubitLabelSprites);
    Collections.sort(sprites, new Comparator<ShotQubitLabelSprite>() {
      public int compare(ShotQubitLabelSprite a, ShotQubitLabelSprite b) {
        return Float.compare(a.screenX, b.screenX);
      }
    });

    float baseTextSize = clampFloat(11.6 - max(0.0, sprites.size() - 3.0) * 0.22, 9.2, 12.0);
    float minGap = max(18.0, baseTextSize * 1.8);
    float lastX = -1e9;
    int overlapRun = 0;

    hint(DISABLE_DEPTH_TEST);
    pushStyle();
    textAlign(CENTER, BOTTOM);
    textSize(baseTextSize);

    for (ShotQubitLabelSprite sprite : sprites) {
      if (sprite == null || sprite.label == null || sprite.label.length() == 0) {
        continue;
      }
      if (sprite.alpha <= 1e-4) {
        continue;
      }

      float x = sprite.screenX;
      if (x - lastX < minGap) {
        overlapRun += 1;
      } else {
        overlapRun = 0;
      }
      lastX = x;

      float rowOffset = overlapRun * 11.0;
      float drawX = clampFloat(x, panel.x + 10.0, panel.x + panel.w - 10.0);
      float drawY = clampFloat(
        sprite.screenY - SHOT_QUBIT_LABEL_Y_OFFSET - rowOffset,
        panel.y + 12.0,
        panel.y + panel.h - 18.0
      );
      int alpha = round(clampFloat(sprite.alpha, 0.0, 1.0) * 255.0);
      if (alpha <= 0) {
        continue;
      }

      fill(0, 15 + round(alpha * 0.48));
      text(sprite.label, drawX + 1.0, drawY + 1.0);
      if (sprite.active) {
        fill(244, 244, 244, min(255, 44 + round(alpha * 0.92)));
      } else {
        fill(214, 214, 214, min(255, 38 + round(alpha * 0.86)));
      }
      text(sprite.label, drawX, drawY);
    }

    popStyle();
    hint(ENABLE_DEPTH_TEST);
  }

  void drawShotReplayHistogramLabels(PanelRect panel, PlaybackState playback) {
    if (panel == null || playback == null || shotHistogramLabelSprites.isEmpty()) {
      return;
    }

    ArrayList<ShotHistogramLabelSprite> sprites = new ArrayList<ShotHistogramLabelSprite>(shotHistogramLabelSprites);
    Collections.sort(sprites, new Comparator<ShotHistogramLabelSprite>() {
      public int compare(ShotHistogramLabelSprite a, ShotHistogramLabelSprite b) {
        return Float.compare(a.screenX, b.screenX);
      }
    });

    float baseTextSize = clampFloat(13.0 - max(0.0, sprites.size() - 2.0) * 0.42, 8.2, 13.0);
    float minGap = max(SHOT_LABEL_MIN_GAP_PX, baseTextSize * 2.0);
    float lastX = -1e9;
    int overlapRun = 0;

    hint(DISABLE_DEPTH_TEST);
    pushStyle();
    textAlign(CENTER, TOP);
    textSize(baseTextSize);

    for (ShotHistogramLabelSprite sprite : sprites) {
      if (sprite == null || sprite.label == null || sprite.label.length() == 0) {
        continue;
      }
      if (sprite.alpha <= 1e-4) {
        continue;
      }

      float x = sprite.screenX;
      if (x - lastX < minGap) {
        overlapRun += 1;
      } else {
        overlapRun = 0;
      }
      lastX = x;

      float rowOffset = (overlapRun % 2 == 0) ? 0.0 : (baseTextSize + SHOT_LABEL_STAGGER_PX);
      float drawX = clampFloat(x, panel.x + 10.0, panel.x + panel.w - 10.0);
      float drawY = clampFloat(
        sprite.screenY + SHOT_LABEL_BASE_Y_OFFSET + rowOffset,
        panel.y + 8.0,
        panel.y + panel.h - 18.0
      );
      int alpha = round(clampFloat(sprite.alpha, 0.0, 1.0) * 255.0);
      if (alpha <= 0) {
        continue;
      }

      fill(0, 12 + round(alpha * 0.52));
      text(sprite.label, drawX + 1.0, drawY + 1.0);

      if (sprite.active) {
        fill(THEME.amber[0], THEME.amber[1], THEME.amber[2], min(255, 36 + round(alpha * 0.94)));
      } else {
        fill(230, 247, 255, min(255, 28 + round(alpha * 0.92)));
      }
      text(sprite.label, drawX, drawY);
    }

    popStyle();
    hint(ENABLE_DEPTH_TEST);
  }

  ArrayList<DensityLayerFrame> resolveLayerFrames(
    PlaybackState playback,
    TraceModel traceModel,
    ReducedDensitySample activeRho,
    String activeStateHash
  ) {
    ArrayList<DensityLayerFrame> layers = new ArrayList<DensityLayerFrame>();
    if (playback == null || traceModel == null || activeRho == null || !isRectangular(activeRho.real, activeRho.imag)) {
      return layers;
    }

    int rows = activeRho.real.length;
    int cols = activeRho.real[0].length;
    int activeStepIndex = clampInt(playback.stepIndex, 0, max(0, traceModel.stepCount - 1));
    boolean showActiveLayer = shouldRenderActiveGateLayer(playback);
    if (isShotReplaySourcePhase(playback) && showActiveLayer) {
      layers.add(
        new DensityLayerFrame(
          activeStepIndex,
          0,
          playback.phase,
          activeRho.real,
          activeRho.imag,
          activeStateHash != null ? activeStateHash : "",
          true
        )
      );
      return layers;
    }
    int startStep = 0;

    ReducedDensitySample initRho = resolveGroundStateLayerBlock(activeRho);
    int initAge = max(0, activeStepIndex - INIT_LAYER_STEP_INDEX - (showActiveLayer ? 0 : 1));
    if (initRho != null && initRho.real.length == rows && initRho.real[0].length == cols) {
      layers.add(
        new DensityLayerFrame(
          INIT_LAYER_STEP_INDEX,
          initAge,
          INIT_LAYER_PHASE,
          initRho.real,
          initRho.imag,
          initLayerStateHash,
          false
        )
      );
    }

    for (int stepIndex = startStep; stepIndex <= activeStepIndex; stepIndex += 1) {
      int age = activeStepIndex - stepIndex;
      boolean isActive = stepIndex == activeStepIndex;
      if (isActive) {
        if (!showActiveLayer) {
          continue;
        }
        layers.add(
          new DensityLayerFrame(
            stepIndex,
            age,
            playback.phase,
            activeRho.real,
            activeRho.imag,
            activeStateHash != null ? activeStateHash : "",
            true
          )
        );
        continue;
      }

      TraceStep sourceStep = traceModel.steps.get(stepIndex);
      EvolutionSample settleSample = resolveSettleEvolutionSample(sourceStep);
      if (settleSample == null) {
        continue;
      }

      ReducedDensitySample settledRho = selectPreferredBlock(settleSample);
      if (settledRho == null || !isRectangular(settledRho.real, settledRho.imag)) {
        continue;
      }
      if (settledRho.real.length != rows || settledRho.real[0].length != cols) {
        continue;
      }

      layers.add(
        new DensityLayerFrame(
          stepIndex,
          age,
          settleSample.phase,
          settledRho.real,
          settledRho.imag,
          settleSample.stateHash,
          false
        )
      );
    }

    return layers;
  }

  boolean shouldRenderActiveGateLayer(PlaybackState playback) {
    if (playback == null) {
      return true;
    }
    return !(playback.stepIndex == 0 && "pre_gate".equals(playback.phase));
  }

  String resolveInitialLayerStateHash(TraceModel traceModel) {
    if (traceModel == null || traceModel.steps == null || traceModel.steps.isEmpty()) {
      return "synthetic_ground";
    }

    TraceStep firstStep = traceModel.steps.get(0);
    if (firstStep != null && firstStep.gateStartHash != null && firstStep.gateStartHash.length() > 0) {
      return firstStep.gateStartHash;
    }

    if (firstStep != null && firstStep.evolutionSamples != null) {
      for (EvolutionSample sample : firstStep.evolutionSamples) {
        if (sample != null && sample.stateHash != null && sample.stateHash.length() > 0) {
          return sample.stateHash;
        }
      }
    }

    if (firstStep != null && firstStep.gateEndHash != null && firstStep.gateEndHash.length() > 0) {
      return firstStep.gateEndHash;
    }
    return "synthetic_ground";
  }

  ReducedDensitySample resolveGroundStateLayerBlock(ReducedDensitySample activeRho) {
    if (activeRho == null || !isRectangular(activeRho.real, activeRho.imag)) {
      return null;
    }

    int rows = max(1, activeRho.real.length);
    int cols = max(1, activeRho.real[0].length);
    String qubitKey = activeRho.qubitKey != null ? activeRho.qubitKey : "";
    String cacheKey = rows + "x" + cols + "|" + qubitKey;
    ReducedDensitySample cached = initGroundBlockCache.get(cacheKey);
    if (cached != null) {
      return cached;
    }

    float[][] real = new float[rows][cols];
    float[][] imag = new float[rows][cols];
    real[0][0] = 1.0;

    ReducedDensitySample synthetic = new ReducedDensitySample(copyQubits(activeRho.qubits), real, imag);
    initGroundBlockCache.put(cacheKey, synthetic);
    return synthetic;
  }

  int[] copyQubits(int[] qubits) {
    if (qubits == null || qubits.length == 0) {
      return new int[0];
    }
    int[] copied = new int[qubits.length];
    for (int i = 0; i < qubits.length; i += 1) {
      copied[i] = qubits[i];
    }
    return copied;
  }

  int resolveEstimatedLayerCount(PlaybackState playback) {
    if (playback == null) {
      return 1;
    }
    boolean showActiveLayer = shouldRenderActiveGateLayer(playback);
    return max(1, playback.stepIndex + (showActiveLayer ? 2 : 1));
  }

  int resolveLayerWindowCap(ReducedDensitySample activeRho) {
    if (activeRho == null || !isRectangular(activeRho.real, activeRho.imag)) {
      return 0;
    }
    return Integer.MAX_VALUE;
  }

  EvolutionSample resolveSettleEvolutionSample(TraceStep step) {
    if (step == null || step.evolutionSamples == null || step.evolutionSamples.isEmpty()) {
      return null;
    }
    EvolutionSample latestSettle = null;
    for (EvolutionSample sample : step.evolutionSamples) {
      if (sample != null && "settle".equals(sample.phase)) {
        latestSettle = sample;
      }
    }
    if (latestSettle != null) {
      return latestSettle;
    }
    return step.evolutionSamples.get(step.evolutionSamples.size() - 1);
  }

  void pruneStaleRhoEntities(HashSet<String> renderedKeys) {
    if (renderedKeys == null) {
      rhoEntities.clear();
      return;
    }

    ArrayList<String> staleKeys = new ArrayList<String>();
    for (String key : rhoEntities.keySet()) {
      if (!renderedKeys.contains(key)) {
        staleKeys.add(key);
      }
    }
    for (String key : staleKeys) {
      rhoEntities.remove(key);
    }
  }

  float resolveStackDepthBudget(MatrixViewMetrics geometry, int layerCount) {
    if (geometry == null) {
      return 120.0;
    }
    return resolveStackDepthBudget(geometry.matrixW, geometry.matrixH, geometry.cubeSize, layerCount);
  }

  float resolveBaseStackDepthStep(float cubeSize) {
    float safeCube = max(0.0, cubeSize);
    return clampFloat(safeCube * STACK_DEPTH_STEP_MULT, STACK_DEPTH_STEP_MIN, STACK_DEPTH_STEP_MAX);
  }

  float resolveConservativeNoOverlapGap(float cubeSize) {
    float safeCube = max(0.0, cubeSize);
    float sideA = safeCube * max(0.72, 1.0);
    float sideB = safeCube * max(0.72, 1.0 - LAYER_SCALE_DECAY_PER_AGE);
    return (sideA + sideB) * 0.5 + STACK_NO_OVERLAP_MARGIN;
  }

  float resolveGuaranteedDepthStep(float cubeSize) {
    float safeCube = max(0.0, cubeSize);
    float baseStep = resolveBaseStackDepthStep(safeCube);
    float noOverlapStep = safeCube * STACK_NO_OVERLAP_MULT + STACK_NO_OVERLAP_MARGIN;
    float conservativeGap = resolveConservativeNoOverlapGap(safeCube);
    return max(baseStep, max(noOverlapStep, conservativeGap));
  }

  float resolveStackDepthBudget(float matrixW, float matrixH, float cubeSize, int layerCount) {
    float depthStep = resolveGuaranteedDepthStep(cubeSize);
    float depthSpan = depthStep * max(0, layerCount - 1);
    return max(44.0, depthSpan + cubeSize * 0.9);
  }

  float resolveStackLateralBudgetX(MatrixViewMetrics geometry, int layerCount) {
    if (geometry == null) {
      return 26.0;
    }
    float stageSpan = max(24.0, geometry.matrixW);
    float suggested = stageSpan * 0.16;
    return clampFloat(suggested, 12.0, stageSpan * 0.38);
  }

  float resolveStackLateralBudgetY(MatrixViewMetrics geometry, int layerCount) {
    if (geometry == null) {
      return 18.0;
    }
    float stageSpan = max(24.0, geometry.matrixH);
    float suggested = stageSpan * 0.11;
    return clampFloat(suggested, 10.0, stageSpan * 0.32);
  }

  float resolveStagePlaneZ(
    ArrayList<DensityLayerFrame> layers,
    MatrixViewMetrics geometry,
    int rows,
    int cols,
    float depthStep
  ) {
    if (geometry == null || layers == null || layers.isEmpty()) {
      return -0.18;
    }

    float minBackZ = Float.POSITIVE_INFINITY;
    for (DensityLayerFrame layer : layers) {
      if (layer == null || !isRectangular(layer.real, layer.imag)) {
        continue;
      }
      if (layer.real.length != rows || layer.real[0].length != cols) {
        continue;
      }

      int age = max(0, layer.age);
      float layerScaleAttenuation = clampFloat(1.0 - age * LAYER_SCALE_DECAY_PER_AGE, 0.72, 1.0);
      float cubeSide = geometry.cubeSize * 0.92 * layerScaleAttenuation;
      float centerZ = 1.10 + cubeSide * 0.5 - age * depthStep;
      float backZ = centerZ - cubeSide * 0.5 - 2.0;
      minBackZ = min(minBackZ, backZ);
    }

    if (!Float.isFinite(minBackZ)) {
      return -0.18;
    }
    return min(-0.18, minBackZ - 1.5);
  }

  void renderStageSurface(MatrixViewMetrics geometry, float planeZ) {
    noStroke();
    fill(0, 184);
    rectMode(CENTER);
    pushMatrix();
    translate(0, 0, planeZ);
    rect(0, 0, geometry.matrixW + geometry.pitch * 1.2, geometry.matrixH + geometry.pitch * 1.2);

    stroke(255, 30);
    strokeWeight(1.0);
    noFill();
    rectMode(CENTER);
    rect(0, 0, geometry.matrixW + geometry.pitch * 0.7, geometry.matrixH + geometry.pitch * 0.7);

    stroke(255, 14);
    strokeWeight(0.55);
    for (int row = 0; row <= geometry.rows; row += 1) {
      float y = (row - geometry.rows * 0.5) * geometry.pitch;
      line(-geometry.matrixW * 0.5, y, 0, geometry.matrixW * 0.5, y, 0);
    }
    for (int col = 0; col <= geometry.cols; col += 1) {
      float x = (col - geometry.cols * 0.5) * geometry.pitch;
      line(x, -geometry.matrixH * 0.5, 0, x, geometry.matrixH * 0.5, 0);
    }
    popMatrix();
  }

  void updateGateActor(
    MatrixViewMetrics geometry,
    CellInfluenceMap influenceMap,
    StoryBeat beat,
    int frameIndex,
    int motionDuration
  ) {
    PVector target = influenceMap.actorTarget(beat, geometry);
    float z = 1.4 + beat.actorIntensity * 0.9;
    float base = geometry.cubeSize * 0.42;
    float stretch = "scan".equals(beat.beat) ? 1.08 : 0.94;
    float w = base * stretch;
    float h = base * 0.70;

    if (gateActor == null) {
      gateActor = new GateActorEntity(
        new PVector(target.x, target.y, z),
        new PVector(w, h, 1.0),
        new PVector(beat.actorIntensity, 0, 0),
        frameIndex,
        motionDuration
      );
    }

    gateActor.setTarget(
      new PVector(target.x, target.y, z),
      new PVector(w, h, 1.0),
      new PVector(beat.actorIntensity, 0, 0),
      frameIndex,
      motionDuration
    );
    gateActor.update(frameIndex);
  }

  void drawGateActor(String actorLabel, StoryBeat beat) {
    if (gateActor == null || !beat.actorVisible) {
      return;
    }

    float intensity = clampFloat(gateActor.curValue.x, 0, 1);
    float w = max(8.0, gateActor.curSize.x);
    float h = max(6.0, gateActor.curSize.y);

    pushMatrix();
    translate(gateActor.curPos.x, gateActor.curPos.y, gateActor.curPos.z);

    noStroke();
    fill(238, 240, 245, 120 + 90 * intensity);
    rectMode(CENTER);
    rect(0, 0, w, h);

    noFill();
    stroke(255, 155 + 80 * intensity);
    strokeWeight(0.8 + 0.45 * intensity);
    rect(0, 0, w + 2.2, h + 2.2);

    noStroke();
    fill(20, 22, 26, 190);
    textAlign(CENTER, CENTER);
    textSize(max(8.0, h * 0.56));
    text(actorLabel, 0, 0);

    popMatrix();
  }

  void drawOperatorStripe(MatrixViewMetrics geometry, StoryBeat beat) {
    if (gateActor == null || !beat.actorVisible) {
      return;
    }
    float intensity = clampFloat(gateActor.curValue.x, 0, 1);
    float stripeAlpha = 26 + 62 * intensity;
    float stripeZ = gateActor.curPos.z + 0.18;
    float y = gateActor.curPos.y;
    float left = -geometry.matrixW * 0.53;
    float right = geometry.matrixW * 0.53;

    stroke(240, 244, 250, stripeAlpha);
    strokeWeight(0.95 + 0.65 * intensity);
    line(left, y, stripeZ, right, y, stripeZ);

    stroke(220, 228, 242, 16 + 36 * intensity);
    strokeWeight(0.45 + 0.35 * intensity);
    line(left, y - 2.4, stripeZ, right, y - 2.4, stripeZ);
    line(left, y + 2.4, stripeZ, right, y + 2.4, stripeZ);
  }

  void drawHandoffCellOverlay(
    MatrixCellEntity entity,
    boolean inSourceSet,
    boolean inActiveFrontier,
    boolean inTargetSet,
    float actorInfluence,
    StoryBeat beat
  ) {
    if (!inSourceSet && !inActiveFrontier && !inTargetSet) {
      return;
    }

    float w = max(2.0, entity.curSize.x);
    float h = max(2.0, entity.curSize.y);
    float z = entity.curPos.z + max(1.0, entity.curSize.z * 0.5) + 0.35;
    float influence = clampFloat(actorInfluence, 0, 1);

    pushMatrix();
    translate(entity.curPos.x, entity.curPos.y, z);

    if (inSourceSet) {
      float bw = w * 0.44;
      float bh = h * 0.44;
      float a = 42 + 58 * influence;
      stroke(240, 245, 252, a);
      strokeWeight(0.72);

      line(-w * 0.5, -h * 0.5, 0, -w * 0.5 + bw, -h * 0.5, 0);
      line(-w * 0.5, -h * 0.5, 0, -w * 0.5, -h * 0.5 + bh, 0);

      line(w * 0.5, h * 0.5, 0, w * 0.5 - bw, h * 0.5, 0);
      line(w * 0.5, h * 0.5, 0, w * 0.5, h * 0.5 - bh, 0);
    }

    if (inActiveFrontier) {
      float a = 34 + 96 * influence;
      stroke(246, 248, 253, a);
      strokeWeight(0.85 + 0.45 * influence);
      line(-w * 0.50, 0, 0, w * 0.50, 0, 0);
      line(0, -h * 0.50, 0, 0, h * 0.50, 0);
    }

    if (inTargetSet) {
      float pulse = "scan".equals(beat.beat)
        ? 1.0 - abs(0.5 - beat.beatProgress) * 2.0
        : (inActiveFrontier ? 0.75 : 0.45);
      pulse = clampFloat(pulse, 0.0, 1.0);
      float railGrow = 1.2 + 4.2 * pulse;
      float a = 30 + 100 * pulse;
      stroke(233, 238, 248, a);
      strokeWeight(0.55 + 0.95 * pulse);
      line(-w * 0.5 - railGrow, h * 0.5 + railGrow, 0, w * 0.5 + railGrow, h * 0.5 + railGrow, 0);
    }

    popMatrix();
  }

  DecompositionOverlayState resolveDecompositionOverlay(
    PlaybackState playback,
    ReducedDensitySample activeBlock,
    int rows,
    int cols,
    CellInfluenceMap influenceMap,
    StoryBeat beat
  ) {
    DecompositionOverlayState state = new DecompositionOverlayState();
    state.reason = "inactive: unavailable";

    if (playback == null || playback.step == null || playback.sample == null) {
      return state;
    }
    if (!"apply_gate".equals(playback.phase)) {
      state.reason = "inactive: phase";
      return state;
    }
    if (activeBlock == null || !isRectangular(activeBlock.real, activeBlock.imag)) {
      state.reason = "inactive: block missing";
      return state;
    }
    if (rows != cols || rows > RAW_DETAIL_MAX_DIM || !isPowerOfTwo(rows)) {
      state.reason = "inactive: unsupported size";
      return state;
    }

    GateMatrixSample gateMatrix = playback.sample.gateMatrix;
    if (gateMatrix == null || !isSquareMatrix(gateMatrix.real, gateMatrix.imag)) {
      state.reason = "inactive: gate matrix missing";
      return state;
    }
    if (!isPowerOfTwo(gateMatrix.real.length)) {
      state.reason = "inactive: malformed gate matrix";
      return state;
    }
    if (gateMatrix.real.length != (1 << max(0, gateMatrix.qubits.length))) {
      state.reason = "inactive: gate size mismatch";
      return state;
    }
    if (!isGateQubitSubset(gateMatrix.qubits, activeBlock.qubits)) {
      state.reason = "inactive: gate qubits outside block";
      return state;
    }

    ReducedDensitySample gateStartBlock = resolveGateStartBlock(playback.step, activeBlock);
    if (gateStartBlock == null || !isRectangular(gateStartBlock.real, gateStartBlock.imag)) {
      state.reason = "inactive: gate-start rho missing";
      return state;
    }
    if (gateStartBlock.real.length != rows || gateStartBlock.real[0].length != cols) {
      state.reason = "inactive: gate-start shape mismatch";
      return state;
    }

    ComplexEntry[][] embedded = buildEmbeddedGateMatrix(gateMatrix, activeBlock);
    if (embedded == null) {
      state.reason = "inactive: embed failed";
      return state;
    }

    int totalCells = max(1, rows * cols);
    int targetRank = resolveActiveTargetRank(influenceMap, beat, totalCells);
    int targetRow = 0;
    int targetCol = 0;
    if (influenceMap != null && influenceMap.ranked != null && !influenceMap.ranked.isEmpty()) {
      int safeRank = clampInt(targetRank, 0, influenceMap.ranked.size() - 1);
      CellDeltaSample targetSample = influenceMap.ranked.get(safeRank);
      targetRow = targetSample.row;
      targetCol = targetSample.col;
    }
    state.targetRow = targetRow;
    state.targetCol = targetCol;

    float[][] predictedReal = new float[rows][cols];
    float[][] predictedImag = new float[rows][cols];
    ArrayList<DecompositionTerm> terms = new ArrayList<DecompositionTerm>();

    for (int i = 0; i < rows; i += 1) {
      for (int j = 0; j < cols; j += 1) {
        float sumRe = 0.0;
        float sumIm = 0.0;
        for (int a = 0; a < rows; a += 1) {
          ComplexEntry kia = embedded[i][a];
          for (int b = 0; b < cols; b += 1) {
            ComplexEntry kjb = embedded[j][b];
            float rhoRe = gateStartBlock.real[a][b];
            float rhoIm = gateStartBlock.imag[a][b];
            float re1 = kia.re * rhoRe - kia.im * rhoIm;
            float im1 = kia.re * rhoIm + kia.im * rhoRe;
            float termRe = re1 * kjb.re + im1 * kjb.im;
            float termIm = im1 * kjb.re - re1 * kjb.im;
            sumRe += termRe;
            sumIm += termIm;

            if (i == targetRow && j == targetCol) {
              terms.add(new DecompositionTerm(a, b, termRe, termIm));
            }
          }
        }
        predictedReal[i][j] = sumRe;
        predictedImag[i][j] = sumIm;
      }
    }

    String normalizedGateName = normalizeGateNameForLens(gateMatrix.gateName);
    boolean classifiedNonUnitary = isMeasureGateName(normalizedGateName) || isResetGateName(normalizedGateName);
    boolean nonUnitary = classifiedNonUnitary || !isApproximatelyUnitary(embedded, DECOMP_UNITARY_EPS);
    if (nonUnitary) {
      float traceReal = 0.0;
      for (int i = 0; i < rows; i += 1) {
        traceReal += predictedReal[i][i];
      }
      if (traceReal > DECOMP_EPS) {
        float invTrace = 1.0 / traceReal;
        for (int i = 0; i < rows; i += 1) {
          for (int j = 0; j < cols; j += 1) {
            predictedReal[i][j] *= invTrace;
            predictedImag[i][j] *= invTrace;
          }
        }
        for (DecompositionTerm term : terms) {
          term.re *= invTrace;
          term.im *= invTrace;
          term.weight = sqrt(term.re * term.re + term.im * term.im);
          term.phase = atan2(term.im, term.re);
        }
      }
    }

    float errSq = 0.0;
    for (int i = 0; i < rows; i += 1) {
      for (int j = 0; j < cols; j += 1) {
        float diffRe = predictedReal[i][j] - activeBlock.real[i][j];
        float diffIm = predictedImag[i][j] - activeBlock.imag[i][j];
        errSq += diffRe * diffRe + diffIm * diffIm;
      }
    }
    state.error = sqrt(errSq / float(max(1, rows * cols)));

    ArrayList<DecompositionTerm> filtered = new ArrayList<DecompositionTerm>();
    for (DecompositionTerm term : terms) {
      if (term.weight > DECOMP_EPS) {
        filtered.add(term);
      }
    }
    if (filtered.isEmpty()) {
      state.reason = "inactive: zero contribution";
      return state;
    }

    Collections.sort(filtered, new Comparator<DecompositionTerm>() {
      public int compare(DecompositionTerm a, DecompositionTerm b) {
        int byWeight = Float.compare(b.weight, a.weight);
        if (byWeight != 0) {
          return byWeight;
        }
        if (a.srcRow != b.srcRow) {
          return a.srcRow - b.srcRow;
        }
        return a.srcCol - b.srcCol;
      }
    });

    int takeCount = min(DECOMP_TOP_K, filtered.size());
    state.maxWeight = 0.0;
    for (int i = 0; i < takeCount; i += 1) {
      DecompositionTerm term = filtered.get(i);
      state.terms.add(term);
      state.maxWeight = max(state.maxWeight, term.weight);
    }
    if (state.terms.isEmpty()) {
      state.reason = "inactive: no top-k terms";
      return state;
    }

    state.active = true;
    state.reason = "";
    return state;
  }

  ReducedDensitySample resolveGateStartBlock(TraceStep step, ReducedDensitySample activeBlock) {
    if (step == null || activeBlock == null || step.evolutionSamples == null || step.evolutionSamples.isEmpty()) {
      return null;
    }

    int rows = activeBlock.real.length;
    int cols = activeBlock.real[0].length;
    EvolutionSample earliestPre = null;
    EvolutionSample earliestAny = null;
    for (EvolutionSample sample : step.evolutionSamples) {
      if (sample == null) {
        continue;
      }
      ReducedDensitySample block = selectMatchingBlock(sample.reducedDensityBlocks, activeBlock, rows, cols);
      if (block == null) {
        continue;
      }
      if (earliestAny == null || isEarlierEvolutionSample(sample, earliestAny)) {
        earliestAny = sample;
      }
      if ("pre_gate".equals(sample.phase)) {
        if (earliestPre == null || isEarlierEvolutionSample(sample, earliestPre)) {
          earliestPre = sample;
        }
      }
    }

    EvolutionSample selected = earliestPre != null ? earliestPre : earliestAny;
    if (selected == null) {
      return null;
    }
    return selectMatchingBlock(selected.reducedDensityBlocks, activeBlock, rows, cols);
  }

  ReducedDensitySample selectMatchingBlock(
    ArrayList<ReducedDensitySample> blocks,
    ReducedDensitySample activeBlock,
    int rows,
    int cols
  ) {
    if (blocks == null || activeBlock == null) {
      return null;
    }
    for (ReducedDensitySample block : blocks) {
      if (block == null || !isRectangular(block.real, block.imag)) {
        continue;
      }
      if (block.real.length != rows || block.real[0].length != cols) {
        continue;
      }
      if (block.qubitKey.equals(activeBlock.qubitKey)) {
        return block;
      }
    }
    return null;
  }

  boolean isEarlierEvolutionSample(EvolutionSample candidate, EvolutionSample current) {
    if (candidate == null) {
      return false;
    }
    if (current == null) {
      return true;
    }
    if (candidate.tNormalized < current.tNormalized - 1e-6) {
      return true;
    }
    if (candidate.tNormalized > current.tNormalized + 1e-6) {
      return false;
    }
    return candidate.sampleIndex < current.sampleIndex;
  }

  ComplexEntry[][] buildEmbeddedGateMatrix(GateMatrixSample gateMatrix, ReducedDensitySample activeBlock) {
    if (gateMatrix == null || activeBlock == null) {
      return null;
    }
    if (!isSquareMatrix(gateMatrix.real, gateMatrix.imag) || !isRectangular(activeBlock.real, activeBlock.imag)) {
      return null;
    }

    int blockDim = activeBlock.real.length;
    int blockQubitCount = activeBlock.qubits.length;
    if (blockDim != (1 << max(0, blockQubitCount))) {
      return null;
    }

    int localQubitCount = gateMatrix.qubits.length;
    int localDim = gateMatrix.real.length;
    if (localDim != (1 << max(0, localQubitCount))) {
      return null;
    }

    int[] gatePositions = new int[localQubitCount];
    boolean[] isGatePosition = new boolean[blockQubitCount];
    for (int i = 0; i < localQubitCount; i += 1) {
      int blockPos = indexOfQubit(activeBlock.qubits, gateMatrix.qubits[i]);
      if (blockPos < 0 || blockPos >= blockQubitCount || isGatePosition[blockPos]) {
        return null;
      }
      gatePositions[i] = blockPos;
      isGatePosition[blockPos] = true;
    }

    ComplexEntry[][] embedded = new ComplexEntry[blockDim][blockDim];
    for (int row = 0; row < blockDim; row += 1) {
      for (int col = 0; col < blockDim; col += 1) {
        embedded[row][col] = new ComplexEntry(0.0, 0.0);
      }
    }

    for (int row = 0; row < blockDim; row += 1) {
      for (int col = 0; col < blockDim; col += 1) {
        boolean envMatch = true;
        for (int blockPos = 0; blockPos < blockQubitCount; blockPos += 1) {
          if (isGatePosition[blockPos]) {
            continue;
          }
          int rowBit = basisBit(row, blockQubitCount, blockPos);
          int colBit = basisBit(col, blockQubitCount, blockPos);
          if (rowBit != colBit) {
            envMatch = false;
            break;
          }
        }
        if (!envMatch) {
          continue;
        }

        int localRow = localGateBasisIndex(row, blockQubitCount, gatePositions);
        int localCol = localGateBasisIndex(col, blockQubitCount, gatePositions);
        embedded[row][col] = new ComplexEntry(
          gateMatrix.real[localRow][localCol],
          gateMatrix.imag[localRow][localCol]
        );
      }
    }
    return embedded;
  }

  boolean isSquareMatrix(float[][] real, float[][] imag) {
    if (!isRectangular(real, imag)) {
      return false;
    }
    return real.length == real[0].length;
  }

  boolean isPowerOfTwo(int value) {
    if (value <= 0) {
      return false;
    }
    return (value & (value - 1)) == 0;
  }

  boolean isGateQubitSubset(int[] gateQubits, int[] blockQubits) {
    if (gateQubits == null || blockQubits == null) {
      return false;
    }
    for (int gateQubit : gateQubits) {
      if (indexOfQubit(blockQubits, gateQubit) < 0) {
        return false;
      }
    }
    return true;
  }

  int indexOfQubit(int[] qubits, int target) {
    if (qubits == null) {
      return -1;
    }
    for (int i = 0; i < qubits.length; i += 1) {
      if (qubits[i] == target) {
        return i;
      }
    }
    return -1;
  }

  int basisBit(int basisIndex, int blockQubitCount, int blockPosition) {
    return (basisIndex >> max(0, blockPosition)) & 1;
  }

  int localGateBasisIndex(int basisIndex, int blockQubitCount, int[] gatePositions) {
    int localIndex = 0;
    for (int i = 0; i < gatePositions.length; i += 1) {
      int bit = basisBit(basisIndex, blockQubitCount, gatePositions[i]);
      localIndex = (localIndex << 1) | bit;
    }
    return localIndex;
  }

  boolean isApproximatelyUnitary(ComplexEntry[][] matrix, float eps) {
    if (matrix == null || matrix.length == 0 || matrix.length != matrix[0].length) {
      return false;
    }
    int dim = matrix.length;
    for (int i = 0; i < dim; i += 1) {
      for (int j = 0; j < dim; j += 1) {
        float sumRe = 0.0;
        float sumIm = 0.0;
        for (int k = 0; k < dim; k += 1) {
          ComplexEntry aik = matrix[i][k];
          ComplexEntry ajk = matrix[j][k];
          sumRe += aik.re * ajk.re + aik.im * ajk.im;
          sumIm += aik.im * ajk.re - aik.re * ajk.im;
        }
        float targetRe = i == j ? 1.0 : 0.0;
        float diffRe = sumRe - targetRe;
        float diffIm = sumIm;
        float err = sqrt(diffRe * diffRe + diffIm * diffIm);
        if (err > eps) {
          return false;
        }
      }
    }
    return true;
  }

  int resolveActiveTargetRank(CellInfluenceMap influenceMap, StoryBeat beat, int totalCells) {
    if (influenceMap == null || influenceMap.ranked == null || influenceMap.ranked.isEmpty()) {
      return 0;
    }
    float frontier = influenceMap.frontierIndex(beat);
    int maxRank = min(influenceMap.ranked.size() - 1, max(0, totalCells - 1));
    return clampInt(round(frontier), 0, maxRank);
  }

  void drawDecompositionOverlay(MatrixViewMetrics geometry, DecompositionOverlayState state, float revealDim) {
    if (geometry == null || state == null || !state.active || state.terms == null || state.terms.isEmpty()) {
      return;
    }

    float safeReveal = clampFloat(revealDim, 0.0, 1.0);
    float safeMaxWeight = max(state.maxWeight, DECOMP_EPS);
    float targetX = geometry.localXForIndex(state.targetCol);
    float targetY = geometry.localYForIndex(state.targetRow);

    pushStyle();
    for (DecompositionTerm term : state.terms) {
      float sourceX = geometry.localXForIndex(term.srcCol);
      float sourceY = geometry.localYForIndex(term.srcRow);
      float strength = clampFloat(term.weight / safeMaxWeight, 0.0, 1.0);
      int rayColor = decompositionPhaseColor(term.phase, strength, safeReveal);

      stroke(rayColor);
      strokeWeight(0.55 + 2.2 * strength);
      line(sourceX, sourceY, DECOMP_MARKER_Z, targetX, targetY, DECOMP_TARGET_Z);

      noStroke();
      fill(red(rayColor), green(rayColor), blue(rayColor), 55 + 145 * strength);
      pushMatrix();
      translate(sourceX, sourceY, DECOMP_MARKER_Z + 0.05);
      ellipse(0, 0, 2.3 + 3.8 * strength, 2.3 + 3.8 * strength);
      popMatrix();
    }

    float pulse = 0.5 + 0.5 * sin(frameCount * 0.12);
    noFill();
    stroke(246, 249, 255, (118 + 92 * pulse) * safeReveal);
    strokeWeight(1.15);
    pushMatrix();
    translate(targetX, targetY, DECOMP_TARGET_Z + 0.08);
    float ring = max(7.0, geometry.cubeSize * 0.50);
    ellipse(0, 0, ring, ring);
    stroke(238, 245, 255, (96 + 72 * pulse) * safeReveal);
    strokeWeight(0.85);
    line(-ring * 0.28, 0, ring * 0.28, 0);
    line(0, -ring * 0.28, 0, ring * 0.28);
    popMatrix();
    popStyle();
  }

  int decompositionPhaseColor(float phase, float strength, float revealDim) {
    float hue = ((phase + PI) / TWO_PI) * 360.0;
    float sat = 22.0 + 28.0 * clampFloat(strength, 0.0, 1.0);
    float bri = 90.0;
    float alpha = (36.0 + 190.0 * clampFloat(strength, 0.0, 1.0)) * clampFloat(revealDim, 0.0, 1.0);
    pushStyle();
    colorMode(HSB, 360, 100, 100, 255);
    int value = color(hue, sat, bri, alpha);
    popStyle();
    return value;
  }

  void drawMinimalCaption(
    PanelRect panel,
    PlaybackState playback,
    TraceModel traceModel,
    float revealProgress,
    ReducedDensitySample rho
  ) {
    int alpha = round(clampFloat(revealProgress, 0, 1) * 255);
    hint(DISABLE_DEPTH_TEST);
    noStroke();

    fill(255, alpha);
    textAlign(LEFT, TOP);
    textSize(16);
    text("rho(t)", panel.x + 14, panel.y + 12);

    fill(255, 210);
    textSize(12);
    text(
      "Step " + (playback.stepIndex + 1) + "/" + traceModel.stepCount + " · phase " + playback.phase,
      panel.x + 14,
      panel.y + 32
    );

    fill(255, 175);
    textAlign(RIGHT, TOP);
    textSize(11);
    text(gateCaption(playback), panel.x + panel.w - 14, panel.y + 12);
    String blockLabel = rho != null ? "Block " + qubitLabel(rho.qubits) : "Block unavailable";
    text(blockLabel, panel.x + panel.w - 14, panel.y + 28);
    textSize(10);
    text("Mode: " + hudRenderModeLabel, panel.x + panel.w - 14, panel.y + 44);
    text(hudContextLabel, panel.x + panel.w - 14, panel.y + 58);
    text(hudCircuitLabel, panel.x + panel.w - 14, panel.y + 72);
    String layerCaption = "Layers: " + hudVisibleLayerCount + "/" + max(0, hudAvailableLayerCount)
      + " (full-history, no cap, includes |0...0> base)";
    if (isShotReplaySourcePhase(playback)) {
      layerCaption = "Layers: 1/1 (active measured shot state only)";
    }
    text(layerCaption, panel.x + panel.w - 14, panel.y + 86);
    if (playback.inShotReplay) {
      String shotLabel = playback.shotIndex >= 0
        ? ("Shot " + (playback.shotIndex + 1) + "/" + max(1, playback.shotsTotal))
        : ("Shot replay prep · total " + max(0, playback.shotsTotal));
      String outcomeLabel = playback.shotOutcomeLabel != null && playback.shotOutcomeLabel.length() > 0
        ? ("Outcome " + playback.shotOutcomeLabel)
        : "Outcome pending";
      boolean showSourceLabel = hudShotResponsibleSourceLabel != null
        && hudShotResponsibleSourceLabel.length() > 0
        && ("shot_stack".equals(playback.phase)
          || ("shot_histogram_project".equals(playback.phase) && playback.shotIndex >= 0));
      if (showSourceLabel) {
        outcomeLabel += " · source " + hudShotResponsibleSourceLabel;
      }
      text(shotLabel + " · " + outcomeLabel, panel.x + panel.w - 14, panel.y + 100);
    }

    drawCircuitLensInset(panel, playback, traceModel, revealProgress);

    float summaryY = panel.y + panel.h - 24;
    if ("apply_gate".equals(playback.phase)) {
      if (hudDecompositionActive) {
        fill(255, 122);
        textAlign(LEFT, TOP);
        textSize(10);
        text(hudDecompositionLabel, panel.x + 14, summaryY - 28);
      } else if (hudDecompositionReason != null && hudDecompositionReason.length() > 0) {
        fill(255, 96);
        textAlign(LEFT, TOP);
        textSize(9);
        text("Decomp: " + hudDecompositionReason, panel.x + 14, summaryY - 28);
      }
      fill(255, 120);
      textAlign(LEFT, TOP);
      textSize(10);
      text("rho(t) = U(t) rho U(t)^dagger", panel.x + 14, summaryY - 14);
    } else if ("shot_stack".equals(playback.phase)) {
      fill(255, 126);
      textAlign(LEFT, TOP);
      textSize(10);
      text("Shot stack: active density shows this shot's measured outcome state; histogram pending", panel.x + 14, summaryY - 14);
    } else if ("shot_camera_pullback".equals(playback.phase)) {
      fill(255, 120);
      textAlign(LEFT, TOP);
      textSize(10);
      text("Replay prep: camera pulls back while density holds collapsed measured state; qubit cubes stay hidden", panel.x + 14, summaryY - 14);
    } else if ("shot_histogram_project".equals(playback.phase)) {
      fill(255, 120);
      textAlign(LEFT, TOP);
      textSize(10);
      if (playback.shotIndex < 0) {
        text("Projection prep: camera shifts to histogram while density holds the final stacked measured shot state", panel.x + 14, summaryY - 14);
      } else {
        text("Projecting stacked shots to histogram from this shot's measured outcome state", panel.x + 14, summaryY - 14);
      }
    }

    fill(255, "apply_gate".equals(playback.phase) ? 120 : 140);
    textAlign(LEFT, TOP);
    textSize(11);
    text(stageSummary(playback), panel.x + 14, summaryY);

    if (!"apply_gate".equals(playback.phase)) {
      fill(255, 110);
      textAlign(RIGHT, TOP);
      textSize(10);
      text("H: toggle controls", panel.x + panel.w - 14, summaryY);
    }

    // Measurement reveal text overlay is intentionally suppressed.
    hint(ENABLE_DEPTH_TEST);
  }

  void drawMissingBlockMessage(PanelRect panel, String message) {
    noStroke();
    fill(255, 180);
    textAlign(CENTER, CENTER);
    textSize(14);
    text(message, panel.x + panel.w * 0.5, panel.y + panel.h * 0.5);
  }

  void drawMeasurementRevealLabel(PanelRect panel, TraceModel traceModel, float phaseProgress) {
    String outcome = traceModel.selectedOutcome != null ? traceModel.selectedOutcome : "";
    StoryBeat beat = resolveStoryBeat("measurement_reveal", phaseProgress);
    float progress = easeInOutCirc01(beat.beatProgress);
    float cx = panel.x + panel.w * 0.5;
    float cy = panel.y + panel.h * 0.53;
    float glyphSize = clampFloat(min(panel.w, panel.h) * 0.22, 86.0, 230.0);

    if (outcome.length() == 0) {
      float missAlpha = 145 + 95 * progress;
      fill(255, missAlpha);
      textAlign(CENTER, CENTER);
      textSize(clampFloat(panel.w * 0.024, 20, 34));
      text("Outcome unavailable", cx, cy - 8);
      fill(255, 132);
      textSize(clampFloat(panel.w * 0.010, 11, 16));
      text("collapse label missing in trace", cx, cy + 24);
      return;
    }

    float fillAlpha = 165 + 80 * progress;
    float shadowAlpha = 75 + 55 * progress;
    float subtitleAlpha = 130 + 100 * progress;
    float subtitleSize = clampFloat(panel.w * 0.010, 12, 19);

    textAlign(CENTER, CENTER);
    textSize(glyphSize);

    fill(0, shadowAlpha);
    text(outcome, cx + 3, cy + 4);

    fill(255, fillAlpha);
    text(outcome, cx, cy);

    fill(255, subtitleAlpha);
    textSize(subtitleSize);
    text("mode=collapse · p=" + nf(traceModel.selectedOutcomeProbability, 1, 4), cx, cy + glyphSize * 0.36);
  }

  void drawCircuitLensInset(
    PanelRect panel,
    PlaybackState playback,
    TraceModel traceModel,
    float revealProgress
  ) {
    if (traceModel == null || traceModel.steps == null || traceModel.steps.isEmpty() || playback == null) {
      return;
    }

    int stepCount = max(1, traceModel.stepCount);
    int activeIndex = clampInt(playback.stepIndex, 0, stepCount - 1);
    CircuitLensGateSpec activeSpec = circuitLensSpecAt(activeIndex);
    float alphaGate = clampFloat(revealProgress, 0.0, 1.0);
    if ("measurement_reveal".equals(playback.phase)) {
      alphaGate *= 0.82;
    } else if (playback.inShotReplay) {
      alphaGate *= 0.66;
    }

    float insetX = panel.x + 14;
    float insetY = panel.y + 54;
    float insetW = clampFloat(panel.w * 0.30, 260.0, 620.0);
    int qubitCount = max(1, circuitLensQubitCount);
    float desiredWirePitch = 13.0;
    float requiredWireSpan = max(0, qubitCount - 1) * desiredWirePitch;
    float insetH = clampFloat(max(96.0, 58.0 + requiredWireSpan), 96.0, 228.0);
    float padding = 8.0;
    float labelLaneW = qubitCount >= 10 ? 36.0 : 30.0;
    float laneLeft = insetX + padding + labelLaneW;
    float laneRight = insetX + insetW - padding;
    float laneWidth = max(1.0, laneRight - laneLeft);
    float wiresTop = insetY + 26.0;
    float wiresBottom = insetY + insetH - 28.0;
    if (wiresBottom <= wiresTop) {
      wiresBottom = wiresTop + 1.0;
    }
    float wireSpacing = qubitCount <= 1 ? 0.0 : (wiresBottom - wiresTop) / float(max(1, qubitCount - 1));
    float[] wireY = new float[qubitCount];
    for (int qubitIndex = 0; qubitIndex < qubitCount; qubitIndex += 1) {
      wireY[qubitIndex] = qubitCount <= 1
        ? (wiresTop + wiresBottom) * 0.5
        : wiresTop + qubitIndex * wireSpacing;
    }
    float spacing = CIRCUIT_LENS_GATE_PITCH_PX;
    float contentSpan = circuitLensContentSpan(stepCount, spacing);
    float maxOffset = circuitLensMaxOffset(contentSpan, laneWidth);
    float anchorX = laneWidth * CIRCUIT_LENS_ACTIVE_ANCHOR_RATIO;
    float targetOffset = circuitLensTargetOffset(activeIndex, spacing, anchorX);
    float scrollOffset = circuitLensScrollOffset(targetOffset, maxOffset);
    int phaseTint = phaseColor(playback.phase);
    float activeX = circuitLensXForIndex(laneLeft, spacing, scrollOffset, activeIndex);
    float activeProgress = clampFloat(playback.phaseProgress, 0.0, 1.0);

    noStroke();
    fill(8, 10, 14, 172 * alphaGate);
    rect(insetX, insetY, insetW, insetH, 7);
    stroke(218, 224, 238, 72 * alphaGate);
    strokeWeight(0.8);
    noFill();
    rect(insetX, insetY, insetW, insetH, 7);

    noStroke();
    fill(255, 188 * alphaGate);
    textAlign(LEFT, TOP);
    textSize(10);
    text(
      "Circuit Lens · Step " + (activeIndex + 1) + "/" + stepCount + " · " + playback.phase,
      insetX + padding,
      insetY + 5
    );

    float activeColumnW = clampFloat(spacing * 0.72, 6.0, 24.0);
    noStroke();
    fill(red(phaseTint), green(phaseTint), blue(phaseTint), 34 * alphaGate);
    rect(activeX - activeColumnW * 0.5, wiresTop - 7.0, activeColumnW, (wiresBottom - wiresTop) + 14.0, 3.0);

    textAlign(RIGHT, CENTER);
    textSize(8);
    for (int qubitIndex = 0; qubitIndex < qubitCount; qubitIndex += 1) {
      stroke(206, 214, 232, 72 * alphaGate);
      strokeWeight(qubitIndex == 0 || qubitIndex == qubitCount - 1 ? 1.0 : 0.8);
      line(laneLeft, wireY[qubitIndex], laneRight, wireY[qubitIndex]);
      fill(194, 204, 226, 150 * alphaGate);
      text("q" + qubitIndex, laneLeft - 4, wireY[qubitIndex]);
    }

    if (maxOffset > 0.0) {
      float indicatorCenterY = (wiresTop + wiresBottom) * 0.5;
      float indicatorArm = 4.0;
      noStroke();
      fill(194, 204, 226, 142 * alphaGate);
      if (scrollOffset > 0.0) {
        triangle(
          laneLeft + 4.0,
          indicatorCenterY,
          laneLeft + 10.0,
          indicatorCenterY - indicatorArm,
          laneLeft + 10.0,
          indicatorCenterY + indicatorArm
        );
      }
      if (scrollOffset < maxOffset - 1e-4) {
        triangle(
          laneRight - 4.0,
          indicatorCenterY,
          laneRight - 10.0,
          indicatorCenterY - indicatorArm,
          laneRight - 10.0,
          indicatorCenterY + indicatorArm
        );
      }
    }

    int visibleColumns = max(1, floor(laneWidth / spacing) + 1);
    int maxLabelCount = clampInt(visibleColumns, 4, 12);
    int labelStride = max(1, ceil(stepCount / float(max(1, maxLabelCount))));
    for (int index = 0; index < stepCount; index += 1) {
      float x = circuitLensXForIndex(laneLeft, spacing, scrollOffset, index);
      CircuitLensGateSpec spec = circuitLensSpecAt(index);
      boolean active = index == activeIndex;
      boolean visible = circuitLensColumnVisible(x, laneLeft, laneRight, CIRCUIT_LENS_CULL_MARGIN_PX);
      if (!visible && !active) {
        continue;
      }
      drawCircuitLensGateGlyph(spec, x, wireY, qubitCount, active, phaseTint, alphaGate);

      boolean showLabel = visible && (active || index == 0 || index == stepCount - 1 || index % labelStride == 0);
      if (showLabel) {
        String token = spec != null ? spec.gateToken : "U";
        textAlign(CENTER, BOTTOM);
        textSize(active ? 9 : 8);
        if (active) {
          fill(red(phaseTint), green(phaseTint), blue(phaseTint), 235 * alphaGate);
        } else {
          fill(194, 204, 226, 135 * alphaGate);
        }
        float offset = active ? 0.0 : ((index / max(1, labelStride)) % 2 == 0 ? 0.0 : 7.0);
        text(token, x, wiresTop - 5.0 - offset);
      }
    }

    float progressW = clampFloat(spacing * 0.92, 14.0, 34.0);
    float progressLeft = activeX - progressW * 0.5;
    float progressY = insetY + insetH - 14.0;
    noStroke();
    fill(255, 45 * alphaGate);
    rect(progressLeft, progressY, progressW, 2.4, 1.1);
    fill(phaseTint);
    rect(progressLeft, progressY, progressW * activeProgress, 2.4, 1.1);

    String activeGateLabel = "UNAVAILABLE";
    String activeQubitLabel = "[]";
    if (activeSpec != null) {
      activeGateLabel = activeSpec.rawGateName != null && activeSpec.rawGateName.length() > 0
        ? activeSpec.rawGateName
        : activeSpec.operationId;
      if (activeSpec.qubits != null && activeSpec.qubits.length > 0) {
        activeQubitLabel = qubitLabel(activeSpec.qubits);
      }
    } else if (playback.step != null) {
      activeGateLabel = playback.step.gateLabel != null && playback.step.gateLabel.length() > 0
        ? playback.step.gateLabel
        : playback.step.operationId;
    }

    noStroke();
    fill(255, 154 * alphaGate);
    textAlign(LEFT, TOP);
    textSize(10);
    text(
      "active " + activeGateLabel + " · " + activeQubitLabel,
      insetX + padding,
      insetY + insetH - 16
    );
  }

  void drawCircuitLensGateGlyph(
    CircuitLensGateSpec spec,
    float x,
    float[] wireY,
    int qubitCount,
    boolean active,
    int phaseTint,
    float alphaGate
  ) {
    if (wireY == null || wireY.length == 0) {
      return;
    }
    if (spec == null) {
      spec = new CircuitLensGateSpec(
        0,
        "U",
        "unknown",
        "unknown",
        new int[] { 0 },
        new int[0],
        new int[] { 0 },
        CircuitLensRenderKind.IDLE_UNKNOWN
      );
    }

    int neutralR = 214;
    int neutralG = 222;
    int neutralB = 238;
    float activeMix = active ? 1.0 : 0.0;
    float r = lerp(neutralR, red(phaseTint), activeMix);
    float g = lerp(neutralG, green(phaseTint), activeMix);
    float b = lerp(neutralB, blue(phaseTint), activeMix);
    float connectorAlpha = (active ? 175.0 : 108.0) * alphaGate;
    float glyphAlpha = (active ? 220.0 : 158.0) * alphaGate;
    float tokenAlpha = (active ? 245.0 : 176.0) * alphaGate;

    int[] mappedQubits = mapQubitsToLensWires(spec.qubits, qubitCount);
    int[] mappedControls = mapQubitsToLensWires(spec.controlQubits, qubitCount);
    int[] mappedTargets = mapQubitsToLensWires(spec.targetQubits, qubitCount);

    int minWire = mappedQubits.length > 0 ? mappedQubits[0] : max(0, qubitCount / 2);
    int maxWire = mappedQubits.length > 0 ? mappedQubits[mappedQubits.length - 1] : minWire;
    for (int wire : mappedQubits) {
      minWire = min(minWire, wire);
      maxWire = max(maxWire, wire);
    }
    float centerY = wireY[clampInt((minWire + maxWire) / 2, 0, qubitCount - 1)];
    float boxW = 13.0;
    float boxH = 10.0;
    if (spec.renderKind == CircuitLensRenderKind.IDLE_UNKNOWN && mappedQubits.length == 0) {
      boxW = 11.0;
      boxH = 9.0;
    }

    if ((spec.renderKind == CircuitLensRenderKind.CONTROL_TARGET
        || spec.renderKind == CircuitLensRenderKind.SWAP
        || spec.renderKind == CircuitLensRenderKind.GENERIC_MULTI)
      && maxWire > minWire) {
      stroke(r, g, b, connectorAlpha);
      strokeWeight(active ? 1.35 : 1.0);
      line(x, wireY[minWire], x, wireY[maxWire]);
    }

    if (spec.renderKind == CircuitLensRenderKind.CONTROL_TARGET || spec.renderKind == CircuitLensRenderKind.SWAP) {
      for (int controlWire : mappedControls) {
        noStroke();
        fill(r, g, b, glyphAlpha);
        ellipse(x, wireY[controlWire], active ? 8.0 : 6.2, active ? 8.0 : 6.2);
      }
    }

    if (spec.renderKind == CircuitLensRenderKind.SWAP) {
      for (int targetWire : mappedTargets) {
        float y = wireY[targetWire];
        stroke(r, g, b, glyphAlpha);
        strokeWeight(active ? 1.65 : 1.25);
        float arm = active ? 5.5 : 4.3;
        line(x - arm, y - arm, x + arm, y + arm);
        line(x - arm, y + arm, x + arm, y - arm);
      }
    } else if (spec.renderKind == CircuitLensRenderKind.CONTROL_TARGET) {
      int[] drawTargets = mappedTargets.length > 0 ? mappedTargets : mappedQubits;
      for (int targetWire : drawTargets) {
        drawCircuitLensGateBox(x, wireY[targetWire], boxW, boxH, spec.gateToken, r, g, b, glyphAlpha, tokenAlpha, active);
      }
    } else if (spec.renderKind == CircuitLensRenderKind.MEASURE) {
      int[] drawTargets = mappedTargets.length > 0 ? mappedTargets : mappedQubits;
      if (drawTargets.length == 0) {
        drawTargets = new int[] { clampInt(qubitCount / 2, 0, qubitCount - 1) };
      }
      for (int targetWire : drawTargets) {
        drawCircuitLensGateBox(x, wireY[targetWire], boxW, boxH, "M", r, g, b, glyphAlpha, tokenAlpha, active);
      }
    } else if (spec.renderKind == CircuitLensRenderKind.SINGLE) {
      int drawWire = mappedTargets.length > 0
        ? mappedTargets[0]
        : (mappedQubits.length > 0 ? mappedQubits[0] : clampInt(qubitCount / 2, 0, qubitCount - 1));
      drawCircuitLensGateBox(x, wireY[drawWire], boxW, boxH, spec.gateToken, r, g, b, glyphAlpha, tokenAlpha, active);
    } else if (spec.renderKind == CircuitLensRenderKind.GENERIC_MULTI) {
      int[] drawQubits = mappedQubits.length > 0 ? mappedQubits : mappedTargets;
      if (drawQubits.length == 0) {
        drawQubits = new int[] { clampInt(qubitCount / 2, 0, qubitCount - 1) };
      }
      for (int qubit : drawQubits) {
        drawCircuitLensGateBox(x, wireY[qubit], boxW, boxH, spec.gateToken, r, g, b, glyphAlpha, tokenAlpha, active);
      }
    } else {
      drawCircuitLensGateBox(x, centerY, boxW, boxH, spec.gateToken, r, g, b, glyphAlpha, tokenAlpha, active);
    }

  }

  void drawCircuitLensGateBox(
    float x,
    float y,
    float boxW,
    float boxH,
    String token,
    float r,
    float g,
    float b,
    float fillAlpha,
    float tokenAlpha,
    boolean active
  ) {
    float safeW = max(8.0, boxW);
    float safeH = max(7.0, boxH);
    stroke(r, g, b, active ? min(255.0, fillAlpha + 24.0) : fillAlpha);
    strokeWeight(active ? 1.35 : 1.0);
    fill(13, 18, 28, active ? 224 : 188);
    rect(x - safeW * 0.5, y - safeH * 0.5, safeW, safeH, 2.0);

    fill(r, g, b, tokenAlpha);
    textAlign(CENTER, CENTER);
    textSize(active ? 8 : 7);
    String safeToken = token != null && token.length() > 0 ? token : "U";
    if (safeToken.length() > 4) {
      safeToken = safeToken.substring(0, 4);
    }
    text(safeToken, x, y + 0.3);
  }

  int luminanceColor(float normalizedMagnitude) {
    float n = clampFloat(normalizedMagnitude, 0, 1);
    int v = round(34 + n * 212);
    return color(v, v, v, 255);
  }

  int phaseEdgeColor(float normalizedPhase, boolean changed, float actorInfluence, float normalizedDelta) {
    float n = clampFloat(normalizedPhase, 0, 1);
    float a = clampFloat(actorInfluence, 0, 1);
    float d = clampFloat(normalizedDelta, 0, 1);
    float hue = n * 360.0;
    float sat = (changed ? 13 : 7) + a * 9.0 + d * 6.0;
    float bri = 88 + a * 8.0;
    float alpha = (changed ? 82 : 60) + a * 64.0 + d * 18.0;

    pushStyle();
    colorMode(HSB, 360, 100, 100, 255);
    int value = color(hue, sat, min(100, bri), min(255, alpha));
    popStyle();
    return value;
  }

  int pulseRingColor(float pulse) {
    float p = clampFloat(pulse, 0, 1);
    int v = round(212 + 38 * p);
    int alpha = round(46 + 122 * p);
    return color(v, v, v, alpha);
  }

  int applyLuminanceDim(int baseColor, float dim) {
    float safeDim = clampFloat(dim, 0.0, 1.0);
    return color(
      round(red(baseColor) * safeDim),
      round(green(baseColor) * safeDim),
      round(blue(baseColor) * safeDim),
      alpha(baseColor)
    );
  }

  int applyAlphaDim(int baseColor, float dim) {
    float safeDim = clampFloat(dim, 0.0, 1.0);
    return color(
      red(baseColor),
      green(baseColor),
      blue(baseColor),
      round(alpha(baseColor) * safeDim)
    );
  }

  int resolveShotQubitBitGray(int bit, float bitValue) {
    if (bit < 0) {
      return SHOT_QUBIT_BIT_UNKNOWN_GRAY;
    }
    float safeBitValue = clampFloat(bitValue, 0.0, 1.0);
    float mapped = lerp(
      float(SHOT_QUBIT_BIT_0_GRAY),
      float(SHOT_QUBIT_BIT_1_GRAY),
      safeBitValue
    );
    return round(clampFloat(mapped, SHOT_QUBIT_BIT_0_GRAY, SHOT_QUBIT_BIT_1_GRAY));
  }

  float resolveShotQubitLayerLumaDim(boolean activeLayer, float ageAlpha) {
    if (activeLayer) {
      return 1.0;
    }
    float safeAgeAlpha = clampFloat(ageAlpha, 0.0, 1.0);
    return clampFloat(
      lerp(SHOT_QUBIT_HISTORICAL_LUMA_DIM_MIN, 1.0, safeAgeAlpha),
      SHOT_QUBIT_HISTORICAL_LUMA_DIM_MIN,
      1.0
    );
  }

  float resolveShotQubitLayerAlphaDim(boolean activeLayer, float ageAlpha, float phaseAlpha) {
    float safeAgeAlpha = clampFloat(ageAlpha, 0.0, 1.0);
    float safePhaseAlpha = clampFloat(phaseAlpha, 0.0, 1.0);
    if (activeLayer) {
      return safePhaseAlpha;
    }
    float historical = lerp(SHOT_QUBIT_HISTORICAL_ALPHA_DIM_MIN, 1.0, safeAgeAlpha);
    return clampFloat(historical * safePhaseAlpha, SHOT_QUBIT_HISTORICAL_ALPHA_DIM_MIN * safePhaseAlpha, safePhaseAlpha);
  }

  int resolveShotQubitFillColor(int bit, float bitValue, boolean activeLayer, float ageAlpha, float phaseAlpha) {
    int baseGray = resolveShotQubitBitGray(bit, bitValue);
    int baseColor = color(baseGray, baseGray, baseGray, 255);
    int lumColor = applyLuminanceDim(baseColor, resolveShotQubitLayerLumaDim(activeLayer, ageAlpha));
    return applyAlphaDim(lumColor, resolveShotQubitLayerAlphaDim(activeLayer, ageAlpha, phaseAlpha));
  }

  int resolveShotQubitEdgeColor(
    int bit,
    float bitValue,
    boolean activeLayer,
    float ageAlpha,
    float phaseAlpha,
    float pulse
  ) {
    int baseGray = resolveShotQubitBitGray(bit, bitValue);
    float safePulse = clampFloat(pulse, 0.0, 1.0);
    int edgeBoost = activeLayer
      ? round(lerp(float(SHOT_QUBIT_EDGE_GRAY_BOOST_BASE), float(SHOT_QUBIT_EDGE_GRAY_BOOST_ACTIVE), safePulse))
      : SHOT_QUBIT_EDGE_GRAY_BOOST_BASE;
    int edgeGray = min(255, baseGray + edgeBoost);
    int baseColor = color(edgeGray, edgeGray, edgeGray, 255);
    int lumColor = applyLuminanceDim(baseColor, resolveShotQubitLayerLumaDim(activeLayer, ageAlpha));
    return applyAlphaDim(lumColor, resolveShotQubitLayerAlphaDim(activeLayer, ageAlpha, phaseAlpha));
  }

  void drawCubeCell(
    MatrixCellEntity entity,
    int fillColor,
    int edgeColor,
    boolean changed,
    float actorInfluence,
    boolean allowPulse
  ) {
    float w = max(2.0, entity.curSize.x);
    float h = max(2.0, entity.curSize.y);
    float d = max(2.0, entity.curSize.z);
    float influence = clampFloat(actorInfluence, 0, 1);

    pushMatrix();
    translate(entity.curPos.x, entity.curPos.y, entity.curPos.z);

    fill(fillColor);
    stroke(edgeColor);
    strokeWeight((changed ? 0.95 : 0.70) + 0.50 * influence);
    box(w, h, d);

    if (allowPulse && influence > 0.12) {
      float pulse = clampFloat((influence - 0.12) / 0.88, 0, 1);
      float ringGrow = (1.0 - pulse) * 5.2 + 1.2;
      noFill();
      stroke(pulseRingColor(pulse));
      strokeWeight(0.55 + pulse * 1.1);
      box(w + ringGrow, h + ringGrow, d + ringGrow);
    }

    popMatrix();
  }

  StoryBeat resolveStoryBeat(String phase, float phaseProgress) {
    float p = clampFloat(phaseProgress, 0.0, 1.0);

    if ("apply_gate".equals(phase)) {
      float enterEnd = 0.15;
      float scanEnd = 0.85;

      if (p < enterEnd) {
        float local = clampFloat(p / max(1e-6, enterEnd), 0.0, 1.0);
        float intensity = 0.30 + 0.70 * easeInOutCirc01(local);
        return new StoryBeat(phase, "enter", p, local, true, intensity, 0.0);
      }

      if (p < scanEnd) {
        float local = clampFloat((p - enterEnd) / max(1e-6, scanEnd - enterEnd), 0.0, 1.0);
        return new StoryBeat(phase, "scan", p, local, true, 1.0, local);
      }

      float local = clampFloat((p - scanEnd) / max(1e-6, 1.0 - scanEnd), 0.0, 1.0);
      float intensity = 1.0 - easeInOutCirc01(local);
      return new StoryBeat(phase, "exit", p, local, true, intensity, 1.0);
    }

    if ("measurement_reveal".equals(phase)) {
      if (p < 0.40) {
        float local = clampFloat(p / 0.40, 0.0, 1.0);
        return new StoryBeat(phase, "label_in", p, local, false, 0.0, 0.0);
      }
      float local = clampFloat((p - 0.40) / 0.60, 0.0, 1.0);
      return new StoryBeat(phase, "label_hold", p, local, false, 0.0, 0.0);
    }

    if ("shot_camera_pullback".equals(phase)) {
      return new StoryBeat(phase, "pullback", p, p, false, 0.0, 0.0);
    }

    if ("shot_histogram_project".equals(phase)) {
      return new StoryBeat(phase, "project", p, p, false, 0.0, 0.0);
    }

    if ("shot_stack".equals(phase)) {
      return new StoryBeat(phase, "stack", p, p, false, 0.0, 0.0);
    }

    if ("settle".equals(phase)) {
      return new StoryBeat(phase, "hold", p, p, false, 0.0, 0.0);
    }

    return new StoryBeat(phase, "hold", p, p, false, 0.0, 0.0);
  }

  int durationForBeat(StoryBeat beat, TraceStep step) {
    int nominal = 24;
    if ("enter".equals(beat.beat) || "exit".equals(beat.beat)) {
      nominal = 26;
    } else if ("scan".equals(beat.beat)) {
      nominal = 40;
    } else if ("stack".equals(beat.beat)) {
      nominal = 10;
    } else if ("project".equals(beat.beat) || "pullback".equals(beat.beat)) {
      nominal = 14;
    } else if ("hold".equals(beat.beat) || "label_in".equals(beat.beat) || "label_hold".equals(beat.beat)) {
      nominal = 24;
    }

    int phaseFrames = phaseFrameCount(step, beat.phase);
    if ("measurement_reveal".equals(beat.phase)) {
      phaseFrames = 48;
    }
    if (phaseFrames <= 0) {
      return nominal;
    }

    int reference = 24;
    if ("apply_gate".equals(beat.phase)) {
      reference = 53;
    } else if ("pre_gate".equals(beat.phase)) {
      reference = 19;
    } else if ("settle".equals(beat.phase)) {
      reference = 24;
    } else if ("measurement_reveal".equals(beat.phase)) {
      reference = 48;
    } else if ("shot_camera_pullback".equals(beat.phase)) {
      reference = 36;
    } else if ("shot_histogram_project".equals(beat.phase)) {
      reference = 30;
    } else if ("shot_stack".equals(beat.phase)) {
      reference = 6;
    }
    float scaled = nominal * (phaseFrames / float(max(1, reference)));
    return max(6, round(scaled));
  }

  int phaseFrameCount(TraceStep step, String phase) {
    if (step == null || step.phaseWindows == null || step.phaseWindows.isEmpty()) {
      return 0;
    }
    int total = 0;
    for (PhaseWindow window : step.phaseWindows) {
      if (window != null && phase.equals(window.phase)) {
        total += max(0, window.endFrame - window.startFrame);
      }
    }
    return total;
  }

  CellInfluenceMap buildCellInfluenceMap(
    float[][] real,
    float[][] imag,
    float[][] previousReal,
    float[][] previousImag,
    MatrixViewMetrics geometry
  ) {
    int rows = real.length;
    int cols = real[0].length;
    CellInfluenceMap map = new CellInfluenceMap(rows, cols);

    for (int row = 0; row < rows; row += 1) {
      for (int col = 0; col < cols; col += 1) {
        float re = real[row][col];
        float im = imag[row][col];
        float prevRe = matrixValue(previousReal, row, col, re);
        float prevIm = matrixValue(previousImag, row, col, im);
        float diffRe = re - prevRe;
        float diffIm = im - prevIm;
        float delta = sqrt(diffRe * diffRe + diffIm * diffIm);
        map.addCell(row, col, delta, geometry.localXForIndex(col), geometry.localYForIndex(row));
      }
    }

    map.finalizeMap();
    return map;
  }

  CellInfluenceMap buildCellInfluenceMapFromDelta(float[][] deltaMatrix, MatrixViewMetrics geometry) {
    int rows = deltaMatrix != null ? max(1, deltaMatrix.length) : max(1, geometry != null ? geometry.rows : 1);
    int cols = 1;
    if (deltaMatrix != null && deltaMatrix.length > 0 && deltaMatrix[0] != null) {
      cols = max(1, deltaMatrix[0].length);
    } else if (geometry != null) {
      cols = max(1, geometry.cols);
    }

    CellInfluenceMap map = new CellInfluenceMap(rows, cols);
    if (deltaMatrix == null || geometry == null) {
      return map;
    }

    for (int row = 0; row < rows; row += 1) {
      for (int col = 0; col < cols; col += 1) {
        float delta = matrixValue(deltaMatrix, row, col, 0.0);
        map.addCell(row, col, max(0.0, delta), geometry.localXForIndex(col), geometry.localYForIndex(row));
      }
    }
    map.finalizeMap();
    return map;
  }

  int resolveDensityRenderMode(int fullDim) {
    return DensityRenderMode.RAW;
  }

  int resolveLodGridDim(int fullDim) {
    return max(1, fullDim);
  }

  LodDensityGrid buildLodDensityGrid(
    float[][] real,
    float[][] imag,
    float[][] previousReal,
    float[][] previousImag,
    int targetDim
  ) {
    if (!isRectangular(real, imag)) {
      return new LodDensityGrid(1, 1);
    }

    int sourceRows = real.length;
    int sourceCols = real[0].length;
    int targetRows = clampInt(targetDim, 1, sourceRows);
    int targetCols = clampInt(targetDim, 1, sourceCols);
    LodDensityGrid grid = new LodDensityGrid(targetRows, targetCols);

    float[][] sumRe = new float[targetRows][targetCols];
    float[][] sumIm = new float[targetRows][targetCols];
    float[][] sumMagSq = new float[targetRows][targetCols];
    float[][] sumDelta = new float[targetRows][targetCols];
    float[][] count = new float[targetRows][targetCols];
    float[][] diagCount = new float[targetRows][targetCols];

    for (int row = 0; row < sourceRows; row += 1) {
      int tileRow = clampInt(floor(row * targetRows / float(max(1, sourceRows))), 0, targetRows - 1);
      for (int col = 0; col < sourceCols; col += 1) {
        int tileCol = clampInt(floor(col * targetCols / float(max(1, sourceCols))), 0, targetCols - 1);
        float re = real[row][col];
        float im = imag[row][col];
        float prevRe = matrixValue(previousReal, row, col, re);
        float prevIm = matrixValue(previousImag, row, col, im);
        float diffRe = re - prevRe;
        float diffIm = im - prevIm;

        sumRe[tileRow][tileCol] += re;
        sumIm[tileRow][tileCol] += im;
        sumMagSq[tileRow][tileCol] += re * re + im * im;
        sumDelta[tileRow][tileCol] += sqrt(diffRe * diffRe + diffIm * diffIm);
        count[tileRow][tileCol] += 1.0;
        if (row == col) {
          diagCount[tileRow][tileCol] += 1.0;
        }
      }
    }

    for (int tileRow = 0; tileRow < targetRows; tileRow += 1) {
      for (int tileCol = 0; tileCol < targetCols; tileCol += 1) {
        float cellCount = max(1.0, count[tileRow][tileCol]);
        float avgRe = sumRe[tileRow][tileCol] / cellCount;
        float avgIm = sumIm[tileRow][tileCol] / cellCount;
        float magnitudeRms = sqrt(sumMagSq[tileRow][tileCol] / cellCount);
        float phaseAngle = magnitudeRms > MAG_EPS ? atan2(sumIm[tileRow][tileCol], sumRe[tileRow][tileCol]) : 0.0;
        float deltaAvg = sumDelta[tileRow][tileCol] / cellCount;
        float diagWeight = clampFloat(diagCount[tileRow][tileCol] / cellCount, 0.0, 1.0);

        int rowStart = floor(tileRow * sourceRows / float(max(1, targetRows)));
        int rowEnd = max(rowStart + 1, floor((tileRow + 1) * sourceRows / float(max(1, targetRows))));
        int colStart = floor(tileCol * sourceCols / float(max(1, targetCols)));
        int colEnd = max(colStart + 1, floor((tileCol + 1) * sourceCols / float(max(1, targetCols))));

        grid.tiles[tileRow][tileCol] = new LodTileSample(
          rowStart,
          min(sourceRows, rowEnd),
          colStart,
          min(sourceCols, colEnd),
          magnitudeRms,
          phaseAngle,
          deltaAvg,
          diagWeight
        );
        grid.real[tileRow][tileCol] = avgRe;
        grid.imag[tileRow][tileCol] = avgIm;
        grid.mag[tileRow][tileCol] = magnitudeRms;
        grid.phase[tileRow][tileCol] = phaseAngle;
        grid.delta[tileRow][tileCol] = deltaAvg;
        grid.diag[tileRow][tileCol] = diagWeight;
      }
    }

    grid.valid = true;
    return grid;
  }

  float matrixValue(float[][] matrix, int row, int col, float fallback) {
    if (matrix == null || row < 0 || col < 0 || row >= matrix.length) {
      return fallback;
    }
    if (matrix[row] == null || col >= matrix[row].length) {
      return fallback;
    }
    return matrix[row][col];
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

  ReducedDensitySample selectPreferredBlock(FrameSample sample) {
    if (sample == null) {
      return null;
    }
    return selectPreferredBlock(sample.reducedDensityBlocks);
  }

  ReducedDensitySample selectPreferredBlock(EvolutionSample sample) {
    if (sample == null) {
      return null;
    }
    return selectPreferredBlock(sample.reducedDensityBlocks);
  }

  ReducedDensitySample selectPreferredBlock(ArrayList<ReducedDensitySample> blocks) {
    if (blocks == null || blocks.isEmpty()) {
      return null;
    }

    ReducedDensitySample largestBlock = null;
    int largestSpan = -1;
    for (ReducedDensitySample block : blocks) {
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

    for (ReducedDensitySample block : blocks) {
      if (block != null && "0,1".equals(block.qubitKey)) {
        return block;
      }
    }
    for (ReducedDensitySample block : blocks) {
      if (block != null && "0".equals(block.qubitKey)) {
        return block;
      }
    }
    return blocks.get(0);
  }

  float computeGlobalRhoMagnitude(TraceModel traceModel) {
    if (traceModel == null || traceModel.steps == null || traceModel.steps.isEmpty()) {
      return 1.0;
    }

    float maxMagnitude = MIN_SCALE;
    for (TraceStep step : traceModel.steps) {
      if (step.evolutionSamples == null || step.evolutionSamples.isEmpty()) {
        continue;
      }
      for (EvolutionSample sample : step.evolutionSamples) {
        ReducedDensitySample block = selectPreferredBlock(sample);
        if (block == null || !isRectangular(block.real, block.imag)) {
          continue;
        }
        for (int row = 0; row < block.real.length; row += 1) {
          for (int col = 0; col < block.real[row].length; col += 1) {
            float re = block.real[row][col];
            float im = block.imag[row][col];
            maxMagnitude = max(maxMagnitude, sqrt(re * re + im * im));
          }
        }
      }
    }
    return max(maxMagnitude, MIN_SCALE);
  }

  void buildCircuitLensSpecs(TraceModel traceModel) {
    circuitLensSpecs.clear();
    circuitLensQubitCount = 1;
    circuitLensMaxQubitIndex = 0;

    if (traceModel == null || traceModel.steps == null || traceModel.steps.isEmpty()) {
      return;
    }

    int observedMaxQubit = -1;
    for (int stepIndex = 0; stepIndex < traceModel.steps.size(); stepIndex += 1) {
      TraceStep step = traceModel.steps.get(stepIndex);
      CircuitLensGateSpec spec = buildCircuitLensGateSpec(stepIndex, step);
      circuitLensSpecs.add(spec);
      observedMaxQubit = max(observedMaxQubit, maxQubitIndexOf(spec.qubits));
    }

    if (observedMaxQubit < 0) {
      observedMaxQubit = resolveFallbackQubitMax(traceModel);
    }
    if (observedMaxQubit < 0) {
      observedMaxQubit = 0;
    }

    circuitLensMaxQubitIndex = observedMaxQubit;
    circuitLensQubitCount = max(1, circuitLensMaxQubitIndex + 1);
  }

  CircuitLensGateSpec buildCircuitLensGateSpec(int stepIndex, TraceStep step) {
    EvolutionSample representative = resolveRepresentativeEvolutionSample(step);
    GateMatrixSample gateMatrix = representative != null ? representative.gateMatrix : null;

    String operationId = step != null && step.operationId != null ? step.operationId : "step_" + stepIndex;
    String operationName = step != null && step.operationName != null ? step.operationName : "";
    String rawGateName = "";
    if (gateMatrix != null && gateMatrix.gateName != null && gateMatrix.gateName.length() > 0) {
      rawGateName = gateMatrix.gateName;
    } else if (operationName.length() > 0) {
      rawGateName = operationName;
    } else if (step != null && step.gateLabel != null && step.gateLabel.length() > 0) {
      rawGateName = step.gateLabel;
    } else {
      rawGateName = operationId;
    }

    int[] matrixQubits = uniqueOrderedQubits(gateMatrix != null ? gateMatrix.qubits : null);
    int[] operationQubits = uniqueOrderedQubits(step != null ? step.operationQubits : null);
    int[] operationControls = uniqueOrderedQubits(step != null ? step.operationControls : null);
    int[] operationTargets = uniqueOrderedQubits(step != null ? step.operationTargets : null);
    int[] qubits = matrixQubits.length > 0
      ? matrixQubits
      : (operationQubits.length > 0 ? operationQubits : mergeQubitArrays(operationControls, operationTargets));
    String normalizedGateName = normalizeGateNameForLens(rawGateName);
    String gateToken = compactLensGateToken(rawGateName, operationId);

    int renderKind = CircuitLensRenderKind.IDLE_UNKNOWN;
    int[] controlQubits = new int[0];
    int[] targetQubits = new int[0];

    if (isMeasureGateName(normalizedGateName) || isResetGateName(normalizedGateName)) {
      renderKind = CircuitLensRenderKind.MEASURE;
      targetQubits = operationTargets.length > 0 ? operationTargets : qubits;
    } else if (qubits.length == 0) {
      renderKind = CircuitLensRenderKind.IDLE_UNKNOWN;
    } else if ("cswap".equals(normalizedGateName) || "fredkin".equals(normalizedGateName)) {
      if (qubits.length >= 3) {
        renderKind = CircuitLensRenderKind.SWAP;
        controlQubits = new int[] { qubits[0] };
        targetQubits = new int[] { qubits[1], qubits[2] };
      } else if (qubits.length >= 2) {
        renderKind = CircuitLensRenderKind.SWAP;
        targetQubits = new int[] { qubits[0], qubits[1] };
      } else {
        renderKind = CircuitLensRenderKind.SINGLE;
        targetQubits = qubits;
      }
    } else if ("swap".equals(normalizedGateName)) {
      if (qubits.length >= 2) {
        renderKind = CircuitLensRenderKind.SWAP;
        targetQubits = new int[] { qubits[0], qubits[1] };
      } else {
        renderKind = CircuitLensRenderKind.SINGLE;
        targetQubits = qubits;
      }
    } else if ("ccx".equals(normalizedGateName)) {
      if (qubits.length >= 3) {
        renderKind = CircuitLensRenderKind.CONTROL_TARGET;
        controlQubits = new int[] { qubits[0], qubits[1] };
        targetQubits = new int[] { qubits[qubits.length - 1] };
      } else {
        renderKind = CircuitLensRenderKind.GENERIC_MULTI;
        targetQubits = qubits;
      }
    } else if (isSingleControlPairGate(normalizedGateName)) {
      if (qubits.length >= 2) {
        renderKind = CircuitLensRenderKind.CONTROL_TARGET;
        controlQubits = new int[] { qubits[0] };
        targetQubits = new int[] { qubits[1] };
      } else {
        renderKind = CircuitLensRenderKind.GENERIC_MULTI;
        targetQubits = qubits;
      }
    } else if (qubits.length == 1) {
      renderKind = CircuitLensRenderKind.SINGLE;
      targetQubits = qubits;
    } else {
      renderKind = CircuitLensRenderKind.GENERIC_MULTI;
      targetQubits = qubits;
    }

    return new CircuitLensGateSpec(
      stepIndex,
      gateToken,
      rawGateName,
      operationId,
      qubits,
      controlQubits,
      targetQubits,
      renderKind
    );
  }

  EvolutionSample resolveRepresentativeEvolutionSample(TraceStep step) {
    if (step == null || step.evolutionSamples == null || step.evolutionSamples.isEmpty()) {
      return null;
    }
    for (EvolutionSample sample : step.evolutionSamples) {
      if (sample != null && sample.gateMatrix != null) {
        return sample;
      }
    }
    return step.evolutionSamples.get(0);
  }

  int resolveFallbackQubitMax(TraceModel traceModel) {
    if (traceModel == null || traceModel.steps == null) {
      return -1;
    }

    int bestSpan = -1;
    int bestMaxQubit = -1;
    for (TraceStep step : traceModel.steps) {
      if (step == null || step.evolutionSamples == null) {
        continue;
      }
      for (EvolutionSample sample : step.evolutionSamples) {
        if (sample == null || sample.reducedDensityBlocks == null) {
          continue;
        }
        for (ReducedDensitySample block : sample.reducedDensityBlocks) {
          if (block == null || block.qubits == null || block.qubits.length == 0) {
            continue;
          }
          int span = block.qubits.length;
          int maxQubit = maxQubitIndexOf(block.qubits);
          if (span > bestSpan) {
            bestSpan = span;
            bestMaxQubit = maxQubit;
          } else if (span == bestSpan) {
            bestMaxQubit = max(bestMaxQubit, maxQubit);
          }
        }
      }
    }
    return bestMaxQubit;
  }

  CircuitLensGateSpec circuitLensSpecAt(int stepIndex) {
    if (circuitLensSpecs == null || circuitLensSpecs.isEmpty()) {
      return null;
    }
    if (stepIndex >= 0 && stepIndex < circuitLensSpecs.size()) {
      return circuitLensSpecs.get(stepIndex);
    }
    int clamped = clampInt(stepIndex, 0, circuitLensSpecs.size() - 1);
    return circuitLensSpecs.get(clamped);
  }

  float circuitLensContentSpan(int stepCount, float pitch) {
    if (stepCount <= 1) {
      return 0.0;
    }
    return max(0.0, float(stepCount - 1) * pitch);
  }

  float circuitLensMaxOffset(float contentSpan, float laneWidth) {
    return max(0.0, contentSpan - laneWidth);
  }

  float circuitLensTargetOffset(int activeIndex, float pitch, float anchorX) {
    return activeIndex * pitch - anchorX;
  }

  float circuitLensScrollOffset(float targetOffset, float maxOffset) {
    return clampFloat(targetOffset, 0.0, maxOffset);
  }

  float circuitLensXForIndex(float laneLeft, float pitch, float scrollOffset, int index) {
    return laneLeft + index * pitch - scrollOffset;
  }

  boolean circuitLensColumnVisible(float x, float laneLeft, float laneRight, float cullMargin) {
    return x >= (laneLeft - cullMargin) && x <= (laneRight + cullMargin);
  }

  int[] mapQubitsToLensWires(int[] qubits, int qubitCount) {
    int[] normalized = uniqueOrderedQubits(qubits);
    if (normalized.length == 0) {
      return normalized;
    }

    ArrayList<Integer> mapped = new ArrayList<Integer>();
    int maxWire = max(0, qubitCount - 1);
    for (int qubit : normalized) {
      int wire = clampInt(qubit, 0, maxWire);
      boolean exists = false;
      for (int existing : mapped) {
        if (existing == wire) {
          exists = true;
          break;
        }
      }
      if (!exists) {
        mapped.add(wire);
      }
    }

    int[] values = new int[mapped.size()];
    for (int i = 0; i < mapped.size(); i += 1) {
      values[i] = mapped.get(i);
    }
    Arrays.sort(values);
    return values;
  }

  int[] mergeQubitArrays(int[] first, int[] second) {
    ArrayList<Integer> merged = new ArrayList<Integer>();
    int[][] sources = new int[][] { first, second };
    for (int[] source : sources) {
      if (source == null) {
        continue;
      }
      for (int qubit : source) {
        if (qubit < 0) {
          continue;
        }
        boolean exists = false;
        for (int existing : merged) {
          if (existing == qubit) {
            exists = true;
            break;
          }
        }
        if (!exists) {
          merged.add(qubit);
        }
      }
    }

    int[] values = new int[merged.size()];
    for (int i = 0; i < merged.size(); i += 1) {
      values[i] = merged.get(i);
    }
    return values;
  }

  int[] uniqueOrderedQubits(int[] qubits) {
    if (qubits == null || qubits.length == 0) {
      return new int[0];
    }

    ArrayList<Integer> values = new ArrayList<Integer>();
    for (int qubit : qubits) {
      if (qubit < 0) {
        continue;
      }
      boolean exists = false;
      for (int existing : values) {
        if (existing == qubit) {
          exists = true;
          break;
        }
      }
      if (!exists) {
        values.add(qubit);
      }
    }

    int[] ordered = new int[values.size()];
    for (int i = 0; i < values.size(); i += 1) {
      ordered[i] = values.get(i);
    }
    return ordered;
  }

  int maxQubitIndexOf(int[] qubits) {
    if (qubits == null || qubits.length == 0) {
      return -1;
    }
    int maxQubit = -1;
    for (int qubit : qubits) {
      maxQubit = max(maxQubit, qubit);
    }
    return maxQubit;
  }

  String compactLensGateToken(String rawGateName, String operationId) {
    String source = rawGateName != null && rawGateName.length() > 0
      ? rawGateName
      : operationId;
    if (source == null || source.length() == 0) {
      return "U";
    }
    String normalized = source.toUpperCase(Locale.US).replaceAll("[^A-Z0-9]+", " ").trim();
    if (normalized.length() == 0) {
      return "U";
    }
    String[] parts = normalized.split("\\s+");
    String token = parts.length > 0 ? parts[0] : normalized;
    if (token.length() > 4) {
      token = token.substring(0, 4);
    }
    return token.length() > 0 ? token : "U";
  }

  String normalizeGateNameForLens(String value) {
    if (value == null) {
      return "";
    }
    String normalized = value.toLowerCase(Locale.US);
    normalized = normalized.replaceAll("[^a-z0-9]+", "");
    return normalized;
  }

  boolean isMeasureGateName(String name) {
    return "measure".equals(name) || "m".equals(name);
  }

  boolean isResetGateName(String name) {
    return "reset".equals(name);
  }

  boolean isSingleControlPairGate(String name) {
    if (name == null || name.length() == 0) {
      return false;
    }
    if ("cx".equals(name)
      || "cy".equals(name)
      || "cz".equals(name)
      || "ch".equals(name)
      || "cp".equals(name)
      || "crx".equals(name)
      || "cry".equals(name)
      || "crz".equals(name)
      || "cnot".equals(name)) {
      return true;
    }
    return name.startsWith("cu");
  }

  String gateCaption(PlaybackState playback) {
    if (playback == null || playback.step == null) {
      return "Gate: unavailable";
    }
    GateMatrixSample gate = playback.sample != null ? playback.sample.gateMatrix : null;
    if (gate != null && gate.gateName != null && gate.gateName.length() > 0) {
      return "Gate: " + gate.gateName.toUpperCase(Locale.US) + " on " + qubitLabel(gate.qubits);
    }
    if (playback.step.operationId != null && playback.step.operationId.length() > 0) {
      return "Gate: " + playback.step.operationId;
    }
    return "Gate: " + playback.step.gateLabel;
  }

  String circuitLensLabel(PlaybackState playback) {
    if (playback == null || playback.step == null) {
      return "Circuit: unavailable";
    }
    CircuitLensGateSpec spec = circuitLensSpecAt(playback.stepIndex);
    if (spec != null) {
      String label = spec.rawGateName != null && spec.rawGateName.length() > 0
        ? spec.rawGateName
        : spec.operationId;
      String suffix = spec.qubits != null && spec.qubits.length > 0 ? " " + qubitLabel(spec.qubits) : "";
      return "Circuit: " + label + suffix;
    }
    String label = playback.step.gateLabel != null && playback.step.gateLabel.length() > 0
      ? playback.step.gateLabel
      : playback.step.operationId;
    return "Circuit: " + label;
  }

  String stageSummary(PlaybackState playback) {
    String phase = playback != null ? playback.phase : "";
    if (playback != null && playback.stepIndex == 0 && "pre_gate".equals(phase)) {
      return "Init-only view: rho0 = |0...0><0...0|; gate layer appears at apply_gate.";
    }
    if ("pre_gate".equals(phase)) {
      return "Preview: active layer at gate-start boundary over fixed |0...0><0...0| base.";
    }
    if ("apply_gate".equals(phase)) {
      if (hudDecompositionActive) {
        return "Apply: active layer follows physical substep samples; decomp rays show K(t)rho_startK(t)^dagger flow.";
      }
      return "Apply: active layer follows physical substep samples; base and history stay frozen.";
    }
    if ("measurement_reveal".equals(phase)) {
      return "";
    }
    if ("shot_camera_pullback".equals(phase)) {
      return "Replay prep: camera pullback runs while density holds collapsed measured state and qubit cubes stay hidden.";
    }
    if ("shot_histogram_project".equals(phase)) {
      if (playback != null && playback.shotIndex < 0) {
        return "Projection prep: camera transitions from stacked qubit focus to histogram focus while density holds the final stacked measured shot state.";
      }
      if (hudShotResponsibleSourceLabel != null && hudShotResponsibleSourceLabel.length() > 0) {
        return "Projection: stacked shot layers project in chronological order while density shows this shot's measured state; source "
          + hudShotResponsibleSourceLabel + " stays highlighted.";
      }
      return "Projection: stacked shot layers project in chronological order while density shows this shot's measured state.";
    }
    if ("shot_stack".equals(phase)) {
      if (playback != null && playback.shotBeat != null && playback.shotBeat.length() > 0) {
        String summary = "Shot stack: " + playback.shotBeat + " ("
          + nf(clampFloat(playback.shotBeatProgress, 0.0, 1.0), 1, 2)
          + "); density shows this shot's measured outcome state; active cube originates from the per-shot responsible source cell.";
        if (hudShotResponsibleSourceLabel != null && hudShotResponsibleSourceLabel.length() > 0) {
          summary += " source " + hudShotResponsibleSourceLabel + ".";
        }
        if (hudShotActiveContributorQubit >= 0 && hudShotActiveContributorCount >= 0) {
          summary += " q" + hudShotActiveContributorQubit + " sources: " + hudShotActiveContributorCount + ".";
        }
        return summary;
      }
      return "Shot stack: each shot interval shows that shot's measured outcome density state.";
    }
    return "Settle: active layer converges to gate-end checkpoint; base/history remain fixed.";
  }

  String qubitLabel(int[] qubits) {
    if (qubits == null || qubits.length == 0) {
      return "[]";
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
}
