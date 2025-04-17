# Stop current containers
docker-compose down

# Rebuild and start containers
docker-compose up --build -d

# View logs if needed
docker-compose logs -f web

# However, for just Python code changes, you can often just restart the web container:
docker-compose restart web

# Make migrationsc
docker-compose exec web python manage.py makemigrations

# Apply migrations
docker-compose exec web python manage.py migrate

# create superuser
docker-compose exec web python manage.py createsuperuser

curl http://127.0.0.1:10000/api/health/  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQ0ODg5MjY0LCJpYXQiOjE3NDQ4ODU2NjQsImp0aSI6IjNmNGM2ZjcyN2E0MDRlMWVhZTExOWRjZmI3MjAyODRjIiwidXNlcl9pZCI6MX0.paspXmUcwzyIPm-3B8RE49236NTC8L-VXJuJpRO3UJU"