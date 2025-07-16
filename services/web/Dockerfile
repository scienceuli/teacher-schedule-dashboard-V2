# Use the latest available Python 3.12 slim image (3.13 may not be available yet)
FROM python:3.12-slim

ENV COMPOSE_BAKE=true \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy the uv and uvx binaries from the official uv image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set work directory
WORKDIR /usr/src/app

# Copy only dependency files first for better Docker cache utilization
#COPY pyproject.toml uv.lock /usr/src/app/

# Install dependencies using uv
#RUN uv sync --locked
RUN pip install --upgrade pip
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

# Now copy the rest of the application code
COPY . /usr/src/app

# Path
# ENV PATH="/app/.venv/bin:$PATH"
# ENV FLASK_APP=app.py

# Expose port 5000 for the application
# EXPOSE 5050

# Start the application using gunicorn through uv
# CMD ["uv", "run", "gunicorn", "-w", "2", "-b", "0.0.0.0", "app:app"]
# CMD ["uv", "run", "app:app"]