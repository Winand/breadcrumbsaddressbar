import ctypes, pythoncom
from ctypes import POINTER, Structure, byref
from ctypes.wintypes import DWORD, WORD, USHORT, BYTE, MSG
shell32 = ctypes.windll.shell32
ole32 = ctypes.windll.ole32


WM_DEVICECHANGE = 0x219  # Notifies an application of a change to the hardware configuration of a device or the computer.
DBT_DEVICEARRIVAL = 0x8000  # A device or piece of media has been inserted and is now available.
DBT_DEVICEREMOVECOMPLETE = 0x8004  # A device or piece of media has been removed.
DBT_DEVTYP_VOLUME = 2  # Logical volume
class DEV_BROADCAST_HDR(Structure):
    _fields_ = [
        ("dbch_size", DWORD),
        ("dbch_devicetype", DWORD),
        ("dbch_reserved", DWORD)
    ]
class DEV_BROADCAST_VOLUME(Structure):
    _fields_ = [
        ("dbcv_size", DWORD),
        ("dbcv_devicetype", DWORD),
        ("dbcv_reserved", DWORD),
        ("dbcv_unitmask", DWORD),
        ("dbcv_flags", WORD)
    ]


def parse_message(message):
    "Parse Windows message"
    return MSG.from_address(message.__int__())


def event_device_connection(message) -> tuple:
    """
    Device insert/remove message
    
    Returns: list of drive letters, True (insert) / False (remove)
    """
    if (message.message != WM_DEVICECHANGE or
        message.wParam not in (DBT_DEVICEARRIVAL, DBT_DEVICEREMOVECOMPLETE)):
        return
    devvol = DEV_BROADCAST_HDR.from_address(message.lParam)
    if devvol.dbch_devicetype == DBT_DEVTYP_VOLUME:
        mask = DEV_BROADCAST_VOLUME.from_address(message.lParam).dbcv_unitmask
        letters = [chr(65+sh) for sh in range(26) if mask>>sh&1]
        return letters, message.wParam == DBT_DEVICEARRIVAL


class SHITEMID(Structure):
    _fields_ = [
        ("cb", USHORT),
        ("abID", BYTE * 1),
    ]
class ITEMIDLIST(Structure):
    _fields_ = [
        ("mkid", SHITEMID)]
NORMALDISPLAY = 0x00000000  # Samsung Evo 850 (C:)
PARENTRELATIVEPARSING = 0x80018001  # C:
DESKTOPABSOLUTEPARSING = 0x80028000  # C:\
PARENTRELATIVEEDITING = 0x80031001  # Samsung Evo 850
DESKTOPABSOLUTEEDITING = 0x8004c000  # C:\
FILESYSPATH = 0x80058000  # C:\
URL = 0x80068000  # file:///C:/
PARENTRELATIVEFORADDRESSBAR = 0x8007c001  # C:
PARENTRELATIVE = 0x80080001  # Samsung Evo 850 (C:)


def get_path_label(path):
    "Get label for path (https://stackoverflow.com/a/29198314)"
    idlist = POINTER(ITEMIDLIST)()
    ret = shell32.SHParseDisplayName(path, 0, byref(idlist), 0, 0)
    if ret:
        raise Exception("Exception %d in SHParseDisplayName" % ret)
    # x = (BYTE * (idlist.contents.mkid.cb-2)).from_address(addressof(idlist.contents)+2)
    # print(bytes(x))
    name = ctypes.c_wchar_p()
    ret = shell32.SHGetNameFromIDList(idlist, PARENTRELATIVEEDITING,
                                      byref(name))
    if ret:
        raise Exception("Exception %d in SHGetNameFromIDList" % ret)
    return name.value
