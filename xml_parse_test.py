import xml.etree.ElementTree as ET
import os

def parse_folder_node(node, parent_path=""):
    folder_name_raw = node.findtext('Name')
    folder_name = os.path.join(parent_path, folder_name_raw) if parent_path else folder_name_raw
    folder_inherited = node.findtext('IsInherited') == 'true'

    print(f"Папка: {folder_name}, Наследование: {folder_inherited}")

    # Права на папку
    for perm in node.findall('./FolderPermissions/FolderPermission'):
        account = perm.findtext('./PrincipalDetails/AccountName')
        rights = perm.findtext('Rights')
        allow = perm.findtext('Allow') == 'true'
        print(f"  Права на папку - {account}: {rights}, Allow: {allow}")

    # Права на файлы
    for fperm in node.findall('./FilePermissions/FilePermission'):
        fname_raw = fperm.findtext('Name')
        fname = os.path.join(folder_name, fname_raw)
        print(f"  Файл: {fname}")
        for diff in fperm.findall('./DiffPerms/DiffPerm'):
            account = diff.findtext('AccountName')
            rights = diff.findtext('Rights')
            allow = diff.findtext('Allow') == 'true'
            print(f"    Права на файл - {account}: {rights}, Allow: {allow}")

    # Рекурсивный вызов
    for subnode in node.findall('./FolderNodes/FolderNode'):
        parse_folder_node(subnode, folder_name)

# Парсинг XML-файла
xml_file = 'PermissionsReport.xml'
tree = ET.parse(xml_file)
root = tree.getroot()

folder_nodes = root.find('FolderNodes')
if folder_nodes is not None:
    for top_folder in folder_nodes.findall('FolderNode'):
        parse_folder_node(top_folder)
