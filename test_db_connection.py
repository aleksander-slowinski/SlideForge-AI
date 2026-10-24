
from services.db_service import get_connection


def test_connection():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Sprawdzenie aktywnej bazy
        cursor.execute("SELECT DB_NAME()")
        database_name = cursor.fetchone()[0]

        print(f"Połączono z bazą: {database_name}")

        # Odczyt tabel
        cursor.execute("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo'
              AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)

        tables = [row[0] for row in cursor.fetchall()]

        print("\nZnalezione tabele:")

        for table in tables:
            print(f"- {table}")

        required_tables = {
            "GenerationRun",
            "GeneratedSlide"
        }

        missing = required_tables - set(tables)

        if missing:
            raise RuntimeError(
                f"Brak wymaganych tabel: {missing}"
            )

        print("\n[SUKCES] SQL Server działa poprawnie!")

    finally:
        connection.close()


if __name__ == "__main__":
    test_connection()
