FROM python:3.12-slim
ENV TRAKTARR_CONFIG=/config/config.json TRAKTARR_CACHEFILE=/config/cache.db \
    TRAKTARR_LOGFILE=/config/traktarr.log PYTHONUNBUFFERED=1
WORKDIR /traktarr
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
VOLUME /config
ENTRYPOINT ["python", "traktarr.py"]
CMD ["run", "--run-now"]
