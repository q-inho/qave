"""Contract and API models for Backend A."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Scalar = str | int | float | bool
AlgorithmId = Literal[
    "bell",
    "ghz",
    "qft",
    "teleportation",
    "grover",
    "vqe",
    "custom",
]
SourceFormat = Literal["openqasm", "qiskit_qasm", "qiskit_json", "cirq_json"]


class ContractModel(BaseModel):
    """Strict model base for external contracts."""

    model_config = ConfigDict(extra="forbid")


class ClassicalMapEntry(ContractModel):
    """Represent Classical Map Entry."""

    qubit: int
    classical_bit: int
    register_name: str | None = Field(default=None, alias="register")


class GateOp(ContractModel):
    """Represent Gate Op."""

    id: str
    kind: Literal["unitary", "measurement", "reset"]
    name: str
    targets: list[int]
    controls: list[int] = Field(default_factory=list)
    classical_targets: list[int] | None = None
    params: list[float] = Field(default_factory=list)
    time_index: int
    metadata: dict[str, Scalar] = Field(default_factory=dict)


class QuantumCircuitIR(ContractModel):
    """Represent Quantum Circuit I R."""

    contract_version: str
    circuit_id: str
    source_format: SourceFormat
    source_metadata: dict[str, Scalar] = Field(default_factory=dict)
    qubits: int
    classical_bits: int
    steps: list[GateOp]
    moments_or_steps_mode: Literal["moments", "single_gate_steps"]
    classical_map: list[ClassicalMapEntry] = Field(default_factory=list)
    parameters: dict[str, Scalar] = Field(default_factory=dict)
    metadata: dict[str, Scalar] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_step_indices(self) -> QuantumCircuitIR:
        """Validate step indices."""
        previous = -1
        for step in self.steps:
            if step.time_index < previous:
                msg = "GateOp.time_index must be monotonic non-decreasing"
                raise ValueError(msg)
            previous = step.time_index
        return self


class StateSummary(ContractModel):
    """Represent State Summary."""

    norm: float
    entropy: float | None = None


class AmplitudeComplex(ContractModel):
    """Represent Amplitude Complex."""

    basis: str
    re: float
    im: float


class BasisProbability(ContractModel):
    """Represent Basis Probability."""

    basis: str
    p: float


class MeasurementStepInfo(ContractModel):
    """Represent Measurement Step Info."""

    is_measurement: bool
    outcome_labels: list[str] | None = None


class PhaseWindow(ContractModel):
    """Represent Phase Window."""

    phase: Literal["pre_gate", "apply_gate", "settle"]
    t_start: float
    t_end: float


class BoundaryCheckpoint(ContractModel):
    """Represent Boundary Checkpoint."""

    gate_start_hash: str
    gate_end_hash: str


class TransitionHints(ContractModel):
    """Represent Transition Hints."""

    interpolation: Literal["linear", "ease_in_out"]
    emphasis_targets: list[str] | None = None


class TraceStep(ContractModel):
    """Represent Trace Step."""

    step_index: int
    operation_id: str
    operation_name: str | None = None
    operation_qubits: list[int] | None = None
    operation_controls: list[int] | None = None
    operation_targets: list[int] | None = None
    state_summary: StateSummary
    amplitudes: list[AmplitudeComplex] | None = None
    probabilities: list[BasisProbability]
    measurement: MeasurementStepInfo | None = None
    phase_windows: list[PhaseWindow]
    boundary_checkpoint: BoundaryCheckpoint
    transition_hints: TransitionHints | None = None
    evolution_samples: list[StepEvolutionSample] = Field(default_factory=list)


class TraceAnnotation(ContractModel):
    """Represent Trace Annotation."""

    kind: str
    message: str


class MeasurementOutcome(ContractModel):
    """Represent Measurement Outcome."""

    label: str
    probability: float


class MeasurementModel(ContractModel):
    """Represent Measurement Model."""

    mode: Literal["collapse"]
    outcomes: list[MeasurementOutcome]
    selected_outcome: str


class BlochVector(ContractModel):
    """Represent Bloch Vector."""

    qubit: int
    x: float
    y: float
    z: float


class PurityEntropy(ContractModel):
    """Represent Purity Entropy."""

    qubit: int
    purity: float
    entropy: float


class TopKAmplitude(ContractModel):
    """Represent Top K Amplitude."""

    basis: str
    magnitude: float
    phase: float


class ReducedDensityBlock(ContractModel):
    """Represent Reduced Density Block."""

    qubits: list[int]
    real: list[list[float]]
    imag: list[list[float]]


class MutualInformationEdge(ContractModel):
    """Represent Mutual Information Edge."""

    i: int
    j: int
    value: float


class BipartitionEntropy(ContractModel):
    """Represent Bipartition Entropy."""

    left: list[int]
    right: list[int]
    value: float


class EntanglementMetrics(ContractModel):
    """Represent Entanglement Metrics."""

    mutual_information_edges: list[MutualInformationEdge] | None = None
    bipartition_entropy: list[BipartitionEntropy] | None = None


class MeasurementHistogramEntry(ContractModel):
    """Represent Measurement Histogram Entry."""

    outcome: str
    probability: float
    samples: int | None = None


class GateMatrixSample(ContractModel):
    """Represent Gate Matrix Sample."""

    gate_name: str
    qubits: list[int]
    real: list[list[float]]
    imag: list[list[float]]


class StepEvolutionSample(ContractModel):
    """Represent Step Evolution Sample."""

    sample_index: int
    phase: Literal["pre_gate", "apply_gate", "settle"]
    t_normalized: float
    state_hash: str
    top_k_amplitudes: list[TopKAmplitude]
    reduced_density_blocks: list[ReducedDensityBlock]
    measurement_histogram: list[MeasurementHistogramEntry]
    gate_matrix: GateMatrixSample | None = None


class MeasurementShotReplayTimeline(ContractModel):
    """Represent Measurement Shot Replay Timeline."""

    camera_pullback_frames: int
    histogram_project_frames: int
    frames_per_shot: int


class MeasurementShotReplayOutcome(ContractModel):
    """Represent Measurement Shot Replay Outcome."""

    label: str
    probability: float
    state_hash: str | None = None


class MeasurementShotReplayState(ContractModel):
    """Represent Measurement Shot Replay State."""

    label: str
    state_hash: str
    top_k_amplitudes: list[TopKAmplitude]
    reduced_density_blocks: list[ReducedDensityBlock]


class MeasurementShotReplayEvent(ContractModel):
    """Represent Measurement Shot Replay Event."""

    shot_index: int
    outcome_label: str
    state_hash: str


class MeasurementShotReplay(ContractModel):
    """Represent Measurement Shot Replay."""

    source_step_index: int
    measured_qubits: list[int]
    measured_classical_targets: list[int]
    shots_total: int
    sampling_seed: int
    outcomes: list[MeasurementShotReplayOutcome]
    outcome_states: list[MeasurementShotReplayState]
    shot_events: list[MeasurementShotReplayEvent]
    timeline: MeasurementShotReplayTimeline


class ObservableSnapshot(ContractModel):
    """Represent Observable Snapshot."""

    snapshot_id: str
    step_index: int
    bloch_vectors: list[BlochVector]
    purity_entropy: list[PurityEntropy]
    top_k_amplitudes: list[TopKAmplitude]
    reduced_density_blocks: list[ReducedDensityBlock]
    entanglement_metrics: EntanglementMetrics
    measurement_histogram: list[MeasurementHistogramEntry]


class ApproximationPolicy(ContractModel):
    """Represent Approximation Policy."""

    allow_approx_backends: bool
    fallback_backend_order: list[str]


class ScalabilityPolicy(ContractModel):
    """Represent Scalability Policy."""

    small_n_max: int
    medium_n_max: int
    small_mode_features: list[str]
    medium_mode_features: list[str]
    large_mode_features: list[str]
    approximation_policy: ApproximationPolicy


class BackendCapability(ContractModel):
    """Represent Backend Capability."""

    backend_id: str
    supports_pure_state: bool
    supports_mixed_state: bool
    supports_noise: bool
    supports_approximation: bool
    max_recommended_qubits: int


class SceneNode(ContractModel):
    """Represent Scene Node."""

    node_id: str
    label: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class SceneEdge(ContractModel):
    """Represent Scene Edge."""

    edge_id: str
    source: str
    target: str
    data: dict[str, Any] = Field(default_factory=dict)


class TimingSpec(ContractModel):
    """Represent Timing Spec."""

    duration_ms: int
    keyframes: list[int]


class CameraSpec(ContractModel):
    """Represent Camera Spec."""

    x: float
    y: float
    z: float
    zoom: float


class TimelineBinding(ContractModel):
    """Represent Timeline Binding."""

    source: Literal["AlgorithmTrace.timeline"]
    sync_group: str


class PlaybackControls(ContractModel):
    """Represent Playback Controls."""

    play_pause: bool
    step: bool
    speed: bool
    scrub: bool
    loop_range: bool


class FramePolicy(ContractModel):
    """Represent Frame Policy."""

    deterministic: bool
    drop_frame_strategy: Literal["interpolate_preserve_time", "hold_last"]


class VisualizationSceneSpec(ContractModel):
    """Represent Visualization Scene Spec."""

    contract_version: str
    scene_id: str
    nodes: list[SceneNode]
    edges: list[SceneEdge]
    layers: list[str]
    timing: TimingSpec
    camera: CameraSpec
    layout_hints: dict[str, Scalar] = Field(default_factory=dict)
    timeline_binding: TimelineBinding
    playback_controls: PlaybackControls
    frame_policy: FramePolicy


class AnimationKeyframe(ContractModel):
    """Represent Animation Keyframe."""

    frame_id: str
    step_index: int
    phase: Literal["pre_gate", "apply_gate", "settle"]
    t_normalized: float


class AnimationPhaseRatio(ContractModel):
    """Represent Animation Phase Ratio."""

    pre_gate: float
    apply_gate: float
    settle: float


class AnimationTimelineSpec(ContractModel):
    """Represent Animation Timeline Spec."""

    contract_version: str
    timeline_id: str
    total_steps: int
    default_step_duration_ms: int
    phase_ratio: AnimationPhaseRatio
    keyframes: list[AnimationKeyframe]
    sync_fence_ids: list[str]


class AlgorithmTrace(ContractModel):
    """Represent Algorithm Trace."""

    contract_version: str
    algorithm_id: AlgorithmId
    steps: list[TraceStep]
    annotations: list[TraceAnnotation] = Field(default_factory=list)
    measurement_model: MeasurementModel
    observable_snapshots: list[ObservableSnapshot]
    scalability_policy: ScalabilityPolicy
    timeline: AnimationTimelineSpec
    view_sync_groups: list[str]
    measurement_shot_replay: MeasurementShotReplay | None = None


class SimulationRequest(ContractModel):
    """Represent Simulation Request."""

    contract_version: str
    request_id: str
    algorithm_id: AlgorithmId
    params: dict[str, Scalar] = Field(default_factory=dict)
    mode: Literal["preview", "validation"]
    seed: int
    precision_profile: Literal["fast", "balanced", "strict"]
    measurement_mode: Literal["collapse"]
    backend_preference: str | None = None
    animation_profile: Literal["teaching_default", "analysis_slow", "presentation_fast"]
    target_timeline_step_ms: int | None = None
    scalability_override: Literal["auto", "small", "medium", "large"] | None = None
    shot_count: int | None = Field(default=None, ge=1)


class Diagnostic(ContractModel):
    """Represent Diagnostic."""

    code: str
    message: str


class ConvergenceInfo(ContractModel):
    """Represent Convergence Info."""

    iterations: int | None = None
    final_delta: float | None = None
    converged: bool | None = None


class StateCheckpoint(ContractModel):
    """Represent State Checkpoint."""

    step_index: int
    state_hash: str


class SimulationResult(ContractModel):
    """Represent Simulation Result."""

    contract_version: str
    request_id: str
    status: Literal["ok", "error"]
    outputs: dict[str, Any] = Field(default_factory=dict)
    observables: list[ObservableSnapshot]
    measurement_model: MeasurementModel
    backend_capability: BackendCapability
    convergence: ConvergenceInfo = Field(default_factory=ConvergenceInfo)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    state_checkpoints: list[StateCheckpoint]


class ValidationCheck(ContractModel):
    """Represent Validation Check."""

    name: str
    tolerance: float
    measured: float
    pass_: bool = Field(alias="pass")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ConventionCheck(ContractModel):
    """Represent Convention Check."""

    name: Literal["global_phase_invariance", "basis_ordering_consistency"]
    pass_: bool = Field(alias="pass")
    details: str | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ValidationReport(ContractModel):
    """Represent Validation Report."""

    contract_version: str
    request_id: str
    checks: list[ValidationCheck]
    overall_pass: bool
    evidence_refs: list[str] = Field(default_factory=list)
    convention_checks: list[ConventionCheck]
