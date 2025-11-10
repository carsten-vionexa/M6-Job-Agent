
import sys, os, json, sqlite3
# --------------------------------------------------
# Pfadkorrektur
# --------------------------------------------------
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.ba_classification import BAClassification
c = BAClassification()
print(c.classify_term("Bürokaufmann"))