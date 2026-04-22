import shutil
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urljoin
from uuid import uuid4

import aerosandbox as asb
import matplotlib
import numpy as np
from fastapi import APIRouter, File, Query, Response, UploadFile, HTTPException, status, Request, Body, Depends
from pydantic import BaseModel, Field, PositiveFloat, model_validator

from app.core.exceptions import (
    ServiceException,
    NotFoundError,
    ValidationError,
    ValidationDomainError,
    ConflictError,
    InternalError,
)
from app.settings import Settings, get_settings

matplotlib.use("Agg")
import matplotlib.pyplot as plt

router = APIRouter()

AIRFOILS_DIR = Path("components") / "airfoils"


class AirfoilKnownResponse(BaseModel):
    airfoil_name: str
    file_name: str
    known: bool
    relative_path: str | None = None


class AirfoilUploadResponse(BaseModel):
    airfoil_name: str
    file_name: str
    relative_path: str
    size_bytes: int
    overwritten: bool


class AirfoilListEntryResponse(BaseModel):
    airfoil_name: str
    file_name: str
    relative_path: str
    size_bytes: int


class AirfoilListResponse(BaseModel):
    count: int
    airfoils: list[AirfoilListEntryResponse]


class AirfoilDatDownloadResponse(BaseModel):
    airfoil_name: str
    file_name: str
    relative_path: str
    url: str
    mime_type: str
    size_bytes: int


class AirfoilGeometryStatsResponse(BaseModel):
    airfoil_name: str = Field(..., description="Name of the airfoil (without .dat extension).")
    max_thickness_pct: float = Field(
        ..., description="Maximum thickness as percentage of chord (upper_y - lower_y)."
    )
    max_thickness_x: float = Field(
        ..., description="Chordwise position of maximum thickness (0..1)."
    )
    max_camber_pct: float = Field(
        ..., description="Maximum camber-line deviation as percentage of chord."
    )
    max_camber_x: float = Field(
        ..., description="Chordwise position of maximum camber (0..1)."
    )


class AirfoilNeuralFoilRequest(BaseModel):
    reynolds_numbers: list[PositiveFloat] = Field(
        default_factory=lambda: [10000.0, 30000, 50000.0, 100000.0, 200000.0, 500000.0],
        min_length=1,
        description="Liste der Reynolds-Zahlen, für die das Airfoil analysiert wird.",
)
    alpha_start_deg: float = Field(-10.0, description="Start-Anstellwinkel in Grad.")
    alpha_end_deg: float = Field(16.0, description="End-Anstellwinkel in Grad.")
    alpha_step_deg: PositiveFloat = Field(1.0, description="Schrittweite des Anstellwinkels in Grad.")
    mach: float = Field(0.0, ge=0.0, description="Mach-Zahl für die Analyse.")
    n_crit: PositiveFloat = Field(9.0, description="e^N-Kriterium für Transition.")
    xtr_upper: float = Field(1.0, ge=0.0, le=1.0, description="Forced transition upper side (0..1).")
    xtr_lower: float = Field(1.0, ge=0.0, le=1.0, description="Forced transition lower side (0..1).")
    model_size: str = Field("large", description="NeuralFoil Modellgröße.")
    include_360_deg_effects: bool = Field(True, description="Post-stall 360°-Effekte einbeziehen.")

    @model_validator(mode="after")
    def _validate_alpha_range(self):
        if self.alpha_end_deg < self.alpha_start_deg:
            raise ValueError("alpha_end_deg muss größer oder gleich alpha_start_deg sein.")
        return self


class AirfoilNeuralFoilReynoldsResult(BaseModel):
    reynolds_number: float
    cl: list[float | None]
    cd: list[float | None]
    cm: list[float | None]
    cl_over_cd: list[float | None]
    analysis_confidence: list[float | None]
    cl_max: float | None
    alpha_at_cl_max_deg: float | None
    cd_min: float | None
    alpha_at_cd_min_deg: float | None


class AirfoilNeuralFoilAnalysisResponse(BaseModel):
    airfoil_name: str
    file_name: str
    alpha_deg: list[float]
    reynolds_results: list[AirfoilNeuralFoilReynoldsResult]


class AirfoilNeuralFoilDiagramResponse(BaseModel):
    airfoil_name: str
    file_name: str
    cl_vs_alpha_url: str
    cd_vs_alpha_url: str
    cm_vs_alpha_url: str
    cd_vs_cl_url: str
    cl_over_cd_vs_alpha_url: str


def _normalize_dat_filename(file_name: str) -> str:
    candidate = (file_name or "").strip()
    if not candidate:
        raise ValidationError(message="Dateiname darf nicht leer sein.")

    file_part = Path(candidate).name
    if file_part != candidate:
        raise ValidationError(message="Dateiname darf keine Pfadsegmente enthalten.")

    if file_part in {".", ".."}:
        raise ValidationError(message="Ungültiger Dateiname.")

    if not file_part.lower().endswith(".dat"):
        file_part = f"{file_part}.dat"

    return file_part


def _find_airfoil_filename(file_name: str) -> str | None:
    if not AIRFOILS_DIR.exists():
        return None

    wanted = file_name.lower()
    for entry in AIRFOILS_DIR.iterdir():
        if entry.is_file() and entry.suffix.lower() == ".dat" and entry.name.lower() == wanted:
            return entry.name
    return None


def _relative_airfoil_path(file_name: str) -> str:
    return (AIRFOILS_DIR / file_name).as_posix()


def _resolve_base_url(request: Request | None, settings: Settings) -> str:
    base_url = str(request.base_url).rstrip("/") if request else settings.base_url.rstrip("/")
    return base_url if base_url != "apiserver" else settings.base_url.rstrip("/")


def _build_static_url_from_tmp_path(file_path: Path, request: Request | None, settings: Settings) -> str:
    tmp_root = Path("tmp").resolve()
    normalized = file_path.resolve()
    relative = normalized.relative_to(tmp_root).as_posix()
    return urljoin(_resolve_base_url(request, settings), f"/static/{relative}")


def _resolve_airfoil_file(airfoil_name: str) -> tuple[str, Path]:
    file_name = _normalize_dat_filename(airfoil_name)
    known_file_name = _find_airfoil_filename(file_name)
    if known_file_name is None:
        raise NotFoundError(
            message=f"Airfoil '{file_name}' wurde nicht gefunden.",
            details={"file_name": file_name},
        )
    file_path = AIRFOILS_DIR / known_file_name
    if not file_path.is_file():
        raise NotFoundError(
            message=f"Airfoil-Datei '{known_file_name}' existiert nicht.",
            details={"file_name": known_file_name},
        )
    return known_file_name, file_path


def _parse_selig_dat(file_path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Parse a Selig-format .dat file and return (upper_coords, lower_coords).

    Each array has shape (N, 2) with columns [x, y].  Upper surface runs from
    TE (x~1) to LE (x~0); lower surface from LE (x~0) to TE (x~1).
    """
    lines = file_path.read_text().splitlines()
    coords: list[tuple[float, float]] = []
    for line in lines[1:]:  # skip header
        parts = line.split()
        if len(parts) >= 2:
            try:
                coords.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
    if len(coords) < 4:
        raise ValidationError(
            message="Die DAT-Datei enthält zu wenige Koordinaten.",
            details={"file_name": file_path.name, "coordinate_count": len(coords)},
        )
    arr = np.array(coords)
    le_idx = int(np.argmin(arr[:, 0]))
    upper = arr[: le_idx + 1]  # TE -> LE (x descending)
    lower = arr[le_idx:]       # LE -> TE (x ascending)
    return upper, lower


def _compute_geometry_stats(
    upper: np.ndarray, lower: np.ndarray,
) -> tuple[float, float, float, float]:
    """Return (max_thickness_pct, thickness_x, max_camber_pct, camber_x)."""
    # Flip upper so x is ascending for interpolation
    upper_sorted = upper[np.argsort(upper[:, 0])]
    lower_sorted = lower[np.argsort(lower[:, 0])]

    x_min = max(upper_sorted[0, 0], lower_sorted[0, 0])
    x_max = min(upper_sorted[-1, 0], lower_sorted[-1, 0])
    x_eval = np.linspace(x_min, x_max, 200)

    y_upper = np.interp(x_eval, upper_sorted[:, 0], upper_sorted[:, 1])
    y_lower = np.interp(x_eval, lower_sorted[:, 0], lower_sorted[:, 1])

    thickness = y_upper - y_lower
    camber = (y_upper + y_lower) / 2.0

    idx_t = int(np.argmax(thickness))
    idx_c = int(np.argmax(np.abs(camber)))

    return (
        float(thickness[idx_t]) * 100.0,
        float(x_eval[idx_t]),
        float(camber[idx_c]) * 100.0,
        float(x_eval[idx_c]),
    )


def _list_available_airfoil_files() -> list[Path]:
    if not AIRFOILS_DIR.exists():
        return []
    return sorted(
        [entry for entry in AIRFOILS_DIR.iterdir() if entry.is_file() and entry.suffix.lower() == ".dat"],
        key=lambda path: path.name.lower(),
    )


def _build_alpha_grid(request: AirfoilNeuralFoilRequest) -> np.ndarray:
    stop = request.alpha_end_deg + request.alpha_step_deg * 0.5
    alpha_deg = np.arange(request.alpha_start_deg, stop, request.alpha_step_deg, dtype=float)
    if alpha_deg.size == 0:
        raise ValidationError(message="Die Alpha-Range ist leer. Prüfe Start/Ende/Schrittweite.")
    return alpha_deg


def _coerce_array_to_alpha_size(values: Any, alpha_size: int) -> np.ndarray:
    array = np.atleast_1d(np.asarray(values, dtype=float))
    if array.size == alpha_size:
        return array
    if array.size == 1:
        return np.full(alpha_size, float(array[0]), dtype=float)
    raise ValidationError(
        message="NeuralFoil Rückgabe hat unerwartete Array-Länge.",
        details={"expected_size": alpha_size, "actual_size": int(array.size)},
    )


def _finite_or_none(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def _array_to_optional_float_list(values: np.ndarray) -> list[float | None]:
    return [_finite_or_none(float(value)) for value in values]


def _run_neuralfoil_analysis(
    airfoil_path: Path,
    request: AirfoilNeuralFoilRequest,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    alpha_deg = _build_alpha_grid(request)
    airfoil = asb.Airfoil(name=airfoil_path.stem, coordinates=airfoil_path)
    results: list[dict[str, Any]] = []

    for reynolds in request.reynolds_numbers:
        raw = airfoil.get_aero_from_neuralfoil(
            alpha=alpha_deg,
            Re=float(reynolds),
            mach=request.mach,
            n_crit=float(request.n_crit),
            xtr_upper=request.xtr_upper,
            xtr_lower=request.xtr_lower,
            model_size=request.model_size,
            include_360_deg_effects=request.include_360_deg_effects,
        )

        cl = _coerce_array_to_alpha_size(raw.get("CL", np.nan), alpha_deg.size)
        cd = _coerce_array_to_alpha_size(raw.get("CD", np.nan), alpha_deg.size)
        cm = _coerce_array_to_alpha_size(raw.get("CM", np.nan), alpha_deg.size)
        confidence = _coerce_array_to_alpha_size(raw.get("analysis_confidence", np.nan), alpha_deg.size)
        cl_over_cd = np.divide(
            cl,
            cd,
            out=np.full(alpha_deg.size, np.nan, dtype=float),
            where=np.abs(cd) > 1e-12,
        )

        cl_max = alpha_at_cl_max = None
        if np.isfinite(cl).any():
            idx_cl_max = int(np.nanargmax(cl))
            cl_max = _finite_or_none(cl[idx_cl_max])
            alpha_at_cl_max = _finite_or_none(alpha_deg[idx_cl_max])

        cd_min = alpha_at_cd_min = None
        if np.isfinite(cd).any():
            idx_cd_min = int(np.nanargmin(cd))
            cd_min = _finite_or_none(cd[idx_cd_min])
            alpha_at_cd_min = _finite_or_none(alpha_deg[idx_cd_min])

        results.append(
            {
                "reynolds_number": float(reynolds),
                "cl": cl,
                "cd": cd,
                "cm": cm,
                "cl_over_cd": cl_over_cd,
                "analysis_confidence": confidence,
                "cl_max": cl_max,
                "alpha_at_cl_max_deg": alpha_at_cl_max,
                "cd_min": cd_min,
                "alpha_at_cd_min_deg": alpha_at_cd_min,
            }
        )

    return alpha_deg, results


def _save_figure_and_get_url(
    figure: plt.Figure,
    *,
    airfoil_name: str,
    filename_prefix: str,
    request: Request | None,
    settings: Settings,
) -> str:
    airfoil_stem = Path(airfoil_name).stem
    target_dir = Path("tmp") / "airfoils" / "neuralfoil" / airfoil_stem
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / f"{filename_prefix}_{uuid4().hex}.png"
    figure.savefig(file_path, format="png", dpi=220, bbox_inches="tight")
    plt.close(figure)
    return _build_static_url_from_tmp_path(file_path, request, settings)


def _plot_alpha_curve(alpha_deg: np.ndarray, results: list[dict[str, Any]], *, value_key: str, ylabel: str, title: str) -> plt.Figure:
    figure, ax = plt.subplots(figsize=(8.5, 5.5))
    for result in results:
        values = np.asarray(result[value_key], dtype=float)
        ax.plot(alpha_deg, values, linewidth=1.8, label=f"Re={result['reynolds_number']:.0f}")
    ax.set_xlabel("alpha [deg]")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    return figure


def _plot_cd_vs_cl(results: list[dict[str, Any]]) -> plt.Figure:
    figure, ax = plt.subplots(figsize=(8.5, 5.5))
    for result in results:
        cl = np.asarray(result["cl"], dtype=float)
        cd = np.asarray(result["cd"], dtype=float)
        ax.plot(cd, cl, linewidth=1.8, label=f"Re={result['reynolds_number']:.0f}")
    ax.set_xlabel("CD [-]")
    ax.set_ylabel("CL [-]")
    ax.set_title("Drag Polar (CL vs CD)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    return figure


def _save_airfoil_dat(file_name: str, dat_bytes: bytes, overwrite: bool) -> AirfoilUploadResponse:
    if not dat_bytes:
        raise ValidationError(message="Die DAT-Datei darf nicht leer sein.")

    AIRFOILS_DIR.mkdir(parents=True, exist_ok=True)
    target = AIRFOILS_DIR / file_name

    exists = target.exists()
    if exists and not overwrite:
        raise ConflictError(
            message=f"Airfoil '{file_name}' existiert bereits.",
            details={"file_name": file_name},
        )

    target.write_bytes(dat_bytes)
    return AirfoilUploadResponse(
        airfoil_name=Path(file_name).stem,
        file_name=file_name,
        relative_path=_relative_airfoil_path(file_name),
        size_bytes=len(dat_bytes),
        overwritten=exists,
    )


def upload_airfoil_dat_content(file_name: str, dat_content: str, overwrite: bool = False) -> AirfoilUploadResponse:
    normalized_name = _normalize_dat_filename(file_name)
    payload = (dat_content or "").strip()
    if not payload:
        raise ValidationError(message="Der DAT-Inhalt darf nicht leer sein.")
    return _save_airfoil_dat(normalized_name, payload.encode("utf-8"), overwrite=overwrite)


def _raise_http_from_domain(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, (ValidationError, ValidationDomainError)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    if isinstance(exc, InternalError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc


@router.get(
    "/airfoils/{airfoil_name}/known",
    status_code=status.HTTP_200_OK,
    operation_id="is_airfoil_known",
    tags=["airfoils"]
)
async def is_airfoil_known(airfoil_name: str) -> AirfoilKnownResponse:
    try:
        file_name = _normalize_dat_filename(airfoil_name)
        known_file_name = _find_airfoil_filename(file_name)
        if known_file_name is None:
            return AirfoilKnownResponse(
                airfoil_name=Path(file_name).stem,
                file_name=file_name,
                known=False,
                relative_path=None,
            )

        return AirfoilKnownResponse(
            airfoil_name=Path(known_file_name).stem,
            file_name=known_file_name,
            known=True,
            relative_path=_relative_airfoil_path(known_file_name),
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


@router.post(
    "/airfoils/datfile",
    status_code=status.HTTP_201_CREATED,
    operation_id="upload_airfoil_datfile",
    tags=["airfoils"]
)
async def upload_airfoil_datfile(
    response: Response,
    file: Annotated[UploadFile, File(..., description="DAT-Datei mit Airfoil-Koordinaten.")],
    overwrite: Annotated[bool, Query(description="Bestehende Datei überschreiben.")] = False,
) -> AirfoilUploadResponse:
    try:
        raw_name = (file.filename or "").strip()
        if not raw_name:
            raise ValidationError(message="Die hochgeladene Datei benötigt einen Dateinamen.")
        if not raw_name.lower().endswith(".dat"):
            raise ValidationError(message="Nur Dateien mit der Endung .dat sind erlaubt.")

        normalized_name = _normalize_dat_filename(raw_name)
        dat_bytes = await file.read()
        result = _save_airfoil_dat(normalized_name, dat_bytes, overwrite=overwrite)
        if result.overwritten:
            response.status_code = status.HTTP_200_OK
        return result
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


@router.get(
    "/airfoils",
    status_code=status.HTTP_200_OK,
    operation_id="list_airfoils",
    tags=["airfoils"]
)
async def list_airfoils() -> AirfoilListResponse:
    try:
        available = _list_available_airfoil_files()
        payload = [
            AirfoilListEntryResponse(
                airfoil_name=entry.stem,
                file_name=entry.name,
                relative_path=_relative_airfoil_path(entry.name),
                size_bytes=entry.stat().st_size,
            )
            for entry in available
        ]
        return AirfoilListResponse(count=len(payload), airfoils=payload)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


@router.get(
    "/airfoils/{airfoil_name}/datfile",
    status_code=status.HTTP_200_OK,
    operation_id="download_airfoil_datfile",
    tags=["airfoils"]
)
async def download_airfoil_datfile(
    airfoil_name: str,
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request = None,
) -> AirfoilDatDownloadResponse:
    try:
        file_name, source_path = _resolve_airfoil_file(airfoil_name)
        target_dir = Path("tmp") / "airfoils" / "downloads"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"{Path(file_name).stem}_{uuid4().hex}.dat"
        shutil.copy2(source_path, target_file)

        return AirfoilDatDownloadResponse(
            airfoil_name=Path(file_name).stem,
            file_name=file_name,
            relative_path=_relative_airfoil_path(file_name),
            url=_build_static_url_from_tmp_path(target_file, request, settings),
            mime_type="text/plain",
            size_bytes=source_path.stat().st_size,
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


@router.get(
    "/airfoils/{airfoil_name}/geometry-stats",
    status_code=status.HTTP_200_OK,
    operation_id="get_airfoil_geometry_stats",
    tags=["airfoils"],
    summary="Get airfoil geometry statistics (thickness, camber)."
)
async def get_airfoil_geometry_stats(airfoil_name: str) -> AirfoilGeometryStatsResponse:
    """Compute max thickness and max camber from the .dat file coordinates."""
    try:
        file_name, file_path = _resolve_airfoil_file(airfoil_name)
        upper, lower = _parse_selig_dat(file_path)
        t_pct, t_x, c_pct, c_x = _compute_geometry_stats(upper, lower)
        return AirfoilGeometryStatsResponse(
            airfoil_name=Path(file_name).stem,
            max_thickness_pct=round(t_pct, 4),
            max_thickness_x=round(t_x, 4),
            max_camber_pct=round(c_pct, 4),
            max_camber_x=round(c_x, 4),
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


@router.get(
    "/airfoils/{airfoil_name}/coordinates",
    status_code=status.HTTP_200_OK,
    operation_id="get_airfoil_coordinates",
    tags=["airfoils"],
    summary="Get airfoil profile coordinates as x/y arrays.",
)
async def get_airfoil_coordinates(airfoil_name: str):
    """Return the parsed Selig-format coordinates as contour + upper/lower split."""
    try:
        _file_name, file_path = _resolve_airfoil_file(airfoil_name)
        upper, lower = _parse_selig_dat(file_path)
        # Concatenate: upper (TE→LE) + lower (LE→TE) = closed contour
        contour = np.concatenate([upper, lower[1:]], axis=0)

        # Camber line: interpolate upper/lower to same x stations, average y
        # Upper runs TE→LE (x descending), lower runs LE→TE (x ascending)
        upper_sorted = upper[upper[:, 0].argsort()]  # sort by x ascending
        lower_sorted = lower.copy()  # already LE→TE (x ascending)
        # Use lower x stations as reference
        from numpy import interp
        camber_x = lower_sorted[:, 0]
        upper_y_interp = interp(camber_x, upper_sorted[:, 0], upper_sorted[:, 1])
        camber_y = (upper_y_interp + lower_sorted[:, 1]) / 2

        return {
            "x": contour[:, 0].tolist(),
            "y": contour[:, 1].tolist(),
            "upper_x": upper_sorted[:, 0].tolist(),
            "upper_y": upper_sorted[:, 1].tolist(),
            "lower_x": lower_sorted[:, 0].tolist(),
            "lower_y": lower_sorted[:, 1].tolist(),
            "camber_x": camber_x.tolist(),
            "camber_y": camber_y.tolist(),
        }
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


@router.post(
    "/airfoils/{airfoil_name}/neuralfoil/analysis",
    status_code=status.HTTP_200_OK,
    operation_id="analyze_airfoil_neuralfoil",
    tags=["airfoils"]
)
async def analyze_airfoil_neuralfoil(
    airfoil_name: str,
    request: Annotated[AirfoilNeuralFoilRequest, Body(..., description="NeuralFoil Analyse-Konfiguration.")],
) -> AirfoilNeuralFoilAnalysisResponse:
    try:
        file_name, file_path = _resolve_airfoil_file(airfoil_name)
        alpha_deg, raw_results = _run_neuralfoil_analysis(file_path, request)

        reynolds_results = [
            AirfoilNeuralFoilReynoldsResult(
                reynolds_number=result["reynolds_number"],
                cl=_array_to_optional_float_list(result["cl"]),
                cd=_array_to_optional_float_list(result["cd"]),
                cm=_array_to_optional_float_list(result["cm"]),
                cl_over_cd=_array_to_optional_float_list(result["cl_over_cd"]),
                analysis_confidence=_array_to_optional_float_list(result["analysis_confidence"]),
                cl_max=result["cl_max"],
                alpha_at_cl_max_deg=result["alpha_at_cl_max_deg"],
                cd_min=result["cd_min"],
                alpha_at_cd_min_deg=result["alpha_at_cd_min_deg"],
            )
            for result in raw_results
        ]

        return AirfoilNeuralFoilAnalysisResponse(
            airfoil_name=Path(file_name).stem,
            file_name=file_name,
            alpha_deg=[float(value) for value in alpha_deg],
            reynolds_results=reynolds_results,
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


@router.post(
    "/airfoils/{airfoil_name}/neuralfoil/analysis/diagrams",
    status_code=status.HTTP_200_OK,
    operation_id="analyze_airfoil_neuralfoil_diagrams",
    tags=["airfoils"]
)
async def analyze_airfoil_neuralfoil_diagrams(
    airfoil_name: str,
    request: Annotated[AirfoilNeuralFoilRequest, Body(..., description="NeuralFoil Analyse-Konfiguration.")],
    settings: Annotated[Settings, Depends(get_settings)],
    http_request: Request = None,
) -> AirfoilNeuralFoilDiagramResponse:
    try:
        file_name, file_path = _resolve_airfoil_file(airfoil_name)
        alpha_deg, raw_results = _run_neuralfoil_analysis(file_path, request)

        cl_vs_alpha_figure = _plot_alpha_curve(
            alpha_deg=alpha_deg,
            results=raw_results,
            value_key="cl",
            ylabel="CL [-]",
            title="Lift Curve (CL vs alpha)",
        )
        cd_vs_alpha_figure = _plot_alpha_curve(
            alpha_deg=alpha_deg,
            results=raw_results,
            value_key="cd",
            ylabel="CD [-]",
            title="Drag Curve (CD vs alpha)",
        )
        cm_vs_alpha_figure = _plot_alpha_curve(
            alpha_deg=alpha_deg,
            results=raw_results,
            value_key="cm",
            ylabel="CM [-]",
            title="Pitching Moment (CM vs alpha)",
        )
        cl_over_cd_vs_alpha_figure = _plot_alpha_curve(
            alpha_deg=alpha_deg,
            results=raw_results,
            value_key="cl_over_cd",
            ylabel="CL/CD [-]",
            title="Efficiency (CL/CD vs alpha)",
        )
        cd_vs_cl_figure = _plot_cd_vs_cl(raw_results)

        return AirfoilNeuralFoilDiagramResponse(
            airfoil_name=Path(file_name).stem,
            file_name=file_name,
            cl_vs_alpha_url=_save_figure_and_get_url(
                cl_vs_alpha_figure,
                airfoil_name=file_name,
                filename_prefix="cl_vs_alpha",
                request=http_request,
                settings=settings,
            ),
            cd_vs_alpha_url=_save_figure_and_get_url(
                cd_vs_alpha_figure,
                airfoil_name=file_name,
                filename_prefix="cd_vs_alpha",
                request=http_request,
                settings=settings,
            ),
            cm_vs_alpha_url=_save_figure_and_get_url(
                cm_vs_alpha_figure,
                airfoil_name=file_name,
                filename_prefix="cm_vs_alpha",
                request=http_request,
                settings=settings,
            ),
            cd_vs_cl_url=_save_figure_and_get_url(
                cd_vs_cl_figure,
                airfoil_name=file_name,
                filename_prefix="cd_vs_cl",
                request=http_request,
                settings=settings,
            ),
            cl_over_cd_vs_alpha_url=_save_figure_and_get_url(
                cl_over_cd_vs_alpha_figure,
                airfoil_name=file_name,
                filename_prefix="cl_over_cd_vs_alpha",
                request=http_request,
                settings=settings,
            ),
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc
