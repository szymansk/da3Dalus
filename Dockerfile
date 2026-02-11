FROM arm64v8/ubuntu:22.04 AS build_avl

COPY ./Avl /home/avl/

SHELL [ "/bin/bash", "-c" ]
WORKDIR /home/avl
RUN apt-get update \
    && apt-get install wget -y \
    && apt-get install build-essential -y \
    && apt-get install cmake -y \
    && apt-get install liblapack-dev -y \
    && apt-get install libblas-dev -y \
    && apt-get install libx11-dev -y \
    && apt-get install gfortran -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN cd plotlib \
    && make gfortran \
    && ln -s libPlt_gSP.a libPlt.a \
    && cd ..

RUN cd eispack \
    && make -f Makefile.mingw \
    && ln -s eispack_gSP.a libeispack.a \
    && cd ..

RUN cd bin \
    && make -f Makefile.gfortran avl


FROM mambaorg/micromamba:2.5-debian13-slim AS runtime

USER root
SHELL [ "/bin/bash", "-c" ]

# Activate the conda env automatically for RUN/CMD
ENV MAMBA_DOCKERFILE_ACTIVATE=1

COPY --from=build_avl /home/avl/bin/avl /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    POETRY_INSTALLER_MAX_WORKERS=10

WORKDIR /app

# System libs needed at runtime (VTK OpenGL/X11 deps + AVL LAPACK/BLAS runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglu1-mesa \
    libxrender1 \
    libxext6 \
    libxt6 \
    libsm6 \
    libice6 \
    liblapack3 \
    libblas3 \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency manifests first (better layer caching)
COPY pyproject.toml poetry.lock ./
COPY external/ ./external/

# Install Python + nlopt from conda-forge (linux/arm64 supported)
# Then install Python deps with Poetry (excluding CadQuery and its heavy deps)
# Then install CadQuery and its heavy deps with pip --no-deps (to avoid building them from source)
RUN micromamba create -y -n py311 -c conda-forge  \
     python=3.11.5 \
     nlopt \
    && micromamba install -y -n py311 -c conda-forge "poetry>=2.0.0,<3.0.0" \
    && micromamba run -n py311 poetry lock --no-cache --regenerate \
    && micromamba run -n py311 poetry install --no-ansi --without binary \
    # CadQuery installed with --no-deps -> install its pure-Python runtime deps explicitly
    && micromamba run -n py311 pip install --no-deps \
        cadquery==2.6.1 \
    && micromamba run -n py311 pip install --no-deps \
        multimethod \
        nptyping \
        typish \
        pyparsing \
        typing-extensions \
        ezdxf \
        numpy \
        scipy \
        casadi \
        path \
        questionary \
    && micromamba run -n py311 pip install --no-deps vtk==9.5.2 \
    && micromamba run -n py311 pip install --no-deps cadquery-ocp==7.9.3.0 \
    #&& micromamba run -n py311 pip install ocp_vscode \
    && micromamba run -n py311 pip install aerosandbox[full] \
    && micromamba clean -a -y

# Install Chromium and its dependencies for headless rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        fonts-liberation \
        libnss3 \
        libgbm1 \
        libasound2 \
        libglib2.0-0 \
        libxshmfence1 \
        libgtk-3-0 \
        libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

ENV BROWSER_PATH=/usr/bin/chromium

# --- Smoke tests (fail build early if native deps are broken) ---
COPY docker_smoke_test.py ./
RUN micromamba run -n py311 python docker_smoke_test.py \
    && (ldd /usr/local/bin/avl | grep -q 'not found' && echo 'Missing shared libs for avl' && ldd /usr/local/bin/avl && exit 1 || true)

# Now copy the rest of the application
COPY app/ ./app/
COPY cad_designer/ ./cad_designer/
COPY components/ ./components/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY db/test.db ./db/test.db
COPY __init__.py ./

RUN mkdir -p ./tmp/exports

EXPOSE 8000

# Run without Poetry at runtime (faster, fewer moving parts)
CMD ["micromamba", "run", "-n", "py311", "python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
