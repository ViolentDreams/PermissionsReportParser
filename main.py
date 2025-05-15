import sqlite3
import pandas as pd

# Путь к Excel-файлу (замените на нужный)
xlsx_file = "test.xlsx"

# Загружаем таблицу
df = pd.read_excel(xlsx_file)

# Убедимся, что названия столбцов соответствуют ожиданиям
df.columns = ['path', 'account', 'access_type', 'inherited', 'permissions']

# Преобразуем флаги
df['inherited'] = df['inherited'].apply(lambda x: str(x).strip().lower() == 'true')
df['write_permission'] = df['permissions'].str.contains("write attributes", case=False)

# Подключение к базе данных
conn = sqlite3.connect("updated_permissions.db")
cursor = conn.cursor()

# Таблица путей
cursor.execute('''
CREATE TABLE IF NOT EXISTS Paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE
)
''')

# Таблица Allow
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

# Таблица Deny
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

# Загрузка данных
for _, row in df.iterrows():
    path = row['path']
    account = row['account']
    access_type = row['access_type'].strip().lower()
    inherited = bool(row['inherited'])
    permissions = row['permissions']
    write_perm = bool(row['write_permission'])

    cursor.execute('INSERT OR IGNORE INTO Paths (path) VALUES (?)', (path,))
    cursor.execute('SELECT id FROM Paths WHERE path = ?', (path,))
    path_id = cursor.fetchone()[0]

    if access_type == 'allow':
        cursor.execute('''
            INSERT INTO AllowEntries (path_id, account, permissions, inherited_permission, write_permission)
            VALUES (?, ?, ?, ?, ?)
        ''', (path_id, account, permissions, inherited, write_perm))
    elif access_type == 'deny':
        cursor.execute('''
            INSERT INTO DenyEntries (path_id, account, permissions, inherited_permission, write_permission)
            VALUES (?, ?, ?, ?, ?)
        ''', (path_id, account, permissions, inherited, write_perm))

conn.commit()
conn.close()