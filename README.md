# spc_ui

```
docker build -f Dockerfile -t docker-dash-prod .
docker run -p 8050:8050 -v "$(pwd)"/app:/app --rm docker-dash-prod
```