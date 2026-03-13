import os, logging, sys
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

USER_ID = "4b5c932c-c0b5-464e-9efa-b9ac3213d698"

DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER','allerac')}:"
    f"{os.getenv('POSTGRES_PASSWORD','allerac_secret')}@"
    f"{os.getenv('POSTGRES_HOST','localhost')}:5432/"
    f"{os.getenv('POSTGRES_DB','allerac_health')}"
)
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

result = session.execute(text("SELECT * FROM garmin_credentials WHERE user_id = :uid"), {"uid": USER_ID})
row = result.fetchone()

if not row:
    print("ERRO: credenciais nao encontradas no banco")
    sys.exit(1)

print(f"Creds encontradas. is_connected={row.is_connected}")

# Tenta autenticar no Garmin
import hashlib, base64
from cryptography.fernet import Fernet

encryption_key = os.getenv("ENCRYPTION_KEY", "32-byte-key-for-encryption-here")
key = hashlib.sha256(encryption_key.encode()).digest()
fernet = Fernet(base64.urlsafe_b64encode(key))

token_data = bytes(row.oauth1_token_encrypted)
session_dump = fernet.decrypt(token_data).decode()
print(f"Session dump: {session_dump[:80]}...")

from garminconnect import Garmin
garmin = Garmin()
garmin.garth.loads(session_dump)

try:
    profile = garmin.garth.profile
    garmin.display_name = profile.get("displayName")
    garmin.full_name = profile.get("fullName")
    print(f"Garmin autenticado como: {garmin.full_name} ({garmin.display_name})")
except Exception as e:
    print(f"ERRO na autenticacao Garmin: {e}")
    sys.exit(1)

# Roda sync completo dos ultimos 30 dias
from datetime import date, timedelta
from app.tasks.garmin_fetch import fetch_and_store_data

end_date = date.today()
start_date = end_date - timedelta(days=7)
print(f"\nSincronizando dados de {start_date} a {end_date} (7 dias)...")
print("Aguarde, cada dia faz ~4 chamadas ao Garmin (~30 segundos total)...")

records = fetch_and_store_data(garmin, USER_ID, start_date, end_date)
print(f"Sync completo: {records} registros gravados no InfluxDB")

session.close()
