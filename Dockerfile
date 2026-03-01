# Dockerfile.gdal
FROM ghcr.io/osgeo/gdal:ubuntu-small-latest

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Установим минимальные утилиты и libpq (runtime)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 python3-venv python3-pip libpq5 \
 && rm -rf /var/lib/apt/lists/*

# Сначала копируем requirements (кэшируем слой)
COPY requirements.txt /app/requirements.txt

# Создадим виртуальное окружение и установим зависимости в него.
# --system-site-packages нужно, чтобы venv видел системные пакеты GDAL/OSGeo,
# иначе модуль osgeo может быть недоступен.
RUN python3 -m venv /opt/venv --system-site-packages \
 && /opt/venv/bin/pip install --upgrade pip setuptools wheel \
 && /opt/venv/bin/pip uninstall -y bcrypt \
 && /opt/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Сделаем venv бинарники доступными в PATH
ENV PATH="/opt/venv/bin:$PATH"

# Копируем код
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
