import logging
from ctypes import (HRESULT, POINTER, WINFUNCTYPE, Structure, byref, c_short,
                    c_ubyte, c_uint, c_void_p, c_wchar_p, cast,
                    create_unicode_buffer, oledll, pointer)
from ctypes.wintypes import BYTE, DWORD, INT, MAX_PATH, USHORT, WCHAR, WORD
from types import FunctionType
from typing import Optional, TypeVar
from typing import Union as U
from typing import get_args, get_type_hints

ole32 = oledll.ole32
CLSCTX_INPROC_SERVER = 0x1

ole32.CoInitialize(None)  # instead of `import pythoncom`

################################ ENUMERATIONS #################################
class SLGP:  # SLGP_FLAGS https://github.com/tpn/winsdk-10/blob/9b69fd26ac0c7d0b83d378dba01080e93349c2ed/Include/10.0.16299.0/um/ShObjIdl_core.h#L11230
    SHORTPATH = 1
    UNCPRIORITY = 2
    RAWPATH = 4
    RELATIVEPRIORITY = 8

################################# STRUCTURES ##################################
class Guid(Structure):
    _fields_ = [("Data1", c_uint),
                ("Data2", c_short),
                ("Data3", c_short),
                ("Data4", c_ubyte*8)]
                
    def __init__(self, name):
        ole32.CLSIDFromString(name, byref(self))

class FILETIME(Structure):
    _fields_ = [
        ("dwLowDateTime", DWORD),
        ("dwHighDateTime", DWORD),
    ]

class WIN32_FIND_DATA(Structure):
    _fields_ = [
        ("dwFileAttributes", DWORD),
        ("ftCreationTime", FILETIME),
        ("ftLastAccessTime", FILETIME),
        ("ftLastWriteTime", FILETIME),
        ("nFileSizeHigh", DWORD),
        ("nFileSizeLow", DWORD),
        ("dwReserved0", DWORD),
        ("dwReserved1", DWORD),
        ("cFileName", WCHAR * MAX_PATH),
        ("cAlternateFileName", WCHAR * 14),
        ("dwFileType", DWORD),  # Obsolete. Do not use.
        ("dwCreatorType", DWORD),  # Obsolete. Do not use
        ("wFinderFlags", WORD),  # Obsolete. Do not use
    ]

class SHITEMID(Structure):
    _fields_ = [
        ("cb", USHORT),
        ("abID", BYTE * 1),
    ]
class ITEMIDLIST(Structure):
    _fields_ = [
        ("mkid", SHITEMID)]
###############################################################################

def gen_method(ptr, method_index, *arg_types):
    # https://stackoverflow.com/a/49053176
    # https://stackoverflow.com/a/12638860
    vtable = cast(ptr, POINTER(c_void_p))
    wk = c_void_p(vtable[0])
    function = cast(wk, POINTER(c_void_p))
    WFC = WINFUNCTYPE(HRESULT, c_void_p, *arg_types)
    METH = WFC(function[method_index])
    return lambda *args: METH(ptr, *args)

def create_instance(clsid, iid):
    ptr = c_void_p()
    ole32.CoCreateInstance(byref(Guid(clsid)), 0, CLSCTX_INPROC_SERVER,
                           byref(Guid(iid)), byref(ptr))
    return ptr


CArgObject = type(byref(c_void_p()))

class DT:
    "Additional data types for type hints"
    DWORD = U[DWORD, int]
    INT = U[INT, int]
    REFIID = U[POINTER(Guid), CArgObject]
    void_pp = U[POINTER(c_void_p), CArgObject]
    LPCOLESTR = c_wchar_p  # https://stackoverflow.com/a/1607840
    WIN32_FIND_DATA_p = U[POINTER(WIN32_FIND_DATA), CArgObject]
    PIDLIST_ABSOLUTE = POINTER(POINTER(ITEMIDLIST))  # https://microsoft.public.win32.programmer.ui.narkive.com/p5Xl5twk/where-is-pidlist-absolute-defined


class IUnknown:
    """
    IUnknown https://github.com/tpn/winsdk-10/blob/9b69fd26ac0c7d0b83d378dba01080e93349c2ed/Include/10.0.14393.0/um/Unknwn.h#L108
    """
    clsid, iid = None, None
    _methods_ = {}
    T = TypeVar('T', bound="IUnknown")

    def __init__(self, ptr: Optional[c_void_p]=None):
        "Creates an instance and generates methods"
        self.ptr = ptr or create_instance(self.clsid, self.iid)
        self.__generate_methods_from_class(IUnknown)
        self.__generate_methods_from_class(self.__class__)
        self.__generate_methods_from_dict(self._methods_)
    
    def query_interface(self, IID: type[T]) -> T:
        "Helper method for QueryInterface"
        ptr = c_void_p()
        self.QueryInterface(byref(Guid(IID.iid)), byref(ptr))
        return IID(ptr)

    def QueryInterface(self, riid: DT.REFIID, ppvObject: DT.void_pp):
        "index: 0"

    def Release(self):
        "index: 2"

    def __del__(self):
        if self.ptr:
            self.Release()

    def isAccessible(self):
        return bool(self.ptr)

    def __generate_methods_from_dict(self, methods: dict):
        """
        Methods are described in a `_methods_` dict of a class:
        _methods_ = {
            "Method1": {'index': 1, 'args': {"hwnd": DT.HWND}},
            "Method2": {'index': 5, 'args': (HWND, INT)},
            "Method3": {'index': 6},
        }
        """
        for name, info in methods.items():
            if hasattr(self, name):
                logging.warning("Overriding existing method %s", name)
            args = info.get('args', ())
            if isinstance(args, dict):
                args = tuple(args.values())
            args = tuple((get_args(i) or [i])[0] for i in args)
            setattr(self, name, gen_method(self.ptr, info['index'], *args))

    def __generate_methods_from_class(self, cls):
        """
        Method argument types are specified in type hints of a Python method.
        If a type hint is a Union then its first element is used.
        Method index is specified on the 1st line of a doc string like this "index: 1"
        """
        for func_name, func in cls.__dict__.items():
            if not isinstance(func, FunctionType) or not func.__doc__:
                continue
            check_idx = func.__doc__.partition('\n')[0].split(":")
            if len(check_idx) != 2:
                continue
            s_index, index = (i.strip() for i in check_idx)
            if s_index.lower() != "index" or not index.isdecimal():
                raise ValueError("Specify `index:<int>` on the first line of doc string")
            setattr(self, func_name,
                gen_method(
                    self.ptr, int(index),
                    *((get_args(i) or [i])[0] for i in get_type_hints(func).values())
                )
            )


class IShellLink(IUnknown):
    """
    https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nn-shobjidl_core-ishelllinkw
    IShellLinkW https://github.com/tpn/winsdk-10/blob/9b69fd26ac0c7d0b83d378dba01080e93349c2ed/Include/10.0.16299.0/um/ShObjIdl_core.h#L11527
    """
    clsid = CLSID_ShellLink = "{00021401-0000-0000-C000-000000000046}"
    iid = IID_IShellLink  = "{000214F9-0000-0000-C000-000000000046}"
    LPTSTR = WCHAR * MAX_PATH  # https://habr.com/ru/post/164193

    def GetPath(self, pszFile: LPTSTR, cch: DT.INT, pfd: DT.WIN32_FIND_DATA_p, fFlags: DT.DWORD):
        """ index: 3
        Gets the path and file name of the target of a Shell link object.
        """
    
    def get_path(self, path: Optional[str]) -> Optional[str]:
        "Helper method for GetPath"
        if path:
            pf = self.query_interface(IPersistFile)
            pf.load(path)
        # create_unicode_buffer is used instead of c_wchar_p for mutable strings
        buf = create_unicode_buffer(MAX_PATH)
        fd = WIN32_FIND_DATA()
        if not self.GetPath(buf, len(buf), byref(fd), SLGP.UNCPRIORITY):
            return buf.value
    
    def GetIDList(self, ppidl: DT.PIDLIST_ABSOLUTE):
        """ index: 4
        Gets the list of item identifiers for the target of a Shell link object.
        """

    def get_id_list(self):
        "Helper method for GetIDList"
        idlist = POINTER(ITEMIDLIST)()
        self.GetIDList(pointer(idlist))
        return idlist


class IPersistFile(IUnknown):
    """
    https://learn.microsoft.com/en-us/windows/win32/api/objidl/nn-objidl-ipersistfile
    IPersist https://github.com/tpn/winsdk-10/blob/9b69fd26ac0c7d0b83d378dba01080e93349c2ed/Include/10.0.16299.0/um/ObjIdl.h#L9140
    IPersistFile https://github.com/tpn/winsdk-10/blob/9b69fd26ac0c7d0b83d378dba01080e93349c2ed/Include/10.0.16299.0/um/ObjIdl.h#L10336
    """
    clsid = CLSID_ShellLink = "{00021401-0000-0000-C000-000000000046}"
    iid = IID_IPersistFile = "{0000010b-0000-0000-C000-000000000046}"

    def __init__(self, ptr: c_void_p):
        super().__init__(ptr)

    def Load(self, pszFileName: DT.LPCOLESTR, dwMode: DT.DWORD):
        "index: 5"

    def load(self, pszFileName: str, dwMode: int=0):
        "Helper method for Load"
        buf = c_wchar_p(pszFileName)
        if self.Load(buf, dwMode):
            raise WindowsError("Load failed.")
