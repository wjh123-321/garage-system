FROM python:3.12
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD python -u -c "
import sys, logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.debug('CONTAINER_STARTED')
try:
    import uvicorn
    logging.debug('uvicorn loaded')
    from app.main import app
    logging.debug('app loaded, routes: %%d', len(app.routes))
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='debug')
except Exception as e:
    logging.error('CRASH: %%s', str(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
