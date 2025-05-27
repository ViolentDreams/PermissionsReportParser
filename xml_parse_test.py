import xml.etree.ElementTree as ET
import sqlite3
import os

PERMISSIONS = {
    0x1: 'Read Data / List Directory',
    0x2: 'Write Data',
    0x4: 'Append Data',
    0x8: 'Read Extended Attributes',
    0x10: 'Write Extended Attributes',
    0x20: 'Execute / Traverse',
    0x40: 'Delete Child',
    0x80: 'Read Attributes',
    0x100: 'Write Attributes',
    0x10000: 'Delete',
    0x20000: 'Read Permissions',
    0x40000: 'Change Permissions',
    0x80000: 'Take Ownership',
    0x100000: 'Synchronize',
}

def decode_rights(rights_value: int) -> list[str]:
    decoded = [name for bit, name in PERMISSIONS.items() if rights_value & bit]
    if rights_value == 0x1F01FF:
        decoded.append("FULL CONTROL")
    return decoded

conn = sqlite3.connect("test.db")
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS Paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE,
    parent_id INTEGER,
    FOREIGN KEY(parent_id) REFERENCES Paths(id))''')

cursor.execute('''CREATE TABLE IF NOT EXISTS AllowEntries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path_id INTEGER,
    account TEXT,
    permissions TEXT,
    inherited_permission BOOLEAN,
    write_permission BOOLEAN,
    FOREIGN KEY(path_id) REFERENCES Paths(id))''')

cursor.execute('''CREATE TABLE IF NOT EXISTS DenyEntries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path_id INTEGER,
    account TEXT,
    permissions TEXT,
    inherited_permission BOOLEAN,
    write_permission BOOLEAN,
    FOREIGN KEY(path_id) REFERENCES Paths(id))''')

path_cache = {}

def get_or_create_path_id(path: str):
    norm_path = os.path.normpath(path)
    if norm_path in path_cache:
        return path_cache[norm_path]
    parent_path = os.path.dirname(norm_path)
    parent_id = None if parent_path == norm_path else get_or_create_path_id(parent_path)
    cursor.execute('INSERT OR IGNORE INTO Paths (path, parent_id) VALUES (?, ?)', (norm_path, parent_id))
    cursor.execute('SELECT id FROM Paths WHERE path = ?', (norm_path,))
    pid = cursor.fetchone()[0]
    path_cache[norm_path] = pid
    return pid

def parse_folder_node(node, parent_path=""):
    folder_name_raw = node.findtext('Name')
    folder_name = os.path.join(parent_path, folder_name_raw) if parent_path else folder_name_raw
    folder_inherited = node.findtext('IsInherited') == 'true'
    path_id = get_or_create_path_id(folder_name)

    for perm in node.findall('./FolderPermissions/FolderPermission'):
        account = perm.findtext('./PrincipalDetails/AccountName')
        rights = int(perm.findtext('Rights'))
        rights_text = ', '.join(decode_rights(rights))
        allow = perm.findtext('Allow') == 'true'
        write_perm = 'Write Attributes' in rights_text
        table = 'AllowEntries' if allow else 'DenyEntries'
        cursor.execute(f'''
            INSERT INTO {table} (path_id, account, permissions, inherited_permission, write_permission)
            VALUES (?, ?, ?, ?, ?)''', (path_id, account, rights_text, folder_inherited, write_perm))

    for fperm in node.findall('./FilePermissions/FilePermission'):
        fname_raw = fperm.findtext('Name')
        fname = os.path.join(folder_name, fname_raw)
        fid = get_or_create_path_id(fname)
        for diff in fperm.findall('./DiffPerms/DiffPerm'):
            account = diff.findtext('AccountName')
            rights = int(diff.findtext('Rights'))
            rights_text = ', '.join(decode_rights(rights))
            allow = diff.findtext('Allow') == 'true'
            write_perm = 'Write Attributes' in rights_text
            table = 'AllowEntries' if allow else 'DenyEntries'
            cursor.execute(f'''
                INSERT INTO {table} (path_id, account, permissions, inherited_permission, write_permission)
                VALUES (?, ?, ?, ?, ?)''', (fid, account, rights_text, folder_inherited, write_perm))

    for subnode in node.findall('./FolderNodes/FolderNode'):
        parse_folder_node(subnode, folder_name)

xml_file = 'PermissionsReport.xml'
tree = ET.parse(xml_file)
root = tree.getroot()

folder_nodes = root.find('FolderNodes')
if folder_nodes is not None:
    for top_folder in folder_nodes.findall('FolderNode'):
        parse_folder_node(top_folder)

conn.commit()
conn.close()
