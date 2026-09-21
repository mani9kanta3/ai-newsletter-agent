import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')

API_KEY = os.getenv('GOOGLE_API_KEY', '')
MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite')
OUTPUT = ROOT / 'output'
OUTPUT.mkdir(exist_ok=True)
