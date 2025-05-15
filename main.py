import sqlite3
import pandas as pd

# Путь к Excel-файлу
xlsx_file = "test.xlsx"  # замените на свой путь

# Загружаем таблицу
df = pd.read_excel(xlsx_file)
df.columns = ['path', 'account', 'access_type', 'permissions']

# Подключаемся к базе
conn = sqlite3.connect("nested_permissions.db")
cursor = conn.cursor()

# Создаём таблицы
cursor.execute('''
CREATE TABLE IF NOT EXISTS Paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS AllowEntries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path_id INTEGER,
    account TEXT,
    permissions TEXT,
    FOREIGN KEY(path_id) REFERENCES Paths(id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS DenyEntries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path_id INTEGER,
    account TEXT,
    permissions TEXT,
    FOREIGN KEY(path_id) REFERENCES Paths(id)
)
''')

# Заполнение
for _, row in df.iterrows():
    path = row['path']
    account = row['account']
    access_type = row['access_type'].strip().lower()
    permissions = row['permissions']

    cursor.execute('INSERT OR IGNORE INTO Paths (path) VALUES (?)', (path,))
    cursor.execute('SELECT id FROM Paths WHERE path = ?', (path,))
    path_id = cursor.fetchone()[0]

    if access_type == 'allow':
        cursor.execute('''
            INSERT INTO AllowEntries (path_id, account, permissions)
            VALUES (?, ?, ?)
        ''', (path_id, account, permissions))
    elif access_type == 'deny':
        cursor.execute('''
            INSERT INTO DenyEntries (path_id, account, permissions)
            VALUES (?, ?, ?)
        ''', (path_id, account, permissions))

conn.commit()
conn.close()
