"""Expose l'application Streamlit via ngrok pour une démonstration à distance.

Usage : NGROK_AUTHTOKEN=... APP_PASSWORD=... python scripts/expose_ngrok.py
Définissez APP_PASSWORD (la page de connexion protège l'accès) avant de partager l'URL.
"""
import os
import sys
import time

from pyngrok import conf, ngrok

token = os.getenv("NGROK_AUTHTOKEN")
if not token:
    sys.exit("NGROK_AUTHTOKEN manquant : exportez le jeton de votre compte ngrok.")
if not os.getenv("APP_PASSWORD"):
    print("Attention : APP_PASSWORD n'est pas défini, l'application sera accessible sans mot de passe.")
conf.get_default().auth_token = token
tunnel = ngrok.connect(8501, "http")
print(f"URL publique : {tunnel.public_url}  (Ctrl+C pour arrêter)")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    ngrok.kill()
