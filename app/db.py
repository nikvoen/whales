import sqlite3


class Database:
    def __init__(self, db_file):
        """Инициализация соединения с базой данных."""
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()

    def execute_query(self, query, params=None):
        """Выполняет заданный SQL-запрос с параметрами."""
        if params is None:
            params = ()
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
            return self.cursor
        except sqlite3.Error as e:
            print(f"Ошибка выполнения запроса: {e}")
            return None

    def fetchall(self):
        """Возвращает все строки результата запроса."""
        return self.cursor.fetchall()

    def fetchone(self):
        """Возвращает одну строку результата запроса."""
        return self.cursor.fetchone()

    def close(self):
        """Закрывает соединение с базой данных."""
        self.connection.close()

    # Методы для работы с таблицей whales
    def insert_whale(self, whale_id, type="Горбатый кит", family_id=None, photo="pic1.jpg"):
        """Добавляет нового кита в таблицу whales."""
        query = """
        INSERT INTO whales (whale_id, type, family_id, photo)
        VALUES (?, ?, ?, ?)
        """
        params = (whale_id, type, family_id, photo)
        try:
            self.execute_query(query, params)
        except sqlite3.IntegrityError as e:
            print(f"Ошибка при добавлении кита: {e}")

    def get_whale(self, whale_id):
        """Получает информацию о ките по его whale_id."""
        query = "SELECT * FROM whales WHERE whale_id = ?"
        params = (whale_id,)
        cursor = self.execute_query(query, params)
        return cursor.fetchone() if cursor else None

    def get_families(self):
        """Получает список всех family_id."""
        self.cursor.execute("SELECT DISTINCT family_id FROM whales")
        return [row[0] for row in self.cursor.fetchall()]

    def get_family(self, family_id):
        """Получает информацию о всех китах по family_id."""
        self.cursor.execute("SELECT * FROM whales WHERE family_id = ?", (family_id,))
        return self.cursor.fetchall()

    def clear_base(self):
        self.cursor.execute("DELETE FROM whales")
        self.connection.commit()

    # Методы для работы с таблицей records
    def insert_record(self, whales_id, type, latitude, longitude):
        """Добавляет новую запись в таблицу records."""
        query = """
        INSERT INTO records (whales_id, type, latitude, longitude)
        VALUES (?, ?, ?, ?)
        """
        params = (whales_id, type, latitude, longitude)
        try:
            self.execute_query(query, params)
        except sqlite3.IntegrityError as e:
            print(f"Ошибка при добавлении записи: {e}")

    def get_all_whales(self):
        """Возвращает все записи из таблицы records."""
        query = "SELECT * FROM whales"
        cursor = self.execute_query(query)
        if cursor:
            return cursor.fetchall()
        else:
            return []

    def get_records_by_whale(self, whales_id):
        """Получает все записи, связанные с определенным китом."""
        query = "SELECT * FROM records WHERE whales_id = ?"
        params = (whales_id,)
        cursor = self.execute_query(query, params)
        return cursor.fetchall() if cursor else []

    def get_all_records(self):
        """Возвращает все записи из таблицы records."""
        query = "SELECT * FROM records"
        cursor = self.execute_query(query)
        if cursor:
            return cursor.fetchall()
        else:
            return []

    def delete_whale(self, whale_id):
        """Удаляет кита и связанные с ним записи из базы данных."""
        query = "DELETE FROM whales WHERE whale_id = ?"
        params = (whale_id,)
        self.execute_query(query, params)

    def update_whale(self, whale_id, type=None, family_id=None):
        """Обновляет информацию о ките."""
        fields = []
        params = []
        if type is not None:
            fields.append("type = ?")
            params.append(type)
        if family_id is not None:
            fields.append("family_id = ?")
            params.append(family_id)
        params.append(whale_id)
        query = f"UPDATE whales SET {', '.join(fields)} WHERE whale_id = ?"
        self.execute_query(query, params)
