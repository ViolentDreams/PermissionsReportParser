import xml.etree.ElementTree as ET

def parse_folder_node(node):
    folder_name = node.findtext('Name')
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
        fname = fperm.findtext('Name')
        print(f"  Файл: {fname}")
        for diff in fperm.findall('./DiffPerms/DiffPerm'):
            account = diff.findtext('AccountName')
            rights = diff.findtext('Rights')
            allow = diff.findtext('Allow') == 'true'
            print(f"    Права на файл - {account}: {rights}, Allow: {allow}")

    # Рекурсивный вызов
    for subnode in node.findall('./FolderNodes/FolderNode'):
        parse_folder_node(subnode)

# Парсинг XML-файла
xml_file = 'PermissionsReport.xml'
tree = ET.parse(xml_file)
root = tree.getroot()

for top_folder in root.find('FolderNodes').findall('FolderNode'):
    parse_folder_node(top_folder)
