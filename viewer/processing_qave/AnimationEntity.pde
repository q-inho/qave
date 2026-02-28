/*
Purpose: Define reusable animation entity primitives for pane choreography.
Inputs: Shared playback state, trace-derived models, pane metrics, and user interaction state.
Outputs: Deterministic frame-local rendering updates and synchronized visual state transitions.
Determinism/Timing: Uses timeline phases (pre_gate/apply_gate/settle) and fixed frame progression for reproducible output.
*/

class AnimationEntity {
  PVector curPos;
  PVector trgPos;
  PVector velPos;

  PVector curSize;
  PVector trgSize;
  PVector velSize;

  PVector curValue;
  PVector trgValue;

  float speed;
  float stiffness;
  float drag;
  float valueLerp;

  AnimationEntity(PVector pos, PVector size, PVector value, float speed, float stiffness, float drag, float valueLerp) {
    curPos = pos.copy();
    trgPos = pos.copy();
    velPos = new PVector();

    curSize = size.copy();
    trgSize = size.copy();
    velSize = new PVector();

    curValue = value.copy();
    trgValue = value.copy();

    this.speed = speed;
    this.stiffness = stiffness;
    this.drag = drag;
    this.valueLerp = valueLerp;
  }

  void setTarget(PVector pos, PVector size, PVector value) {
    if (pos != null) {
      trgPos.set(pos);
    }
    if (size != null) {
      trgSize.set(size);
    }
    if (value != null) {
      trgValue.set(value);
    }
  }

  void update() {
    curPos.add(PVector.sub(trgPos, curPos).mult(speed));

    velSize.add(PVector.sub(trgSize, curSize).mult(stiffness));
    velSize.mult(drag);
    velSize.x = constrain(velSize.x, -120, 120);
    velSize.y = constrain(velSize.y, -120, 120);
    velSize.z = constrain(velSize.z, -120, 120);
    curSize.add(velSize);

    curValue.add(PVector.sub(trgValue, curValue).mult(valueLerp));

    if (!isFiniteVector(curPos)) {
      curPos.set(trgPos);
    }
    if (!isFiniteVector(curSize)) {
      curSize.set(trgSize);
      velSize.set(0, 0, 0);
    }
    if (!isFiniteVector(curValue)) {
      curValue.set(trgValue);
    }

    clampVector(curPos, -20000, 20000);
    clampVector(trgPos, -20000, 20000);
    clampVector(curSize, 0.05, 512);
    clampVector(trgSize, 0.05, 512);
    clampVector(curValue, -10000, 10000);
    clampVector(trgValue, -10000, 10000);
  }

  boolean isFiniteVector(PVector vector) {
    return !Float.isNaN(vector.x)
      && !Float.isNaN(vector.y)
      && !Float.isNaN(vector.z)
      && !Float.isInfinite(vector.x)
      && !Float.isInfinite(vector.y)
      && !Float.isInfinite(vector.z);
  }

  void clampVector(PVector vector, float minValue, float maxValue) {
    vector.x = constrain(vector.x, minValue, maxValue);
    vector.y = constrain(vector.y, minValue, maxValue);
    vector.z = constrain(vector.z, minValue, maxValue);
  }
}
