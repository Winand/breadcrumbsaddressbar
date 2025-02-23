"""
Module provides functionality for instantiating and accessing Windows COM objects
through interfaces.

A COM interface is described using class with methods. All COM interfaces are
inherited from IUnknown interface.
An interface has @interface decorator and each COM method declaration has
@method(index=...) decorator where `index` is an index of that method in COM interface.
E.g. IUnknown::QueryInterface has index 0, AddRef - index 1, Release - index 2.

@method saves index and arguments in a __com_func__ variable of a method. Then
@interface collects all methods containing that variable into __func_table__ dict
of a class. At runtime IUnknown.__init__ creates an instance of a object
(if object pointer is not passed in arguments) and replaces all declarations
with generated methods which call methods of that object. So if __init__ is
overriden then super().__init__ should be called.

Example of a COM method declaration:
@interface
class IExample(IUnknown)
    @method(index=5)
    def Load(self, pszFileName: DT.LPCOLESTR, dwMode: DT.DWORD):
        ...
Argument type hint may be a Union. Only the first type is used for COM method
initialization. So you can use Union[c_wchar_p, str] to pass string w/o linting error.
Optionally you may raise NotImplementedError in COM method declaration so you never call
those stub methods in runtime accidentally, e.g. in case of not initializing a method
(missing @method decorator, IUnknown.__init__ not called etc.).

Alternatively COM methods can be described in __methods__ dict of a class:
    __methods__ = {
        "Method1": {'index': 1, 'args': {"hwnd": DT.HWND}},
        "Method2": {'index': 5, 'args': (HWND, INT)},
        "Method3": {'index': 6},
    }
But this is not recommended because those methods are not recognized by linter.
"""

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

def interface(cls):
    # if "clsid" not in cls.__dict__ or "iid" not in cls.__dict__:
    #     raise ValueError(f"{cls.__name__}: clsid / iid class variables not found")
    if len(cls.__bases__) != 1:
        # https://stackoverflow.com/questions/70222391/com-multiple-interface-inheritance
        raise TypeError('Multiple inheritance is not supported')
    # if cls.__bases__[0] is object:
    #     if cls.__name__ != 'IUnknown':
    #         logging.warning(f"COM interfaces should be derived from IUnknown, not {cls.__name__}")
    __func_table__ = getattr(cls.__bases__[0], '__func_table__', {}).copy()
    for member_name, member in cls.__dict__.items():
        if not isinstance(member, FunctionType):
            continue
        __com_func__ = getattr(member, '__com_func__', None)
        if not __com_func__:
            continue
        __func_table__[member_name] = __com_func__
    __methods__ = cls.__dict__.get('__methods__')
    if isinstance(__methods__, dict):
        # Collect COM methods from __methods__ dict:
        # __methods__ = {
        #     "Method1": {'index': 1, 'args': {"hwnd": DT.HWND}},
        #     "Method2": {'index': 5, 'args': (HWND, INT)},
        #     "Method3": {'index': 6},
        # }
        for member_name, info in __methods__.items():
            if member_name in __func_table__:
                logging.warning("Overriding existing method %s.%s", cls.__name__, member_name)
            args = info.get('args', ())
            if isinstance(args, dict):
                args = tuple(args.values())
            __func_table__[member_name] = {
                'index': info['index'],
                'args': WINFUNCTYPE(HRESULT, c_void_p,
                    *((get_args(i) or [i])[0] for i in args)
                )
            }
    setattr(cls, '__func_table__', __func_table__)
    return cls

def method(index):
    # https://stackoverflow.com/a/2367605
    def func_decorator(func):
        type_hints = get_type_hints(func)
        # Type of return value is not used.
        # Return type is HRESULT https://stackoverflow.com/a/20733034
        type_hints.pop('return', None)
        func.__com_func__ = {
            'index': index,
            'args': WINFUNCTYPE(HRESULT, c_void_p,
                *((get_args(i) or [i])[0] for i in type_hints.values())
            )
        }
        return func
    return func_decorator

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
    LPCOLESTR = U[c_wchar_p, str]  # https://stackoverflow.com/a/1607840
    WIN32_FIND_DATA_p = U[POINTER(WIN32_FIND_DATA), CArgObject]
    PIDLIST_ABSOLUTE = POINTER(POINTER(ITEMIDLIST))  # https://microsoft.public.win32.programmer.ui.narkive.com/p5Xl5twk/where-is-pidlist-absolute-defined


@interface
class IUnknown:
    """
    The IUnknown interface enables clients to retrieve pointers to other interfaces
    on a given object through the QueryInterface method, and to manage the existence
    of the object through the AddRef and Release methods. All other COM interfaces are
    inherited, directly or indirectly, from IUnknown.

    IUnknown https://learn.microsoft.com/en-us/windows/win32/api/unknwn/nn-unknwn-iunknown
    IUnknown (DCOM) https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-dcom/2b4db106-fb79-4a67-b45f-63654f19c54c
    IUnknown (source) https://github.com/tpn/winsdk-10/blob/9b69fd26ac0c7d0b83d378dba01080e93349c2ed/Include/10.0.14393.0/um/Unknwn.h#L108
    """
    clsid, iid, __func_table__ = None, "{00000000-0000-0000-C000-000000000046}", {}
    T = TypeVar('T', bound="IUnknown")

    def __init__(self, ptr: Optional[c_void_p]=None):
        "Creates an instance and generates methods"
        self.ptr = ptr or create_instance(self.clsid, self.iid)
        # Access COM methods from Python https://stackoverflow.com/a/49053176
        # ctypes + COM access https://stackoverflow.com/a/12638860
        vtable = cast(self.ptr, POINTER(c_void_p))
        wk = c_void_p(vtable[0])
        functions = cast(wk, POINTER(c_void_p))  # method list
        for func_name, __com_opts__ in self.__func_table__.items():
            # Variable in a loop https://www.coursera.org/learn/golang-webservices-1/discussions/threads/0i1G0HswEemBSQpvxxG8fA/replies/m_pdt1kPQqS6XbdZD6Kkiw
            win_func = __com_opts__['args'](functions[__com_opts__['index']])
            setattr(self, func_name,
                lambda *args, f=win_func: f(self.ptr, *args)
            )
    
    def query_interface(self, IID: "type[T]") -> T:
        "Helper method for QueryInterface"
        ptr = c_void_p()
        self.QueryInterface(byref(Guid(IID.iid)), byref(ptr))
        return IID(ptr)

    @method(index=0)
    def QueryInterface(self, riid: DT.REFIID, ppvObject: DT.void_pp) -> HRESULT:
        "Retrieves pointers to the supported interfaces on an object."
        raise NotImplementedError
    
    @method(index=1)
    def AddRef(self) -> HRESULT:
        "Increments the reference count for an interface pointer to a COM object"
        raise NotImplementedError

    @method(index=2)
    def Release(self) -> HRESULT:
        "Decrements the reference count for an interface on a COM object"
        raise NotImplementedError

    def __del__(self):
        if self.ptr:
            self.Release()

    def isAccessible(self):
        return bool(self.ptr)


@interface
class IShellLink(IUnknown):
    """
    Exposes methods that create, modify, and resolve Shell links.

    Shell Links https://learn.microsoft.com/en-us/windows/win32/shell/links
    IShellLinkW https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nn-shobjidl_core-ishelllinkw
    IShellLinkW (source) https://github.com/tpn/winsdk-10/blob/9b69fd26ac0c7d0b83d378dba01080e93349c2ed/Include/10.0.16299.0/um/ShObjIdl_core.h#L11527
    """
    clsid = CLSID_ShellLink = "{00021401-0000-0000-C000-000000000046}"
    iid = IID_IShellLink  = "{000214F9-0000-0000-C000-000000000046}"
    LPTSTR = WCHAR * MAX_PATH  # https://habr.com/ru/post/164193

    @method(index=3)
    def GetPath(self, pszFile: LPTSTR, cch: DT.INT, pfd: DT.WIN32_FIND_DATA_p, fFlags: DT.DWORD):
        """
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
    
    @method(index=4)
    def GetIDList(self, ppidl: DT.PIDLIST_ABSOLUTE):
        """
        Gets the list of item identifiers for the target of a Shell link object.
        """

    def get_id_list(self):
        "Helper method for GetIDList"
        idlist = POINTER(ITEMIDLIST)()
        self.GetIDList(pointer(idlist))
        return idlist


@interface
class IPersistFile(IUnknown):
    """
    Enables an object to be loaded from or saved to a disk file.

    IPersistFile https://learn.microsoft.com/en-us/windows/win32/api/objidl/nn-objidl-ipersistfile
    IPersist (source) https://github.com/tpn/winsdk-10/blob/9b69fd26ac0c7d0b83d378dba01080e93349c2ed/Include/10.0.16299.0/um/ObjIdl.h#L9140
    IPersistFile (source) https://github.com/tpn/winsdk-10/blob/9b69fd26ac0c7d0b83d378dba01080e93349c2ed/Include/10.0.16299.0/um/ObjIdl.h#L10336
    """
    clsid = CLSID_ShellLink = "{00021401-0000-0000-C000-000000000046}"
    iid = IID_IPersistFile = "{0000010b-0000-0000-C000-000000000046}"

    @method(index=5)
    def Load(self, pszFileName: DT.LPCOLESTR, dwMode: DT.DWORD):
        """
        Opens the specified file and initializes an object from the file contents
        """

    def load(self, pszFileName: str, dwMode: int=0):
        "Helper method for Load"
        buf = c_wchar_p(pszFileName)
        if self.Load(buf, dwMode):
            raise WindowsError("Load failed.")


if __name__ == '__main__':
    import os
    link = IShellLink()
    path = link.get_path(fr"{os.environ['LocalAppData']}\Microsoft\Windows\WinX\Group1\1 - Desktop.lnk")  # https://katystech.blog/windows/locking-down-the-winx-menu
    print("IShellLink::GetPath", path)
    print("IShellLink::AddRef", link.AddRef())
    print("IShellLink::AddRef", link.AddRef())
    pf = IPersistFile()
    print("IPersistFile::Load", pf.Load(fr"{os.environ['LocalAppData']}\Microsoft\Windows\WinX\Group1\1 - Desktop.lnk", 0))
    print("IPersistFile::Release", pf.Release())
