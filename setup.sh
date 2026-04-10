#!/bin/bash
echo "=== e-Mebel API Setup ==="
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --no-input
echo "=== Done! ==="
echo "API: http://localhost:8000/api/"
echo "Admin: http://localhost:8000/admin/"
