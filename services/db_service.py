
import os
from pathlib import Path

import pyodbc
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env", override=True)

def get_connection() -> pyodbc.Connection:
    """
    Tworzy połączenie z bazą SlideForgeDB
    na lokalnym serwerze SQL Server.
    """

    server = os.getenv("SQL_SERVER")
    database = os.getenv("SQL_DATABASE", "SlideForgeDB")
    driver = os.getenv(
        "SQL_DRIVER",
        "ODBC Driver 18 for SQL Server"
    )

    if not server:
        raise ValueError(
            "Brak SQL_SERVER w pliku .env."
        )

    if driver not in pyodbc.drivers():
        raise RuntimeError(
            f"Sterownik {driver} nie jest zainstalowany."
        )

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )

    connection = pyodbc.connect(
        connection_string,
        timeout=5
    )

    return connection
