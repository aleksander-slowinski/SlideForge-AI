
from pathlib import Path

import pyodbc
from dotenv import dotenv_values


# Odczyt konfiguracji bezpośrednio z .env
BASE_DIR = Path(__file__).resolve().parent
config = dotenv_values(BASE_DIR / ".env")

driver = config.get(
    "SQL_DRIVER", "ODBC Driver 17 for SQL Server"
)

print("=== DIAGNOSTYKA SQL SERVER ===")
print("Serwer z .env:", repr(config.get("SQL_SERVER")))
print("Sterownik:", driver)
print("Dostępne sterowniki:", pyodbc.drivers())


# Test różnych adresów tej samej instancji
servers = [
    config.get("SQL_SERVER"),
    r"lpc:.\SQLEXPRESS",
    r".\SQLEXPRESS",
    r"DESKTOP-5I9MHMU\SQLEXPRESS",
]

# Usunięcie duplikatów
servers = list(dict.fromkeys(s for s in servers if s))


for server in servers:
    print(f"\nTest połączenia: {server}")

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        "DATABASE=master;"
        "Trusted_Connection=yes;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )

    try:
        connection = pyodbc.connect(
            connection_string,
            timeout=4
        )

        cursor = connection.cursor()
        cursor.execute("SELECT @@SERVERNAME")

        server_name = cursor.fetchone()[0]

        print(f"[SUKCES] Połączono z: {server_name}")

        connection.close()

    except pyodbc.Error as exc:
        print(f"[BŁĄD] {str(exc)[:350]}")


print("\n=== KONIEC DIAGNOSTYKI ===")