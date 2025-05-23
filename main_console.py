import os.path
import sqlite3
import pandas as pd
from pathlib import Path

# Путь к Excel-файлу
while not (xlsx_file_path := Path(input('Input Excel file name (exclude .xlsx) :\n') + '.xlsx')).is_file():
    pass

# Подключение к SQLite
sql_name = (input('Output SQLite file name (exclude .db)\nor leave empty for autogen:\n') or xlsx_file_path.name) + ".db"
conn = sqlite3.connect(sql_name)
cursor = conn.cursor()

# Держим в курсе
print('Creating database. It can take a while. Do not close console')

# Создание таблиц
cursor.execute('''
CREATE TABLE IF NOT EXISTS Paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE,
    parent_id INTEGER,
    FOREIGN KEY(parent_id) REFERENCES Paths(id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS AllowEntries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path_id INTEGER,
    account TEXT,
    permissions TEXT,
    inherited_permission BOOLEAN,
    write_permission BOOLEAN,
    FOREIGN KEY(path_id) REFERENCES Paths(id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS DenyEntries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path_id INTEGER,
    account TEXT,
    permissions TEXT,
    inherited_permission BOOLEAN,
    write_permission BOOLEAN,
    FOREIGN KEY(path_id) REFERENCES Paths(id)
)
''')

cursor.execute('''
    CREATE UNIQUE INDEX IF NOT EXISTS idx_allow_unique
    ON AllowEntries (path_id, account, inherited_permission)
''')

cursor.execute('''
    CREATE UNIQUE INDEX IF NOT EXISTS idx_deny_unique
    ON DenyEntries (path_id, account, inherited_permission)
''')

# Кэш для путей чтобы не делать повторные запросы
path_cache = {}


def get_or_create_path_id(given_path):
    # Нормализация
    norm_path = os.path.normpath(given_path.strip())

    if norm_path in path_cache:
        return path_cache[norm_path]

    # Определяем родительский путь
    parent_path = os.path.dirname(norm_path)

    # Условие остановки рекурсии: если это корень (например, 'E:\')
    if parent_path == norm_path:
        parent_id = None
    else:
        parent_id = get_or_create_path_id(parent_path)

    # Добавляем текущий путь
    cursor.execute('INSERT OR IGNORE INTO Paths (path, parent_id) VALUES (?, ?)', (norm_path, parent_id))
    cursor.execute('SELECT id FROM Paths WHERE path = ?', (norm_path,))
    result = cursor.fetchone()
    if result is None:
        raise ValueError(f"Не удалось найти ID для пути: {norm_path}")

    path_id = result[0]
    path_cache[norm_path] = path_id
    return path_id


# Открываем Excel
xlsx = pd.ExcelFile(xlsx_file_path)

# Обработка всех листов
allow_keys_in_xlsx = set()
deny_keys_in_xlsx = set()
for sheet_name in xlsx.sheet_names:
    df = xlsx.parse(sheet_name)

    # Ожидаемые столбцы: path, account, access_type, inherited, permissions
    df.columns = ['path', 'account', 'access_type', 'inherited', 'permissions']

    # Обработка значений
    df['inherited'] = df['inherited'].apply(lambda x: str(x).strip().lower() == 'true')
    df['write_permission'] = df['permissions'].str.contains("write attributes", case=False)

    for _, row in df.iterrows():
        path = row['path']
        path_id = get_or_create_path_id(path)
        account = row['account']
        access_type = row['access_type'].strip().lower()
        inherited = row['inherited']
        permissions = row['permissions']
        write_perm = row['write_permission']

        # Добавляем путь
        cursor.execute('INSERT OR IGNORE INTO Paths (path) VALUES (?)', (path,))
        cursor.execute('SELECT id FROM Paths WHERE path = ?', (path,))
        path_id = cursor.fetchone()[0]

        # Добавляем запись в нужную таблицу
        key_tuple = (path_id, account.strip(), inherited)

        if access_type == 'allow':
            allow_keys_in_xlsx.add(key_tuple)
            cursor.execute('''
                INSERT INTO AllowEntries (path_id, account, permissions, inherited_permission, write_permission)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (path_id, account, inherited_permission)
                DO UPDATE SET
                    permissions = excluded.permissions,
                    write_permission = excluded.write_permission
            ''', (path_id, account, permissions, inherited, write_perm))

        elif access_type == 'deny':
            deny_keys_in_xlsx.add(key_tuple)
            cursor.execute('''
                INSERT INTO DenyEntries (path_id, account, permissions, inherited_permission, write_permission)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (path_id, account, inherited_permission)
                DO UPDATE SET
                    permissions = excluded.permissions,
                    write_permission = excluded.write_permission
            ''', (path_id, account, permissions, inherited, write_perm))

# Удаляем лишние записи из AllowEntries
cursor.execute('SELECT path_id, account, inherited_permission FROM AllowEntries')
existing_allow_keys = set(cursor.fetchall())
obsolete_allows = existing_allow_keys - allow_keys_in_xlsx
for key in obsolete_allows:
    cursor.execute('DELETE FROM AllowEntries WHERE path_id = ? AND account = ? AND inherited_permission = ?', key)

# Удаляем лишние записи из DenyEntries
cursor.execute('SELECT path_id, account, inherited_permission FROM DenyEntries')
existing_deny_keys = set(cursor.fetchall())
obsolete_denies = existing_deny_keys - deny_keys_in_xlsx
for key in obsolete_denies:
    cursor.execute('DELETE FROM DenyEntries WHERE path_id = ? AND account = ? AND inherited_permission = ?', key)

# Сохраняем и закрываем
conn.commit()
conn.close()

# Держим в курсе
input(
    f'\n\n\nDatabase successfully created in script directory with filename - "{sql_name}"\n\nPress any key to exit...')
