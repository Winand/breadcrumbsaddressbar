import ctypes, ctypes.wintypes as wintypes

WM_DEVICECHANGE = 0x219  # Notifies an application of a change to the hardware configuration of a device or the computer.
DBT_DEVICEARRIVAL = 0x8000  # A device or piece of media has been inserted and is now available.
DBT_DEVICEREMOVECOMPLETE = 0x8004  # A device or piece of media has been removed.
class DEV_BROADCAST_HDR(ctypes.Structure):
  _fields_ = [
    ("dbch_size", wintypes.DWORD),
    ("dbch_devicetype", wintypes.DWORD),
    ("dbch_reserved", wintypes.DWORD)
  ]
DBT_DEVTYP_VOLUME = 2  # Logical volume
class DEV_BROADCAST_VOLUME(ctypes.Structure):
  _fields_ = [
    ("dbcv_size", wintypes.DWORD),
    ("dbcv_devicetype", wintypes.DWORD),
    ("dbcv_reserved", wintypes.DWORD),
    ("dbcv_unitmask", wintypes.DWORD),
    ("dbcv_flags", wintypes.WORD)
  ]


def parse_message(message):
    "Parse Windows message"
    return wintypes.MSG.from_address(message.__int__())


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
