FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD python -u -c "
import http.server
s = http.server.HTTPServer(('0.0.0.0', 8000), http.server.BaseHTTPRequestHandler)
s.serve_forever()
"
