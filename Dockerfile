# Axiom — reproducible backend image.
#
# Builds the dataset and trains the model *inside* the image, so what ships is not a
# pickle someone has to trust: it is rebuilt from the seeded generator at build time and
# any judge can watch it happen. No API keys are needed — every LLM path degrades to a
# deterministic fallback, and the Razorpay actuator returns clearly-labelled simulated
# links unless real test-mode keys are supplied at runtime.
#
#   docker build -t axiom .
#   docker run --rm -p 8000:8000 axiom
#   docker run --rm -p 8000:8000 --env-file .env axiom      # with Gemini / Razorpay keys
#
# The Next.js dashboard runs separately (`npm --prefix web run dev`); this image is the
# API the dashboard talks to.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# libgomp is LightGBM's OpenMP runtime — the wheel needs it and slim images omit it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml Makefile ./
COPY src/ ./src/
COPY docs/ ./docs/
COPY tests/ ./tests/

# Generate + train at build time: the seeds are fixed, so the artifact is reproducible.
RUN python -m src.data.generate_synthetic_cod --n 20000 --seed 42 \
    && python -m src.model.train

# Non-root: the container writes only the audit SQLite file it owns.
RUN useradd --create-home --uid 10001 axiom && chown -R axiom:axiom /app
USER axiom

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/').status==200 else 1)"

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
