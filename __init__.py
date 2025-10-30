from datetime import datetime
import re

try:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QLabel, QPushButton
    )
    QT_BACKEND = "PySide6"
except Exception:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QLabel, QPushButton
    )
    QT_BACKEND = "PyQt5"

LEARNING_STEPS = [60, 10*60]  
DAY = 24 * 3600
PLACEHOLDER_RE = re.compile(r"\{\{\s*([^}\s]+)\s*\}\}") # A regrex pattern that finds placeholders in templates (e.g. {{Front}})

# Convert UNIX to DD/MM/YYYY HH:MM:SS
def convert_human_time(seconds):
    if seconds is None:
        return ""
    try:
        return datetime.fromtimestamp(int(seconds)).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return str(seconds)

# Convert UNIX time to DD/MM/YYYY
def convert_date(seconds):
    if seconds is None:
        return ""
    try:
        return datetime.fromtimestamp(int(seconds)).strftime("%d/%m/%Y")
    except Exception:
        return str(seconds)


