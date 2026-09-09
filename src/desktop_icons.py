"""读取 Windows 桌面图标的位置，并限定本插件只处理桌面项目。"""
import ctypes
import os
from ctypes import wintypes


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

CSIDL_DESKTOPDIRECTORY = 0x0010
CSIDL_COMMON_DESKTOPDIRECTORY = 0x0019
MAX_PATH = 260
LVM_FIRST = 0x1000
LVM_FINDITEMW = LVM_FIRST + 83
LVM_GETITEMPOSITION = LVM_FIRST + 16
LVFI_STRING = 0x0002
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class LVFINDINFOW(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint),
        ("psz", ctypes.c_void_p),
        ("lParam", ctypes.c_ssize_t),
        ("pt", POINT),
        ("vkDirection", ctypes.c_uint),
    ]


def _known_folder(csidl):
    buffer = ctypes.create_unicode_buffer(MAX_PATH)
    if ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buffer) == 0:
        return os.path.normcase(os.path.realpath(buffer.value))
    return None


def desktop_directories():
    """返回当前用户和公共桌面目录。"""
    return {path for path in (_known_folder(CSIDL_DESKTOPDIRECTORY),
                              _known_folder(CSIDL_COMMON_DESKTOPDIRECTORY)) if path}


def is_desktop_item(path):
    """仅允许桌面根目录中的文件、文件夹或快捷方式。"""
    if not path:
        return False
    parent = os.path.normcase(os.path.realpath(os.path.dirname(path)))
    return parent in desktop_directories()


def _desktop_list_view():
    """找到承载桌面图标的 SysListView32 句柄。"""
    progman = user32.FindWindowW("Progman", None)
    def_view = user32.FindWindowExW(progman, None, "SHELLDLL_DefView", None)

    if not def_view:
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        found = wintypes.HWND()

        def callback(hwnd, _):
            nonlocal found
            candidate = user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
            if candidate:
                found = candidate
                return False
            return True

        user32.EnumWindows(callback_type(callback), 0)
        def_view = found

    if not def_view:
        return None
    return user32.FindWindowExW(def_view, None, "SysListView32", "FolderView") or None


def _get_desktop_icon_center_uia(path):
    """用 UI Automation 读取图标控件边界框，优先于旧式 ListView 消息。"""
    try:
        from pywinauto import Desktop
        desktop = Desktop(backend="uia").window(class_name="Progman")
        names = [os.path.basename(path)]
        stem, ext = os.path.splitext(names[0])
        if ext:
            names.append(stem)
        wanted = {name.casefold() for name in names}

        for item in desktop.descendants(control_type="ListItem"):
            if item.element_info.name.casefold() in wanted:
                rect = item.rectangle()
                if rect.width() and rect.height():
                    return ((rect.left + rect.right) // 2,
                            (rect.top + rect.bottom) // 2)
    except Exception:
        # UI Automation 可能暂时不可用；调用方会尝试 ListView 后备方案。
        pass
    return None


def get_desktop_icon_position(path):
    """返回 ``((x, y), source)``；无法解析时返回 None。

    ListView 位于 Explorer 进程中，因而需在该进程分配内存后使用其消息接口。
    """
    if not is_desktop_item(path):
        return None
    uia_center = _get_desktop_icon_center_uia(path)
    if uia_center:
        return uia_center, "UI Automation"
    list_view = _desktop_list_view()
    if not list_view:
        return None

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(list_view, ctypes.byref(pid))
    process = kernel32.OpenProcess(PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE,
                                  False, pid.value)
    if not process:
        return None

    remote_text = remote_find = remote_point = None
    try:
        # Explorer 常显示完整文件名；若启用了“隐藏已知扩展名”，再尝试不带扩展名的版本。
        names = [os.path.basename(path)]
        stem, ext = os.path.splitext(names[0])
        if ext:
            names.append(stem)

        for name in names:
            raw_name = ctypes.create_unicode_buffer(name)
            remote_text = kernel32.VirtualAllocEx(process, None, ctypes.sizeof(raw_name),
                                                   MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
            remote_find = kernel32.VirtualAllocEx(process, None, ctypes.sizeof(LVFINDINFOW),
                                                   MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
            remote_point = kernel32.VirtualAllocEx(process, None, ctypes.sizeof(POINT),
                                                    MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
            if not all((remote_text, remote_find, remote_point)):
                return None
            written = ctypes.c_size_t()
            kernel32.WriteProcessMemory(process, remote_text, ctypes.byref(raw_name),
                                        ctypes.sizeof(raw_name), ctypes.byref(written))
            find = LVFINDINFOW(LVFI_STRING, remote_text, 0, POINT(), 0)
            kernel32.WriteProcessMemory(process, remote_find, ctypes.byref(find),
                                        ctypes.sizeof(find), ctypes.byref(written))
            item = user32.SendMessageW(list_view, LVM_FINDITEMW, -1, remote_find)
            if item != -1:
                if user32.SendMessageW(list_view, LVM_GETITEMPOSITION, item, remote_point):
                    point = POINT()
                    read = ctypes.c_size_t()
                    kernel32.ReadProcessMemory(process, remote_point, ctypes.byref(point),
                                                ctypes.sizeof(point), ctypes.byref(read))
                    screen_point = POINT(point.x, point.y)
                    user32.ClientToScreen(list_view, ctypes.byref(screen_point))
                    # 桌面图标格通常约 96×96；偏向标签上方的图标视觉中心。
                    return (screen_point.x + 48, screen_point.y + 38), "Explorer ListView"
            for address in (remote_text, remote_find, remote_point):
                kernel32.VirtualFreeEx(process, address, 0, MEM_RELEASE)
            remote_text = remote_find = remote_point = None
    finally:
        for address in (remote_text, remote_find, remote_point):
            if address:
                kernel32.VirtualFreeEx(process, address, 0, MEM_RELEASE)
        kernel32.CloseHandle(process)
    return None


def get_desktop_icon_center(path):
    """兼容入口：只返回桌面图标的屏幕中心坐标。"""
    result = get_desktop_icon_position(path)
    return result[0] if result else None
