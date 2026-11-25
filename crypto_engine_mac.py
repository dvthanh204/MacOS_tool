"""
Module: crypto_engine_mac.py
Hệ Thống Bảo Mật, Định Danh Phần Cứng MacBook (Mac HWID) & Mã Hóa AES-256-GCM cho macOS
Tuân thủ 100% chuẩn cấu trúc và logic bảo mật của hash_win:
1. Auto-Lock First Run (TOFU - Tự động bắt & ghim ID máy tính Mac khi mở lần đầu)
2. Chống chia sẻ / chuyển tiếp cho máy khác: Máy thứ 2 bị chặn 100%
3. HỖ TRỢ CHỈNH SỬA VÀ LƯU BÀI GIẢNG (Editable Mode + Auto-Save Sync Back)
4. Tích hợp chính sách Ribbon Policy tối ưu cho Office for Mac (Cấm Save As, Cho phép Edit, Paste, Save)
5. Hỗ trợ định danh phần cứng native macOS (IOPlatformUUID + IOPlatformSerialNumber) và cross-platform
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
            import uuid as py_uuid
            node_id = py_uuid.getnode()
            raw_seed = f"MAC_FALLBACK::{platform.node()}::{node_id}"
    elif sys.platform == "win32":
        raw_seed = get_windows_hwid()
    else:
        # Linux / Unix fallback
        import platform
        import uuid as py_uuid
        raw_seed = f"UNIX::{platform.node()}::{py_uuid.getnode()}"

    digest = hashlib.sha256(raw_seed.encode("utf-8")).hexdigest().upper()
    return f"{digest[:4]}-{digest[4:8]}-{digest[8:12]}-{digest[12:16]}"


def derive_key(seed: str, salt: bytes) -> bytes:
    """
    Tạo khóa mã hóa AES-256 từ seed bằng PBKDF2 (100.000 vòng lặp)
    """
    clean_seed = seed.strip().upper()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return kdf.derive(clean_seed.encode("utf-8"))


def get_local_cache_path(license_id: str) -> str:
    """
    Đường dẫn lưu token kích hoạt cục bộ trên máy khách.
    Trên macOS: ~/Library/Application Support/LockSlideSecure/<hash>.act
    Trên Windows: %LOCALAPPDATA%/LockSlideSecure/<hash>.act
    """
    if sys.platform == "darwin":
        base_dir = os.path.expanduser("~/Library/Application Support")
    else:
        base_dir = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))

    cache_dir = os.path.join(base_dir, "LockSlideSecure")
    os.makedirs(cache_dir, exist_ok=True)
    safe_name = hashlib.md5(license_id.encode("utf-8")).hexdigest()
    return os.path.join(cache_dir, f"{safe_name}.act")


# ==============================================================================
# 1. PHƯƠNG THỨC AUTO-LOCK (FIRST-RUN AUTO-LOCK) HỖ TRỢ CHỈNH SỬA
# ==============================================================================

def build_autolock_payload(
    presentation_bytes: bytes,
    license_id: str,
    server_url: str,
    title: str = "Bài giảng bảo mật",
    allow_edit: bool = True,
    block_save_as: bool = True,
    block_copy: bool = True,
    expiry_date: str = "",
    watermark_text: str = "",
    target_os: str = "MACOS"
) -> bytes:
    """
    Đóng gói bài giảng theo cơ chế Auto-Lock cho MacBook:
    - Không cần biết trước mã máy của khách hàng.
    - Tiêm chính sách Fluent UI Ribbon cấm Save As & Copy, làm sạch font gây lỗi trên Mac.
    - Cho phép mở lên chỉnh sửa trực tiếp trên PowerPoint (nếu allow_edit=True).
    - Đồng bộ lưu tự động khi nhấn Cmd+S hoặc lưu file.
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
    1. Kiểm tra cache cục bộ (nếu đã kích hoạt thành công trên máy này trước đó).
    2. Truy vấn máy chủ bản quyền /api/verify_or_bind:
       - Nếu PENDING: Máy chủ tự động ghim HWID của máy Mac này.
       - Nếu ACTIVATED và trùng HWID: Cho phép mở.
       - Nếu ACTIVATED nhưng khác HWID: Ném lỗi từ chối, ngăn chặn chia sẻ file!
       - Nếu REVOKED: Ném lỗi từ chối, chặn tức thì.
    3. Cập nhật cache token cục bộ sau khi thành công.
    4. Giải mã dữ liệu PowerPoint trực tiếp vào bộ nhớ RAM.
    """
    license_id = metadata["license_id"]
    server_url = metadata["server_url"]
    cache_file = get_local_cache_path(license_id)

    has_valid_local_cache = False
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "rb") as f:
                cached_data = f.read()
            cache_salt = cached_data[:16]
            cache_nonce = cached_data[16:28]
            cache_ciphertext = cached_data[28:]
            hw_key = derive_key(current_hwid, cache_salt)
            aesgcm = AESGCM(hw_key)
            decrypted_cache = aesgcm.decrypt(cache_nonce, cache_ciphertext, None).decode("utf-8")
            if decrypted_cache == f"ACTIVATED::{license_id}::{current_hwid}":
                has_valid_local_cache = True
        except Exception:
            has_valid_local_cache = False

    # Chuẩn bị gửi yêu cầu tới License Server
    req_data = {
        "license_id": license_id,
        "hwid": current_hwid,
        "title": metadata.get("title", "")
    }

    clean_url = server_url.rstrip("/")
    if "script.google.com" in clean_url:
        target_api = clean_url
    else:
        target_api = f"{clean_url}/api/verify_or_bind"

    json_bytes = json.dumps(req_data).encode("utf-8")
    req = urllib.request.Request(
        target_api,
        data=json_bytes,
        headers={"Content-Type": "application/json", "User-Agent": "LockSlideSecurePlayer-Mac/2.5"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            resp_json = json.loads(resp.read().decode("utf-8"))

        if resp_json.get("status") == "success":
            # Ghi hoặc cập nhật cache token cục bộ
            try:
                cache_salt = os.urandom(16)
                hw_key = derive_key(current_hwid, cache_salt)
                cache_nonce = os.urandom(12)
                aesgcm = AESGCM(hw_key)
                token_str = f"ACTIVATED::{license_id}::{current_hwid}"
                encrypted_token = aesgcm.encrypt(cache_nonce, token_str.encode("utf-8"), None)
                with open(cache_file, "wb") as f:
                    f.write(cache_salt + cache_nonce + encrypted_token)
            except Exception:
                pass
        else:
            # Máy chủ từ chối -> Xóa cache nếu có và chặn
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except Exception:
                    pass
            err_msg = resp_json.get("message", "Quyền truy cập bài giảng này đã bị thu hồi hoặc không hợp lệ.")
            raise PermissionError(err_msg)

    except urllib.error.HTTPError as he:
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except Exception:
                pass
        try:
            err_body = json.loads(he.read().decode("utf-8"))
            err_msg = err_body.get("message", "Quyền truy cập bài giảng này đã bị thu hồi bởi tác giả.")
        except Exception:
            err_msg = f"Truy cập bị từ chối bởi máy chủ (Mã lỗi {he.code})."
        raise PermissionError(err_msg)

    except PermissionError:
        raise

    except Exception:
        # Nếu offline hoặc lỗi mạng, kiểm tra xem có cache hợp lệ từ trước không
        if not has_valid_local_cache:
            raise PermissionError(
                "Lần đầu tiên mở bài giảng trên MacBook cần có kết nối Internet để tự động ghim vào máy tính của bạn.\n\n"
                "Vui lòng kết nối Wi-Fi / Internet và mở lại bài giảng!"
            )

    # Giải mã CEK
    lic_salt = bytes.fromhex(metadata["lic_salt"])
    lic_nonce = bytes.fromhex(metadata["lic_nonce"])
    enc_cek = bytes.fromhex(metadata["enc_cek"])

    lic_key = derive_key(license_id, lic_salt)
    aesgcm_lic = AESGCM(lic_key)
    cek = aesgcm_lic.decrypt(lic_nonce, enc_cek, None)

    # Giải mã bài giảng vào RAM
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

    normalized_hwids = [h.strip().upper() for h in allowed_hwids if h.strip()]
    if not normalized_hwids:
        raise ValueError("Phải có ít nhất 1 mã máy HWID được cấp phép!")

    client_slots = {}
    for hw in normalized_hwids:
        slot_salt = os.urandom(16)
        hw_key = derive_key(hw, slot_salt)
        slot_nonce = os.urandom(12)
        aesgcm_slot = AESGCM(hw_key)
        encrypted_cek = aesgcm_slot.encrypt(slot_nonce, cek, None)
        client_slots[hw] = {
            "salt": slot_salt.hex(),
            "nonce": slot_nonce.hex(),
            "enc_cek": encrypted_cek.hex()
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
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "slots": client_slots
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
            f"BẢN QUYỀN KHÔNG HỢP LỆ TRÊN MACBOOK NÀY!\n\n"
            f"Mã máy Mac hiện tại: {clean_hwid}\n"
            f"Bài giảng này đã được khóa bảo mật chỉ mở trên thiết bị được tác giả cấp phép.\n"
            f"Vui lòng gửi mã máy trên cho tác giả để được kích hoạt."
        )

    slot_info = slots[clean_hwid]
    slot_salt = bytes.fromhex(slot_info["salt"])
    slot_nonce = bytes.fromhex(slot_info["nonce"])
    enc_cek = bytes.fromhex(slot_info["enc_cek"])

    hw_key = derive_key(clean_hwid, slot_salt)
    aesgcm_slot = AESGCM(hw_key)
    cek = aesgcm_slot.decrypt(slot_nonce, enc_cek, None)

    aesgcm_main = AESGCM(cek)
    presentation_bytes = aesgcm_main.decrypt(main_nonce, encrypted_data, None)

    return metadata, presentation_bytes


# ==============================================================================
# 3. ĐIỀU PHỐI GIẢI MÃ & TỰ ĐỘNG CẬP NHẬT CHỈNH SỬA (AUTO-SAVE SYNC)
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
    Tái tạo gói payload mã hóa AES-256 giữ nguyên License ID, Server URL và quyền hạn.
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
            server_url=metadata["server_url"],
            title=metadata.get("title", ""),
            allow_edit=metadata.get("allow_edit", True),
            block_save_as=block_save_as,
            block_copy=block_copy,
            expiry_date=metadata.get("expiry_date", ""),
            watermark_text=metadata.get("watermark", ""),
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
