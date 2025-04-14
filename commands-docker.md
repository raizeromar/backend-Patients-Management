# Stop current containers
docker-compose down

# Rebuild and start containers
docker-compose up --build -d

# View logs if needed
docker-compose logs -f web

However, for just Python code changes, you can often just restart the web container:

docker-compose restart web