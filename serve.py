import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dental.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from waitress import serve
from dental.wsgi import application
serve(application, host='0.0.0.0', port=8000, threads=8)