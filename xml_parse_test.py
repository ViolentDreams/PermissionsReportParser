import xml.etree.ElementTree as ET
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

def parse_folder_node(node, parent_path=""):
    folder_name_raw = node.findtext('Name')
    folder_name = os.path.join(parent_path, folder_name_raw) if parent_path else folder_name_raw
    folder_inherited = node.findtext('IsInherited') == 'true'

    print(f"Папка: {folder_name}, Наследование: {folder_inherited}")

    for perm in node.findall('./FolderPermissions/FolderPermission'):
        account = perm.findtext('./PrincipalDetails/AccountName')
        rights = int(perm.findtext('Rights'))
        rights_text = decode_rights(rights)
        allow = perm.findtext('Allow') == 'true'
        print(f"  Права на папку - {account}: {rights} ({', '.join(rights_text)}), Allow: {allow}")

    for fperm in node.findall('./FilePermissions/FilePermission'):
        fname_raw = fperm.findtext('Name')
        fname = os.path.join(folder_name, fname_raw)
        print(f"  Файл: {fname}")
        for diff in fperm.findall('./DiffPerms/DiffPerm'):
            account = diff.findtext('AccountName')
            rights = int(diff.findtext('Rights'))
            rights_text = decode_rights(rights)
            allow = diff.findtext('Allow') == 'true'
            print(f"    Права на файл - {account}: {rights} ({', '.join(rights_text)}), Allow: {allow}")

    for subnode in node.findall('./FolderNodes/FolderNode'):
        parse_folder_node(subnode, folder_name)

xml_file = 'PermissionsReport.xml'
tree = ET.parse(xml_file)
root = tree.getroot()

folder_nodes = root.find('FolderNodes')
if folder_nodes is not None:
    for top_folder in folder_nodes.findall('FolderNode'):
        parse_folder_node(top_folder)