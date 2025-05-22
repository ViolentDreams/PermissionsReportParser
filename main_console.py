import sqlite3
import pandas as pd
from pathlib import Path

# Путь к Excel-файлу
xlsx_file_path = Path()
file_exist = False
while not file_exist:
    if xlsx_file_path.is_file():
        file_exist = True
    else:
        xlsx_file_name = input('Input Excel file name (exclude .xlsx) :\n') + '.xlsx'
        xlsx_file_path = Path(xlsx_file_name)

# Подключение к SQLite
sql_name = input('Output SQLite file name (exclude .db):\n')
sql_name = sql_name or f'{xlsx_file_name}'
sql_name += '.db'
conn = sqlite3.connect(sql_name)
cursor = conn.cursor()

print('Creating database. It can take a while. Do not close console')

# Создание таблиц
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

# Открываем Excel-книгу
xlsx = pd.ExcelFile(xlsx_file_name)

# Обработка всех листов
for sheet_name in xlsx.sheet_names:
    df = xlsx.parse(sheet_name)

    # Ожидаемые столбцы: path, account, access_type, inherited, permissions
    df.columns = ['path', 'account', 'access_type', 'inherited', 'permissions']

    # Обработка значений
    df['inherited'] = df['inherited'].apply(lambda x: str(x).strip().lower() == 'true')
    df['write_permission'] = df['permissions'].str.contains("write attributes", case=False)

    for _, row in df.iterrows():
        path = row['path']
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

# Сохраняем и закрываем
conn.commit()
conn.close()

input(f'\n\n\nDatabase successfully created in script directory with filename - "{sql_name}"\n\nPress any key to exit...')