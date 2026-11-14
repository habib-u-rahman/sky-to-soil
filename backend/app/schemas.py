"""
Pydantic models for every Sky-to-Soil API request/response.

This file IS the source of truth for the JSON contract described in
docs/api_contract.md. If you change a field here, update that doc and the
matching sample in docs/samples/ in the same commit.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Common / shared
# ---------------------------------------------------------------------------

class DataStatus(str, Enum):
    ok = "ok"
    partial = "partial"
    unavailable = "unavailable"
    manual_input_needed = "manual_input_needed"
    error = "error"


class SourceMeta(BaseModel):
    source: str = Field(..., description="Human-readable name of the upstream data source")
    status: DataStatus
    message: Optional[str] = Field(None, description="Explanation when status is not 'ok'")
    cache_hit: bool = False
    fetched_at: Optional[str] = Field(None, description="ISO8601 UTC timestamp this data was fetched/generated")


class Location(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)

    @field_validator("lat", "lon")
    @classmethod
    def _round(cls, v: float) -> float:
        return round(v, 4)


class SeasonWindow(BaseModel):
    """A configurable growing season, e.g. kharif = May-Oct."""
    name: str
    start_month: int = Field(..., ge=1, le=12)
    end_month: int = Field(..., ge=1, le=12)


class SeasonConfig(BaseModel):
    kharif: SeasonWindow = SeasonWindow(name="kharif", start_month=5, end_month=10)
    rabi: SeasonWindow = SeasonWindow(name="rabi", start_month=11, end_month=4)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "sky-to-soil-backend"
    version: str
    time: str


# ---------------------------------------------------------------------------
# /climate — climate shift analysis
# ---------------------------------------------------------------------------

class SeasonalRainfall(BaseModel):
    kharif_mm: Optional[float] = None
    rabi_mm: Optional[float] = None


class SeasonalHotDays(BaseModel):
    kharif: Optional[float] = None
    rabi: Optional[float] = None


class PeriodClimateStats(BaseModel):
    period_label: str
    start_year: int
    end_year: int
    n_years: int
    mean_tmax_c: Optional[float] = None
    mean_tmin_c: Optional[float] = None
    hot_days_gt35_by_season: SeasonalHotDays = SeasonalHotDays()
    hot_days_gt40_by_season: SeasonalHotDays = SeasonalHotDays()
    seasonal_rainfall_mm: SeasonalRainfall = SeasonalRainfall()
    mean_root_zone_wetness: Optional[float] = Field(
        None, description="NASA POWER GWETROOT, 0-1 fraction of saturation"
    )


class TrendResult(BaseModel):
    variable: str
    mk_trend: str = Field(..., description="'increasing' | 'decreasing' | 'no trend'")
    mk_p_value: Optional[float] = None
    sen_slope_per_year: Optional[float] = None
    significant_at_0_10: bool = False


class ClimateShiftResponse(BaseModel):
    location: Location
    baseline: PeriodClimateStats
    recent: PeriodClimateStats
    deltas: dict = Field(
        default_factory=dict,
        description="recent-minus-baseline deltas for mean_tmax_c, mean_tmin_c, "
        "seasonal_rainfall_mm.kharif_mm/rabi_mm, mean_root_zone_wetness",
    )
    trends: list[TrendResult] = Field(default_factory=list)
    seasons_used: SeasonConfig = SeasonConfig()
    source: SourceMeta


# ---------------------------------------------------------------------------
# /soil
# ---------------------------------------------------------------------------

class SoilDepthLayer(BaseModel):
    depth: str = Field(..., description="'0-5cm' | '5-15cm' | '15-30cm'")
    phh2o: Optional[float] = Field(None, description="pH in H2O")
    clay_pct: Optional[float] = None
    sand_pct: Optional[float] = None
    silt_pct: Optional[float] = None
    soc_g_kg: Optional[float] = Field(None, description="soil organic carbon, g/kg")
    nitrogen_g_kg: Optional[float] = None
    cec_cmol_kg: Optional[float] = Field(None, description="cation exchange capacity, cmol(c)/kg")


class SoilProfileResponse(BaseModel):
    location: Location
    layers: list[SoilDepthLayer] = Field(default_factory=list)
    status: DataStatus
    message: Optional[str] = None
    source: SourceMeta


# ---------------------------------------------------------------------------
# /ndvi
# ---------------------------------------------------------------------------

class NdviPoint(BaseModel):
    modis_date: str = Field(..., description="e.g. 'A2023017'")
    calendar_date: str = Field(..., description="ISO date, e.g. '2023-01-17'")
    ndvi: Optional[float] = Field(None, description="Scaled NDVI, -0.2 to 1.0 range")
    quality_code: Optional[int] = Field(None, description="raw 250m_16_days_pixel_reliability code")
    quality_label: Optional[str] = None
    usable: bool = Field(..., description="True if quality_code in {0, 1} (good/marginal)")


class NdviSummaryResponse(BaseModel):
    location: Location
    period_start: str
    period_end: str
    points: list[NdviPoint] = Field(default_factory=list)
    mean_ndvi_good_quality: Optional[float] = None
    pct_usable: Optional[float] = None
    status: DataStatus
    message: Optional[str] = None
    source: SourceMeta


# ---------------------------------------------------------------------------
# /crops
# ---------------------------------------------------------------------------

class KcStage(BaseModel):
    stage: str = Field(..., description="'initial' | 'development' | 'mid' | 'late'")
    length_days: int
    kc: float


class SourceCitation(BaseModel):
    text: str
    verify: bool = Field(False, description="True if this value needs field/expert verification")


class CropProfile(BaseModel):
    id: str
    name: str
    family: str
    n_fixing: bool
    season: str = Field(..., description="'kharif' | 'rabi' | 'either'")
    sowing_window: str
    duration_days: int
    kc_stages: list[KcStage]
    critical_temp_c: float = Field(..., description="Temp above which heat-sensitive stage is damaged")
    heat_sensitive_stage: str
    ph_min: float
    ph_max: float
    texture_preference: list[str]
    residue_contribution: str = Field(..., description="'low' | 'medium' | 'high'")
    rooting_depth_m: float
    sources: dict[str, SourceCitation] = Field(
        default_factory=dict, description="field name -> citation, one entry per sourced value"
    )


class CropsListResponse(BaseModel):
    crops: list[CropProfile]
    count: int


# ---------------------------------------------------------------------------
# /rotations/score and /rotations/stress-test
# ---------------------------------------------------------------------------

class Priorities(BaseModel):
    save_water: float = Field(0.25, ge=0, le=1)
    build_soil: float = Field(0.25, ge=0, le=1)
    lower_climate_risk: float = Field(0.25, ge=0, le=1)
    stay_close_to_current: float = Field(0.25, ge=0, le=1)
    income_proxy: Optional[float] = Field(None, ge=0, le=1)


class RotationScoreRequest(BaseModel):
    location: Location
    current_crops: list[str] = Field(default_factory=list, description="crop ids currently grown")
    priorities: Priorities = Priorities()
    season_config: Optional[SeasonConfig] = None
    top_n: int = Field(10, ge=1, le=50)


SEASON_SLOTS = ["Y1_kharif", "Y1_rabi", "Y2_kharif", "Y2_rabi"]


class RotationPlan(BaseModel):
    Y1_kharif: Optional[str] = Field(None, description="crop id, or null for fallow/cover crop")
    Y1_rabi: Optional[str] = None
    Y2_kharif: Optional[str] = None
    Y2_rabi: Optional[str] = None


class RotationSubScores(BaseModel):
    water_fit: float
    heat_risk: float
    soil_health: float
    soil_suitability: float


class ScoredRotation(BaseModel):
    rotation: RotationPlan
    sub_scores: RotationSubScores
    base_score_0_100: float = Field(..., description="unweighted average of sub-scores")
    priority_weighted_score_0_100: float
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RotationsScoreResponse(BaseModel):
    location: Location
    priorities: Priorities
    candidates_evaluated: int
    top: list[ScoredRotation]
    pareto_optimal: list[ScoredRotation]
    source: SourceMeta


class StressScenario(BaseModel):
    delta_temp_c: float = 1.5
    rainfall_change_pct: float = -15.0


class StressTestRequest(BaseModel):
    location: Location
    current_crops: list[str] = Field(default_factory=list)
    priorities: Priorities = Priorities()
    scenario: StressScenario = StressScenario()
    top_n: int = Field(10, ge=1, le=50)


class StressedRotationResult(BaseModel):
    rotation: RotationPlan
    baseline_score_0_100: float
    stressed_score_0_100: float
    score_drop: float
    resilience_score_0_100: float = Field(
        ..., description="100 = no degradation under stress scenario, 0 = total collapse"
    )
    reasons: list[str] = Field(default_factory=list)


class RotationsStressTestResponse(BaseModel):
    location: Location
    scenario: StressScenario
    results: list[StressedRotationResult]
    source: SourceMeta


# ---------------------------------------------------------------------------
# /farm/analyze — the one-call combined endpoint
# ---------------------------------------------------------------------------

class FarmAnalyzeRequest(BaseModel):
    location: Location
    current_crops: list[str] = Field(default_factory=list)
    priorities: Priorities = Priorities()
    season_config: Optional[SeasonConfig] = None
    include_stress_test: bool = True
    top_n: int = Field(10, ge=1, le=50)


class FarmAnalyzeResponse(BaseModel):
    location: Location
    generated_at: str
    climate: Optional[ClimateShiftResponse] = None
    soil: Optional[SoilProfileResponse] = None
    ndvi: Optional[NdviSummaryResponse] = None
    rotations: Optional[RotationsScoreResponse] = None
    stress_test: Optional[RotationsStressTestResponse] = None
    warnings: list[str] = Field(
        default_factory=list, description="Non-fatal issues, e.g. a data source being unavailable"
    )


class ErrorResponse(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# /advisor/explain and /advisor/chat -- AI Agronomist
# ---------------------------------------------------------------------------

AdvisorLanguage = Literal["en", "ur"]


class AdvisorExplainRequest(BaseModel):
    analysis: Optional[FarmAnalyzeResponse] = Field(
        None, description="A FarmAnalyzeResponse payload (as returned by POST /farm/analyze). Required unless demo=true."
    )
    rotation_id: str = Field(..., description="Which rotation to explain, e.g. 'top_0', 'top_1', 'pareto_0'")
    current_crops: list[str] = Field(default_factory=list, description="Crop ids the farmer currently grows")
    language: AdvisorLanguage = "en"


class AdvisorExplainResponse(BaseModel):
    text: str = Field(..., description="Farmer-friendly explanation in the requested language")
    technical_note: str = Field(..., description="Short technical note for extension officers, always in English")
    language: AdvisorLanguage
    verified: bool
    issues: list[str] = Field(default_factory=list)
    rewrites_used: int = 0
    facts_used: dict = Field(default_factory=dict, description="The compact facts object the AI was restricted to")
    kb_sources: list[str] = Field(default_factory=list, description="Knowledge-base source labels cited, for UI citations")
    model_used: str = Field(..., description="Groq model id that produced this text, or 'fallback_template'")


class AdvisorChatRequest(BaseModel):
    analysis: Optional[FarmAnalyzeResponse] = Field(
        None, description="A FarmAnalyzeResponse payload (as returned by POST /farm/analyze). Required unless demo=true."
    )
    rotation_id: Optional[str] = Field(
        None, description="Which rotation to ground the chat in, e.g. 'top_0'. Defaults to 'top_0' if omitted."
    )
    current_crops: list[str] = Field(default_factory=list)
    question: str = Field(..., min_length=1)
    language: AdvisorLanguage = "en"


class AdvisorChatResponse(BaseModel):
    answer: str
    language: AdvisorLanguage
    verified: bool
    issues: list[str] = Field(default_factory=list)
    answerable: bool = Field(..., description="False if the question could not be honestly answered from facts+KB")
    rewrites_used: int = 0
    facts_used: dict = Field(default_factory=dict)
    kb_sources: list[str] = Field(default_factory=list)
    model_used: str


# ---------------------------------------------------------------------------
# /soil/presets
# ---------------------------------------------------------------------------

class SoilPreset(BaseModel):
    texture: str = Field(..., description="'sand' | 'sandy_loam' | 'loam' | 'silt_loam' | 'clay_loam' | 'clay'")
    phh2o: float
    clay_pct: float
    sand_pct: float
    silt_pct: float
    soc_g_kg: float
    nitrogen_g_kg: float
    cec_cmol_kg: float


class SoilPresetsResponse(BaseModel):
    presets: list[SoilPreset]
    source: SourceMeta


# ---------------------------------------------------------------------------
# /report/pdf
# ---------------------------------------------------------------------------

class ReportPdfRequest(BaseModel):
    analysis: Optional[FarmAnalyzeResponse] = Field(
        None, description="A FarmAnalyzeResponse payload. Required unless demo=true."
    )
    current_crops: list[str] = Field(default_factory=list)
    language: AdvisorLanguage = "en"
    top_n: int = Field(3, ge=1, le=5, description="How many top rotations to include in the plan")
