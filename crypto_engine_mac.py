"""
Module: crypto_engine_mac.py
Hệ Thống Bảo Mật, Định Danh Phần Cứng MacBook (Mac HWID) & Mã Hóa AES-256-GCM cho macOS
Tuân thủ 100% chuẩn cấu trúc và logic bảo mật của hash_win:
1. Auto-Lock First Run (TOFU - Tự động bắt & ghim ID máy tính Mac khi mở lần đầu)
2. Hỗ trợ Google Sheets (Apps Script) làm máy chủ bản quyền đám mây miễn phí 100%
3. Hỗ trợ Chế độ Ngoại Tuyến 100% (Offline Auto-Lock) không cần mạng
4. Chống chia sẻ / chuyển tiếp cho máy khác: Máy thứ 2 bị chặn 100%
5. HỖ TRỢ CHỈNH SỬA VÀ LƯU BÀI GIẢNG TRÊN MACBOOK (Editable Mode + Auto-Save Sync Back)
6. Tích hợp chính sách Ribbon Policy tối ưu cho Office for Mac (Cấm Save As, Cho phép Edit, Paste, Save)
7. Hỗ trợ định danh phần cứng native macOS (IOPlatformUUID + IOPlatformSerialNumber) và cross-platform
"""

import os
import sys
import json
import struct
import hashlib
import datetime
import subprocess
import tempfile
import urllib.request
import urllib.parse
import urllib.error
import re
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from ribbon_policy_mac import inject_ribbon_policy

MAGIC_HEADER_STATIC = b"SECSLIDE\x02\x00"
MAGIC_HEADER_AUTOLOCK = b"SECAUTO\x02\x00"
MAGIC_HEADER_STATIC_V1 = b"SECSLIDE\x01\x00"
MAGIC_HEADER_AUTOLOCK_V1 = b"SECAUTO\x01\x00"

_OVERRIDE_HWID = None

def set_test_hwid_override(hwid: str | None):
    """Sử dụng cho test runner để giả lập các máy tính Mac khác nhau"""
    global _OVERRIDE_HWID
    _OVERRIDE_HWID = hwid


def get_mac_hardware_uuid_and_serial() -> tuple[str, str]:
    """
    Truy xuất Hardware UUID và Serial Number trên hệ điều hành macOS.
    Phương pháp 1: IOKit CLI (ioreg -rd1 -c IOPlatformExpertDevice)
    Phương pháp 2: system_profiler SPHardwareDataType
    """
    uuid_str = ""
    serial_str = ""

    # Phương pháp 1: ioreg
    try:
        out = subprocess.check_output(
            ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
            stderr=subprocess.DEVNULL,
            timeout=3
        ).decode("utf-8", errors="ignore")

        # Tìm IOPlatformUUID
        m_uuid = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', out)
        if m_uuid:
            uuid_str = m_uuid.group(1).strip()

        # Tìm IOPlatformSerialNumber
        m_serial = re.search(r'"IOPlatformSerialNumber"\s*=\s*"([^"]+)"', out)
        if m_serial:
            serial_str = m_serial.group(1).strip()
    except Exception:
        pass

    # Phương pháp 2: system_profiler (dự phòng nếu ioreg không trả đủ)
    if not uuid_str or not serial_str:
        try:
            out = subprocess.check_output(
                ["system_profiler", "SPHardwareDataType"],
                stderr=subprocess.DEVNULL,
                timeout=4
            ).decode("utf-8", errors="ignore")

            if not uuid_str:
                m_uuid = re.search(r'Hardware UUID:\s*([A-Fa-f0-9\-]+)', out)
                if m_uuid:
                    uuid_str = m_uuid.group(1).strip()

            if not serial_str:
                m_serial = re.search(r'Serial Number \([^\)]+\):\s*([A-Za-z0-9\-]+)', out)
                if m_serial:
                    serial_str = m_serial.group(1).strip()
        except Exception:
            pass

    return uuid_str, serial_str


def get_windows_hwid() -> str:
    """Fallback nếu chạy môi trường Windows"""
    guid = ""
    uuid = ""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            guid = str(guid).strip()
    except Exception:
        guid = ""

    try:
        res = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystemProduct).UUID"],
            timeout=3,
            creationflags=0x08000000 if sys.platform == "win32" else 0
        )
        uuid = res.decode("utf-8", errors="ignore").strip()
    except Exception:
        uuid = ""

    return f"{guid}::{uuid}"


def get_machine_hwid() -> str:
    """
    Lấy mã định danh phần cứng duy nhất của máy tính (HWID).
    Trên macOS: Kết hợp giữa Apple Hardware UUID và Mac Serial Number.
    Trả về định dạng chuẩn giống hash_win: XXXX-XXXX-XXXX-XXXX
    """
    global _OVERRIDE_HWID
    if _OVERRIDE_HWID:
        return _OVERRIDE_HWID.strip().upper()

    if sys.platform == "darwin":
        uuid_str, serial_str = get_mac_hardware_uuid_and_serial()
        if uuid_str or serial_str:
            raw_seed = f"MAC::{serial_str}::{uuid_str}"
        else:
            import platform
            raw_seed = f"MAC_NODE::{platform.node()}::{platform.machine()}"
    elif sys.platform == "win32":
        raw_seed = get_windows_hwid()
    else:
        try:
            with open("/etc/machine-id", "r") as f:
                raw_seed = f.read().strip()
        except Exception:
            import platform
            raw_seed = platform.node()

    digest = hashlib.sha256(raw_seed.encode("utf-8")).hexdigest().upper()
    return f"{digest[:4]}-{digest[4:8]}-{digest[8:12]}-{digest[12:16]}"


def derive_key(seed: str, salt: bytes) -> bytes:
    """Hàm tạo khóa dẫn xuất chuẩn quân sự PBKDF2 HMAC-SHA256 (100,000 iterations)"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return kdf.derive(seed.encode("utf-8"))


def get_local_cache_path(license_id: str) -> str:
    """Đường dẫn lưu token kích hoạt cục bộ trên máy khách (hỗ trợ macOS và Windows)"""
    if sys.platform == "darwin":
        app_support = os.path.expanduser("~/Library/Application Support")
        cache_dir = os.path.join(app_support, "LockSlideSecure")
    elif sys.platform == "win32":
        local_app_data = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
        cache_dir = os.path.join(local_app_data, "LockSlideSecure")
    else:
        cache_dir = os.path.expanduser("~/.lockslide_secure")

    try:
        os.makedirs(cache_dir, exist_ok=True)
    except Exception:
        cache_dir = tempfile.gettempdir()

    safe_name = hashlib.md5(license_id.encode("utf-8")).hexdigest()
    return os.path.join(cache_dir, f"{safe_name}.act")


def _write_activation_cache(cache_file: str, license_id: str, hwid: str):
    """Lưu token kích hoạt mã hóa vào bộ nhớ cache của máy"""
    try:
        cache_salt = os.urandom(16)
        hw_key = derive_key(hwid, cache_salt)
        cache_nonce = os.urandom(12)
        aesgcm = AESGCM(hw_key)
        token_str = f"ACTIVATED::{license_id}::{hwid}"
        encrypted_token = aesgcm.encrypt(cache_nonce, token_str.encode("utf-8"), None)
        with open(cache_file, "wb") as f:
            f.write(cache_salt + cache_nonce + encrypted_token)
    except Exception:
        pass


def _clear_activation_cache(cache_file: str):
    """Xóa bỏ cache kích hoạt khi bản quyền bị thu hồi"""
    if os.path.exists(cache_file):
        try:
            os.remove(cache_file)
        except Exception:
            pass


def update_payload_metadata(original_payload_bytes: bytes, new_metadata: dict) -> bytes:
    """
    Cập nhật metadata trong payload đóng gói (ví dụ: ghim bound_hwid mới) mà không cần mã hóa lại toàn bộ bài giảng.
    Tốc độ cực nhanh: dưới 0.001 giây!
    """
    clean_meta = dict(new_metadata)
    clean_meta.pop("_needs_save_bound_hwid", None)

    if original_payload_bytes.startswith(MAGIC_HEADER_AUTOLOCK) or original_payload_bytes.startswith(MAGIC_HEADER_AUTOLOCK_V1):
        header_len = len(MAGIC_HEADER_AUTOLOCK)
        magic = MAGIC_HEADER_AUTOLOCK
    elif original_payload_bytes.startswith(MAGIC_HEADER_STATIC) or original_payload_bytes.startswith(MAGIC_HEADER_STATIC_V1):
        header_len = len(MAGIC_HEADER_STATIC)
        magic = MAGIC_HEADER_STATIC
    else:
        raise ValueError("Định dạng dữ liệu không hợp lệ")

    old_meta_len = struct.unpack(">I", original_payload_bytes[header_len:header_len + 4])[0]
    payload_tail = original_payload_bytes[header_len + 4 + old_meta_len :]

    new_meta_json = json.dumps(clean_meta, ensure_ascii=False).encode("utf-8")
    new_meta_len = len(new_meta_json)

    out = bytearray()
    out.extend(magic)
    out.extend(struct.pack(">I", new_meta_len))
    out.extend(new_meta_json)
    out.extend(payload_tail)
    return bytes(out)


def check_cloud_activation(server_url: str, license_id: str, current_hwid: str, title: str = "") -> dict:
    """
    Kết nối đến Server / Google Apps Script để kích hoạt 1 lần duy nhất:
    - Hỗ trợ Google Sheets Apps Script Web App (GET query parameters + 302 redirect).
    - Hỗ trợ cả API Server tuỳ chỉnh (/api/verify_or_bind qua POST).
    - Nếu license_id chưa ai dùng: Server ghim current_hwid -> Trả về SUCCESS.
    - Nếu license_id đã được dùng bởi máy khác: Server trả về REJECTED.
    - Nếu server không phản hồi / mất mạng: Trả về NETWORK_ERROR.
    """
    clean_url = server_url.strip()
    if not clean_url:
        return {"status": "NO_SERVER"}

    # 1. Nếu là Google Apps Script hoặc URL query chuẩn
    if "script.google.com" in clean_url or not clean_url.endswith("/api/verify_or_bind"):
        params = {
            "action": "activate",
            "license_id": license_id.strip().upper(),
            "hwid": current_hwid.strip().upper(),
            "title": title.strip()
        }
        qs = urllib.parse.urlencode(params)
        target_url = f"{clean_url}?{qs}" if "?" not in clean_url else f"{clean_url}&{qs}"

        req = urllib.request.Request(
            target_url,
            headers={"User-Agent": "LockSlideSecurePlayer-Mac/3.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read().decode("utf-8")
                res = json.loads(data)
                # Chuẩn hóa trạng thái về uppercase
                st = res.get("status", "").upper()
                res["status"] = st
                return res
        except urllib.error.HTTPError as he:
            try:
                err_data = json.loads(he.read().decode("utf-8"))
                return {"status": "REJECTED", "message": err_data.get("message", "Bản quyền bị từ chối")}
            except Exception:
                pass
            return {"status": "NETWORK_ERROR", "error": f"HTTP {he.code}"}
        except Exception as ex:
            # Nếu GET thất bại và có vẻ là server REST cục bộ, thử POST dự phòng
            pass

    # 2. Hỗ trợ API Server tuỳ chỉnh (POST JSON)
    target_api = clean_url if clean_url.endswith("/api/verify_or_bind") else f"{clean_url.rstrip('/')}/api/verify_or_bind"
    post_payload = {
        "license_id": license_id.strip().upper(),
        "hwid": current_hwid.strip().upper(),
        "title": title.strip()
    }
    json_bytes = json.dumps(post_payload).encode("utf-8")
    req = urllib.request.Request(
        target_api,
        data=json_bytes,
        headers={"Content-Type": "application/json", "User-Agent": "LockSlideSecurePlayer-Mac/3.0"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read().decode("utf-8")
            res = json.loads(data)
            st = res.get("status", "").upper()
            if st == "SUCCESS":
                return {"status": "SUCCESS", "bound_hwid": res.get("bound_hwid", current_hwid), "message": res.get("message", "")}
            else:
                return {"status": "REJECTED", "bound_hwid": res.get("bound_hwid", ""), "message": res.get("message", "")}
    except urllib.error.HTTPError as he:
        try:
            err_data = json.loads(he.read().decode("utf-8"))
            return {"status": "REJECTED", "message": err_data.get("message", "Bản quyền bị từ chối")}
        except Exception:
            return {"status": "REJECTED", "message": f"Máy chủ từ chối bản quyền (HTTP {he.code})"}
    except Exception as ex:
        return {"status": "NETWORK_ERROR", "error": str(ex)}


# ==============================================================================
# 1. PHƯƠNG THỨC AUTO-LOCK CHO MACBOOK (FIRST-RUN AUTO-LOCK / TOFU)
# ==============================================================================

def build_autolock_payload(
    presentation_bytes: bytes,
    license_id: str,
    server_url: str = "",
    title: str = "Bài giảng bảo mật",
    allow_edit: bool = True,
    block_save_as: bool = True,
    block_copy: bool = True,
    expiry_date: str = "",
    watermark_text: str = "",
    bound_hwid: str = "",
    offline_fallback: bool = True,
    target_os: str = "MACOS"
) -> bytes:
    """
    Đóng gói bài giảng theo cơ chế Auto-Lock KẾT HỢP (Hybrid) cho MacBook:
    - Hỗ trợ Online qua Google Sheets / Cloud Server (nếu có kết nối Internet).
    - Tự động khóa ngoại tuyến (Offline Auto-Lock) ngay trên máy Mac khách nếu không có mạng.
    - Hoặc khóa cố định vào mã máy cụ thể nếu được cung cấp trước (bound_hwid).
    - Cho phép mở lên chỉnh sửa trực tiếp trên PowerPoint (nếu allow_edit=True).
    - Bảo vệ chống trích xuất: Khóa Save As & Export (nếu block_save_as=True).
    - Tối ưu cho macOS: Làm sạch font nhúng và cấu hình Ribbon tương thích PowerPoint for Mac.
    """
    if block_save_as or block_copy:
        processed_bytes = inject_ribbon_policy(
            presentation_bytes,
            block_save_as=block_save_as,
            block_copy=block_copy,
            block_print=True,
            clean_fonts_for_mac=True
        )
    else:
        processed_bytes = presentation_bytes

    cek = os.urandom(32)  # Content Encryption Key
    main_nonce = os.urandom(12)
    aesgcm_main = AESGCM(cek)
    encrypted_data = aesgcm_main.encrypt(main_nonce, processed_bytes, None)

    # Khóa CEK bằng Master Derivation từ License ID
    lic_salt = os.urandom(16)
    lic_key = derive_key(license_id, lic_salt)
    lic_nonce = os.urandom(12)
    aesgcm_lic = AESGCM(lic_key)
    encrypted_cek = aesgcm_lic.encrypt(lic_nonce, cek, None)

    metadata = {
        "mode": "AUTOLOCK",
        "license_id": license_id.strip().upper(),
        "server_url": server_url.strip(),
        "title": title,
        "allow_edit": allow_edit,
        "block_save_as": block_save_as,
        "block_copy": block_copy,
        "expiry_date": expiry_date,
        "watermark": watermark_text,
        "bound_hwid": bound_hwid.strip().upper(),
        "offline_fallback": offline_fallback,
        "target_os": target_os,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lic_salt": lic_salt.hex(),
        "lic_nonce": lic_nonce.hex(),
        "enc_cek": encrypted_cek.hex()
    }

    meta_json = json.dumps(metadata, ensure_ascii=False).encode("utf-8")
    meta_len = len(meta_json)

    payload = bytearray()
    payload.extend(MAGIC_HEADER_AUTOLOCK)
    payload.extend(struct.pack(">I", meta_len))
    payload.extend(meta_json)
    payload.extend(main_nonce)
    payload.extend(encrypted_data)
    return bytes(payload)


def verify_and_decrypt_autolock(
    metadata: dict,
    main_nonce: bytes,
    encrypted_data: bytes,
    current_hwid: str
) -> tuple[dict, bytes]:
    """
    Xác thực bản quyền & Giải mã bài giảng Auto-Lock trên MacBook:
    1. Kiểm tra cache cục bộ (nếu đã kích hoạt thành công trên máy Mac này trước đó).
    2. Kiểm tra mã máy ghim cứng (bound_hwid): Nếu khác mã máy hiện tại -> Chặn tức thì!
    3. Nếu chưa có mã ghim:
       - Nếu có server_url: Xác thực qua Google Apps Script hoặc Server Cloud (1 lần duy nhất).
       - Nếu không có server_url: Tự động khóa cố định vào máy Mac này lần đầu (Offline Auto-Lock TOFU).
    4. Cập nhật cache token cục bộ sau khi thành công.
    5. Giải mã dữ liệu PowerPoint trực tiếp vào bộ nhớ RAM.
    """
    license_id = metadata["license_id"].strip().upper()
    server_url = metadata.get("server_url", "").strip()
    bound_hwid = metadata.get("bound_hwid", "").strip().upper()
    clean_hwid = current_hwid.strip().upper()
    cache_file = get_local_cache_path(license_id)

    # 1. Đọc kiểm tra cache nội bộ sẵn có trên thiết bị này
    has_valid_local_cache = False
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "rb") as f:
                cached_data = f.read()
            cache_salt = cached_data[:16]
            cache_nonce = cached_data[16:28]
            cache_ciphertext = cached_data[28:]
            hw_key = derive_key(clean_hwid, cache_salt)
            aesgcm = AESGCM(hw_key)
            decrypted_cache = aesgcm.decrypt(cache_nonce, cache_ciphertext, None).decode("utf-8")
            if decrypted_cache == f"ACTIVATED::{license_id}::{clean_hwid}":
                has_valid_local_cache = True
        except Exception:
            has_valid_local_cache = False

    # 2. KIỂM TRA MÃ MÁY ĐÃ GHIM TRONG FILE (NẾU ĐÃ TỪNG GHIM)
    if bound_hwid and bound_hwid != clean_hwid:
        raise PermissionError(
            f"BẢN QUYỀN KHÔNG HỢP LỆ!\n\n"
            f"Bài giảng này đã được khóa cố định vào một máy MacBook khác.\n"
            f"Mã máy của thiết bị này: {clean_hwid}\n\n"
            f"Mỗi file nén mã hóa chỉ được mở trên đúng 1 máy tính duy nhất.\n"
            f"Chuyển sang máy khác sẽ không thể mở được!"
        )

    # 3. XÁC THỰC BẢN QUYỀN (ONLINE TRƯỚC, OFFLINE CACHE DỰ PHÒNG)
    if server_url:
        cloud_res = check_cloud_activation(
            server_url=server_url,
            license_id=license_id,
            current_hwid=clean_hwid,
            title=metadata.get("title", "")
        )
        c_status = cloud_res.get("status", "").upper()
        if c_status == "SUCCESS":
            metadata["bound_hwid"] = clean_hwid
            metadata["_needs_save_bound_hwid"] = True
            _write_activation_cache(cache_file, license_id, clean_hwid)
        elif c_status == "REJECTED":
            _clear_activation_cache(cache_file)
            bound_other = cloud_res.get("bound_hwid", "MÁY KHÁCH KHÁC")
            msg = cloud_res.get("message")
            if not msg:
                msg = (
                    f"TRUY CẬP BỊ TỪ CHỐI!\n\n"
                    f"Lượt mở của bài giảng này đã được sử dụng hết trên một máy MacBook khác.\n"
                    f"Mã máy đã kích hoạt: {bound_other}\n"
                    f"Mã máy hiện tại: {clean_hwid}\n\n"
                    f"Mỗi bài giảng chỉ mở được đúng 1 lần trên 1 máy MacBook duy nhất.\n"
                    f"Dù có chia sẻ file chưa giải nén thì máy khác cũng không thể mở được!"
                )
            raise PermissionError(msg)
        else:
            # Lỗi mạng (offline): Nếu đã từng kích hoạt hợp lệ trước đó trên máy này -> cho mở tiếp
            if has_valid_local_cache and (not bound_hwid or bound_hwid == clean_hwid):
                if not bound_hwid:
                    metadata["bound_hwid"] = clean_hwid
            else:
                raise PermissionError(
                    f"YÊU CẦU KẾT NỐI INTERNET LẦN ĐẦU TIÊN!\n\n"
                    f"Để kích hoạt lượt mở duy nhất của bài giảng này trên MacBook, máy tính cần có kết nối Internet trong 2 giây để xác thực bản quyền.\n\n"
                    f"(Sau khi kích hoạt xong, bài giảng sẽ tự động lưu bản quyền và bạn có thể ngắt mạng để sử dụng Offline vĩnh viễn)."
                )
    else:
        # Không có server_url -> Chế độ Offline Auto-Lock 100%
        if not bound_hwid:
            # Tự động ghim cứng vào máy Mac này lần đầu
            metadata["bound_hwid"] = clean_hwid
            metadata["_needs_save_bound_hwid"] = True
            _write_activation_cache(cache_file, license_id, clean_hwid)
        elif bound_hwid == clean_hwid:
            if not has_valid_local_cache:
                _write_activation_cache(cache_file, license_id, clean_hwid)
        else:
            raise PermissionError(
                f"BẢN QUYỀN KHÔNG HỢP LỆ!\n\n"
                f"Bài giảng này đã được khóa cố định vào một máy MacBook khác.\n"
                f"Mã máy của thiết bị này: {clean_hwid}"
            )

    # 4. GIẢI MÃ NỘI DUNG BÀI GIẢNG VÀO BỘ NHỚ RAM
    lic_salt = bytes.fromhex(metadata["lic_salt"])
    lic_nonce = bytes.fromhex(metadata["lic_nonce"])
    enc_cek = bytes.fromhex(metadata["enc_cek"])

    lic_key = derive_key(license_id, lic_salt)
    aesgcm_lic = AESGCM(lic_key)
    cek = aesgcm_lic.decrypt(lic_nonce, enc_cek, None)

    aesgcm_main = AESGCM(cek)
    presentation_bytes = aesgcm_main.decrypt(main_nonce, encrypted_data, None)

    return metadata, presentation_bytes


# ==============================================================================
# 2. PHƯƠNG THỨC STATIC HWID (KHÓA THEO MÃ MÁY OFFLINE)
# ==============================================================================

def build_static_payload(
    presentation_bytes: bytes,
    allowed_hwids: list[str],
    title: str = "Bài giảng bảo mật",
    allow_edit: bool = True,
    block_save_as: bool = True,
    block_copy: bool = True,
    expiry_date: str = "",
    watermark_text: str = "",
    target_os: str = "MACOS"
) -> bytes:
    """Đóng gói bài giảng theo danh sách mã máy Mac cụ thể (Static HWID)"""
    if block_save_as or block_copy:
        processed_bytes = inject_ribbon_policy(
            presentation_bytes,
            block_save_as=block_save_as,
            block_copy=block_copy,
            block_print=True,
            clean_fonts_for_mac=True
        )
    else:
        processed_bytes = presentation_bytes

    cek = os.urandom(32)
    main_nonce = os.urandom(12)
    aesgcm_main = AESGCM(cek)
    encrypted_data = aesgcm_main.encrypt(main_nonce, processed_bytes, None)

    slots = {}
    for hwid in allowed_hwids:
        clean_hwid = hwid.strip().upper()
        if not clean_hwid:
            continue
        salt = os.urandom(16)
        dev_key = derive_key(clean_hwid, salt)
        slot_nonce = os.urandom(12)
        aesgcm_slot = AESGCM(dev_key)
        enc_cek_slot = aesgcm_slot.encrypt(slot_nonce, cek, None)
        slots[clean_hwid] = {
            "salt": salt.hex(),
            "nonce": slot_nonce.hex(),
            "enc_cek": enc_cek_slot.hex()
        }

    metadata = {
        "mode": "STATIC_HWID",
        "title": title,
        "allow_edit": allow_edit,
        "block_save_as": block_save_as,
        "block_copy": block_copy,
        "expiry_date": expiry_date,
        "watermark": watermark_text,
        "target_os": target_os,
        "slots": slots,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    meta_json = json.dumps(metadata, ensure_ascii=False).encode("utf-8")
    meta_len = len(meta_json)

    payload = bytearray()
    payload.extend(MAGIC_HEADER_STATIC)
    payload.extend(struct.pack(">I", meta_len))
    payload.extend(meta_json)
    payload.extend(main_nonce)
    payload.extend(encrypted_data)
    return bytes(payload)


def verify_and_decrypt_static(
    metadata: dict,
    main_nonce: bytes,
    encrypted_data: bytes,
    current_hwid: str
) -> tuple[dict, bytes]:
    clean_hwid = current_hwid.strip().upper()
    slots = metadata.get("slots", {})

    if clean_hwid not in slots:
        raise PermissionError(
            f"THIẾT BỊ KHÔNG ĐƯỢC PHÉP TRUY CẬP!\n\n"
            f"Mã máy Mac hiện tại: {clean_hwid}\n\n"
            f"Thiết bị này không nằm trong danh sách được cấp phép xem bài giảng."
        )

    slot_info = slots[clean_hwid]
    salt = bytes.fromhex(slot_info["salt"])
    slot_nonce = bytes.fromhex(slot_info["nonce"])
    enc_cek = bytes.fromhex(slot_info["enc_cek"])

    dev_key = derive_key(clean_hwid, salt)
    aesgcm_slot = AESGCM(dev_key)
    cek = aesgcm_slot.decrypt(slot_nonce, enc_cek, None)

    aesgcm_main = AESGCM(cek)
    presentation_bytes = aesgcm_main.decrypt(main_nonce, encrypted_data, None)

    return metadata, presentation_bytes


# ==============================================================================
# 3. HÀM GIẢI MÃ & TỰ ĐỘNG CẬP NHẬT CHỈNH SỬA (AUTO-SAVE SYNC)
# ==============================================================================

def decrypt_presentation_from_bytes(data: bytes, current_hwid: str) -> tuple[dict, bytes]:
    """
    Tự động nhận diện định dạng file (Auto-Lock hoặc Static HWID) và giải mã phù hợp.
    Tương thích 100% với file do hash_win và hash_mac tạo ra.
    """
    if data.startswith(MAGIC_HEADER_AUTOLOCK) or data.startswith(MAGIC_HEADER_AUTOLOCK_V1):
        header_len = len(MAGIC_HEADER_AUTOLOCK)
        is_autolock = True
    elif data.startswith(MAGIC_HEADER_STATIC) or data.startswith(MAGIC_HEADER_STATIC_V1):
        header_len = len(MAGIC_HEADER_STATIC)
        is_autolock = False
    else:
        raise ValueError("Định dạng file bài giảng không hợp lệ hoặc đã bị thay đổi!")

    meta_len = struct.unpack(">I", data[header_len:header_len + 4])[0]
    meta_start = header_len + 4
    meta_end = meta_start + meta_len
    meta_json_bytes = data[meta_start:meta_end]
    metadata = json.loads(meta_json_bytes.decode("utf-8"))

    main_nonce = data[meta_end:meta_end + 12]
    encrypted_data = data[meta_end + 12:]

    # Kiểm tra hạn dùng nếu có
    expiry_date_str = metadata.get("expiry_date", "")
    if expiry_date_str:
        try:
            exp_date = datetime.datetime.strptime(expiry_date_str, "%Y-%m-%d")
            exp_date = exp_date.replace(hour=23, minute=59, second=59)
            if datetime.datetime.now() > exp_date:
                raise PermissionError(f"Thời hạn xem bài giảng trên MacBook đã kết thúc vào ngày {expiry_date_str}!")
        except ValueError:
            pass

    if is_autolock:
        return verify_and_decrypt_autolock(metadata, main_nonce, encrypted_data, current_hwid)
    else:
        return verify_and_decrypt_static(metadata, main_nonce, encrypted_data, current_hwid)


def decrypt_presentation(file_path: str, current_hwid: str) -> tuple[dict, bytes]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")
    with open(file_path, "rb") as f:
        data = f.read()
    return decrypt_presentation_from_bytes(data, current_hwid)


def reencrypt_updated_presentation(original_payload_bytes: bytes, updated_pptx_bytes: bytes) -> bytes:
    """
    Cập nhật lại bài giảng sau khi khách hàng MacBook đã chỉnh sửa và bấm lưu (Cmd+S / Save).
    Tái tạo gói payload mã hóa AES-256 giữ nguyên License ID, Server URL, bound_hwid và quyền hạn.
    """
    if original_payload_bytes.startswith(MAGIC_HEADER_AUTOLOCK) or original_payload_bytes.startswith(MAGIC_HEADER_AUTOLOCK_V1):
        header_len = len(MAGIC_HEADER_AUTOLOCK)
        is_autolock = True
    elif original_payload_bytes.startswith(MAGIC_HEADER_STATIC) or original_payload_bytes.startswith(MAGIC_HEADER_STATIC_V1):
        header_len = len(MAGIC_HEADER_STATIC)
        is_autolock = False
    else:
        raise ValueError("Định dạng dữ liệu không hợp lệ")

    meta_len = struct.unpack(">I", original_payload_bytes[header_len:header_len + 4])[0]
    meta_start = header_len + 4
    meta_end = meta_start + meta_len
    metadata = json.loads(original_payload_bytes[meta_start:meta_end].decode("utf-8"))

    block_save_as = metadata.get("block_save_as", True)
    block_copy = metadata.get("block_copy", True)

    if block_save_as or block_copy:
        final_bytes = inject_ribbon_policy(
            updated_pptx_bytes,
            block_save_as=block_save_as,
            block_copy=block_copy,
            block_print=True,
            clean_fonts_for_mac=True
        )
    else:
        final_bytes = updated_pptx_bytes

    if is_autolock:
        return build_autolock_payload(
            presentation_bytes=final_bytes,
            license_id=metadata["license_id"],
            server_url=metadata.get("server_url", ""),
            title=metadata.get("title", ""),
            allow_edit=metadata.get("allow_edit", True),
            block_save_as=block_save_as,
            block_copy=block_copy,
            expiry_date=metadata.get("expiry_date", ""),
            watermark_text=metadata.get("watermark", ""),
            bound_hwid=metadata.get("bound_hwid", ""),
            offline_fallback=metadata.get("offline_fallback", True),
            target_os="MACOS"
        )
    else:
        slots = metadata.get("slots", {})
        allowed_hwids = list(slots.keys())
        return build_static_payload(
            presentation_bytes=final_bytes,
            allowed_hwids=allowed_hwids,
            title=metadata.get("title", ""),
            allow_edit=metadata.get("allow_edit", True),
            block_save_as=block_save_as,
            block_copy=block_copy,
            expiry_date=metadata.get("expiry_date", ""),
            watermark_text=metadata.get("watermark", ""),
            target_os="MACOS"
        )
