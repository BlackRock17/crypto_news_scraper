import psycopg2
import psycopg2.extras
import json
from datetime import datetime
import os


class PostgreSQLDatabaseManager:
        def __init__(self):
            print("🐘 Свързване с PostgreSQL...")

            # Конфигурация за базата
            self.db_config = {
                'host': 'localhost',
                'port': 5432,
                'database': 'crypto_news',
                'user': 'crypto_user',
                'password': 'password'
            }

            # Тестваме връзката
            self._test_connection()
            self.init_database()
            print("✅ PostgreSQL готов!")

        def _test_connection(self):
            """Проверява дали може да се свърже с PostgreSQL"""
            try:
                conn = psycopg2.connect(**self.db_config)
                conn.close()
                print("✅ Връзка с PostgreSQL успешна")
            except psycopg2.Error as e:
                print(f"❌ Грешка при свързване: {e}")
                raise

        def get_connection(self):
            """Връща нова връзка към базата"""
            return psycopg2.connect(**self.db_config)