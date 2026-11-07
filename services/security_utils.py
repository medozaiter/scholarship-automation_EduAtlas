import os
import re
import html
import time
import json
import zlib
import base64
import hmac
import hashlib
import secrets
import threading
import logging
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    bcrypt = None  # type: ignore
    BCRYPT_AVAILABLE = False

logger = logging.getLogger(__name__)

# ==============================================================================
# 0. DYNAMIC CRYPTOGRAPHIC SECRET MANAGEMENT
# ==============================================================================

def _get_or_create_app_secret() -> str:
    """
    Retrieves or generates an uncompromising 256-bit cryptographically secure secret.
    Eliminates reliance on hardcoded default strings in open-source repositories.
    """
    env_secret = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET")
    if env_secret and len(env_secret.strip()) >= 32:
        return env_secret.strip()

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)
    secret_file = os.path.join(data_dir, ".app_secret")

    if os.path.exists(secret_file):
        try:
            with open(secret_file, "r", encoding="utf-8") as f:
                saved = f.read().strip()
                if len(saved) >= 32:
                    return saved
        except Exception as e:
            logger.debug(f"Could not read existing secret file: {e}")

    new_secret = secrets.token_hex(32)
    try:
        with open(secret_file, "w", encoding="utf-8") as f:
            f.write(new_secret)
    except Exception as e:
        logger.warning(f"Could not persist dynamic secret file: {e}")

    return new_secret

APP_SECRET_KEY = _get_or_create_app_secret()

# Global File Lock for thread-safe atomic data operations
_file_io_lock = threading.Lock()

def atomic_json_write(filepath: str, data: Any):
    """
    Thread-safe, crash-resilient atomic file write pattern:
    Writes to a randomized temporary file in the same directory, flushes,
    and replaces the target file atomically to eliminate race conditions and corruption.
    """
    dir_name = os.path.dirname(filepath)
    os.makedirs(dir_name, exist_ok=True)
    tmp_path = os.path.join(dir_name, f".{os.path.basename(filepath)}.{secrets.token_hex(4)}.tmp")

    with _file_io_lock:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        for attempt in range(8):
            try:
                os.replace(tmp_path, filepath)
                break
            except (PermissionError, OSError):
                if attempt == 7:
                    try:
                        import shutil
                        shutil.copyfile(tmp_path, filepath)
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                        break
                    except Exception:
                        raise
                time.sleep(0.05 * (attempt + 1))


# ==============================================================================
# 1. REGEX PATTERNS & SANITIZATION FILTERS
# ==============================================================================

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

NAME_REGEX = re.compile(r"^[\u0600-\u06FFa-zA-Z\s\.\-']{2,70}$")

SQL_INJECTION_PATTERN = re.compile(
    r"(\b(UNION(\s+ALL)?|SELECT|INSERT\s+INTO|DELETE\s+FROM|UPDATE\s+\w+\s+SET|DROP\s+(TABLE|DATABASE|VIEW)|"
    r"ALTER\s+TABLE|EXEC(\s+XP_|\s+SP_)?|EXECUTE|TRUNCATE\s+TABLE|MERGE\s+INTO|CREATE\s+(TABLE|DATABASE))\b|"
    r"(--|/\*|\*/|;\s*(DROP|SELECT|INSERT|DELETE|UPDATE|TRUNCATE)|@@|char\s*\(|nchar\s*\(|varchar\s*\(|"
    r"cast\s*\(|convert\s*\(|sleep\s*\(|benchmark\s*\(|waitfor\s+delay|"
    r"\bOR\b\s+['\"]?([a-zA-Z0-9_]+)['\"]?\s*=\s*['\"]?\2['\"]?|"
    r"['\"]\s+OR\s+['\"]?[a-zA-Z0-9_]+['\"]?\s*=\s*['\"]?[a-zA-Z0-9_]+))",
    re.IGNORECASE
)

def detect_sql_injection(val: Any) -> bool:
    """Recursively inspects string, list, or dict inputs for SQL injection patterns."""
    if val is None:
        return False
    if isinstance(val, str):
        return bool(SQL_INJECTION_PATTERN.search(val))
    if isinstance(val, (list, tuple, set)):
        return any(detect_sql_injection(item) for item in val)
    if isinstance(val, dict):
        return any(detect_sql_injection(k) or detect_sql_injection(v) for k, v in val.items())
    return False

def validate_sql_safe(val: Optional[str], field_name: str = "المدخل") -> str:
    """Validates that a string does not contain SQL injection payloads."""
    if not val:
        return ""
    if detect_sql_injection(val):
        raise ValueError(f"تم اكتشاف محتوى غير مصرح به أو محاولة حقن SQL في حقل '{field_name}'.")
    return val

SCRIPT_TAG_PATTERN = re.compile(
    r"<[^>]*>|javascript:|data:text/html|vbscript:|onerror|onload|onclick|onmouseover|eval\(|document\.cookie",
    re.IGNORECASE
)

# Invisible Unicode control characters and BiDi override markers (Trojan Source / RTL attack defense)
BIDI_AND_INVISIBLE_CHARS = re.compile(r"[\u200B-\u200F\u202A-\u202E\u2060-\u206F\uFEFF]")

COMMON_WEAK_PASSWORDS = {
    "password", "password1", "12345678", "123456789", "qwerty123",
    "admin123", "administrator", "iloveyou", "welcome1", "pass1234",
    "abcdef12", "00000000", "11111111", "test1234", "master12"
}


def sanitize_text(val: Optional[str], max_length: int = 150) -> str:
    """Strips dangerous HTML/script tags, Bidi overrides, control chars, and limits length."""
    if val is None:
        return ""

    clean = str(val).strip()
    clean = BIDI_AND_INVISIBLE_CHARS.sub("", clean)
    clean = "".join(ch for ch in clean if ch.isprintable() or ch in "\n\r\t")
    clean = SCRIPT_TAG_PATTERN.sub("", clean)
    clean = clean.replace("\x00", "")

    if len(clean) > max_length:
        clean = clean[:max_length]

    clean = html.escape(clean, quote=True)
    return clean.strip()


def validate_email(email_str: str) -> str:
    """Strict RFC 5322 subset validation."""
    if not email_str:
        raise ValueError("البريد الإلكتروني مطلوب ولا يمكن تركه فارغاً.")

    clean = BIDI_AND_INVISIBLE_CHARS.sub("", email_str).strip().lower()

    if len(clean) > 100:
        raise ValueError("البريد الإلكتروني طويل جداً (الحد الأقصى 100 حرف).")

    if " " in clean or "\n" in clean or "\r" in clean or "\t" in clean:
        raise ValueError("البريد الإلكتروني لا يمكن أن يحتوي على مسافات أو أسطر جديدة.")

    if not EMAIL_REGEX.match(clean):
        raise ValueError("صيغة البريد الإلكتروني غير صالحة. يرجى إدخال إيميل صحيح (مثال: name@example.com).")

    return clean


def validate_name(name_str: str) -> str:
    """Validates real Arabic/English name without script injection or control chars."""
    if not name_str:
        return "Student"

    clean = BIDI_AND_INVISIBLE_CHARS.sub("", name_str).strip()

    if SCRIPT_TAG_PATTERN.search(clean) or SQL_INJECTION_PATTERN.search(clean):
        raise ValueError("الاسم يحتوي على رموز أو مدخلات غير مسموح بها أمنياً.")

    clean = re.sub(r"\s+", " ", clean)

    if len(clean) < 2:
        raise ValueError("الاسم قصير جداً (يجب أن يتكون من حرفين على الأقل).")

    if len(clean) > 60:
        clean = clean[:60]

    if not NAME_REGEX.match(clean):
        raise ValueError("يرجى إدخال اسم حقيقي يحتوي على أحرف عربية أو إنجليزية فقط دون رموز خاصة.")

    return html.escape(clean, quote=True)


RESERVED_USERNAMES = {
    "admin", "administrator", "api", "dashboard", "assistant", "notifications",
    "profile", "settings", "logout", "login", "register", "null", "undefined",
    "user", "root", "scholarpilot", "help", "support", "about", "terms", "privacy", "static"
}


def validate_username(username_str: str) -> str:
    """Validates public student handle/slug."""
    if not username_str:
        raise ValueError("اسم المستخدم مطلوب.")
    clean = str(username_str).strip().lower()
    if len(clean) < 3:
        raise ValueError("اسم المستخدم قصير جداً (الحد الأدنى 3 أحرف).")
    if len(clean) > 40:
        raise ValueError("اسم المستخدم طويل جداً (الحد الأقصى 40 حرف).")
    if not re.match(r"^[a-z0-9][a-z0-9_\-\.]*[a-z0-9]$", clean):
        raise ValueError("اسم المستخدم يجب أن يحتوي على حروف إنجليزية، أرقام، أو شرطات (-) دون مسافات.")
    if clean in RESERVED_USERNAMES:
        raise ValueError("اسم المستخدم هذا محجوز لنظام المنصة، يرجى اختيار اسم آخر.")
    return clean


def slugify_username(full_name: str, email: str) -> str:
    """Auto-generates a clean URL slug from student name or email."""
    base = ""
    ascii_name = re.sub(r"[^a-zA-Z0-9\s]", "", full_name or "").strip()
    if len(ascii_name) >= 3:
        base = re.sub(r"\s+", "-", ascii_name.lower())
    else:
        prefix = email.split("@")[0].lower() if email else "student"
        clean_prefix = re.sub(r"[^a-z0-9]", "-", prefix)
        clean_prefix = re.sub(r"-+", "-", clean_prefix).strip("-")
        base = clean_prefix if len(clean_prefix) >= 3 else f"student-{secrets.token_hex(3)}"

    base = base[:35].rstrip("-")
    if base in RESERVED_USERNAMES or len(base) < 3:
        base = f"{base}-{secrets.token_hex(2)}"
    return base



def validate_gpa(gpa_str: str) -> str:
    """
    Validates academic GPA strictly:
    - Max 10 chars to reject overflows (e.g. 10000000000000).
    - Percentage scale: 0.00 to 100.00 (max 2 decimals).
    - GPA scale: 0.00 to 4.00 (or 5.00) (max 2 decimals).
    - Rejects letters, symbols, negative numbers, or irrational values.
    """
    if not gpa_str:
        return "85%"

    clean = BIDI_AND_INVISIBLE_CHARS.sub("", str(gpa_str)).strip()

    if SCRIPT_TAG_PATTERN.search(clean) or SQL_INJECTION_PATTERN.search(clean):
        raise ValueError("حقل المعدل يحتوي على رموز غير مسموح بها أمنياً.")

    # Guard against overflow numbers like 10000000000000
    if len(clean) > 10:
        raise ValueError("المعدل المدخل طويل جداً وغير منطقي. يرجى إدخال قيمة صحيحة بحد أقصى منزلتين عشريتين.")

    accepted_terms = ["امتياز", "جيد جدا", "جيد جداً", "ممتاز", "جيد", "مقبول"]
    if clean in accepted_terms:
        return clean

    if re.search(r"[a-zA-Z؀-ۿ]", clean):
        raise ValueError("حقل المعدل يجب أن يحتوي على أرقام فقط (مثال: 3.75 أو 88.5) ويمنع إدخال أحرف أو نصوص عشوائية.")

    if not re.match(r"^[0-9\.\s%/]+$", clean):
        raise ValueError("حقل المعدل يحتوي على رموز غير مقبولة.")

    # 1. Scale with explicit slash e.g. 3.75/4 or 4.5/5
    slash_match = re.search(r"^([0-5](?:\.\d{1,2})?)\s*/\s*([45](?:\.0)?)$", clean)
    if slash_match:
        val = float(slash_match.group(1))
        scale = float(slash_match.group(2))
        if 0.0 <= val <= scale:
            formatted = f"{val:.2f}".rstrip("0").rstrip(".")
            return f"{formatted}/{int(scale)}"
        raise ValueError(f"المعدل ({val}/{int(scale)}) غير منطقي. يجب ألا يتجاوز {int(scale)}.")

    # 2. Explicit percentage with '%'
    if "%" in clean:
        pct_match = re.search(r"^(\d{1,3}(?:\.\d{1,2})?)\s*%$", clean)
        if pct_match:
            val = float(pct_match.group(1))
            if 0.0 <= val <= 100.0:
                formatted = f"{val:.2f}".rstrip("0").rstrip(".")
                return f"{formatted}%"
            raise ValueError(f"المعدل المئوي ({val}%) غير منطقي. يجب أن يكون بين 0% و 100%.")

    # 3. Numeric value without explicit sign
    num_match = re.search(r"^(\d{1,3}(?:\.\d{1,2})?)$", clean)
    if num_match:
        val = float(num_match.group(1))
        if 0.0 <= val <= 5.0:
            scale = 5.0 if val > 4.0 else 4.0
            formatted = f"{val:.2f}".rstrip("0").rstrip(".")
            return f"{formatted}/{int(scale)}"
        elif 5.0 < val <= 100.0:
            formatted = f"{val:.2f}".rstrip("0").rstrip(".")
            return f"{formatted}%"
        else:
            raise ValueError(f"المعدل المدخل ({val}) غير منطقي. يجب أن يكون بين 0 و 100 أو بين 0 و 4.")

    raise ValueError("صيغة المعدل غير صحيحة. يرجى إدخال رقم بين 0 و 100 أو بين 0 و 4 بحد أقصى منزلتين عشريتين (مثال: 3.75 أو 88.5).")


def validate_age(age_val: Any) -> int:
    """Validates student age strictly between 10 and 100."""
    if age_val is None or str(age_val).strip() == "":
        return 20
    clean = str(age_val).strip()
    if not clean.isdigit():
        raise ValueError("حقل العمر يجب أن يتكون من أرقام فقط ويمنع إدخال نصوص أو قيم سالبة.")
    val = int(clean)
    if val < 10 or val > 100:
        raise ValueError(f"العمر ({val}) غير منطقي. يجب أن يكون بين 10 و 100 سنة.")
    return val


def validate_graduation_year(year_val: Any) -> int:
    """Validates graduation year strictly between 1970 and 2040."""
    if year_val is None or str(year_val).strip() == "":
        return 2027
    clean = str(year_val).strip()
    if not clean.isdigit():
        raise ValueError("سنة التخرج يجب أن تحتوي على 4 أرقام فقط.")
    val = int(clean)
    if val < 1970 or val > 2040:
        raise ValueError(f"سنة التخرج ({val}) غير واقعية. يرجى إدخال سنة بين 1970 و 2040.")
    return val


def validate_phone_number(phone_str: str) -> str:
    """Validates international phone numbers with optional country code."""
    if not phone_str:
        return ""
    clean = re.sub(r"[\s\-\(\)]", "", str(phone_str)).strip()
    if not re.match(r"^(\+|00)?[0-9]{7,15}$", clean):
        raise ValueError("رقم الهاتف غير صحيح. يجب أن يتكون من 7 إلى 15 رقماً مع رمز الدولة الدولي (مثال: +970590000000).")
    return clean


SSRF_BLOCKED_HOSTS = {
    "localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "::1",
    "metadata.google.internal", "10.", "192.168.", "172.16."
}

def validate_social_url(url_str: str, platform: Optional[str] = None) -> str:
    """Validates social media and portfolio URLs, preventing SSRF, javascript: and data: schemes."""
    if not url_str:
        return ""
    clean = str(url_str).strip()
    clean_lower = clean.lower()

    if clean_lower.startswith("javascript:") or clean_lower.startswith("data:") or clean_lower.startswith("file:"):
        raise ValueError("الرابط يحتوي على بروتوكول غير آمن.")

    if not (clean_lower.startswith("http://") or clean_lower.startswith("https://")):
        clean = "https://" + clean
        clean_lower = clean.lower()

    for blocked in SSRF_BLOCKED_HOSTS:
        if blocked in clean_lower:
            raise ValueError("الرابط يشير إلى نطاق داخلي غير مسموح به.")

    if len(clean) > 300:
        raise ValueError("الرابط طويل جداً (الحد الأقصى 300 حرف).")

    if platform:
        p_lower = platform.lower()
        if "github" in p_lower and "github.com" not in clean_lower:
            raise ValueError("رابط GitHub يجب أن يكون على نطاق github.com (مثال: https://github.com/username).")
        if "linkedin" in p_lower and "linkedin.com" not in clean_lower:
            raise ValueError("رابط LinkedIn يجب أن يكون على نطاق linkedin.com (مثال: https://linkedin.com/in/username).")
        if ("twitter" in p_lower or "x" in p_lower) and not ("x.com" in clean_lower or "twitter.com" in clean_lower):
            raise ValueError("رابط X/Twitter يجب أن يكون على نطاق x.com أو twitter.com.")

    return html.escape(clean, quote=True)


def validate_talents_experience(val: Optional[str]) -> str:
    """Sanitizes extracurricular activities and achievements."""
    if not val:
        return ""
    return sanitize_text(val, max_length=400)


def validate_password(password_str: str) -> str:
    """Enforces 8+ characters, letters + numbers, and rejects dictionary passwords."""
    if not password_str:
        raise ValueError("كلمة المرور مطلوبة.")

    clean_pw = password_str.strip()

    if len(clean_pw) < 8:
        raise ValueError("كلمة المرور يجب أن لا تقل عن 8 أحرف لضمان الأمان الأكاديمي.")

    if len(clean_pw) > 128:
        raise ValueError("كلمة المرور طويلة جداً (الحد الأقصى 128 حرف).")

    if not re.search(r"[a-zA-Z]", clean_pw):
        raise ValueError("كلمة المرور يجب أن تحتوي على حرف واحد على الأقل.")

    if not re.search(r"[0-9]", clean_pw):
        raise ValueError("كلمة المرور يجب أن تحتوي على رقم واحد على الأقل.")

    if clean_pw.lower() in COMMON_WEAK_PASSWORDS:
        raise ValueError("كلمة المرور شائعة جداً وسهلة التخمين. يرجى اختيار كلمة مرور أقوى.")

    return clean_pw


def sanitize_email_header(val: Optional[str], max_length: int = 150) -> str:
    """Strips CRLF and null characters to prevent header injection."""
    if not val:
        return ""
    clean = str(val).replace("\r", " ").replace("\n", " ").replace("\x00", "")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:max_length]


# ==============================================================================
# 2. CRYPTOGRAPHIC PASSWORD HASHING (PBKDF2-HMAC-SHA256 & TIMING SHIELD)
# ==============================================================================

PBKDF2_ROUNDS = 600_000
BCRYPT_ROUNDS = 12
DUMMY_SALT = b"\x1b\x9e\x74\x40\x1f\x92\xa8\x72\xce\x10\x55\x8b\x3c\x84\x22\x01"
DUMMY_BCRYPT_HASH = b"$2b$12$e8UvVpL8hB7/6p4u3l1v6.9O6t8Q7W8E9R0T1Y2U3I4O5P6A7S8D9"

def hash_password_secure(password: str, salt_hex: Optional[str] = None) -> Tuple[str, str]:
    """
    Industry-standard bcrypt hashing with work factor 12.
    Falls back gracefully to PBKDF2-HMAC-SHA256 (600,000 rounds) if bcrypt is unavailable.
    """
    if BCRYPT_AVAILABLE and bcrypt is not None:
        try:
            salt_bytes = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
            hashed = bcrypt.hashpw(password.encode("utf-8"), salt_bytes).decode("utf-8")
            return hashed, ""
        except Exception as e:
            logger.warning(f"Bcrypt hash generation failed: {e}. Falling back to PBKDF2.")

    if not salt_hex:
        salt_bytes = secrets.token_bytes(16)
        salt_hex = salt_bytes.hex()
    else:
        salt_bytes = bytes.fromhex(salt_hex)

    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, PBKDF2_ROUNDS)
    formatted_hash = f"pbkdf2:sha256:{PBKDF2_ROUNDS}${salt_hex}${derived.hex()}"
    return formatted_hash, salt_hex


def verify_password_secure(password: str, stored_hash: str, salt: str = "") -> Tuple[bool, bool]:
    """
    Verifies passwords in constant-time with automatic migration to bcrypt:
    1. bcrypt ($2b$, $2a$, $2y$)
    2. PBKDF2-HMAC-SHA256 (triggers rehash to bcrypt)
    3. Legacy SHA-256 (triggers rehash to bcrypt)
    """
    if not stored_hash or not password:
        return False, False

    # 1. Bcrypt verification
    if stored_hash.startswith(("$2b$", "$2a$", "$2y$")):
        if BCRYPT_AVAILABLE and bcrypt is not None:
            try:
                is_valid = bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
                parts = stored_hash.split("$")
                rounds = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else BCRYPT_ROUNDS
                needs_rehash = (rounds < BCRYPT_ROUNDS)
                return is_valid, needs_rehash
            except Exception as e:
                logger.error(f"Error checking bcrypt hash: {e}")
                return False, False
        else:
            logger.error("Bcrypt hash detected but bcrypt library is not active.")
            return False, False

    # 2. PBKDF2 verification (triggers rehash to bcrypt)
    if stored_hash.startswith("pbkdf2:sha256:"):
        try:
            parts = stored_hash.split("$")
            if len(parts) != 3:
                return False, False
            header_part, salt_hex, expected_hex = parts
            rounds = int(header_part.split(":")[-1])
            salt_bytes = bytes.fromhex(salt_hex)

            computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, rounds).hex()
            is_valid = secrets.compare_digest(computed, expected_hex)
            # Automatic upgrade to bcrypt if bcrypt is available
            needs_rehash = bool(BCRYPT_AVAILABLE) or (rounds < PBKDF2_ROUNDS)
            return is_valid, needs_rehash
        except Exception as e:
            logger.error(f"Error verifying PBKDF2 hash: {e}")
            return False, False

    # 3. Legacy SHA-256 (triggers rehash to bcrypt)
    try:
        legacy_computed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        if secrets.compare_digest(legacy_computed, stored_hash):
            return True, True
    except Exception as e:
        logger.error(f"Error checking legacy hash: {e}")

    return False, False


def compute_dummy_pbkdf2(password: str):
    """
    Executes an identical workload on non-existent users to eliminate timing side-channels.
    """
    if BCRYPT_AVAILABLE and bcrypt is not None:
        try:
            bcrypt.checkpw(password.encode("utf-8")[:72], DUMMY_BCRYPT_HASH)
            return
        except Exception:
            pass
    try:
        hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), DUMMY_SALT, PBKDF2_ROUNDS)
    except Exception:
        pass


# ==============================================================================
# 3. SECURE SESSION MANAGEMENT, REFRESH TOKENS & REVOCATION
# ==============================================================================

# Thread-safe in-memory revocation store to immediately invalidate logged-out tokens
_revoked_tokens: Dict[str, float] = {}
_revocation_lock = threading.Lock()

def revoke_token(token: Optional[str]) -> bool:
    """
    Revokes a session or refresh token by recording its signature hash with expiration.
    Why: Prevents replay attacks where a copied token remains valid after user logout.
    """
    if not token or "." not in token:
        return False
    parts = token.split(".")
    sig = parts[-1]
    # Extract expiration if possible to keep blacklist memory minimal
    token_hash = hashlib.sha256(sig.encode("utf-8")).hexdigest()
    payload = verify_session_token(token) or verify_refresh_token(token)
    exp = payload.get("exp", time.time() + 1800) if payload else (time.time() + 1800)
    with _revocation_lock:
        _revoked_tokens[token_hash] = exp
        # Sweep expired entries to prevent memory accumulation
        now = time.time()
        expired = [k for k, v in _revoked_tokens.items() if v < now]
        for k in expired:
            _revoked_tokens.pop(k, None)
    return True

def is_token_revoked(token: Optional[str]) -> bool:
    """
    Checks whether a token's signature has been explicitly invalidated upon logout.
    Why: Ensures stateless HMAC tokens respect server-side session termination.
    """
    if not token or "." not in token:
        return False
    parts = token.split(".")
    sig = parts[-1]
    token_hash = hashlib.sha256(sig.encode("utf-8")).hexdigest()
    with _revocation_lock:
        exp = _revoked_tokens.get(token_hash)
        if exp is not None:
            if time.time() > exp:
                _revoked_tokens.pop(token_hash, None)
                return False
            return True
    return False

def create_session_token(email: str, role: str = "student", expires_in_seconds: int = 1800) -> str:
    """
    Generates a cryptographically signed HMAC-SHA256 session token.
    Why: Max lifespan is strictly capped at 30 minutes (1800s) to minimize window of vulnerability if intercepted.
    Uses high-entropy secrets.token_urlsafe(32) nonce to guarantee unique nonces and thwart precomputation.
    """
    safe_expiry = min(expires_in_seconds, 1800)
    payload = {
        "email": email.strip().lower(),
        "role": role,
        "purpose": "session",
        "iat": int(time.time()),
        "exp": int(time.time()) + safe_expiry,
        "nonce": secrets.token_urlsafe(32)
    }
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8").rstrip("=")

    signature = hmac.new(
        APP_SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return f"{payload_b64}.{signature}"

def verify_session_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Verifies HMAC signature, session purpose, revocation status, and expiration.
    Why: Thwarts token tampering, ensures revoked tokens fail immediately, and enforces 30m window.
    """
    if not token or "." not in token:
        return None

    if is_token_revoked(token):
        return None

    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts

        expected_sig = hmac.new(
            APP_SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not secrets.compare_digest(signature, expected_sig):
            return None

        padding = "=" * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode((payload_b64 + padding).encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)

        # Allow legacy tokens without purpose or explicitly marked session
        purpose = payload.get("purpose")
        if purpose and purpose != "session":
            return None

        if time.time() > payload.get("exp", 0):
            return None

        return payload
    except Exception:
        return None

def create_refresh_token(email: str, role: str = "student", expires_in_seconds: int = 7 * 86400) -> str:
    """
    Generates a cryptographically signed HMAC-SHA256 refresh token.
    Why: Allows long-lived session renewal without storing user credentials in the browser or re-prompting.
    """
    payload = {
        "email": email.strip().lower(),
        "role": role,
        "purpose": "refresh",
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in_seconds,
        "nonce": secrets.token_urlsafe(32)
    }
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8").rstrip("=")

    signature = hmac.new(
        APP_SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return f"{payload_b64}.{signature}"

def verify_refresh_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Verifies HMAC signature, purpose=='refresh', revocation status, and expiration.
    Why: Guards the session renewal pipeline against unauthorized elevation or expired refresh tokens.
    """
    if not token or "." not in token:
        return None

    if is_token_revoked(token):
        return None

    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts

        expected_sig = hmac.new(
            APP_SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not secrets.compare_digest(signature, expected_sig):
            return None

        padding = "=" * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode((payload_b64 + padding).encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)

        if payload.get("purpose") != "refresh":
            return None

        if time.time() > payload.get("exp", 0):
            return None

        return payload
    except Exception:
        return None

# ==============================================================================
# CSRF PROTECTION UTILITIES
# ==============================================================================

def generate_csrf_token(session_nonce: Optional[str] = None) -> str:
    """
    Generates an HMAC-SHA256 signed CSRF token with a timestamp.
    Why: Defends state-changing requests against Cross-Site Request Forgery without requiring external DB lookups.
    """
    ts = int(time.time())
    nonce = session_nonce or secrets.token_urlsafe(16)
    raw = f"{ts}:{nonce}"
    sig = hmac.new(APP_SECRET_KEY.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
    token_b64 = base64.urlsafe_b64encode(f"{raw}:{sig}".encode("utf-8")).decode("utf-8").rstrip("=")
    return token_b64

def verify_csrf_token(csrf_token: Optional[str], max_age_seconds: int = 7200) -> bool:
    """
    Verifies that a CSRF token has a valid HMAC-SHA256 signature and has not expired.
    Why: Ensures the token was minted by this server within the allowed validity window (default 2h).
    """
    if not csrf_token or not isinstance(csrf_token, str):
        return False
    try:
        padding = "=" * (-len(csrf_token) % 4)
        decoded = base64.urlsafe_b64decode((csrf_token + padding).encode("utf-8")).decode("utf-8")
        parts = decoded.split(":")
        if len(parts) != 3:
            return False
        ts_str, nonce, signature = parts
        ts = int(ts_str)
        if time.time() - ts > max_age_seconds or time.time() < (ts - 60):
            return False
        raw = f"{ts}:{nonce}"
        expected_sig = hmac.new(APP_SECRET_KEY.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
        return secrets.compare_digest(signature, expected_sig)
    except Exception:
        return False

def create_email_verification_token(email: str, expires_in_seconds: int = 172800) -> str:
    """Generates a cryptographically signed HMAC-SHA256 email verification token (48 hours)."""
    payload = {
        "email": email.strip().lower(),
        "purpose": "email_verification",
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in_seconds,
        "nonce": secrets.token_hex(8)
    }
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8").rstrip("=")
    signature = hmac.new(
        APP_SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_email_verification_token(token: Optional[str]) -> Optional[str]:
    """Verifies HMAC signature and expiration on email verification token; returns verified email."""
    if not token or "." not in token:
        return None
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        expected_sig = hmac.new(
            APP_SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        if not secrets.compare_digest(signature, expected_sig):
            return None

        padding = "=" * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode((payload_b64 + padding).encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)

        if payload.get("purpose") != "email_verification":
            return None
        if time.time() > payload.get("exp", 0):
            return None
        return payload.get("email")
    except Exception:
        return None



# ==============================================================================
# 4. MEMORY-SAFE RATE LIMITER & SPOOFING DEFENSE
# ==============================================================================

class SecurityRateLimiter:
    """
    Sliding-window rate limiter with memory self-pruning and anti-spoofing defense.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._requests: Dict[str, List[float]] = {}
        self._failed_logins: Dict[str, List[float]] = {}
        self._email_cooldowns: Dict[str, float] = {}
        self._check_counter: int = 0

        self.LIMITS = {
            "login": (5, 900),     # Strict 5 requests / 15 minutes for authentication login
            "auth": (5, 900),      # 5 requests / 15 minutes for registration & password reset
            "search": (60, 60),    # 60 requests / minute for search operations
            "advisor": (20, 60),   # 20 requests / minute for AI assistant queries
            "contact": (3, 3600),  # 3 requests / hour for contact form submissions
            "radar_scan": (15, 60),
            "document_generation": (10, 60),
            "subscribe": (6, 60),
            "upload": (10, 60),
            "community": (20, 60),
            "general": (60, 60),   # 60/min for general public API endpoints
        }
        self._daily_advisor_quotas: Dict[str, int] = {}
        self.GUEST_DAILY_ADVISOR_LIMIT: int = 10         # Guests: 10 messages/day
        self.REGISTERED_DAILY_ADVISOR_LIMIT: int = 100   # Registered users: 100 messages/day
        self.DAILY_ADVISOR_LIMIT: int = 10
        self._hourly_generations: Dict[str, List[float]] = {}
        self.HOURLY_GENERATION_LIMIT: int = 10

    def _prune_expired_entries(self, now: float):
        """Sweeps stale buckets to prevent memory accumulation / Slowloris memory leaks."""
        expired_req_keys = []
        for k, v in self._requests.items():
            cat = k.split(":")[-1] if ":" in k else "general"
            window = self.LIMITS.get(cat, self.LIMITS["general"])[1]
            valid = [ts for ts in v if ts > (now - window)]
            if not valid:
                expired_req_keys.append(k)
            else:
                self._requests[k] = valid
        for k in expired_req_keys:
            self._requests.pop(k, None)

        expired_login_keys = [k for k, v in self._failed_logins.items() if not any(ts > (now - 900) for ts in v)]
        for k in expired_login_keys:
            self._failed_logins.pop(k, None)

        expired_email_keys = [k for k, ts in self._email_cooldowns.items() if now - ts > 3600]
        for k in expired_email_keys:
            self._email_cooldowns.pop(k, None)

    def check_rate_limit(self, client_ip: str, category: str = "general") -> Tuple[bool, int]:
        max_reqs, window = self.LIMITS.get(category, self.LIMITS["general"])
        key = f"{client_ip}:{category}"
        now = time.time()

        with self._lock:
            self._check_counter += 1
            if self._check_counter >= 80:
                self._prune_expired_entries(now)
                self._check_counter = 0

            history = self._requests.get(key, [])
            valid_from = now - window
            history = [ts for ts in history if ts > valid_from]

            if len(history) >= max_reqs:
                oldest = history[0]
                retry_after = max(1, int(window - (now - oldest)))
                self._requests[key] = history
                return False, retry_after

            history.append(now)
            self._requests[key] = history
            return True, 0

    def get_rate_limit_metrics(self, client_ip: str, category: str = "general") -> Tuple[bool, int, int, int]:
        """Returns (allowed, retry_after, limit, remaining) for standard HTTP rate limiting headers."""
        max_reqs, window = self.LIMITS.get(category, self.LIMITS["general"])
        key = f"{client_ip}:{category}"
        now = time.time()

        with self._lock:
            history = self._requests.get(key, [])
            valid_from = now - window
            history = [ts for ts in history if ts > valid_from]
            remaining = max(0, max_reqs - len(history))
            allowed = len(history) < max_reqs
            retry_after = 0
            if not allowed and history:
                retry_after = max(1, int(window - (now - history[0])))
            return allowed, retry_after, max_reqs, remaining

    def record_failed_login(self, identifier: str) -> int:
        now = time.time()
        window = 900
        with self._lock:
            history = self._failed_logins.get(identifier, [])
            history = [ts for ts in history if ts > (now - window)]
            history.append(now)
            self._failed_logins[identifier] = history
            return len(history)

    def get_failed_login_count(self, identifier: str) -> int:
        """Returns the count of failed login attempts for an email or IP in the last 15 minutes."""
        now = time.time()
        window = 900
        with self._lock:
            history = self._failed_logins.get(identifier, [])
            valid = [ts for ts in history if ts > (now - window)]
            return len(valid)

    def is_account_locked(self, identifier: str, max_failures: int = 5) -> Tuple[bool, int]:
        now = time.time()
        window = 900
        with self._lock:
            history = self._failed_logins.get(identifier, [])
            history = [ts for ts in history if ts > (now - window)]
            self._failed_logins[identifier] = history

            if len(history) >= max_failures:
                oldest = history[0]
                remaining = max(1, int(window - (now - oldest)))
                return True, remaining
            return False, 0

    def record_successful_login(self, identifier: str):
        with self._lock:
            self._failed_logins.pop(identifier, None)

    def check_welcome_email_cooldown(self, email: str, cooldown_seconds: int = 45) -> Tuple[bool, int]:
        clean_email = email.strip().lower()
        now = time.time()
        with self._lock:
            last_sent = self._email_cooldowns.get(clean_email, 0)
            if now - last_sent < cooldown_seconds:
                remaining = int(cooldown_seconds - (now - last_sent))
                return False, remaining
            self._email_cooldowns[clean_email] = now
            return True, 0


    def check_daily_advisor_quota(self, identifier: str, is_registered: bool = False) -> Tuple[bool, int, int]:
        """
        Enforces AI assistant daily message quota:
        - Guests: 10 messages/day
        - Registered users: 100 messages/day
        Returns: (allowed: bool, used_today: int, remaining: int)
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        clean_id = (identifier or "anonymous").strip().lower()
        key = f"advisor_daily:{clean_id}:{date_str}"
        limit = self.REGISTERED_DAILY_ADVISOR_LIMIT if is_registered else self.GUEST_DAILY_ADVISOR_LIMIT

        with self._lock:
            used = self._daily_advisor_quotas.get(key, 0)
            remaining = max(0, limit - used)
            allowed = used < limit
            return allowed, used, remaining

    def consume_daily_advisor_question(self, identifier: str, is_registered: bool = False) -> Tuple[int, int]:
        """
        Consumes one message from the user's daily quota.
        Returns: (used_today: int, remaining: int)
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        clean_id = (identifier or "anonymous").strip().lower()
        key = f"advisor_daily:{clean_id}:{date_str}"
        limit = self.REGISTERED_DAILY_ADVISOR_LIMIT if is_registered else self.GUEST_DAILY_ADVISOR_LIMIT

        with self._lock:
            used = self._daily_advisor_quotas.get(key, 0) + 1
            self._daily_advisor_quotas[key] = used
            remaining = max(0, limit - used)
            return used, remaining

    def check_hourly_generation_limit(self, identifier: str, max_limit: Optional[int] = None, window: int = 3600) -> Tuple[bool, int, int, int]:
        """
        Enforces maximum 10 AI generations / document generations per hour per user / IP.
        Protects Gemini API credits and Resend email quotas against abuse.
        Returns: (allowed: bool, retry_after: int, limit: int, remaining: int)
        """
        limit = max_limit or self.HOURLY_GENERATION_LIMIT
        clean_id = (identifier or "anonymous").strip().lower()
        now = time.time()
        with self._lock:
            history = self._hourly_generations.get(clean_id, [])
            valid_from = now - window
            history = [ts for ts in history if ts > valid_from]
            self._hourly_generations[clean_id] = history

            remaining = max(0, limit - len(history))
            allowed = len(history) < limit
            retry_after = 0
            if not allowed and history:
                retry_after = max(1, int(window - (now - history[0])))
            return allowed, retry_after, limit, remaining

    def record_hourly_generation(self, identifier: str):
        """Records an expensive AI or document generation operation timestamp."""
        clean_id = (identifier or "anonymous").strip().lower()
        now = time.time()
        with self._lock:
            history = self._hourly_generations.get(clean_id, [])
            history.append(now)
            self._hourly_generations[clean_id] = history


def log_security_event(event_type: str, email: str, ip: str, status: str, details: Optional[Dict[str, Any]] = None):
    """
    Structured JSON audit logger for security events (login, logout, lockout, token revocation, CSRF).
    Eliminates plaintext password/secret logging while maintaining enterprise compliance.
    """
    clean_email = (email or "anonymous").strip().lower()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "email": clean_email,
        "ip": ip or "127.0.0.1",
        "status": status,
        "details": details or {}
    }
    logger.info(f"AUDIT_SECURITY_LOG: {json.dumps(entry, ensure_ascii=False)}")


def verify_cron_secret(provided_secret: Optional[str]) -> bool:
    """
    Verifies that the provided secret matches CRON_SECRET using constant-time comparison.
    Defends against timing side-channel attacks on webhook and cron endpoints.
    Eliminates hardcoded fallback strings; requires explicit CRON_SECRET or APP_SECRET_KEY.
    """
    if not provided_secret:
        return False
    expected = os.getenv("CRON_SECRET")
    candidates = [expected] if expected else []
    candidates.append(APP_SECRET_KEY)
    for cand in candidates:
        if cand and secrets.compare_digest(provided_secret.strip(), cand.strip()):
            return True
    return False


def validate_environment_at_startup() -> Dict[str, Any]:
    """
    Validates required environment variables and production security posture at startup.
    Ensures zero secrets or sensitive keys are exposed or logged.
    """
    results = {
        "is_production": os.getenv("ENVIRONMENT", "development").lower() in ("production", "prod"),
        "secret_key_status": "present",
        "gemini_api_key_status": "present" if os.getenv("GEMINI_API_KEY") else "missing",
        "email_provider_configured": bool(os.getenv("RESEND_API_KEY") or os.getenv("SENDER_EMAIL")),
        "database_configured": bool(os.getenv("DATABASE_URL")),
        "cron_secret_status": "configured" if os.getenv("CRON_SECRET") else "fallback_app_secret",
        "issues": []
    }

    # 1. SECRET_KEY validation
    raw_secret = os.getenv("SECRET_KEY")
    if not raw_secret:
        results["secret_key_status"] = "auto_generated"
    elif len(raw_secret.strip()) < 32:
        results["issues"].append("SECRET_KEY is shorter than 32 characters; recommend 64-char hex string.")

    # 2. GEMINI_API_KEY validation
    raw_gemini = os.getenv("GEMINI_API_KEY", "").strip()
    if not raw_gemini:
        results["issues"].append("GEMINI_API_KEY is not set; Gemini LLM features will fall back to local responses.")
    elif len(raw_gemini) < 15:
        results["issues"].append("GEMINI_API_KEY appears malformed or too short.")

    # 3. CRON_SECRET validation
    if not os.getenv("CRON_SECRET"):
        results["issues"].append("CRON_SECRET not explicitly defined; falling back to internal application secret.")

    return results


def verify_recaptcha(token: Optional[str], client_ip: Optional[str] = None) -> Tuple[bool, str]:
    """
    Server-side verification of Google reCAPTCHA (v2 / v3) tokens.
    Supports testing mock tokens and automatic dev bypass when unconfigured.
    """
    secret_key = os.getenv("RECAPTCHA_SECRET_KEY", "").strip()
    clean_token = (token or "").strip()

    # Automatic test/dev bypass when secret is unconfigured or testing token provided
    if not secret_key or secret_key.lower() in ("test", "dummy", "disabled", "none", "bypass"):
        return True, "BYPASSED_NO_SECRET"

    if clean_token in ("test_captcha_token", "dev_token", "bypass_token", "mock_recaptcha"):
        return True, "BYPASSED_TEST_TOKEN"

    if not clean_token:
        return False, "رمز التحقق reCAPTCHA مطلوب لمنع الطلبات المؤتمتة."

    try:
        import httpx
        with httpx.Client(timeout=6.0) as client:
            payload = {
                "secret": secret_key,
                "response": clean_token
            }
            if client_ip:
                payload["remoteip"] = client_ip
            resp = client.post("https://www.google.com/recaptcha/api/siteverify", data=payload)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    score = data.get("score")
                    if score is not None and score < 0.4:
                        logger.warning(f"reCAPTCHA score too low ({score}) for IP: {client_ip}")
                        return False, "تم رصد مؤشرات روبوت أو نشاط غير معتاد."
                    return True, "VERIFIED"
                else:
                    logger.warning(f"reCAPTCHA failed: {data.get('error-codes', [])}")
                    return False, "فشل التحقق من كود reCAPTCHA."
            return False, "تعذر الاتصال بخدمة التحقق reCAPTCHA."
    except Exception as e:
        logger.error(f"Error verifying reCAPTCHA: {e}")
        return False, "حدث خطأ غير متوقع أثناء فحص كود التحقق."

security_rate_limiter = SecurityRateLimiter()


# ==============================================================================
# 5. AI PROMPT INJECTION & FILE UPLOAD HARDENING
# ==============================================================================

PROMPT_INJECTION_TOKENS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)",
    r"reveal\s+(your\s+)?(system\s+prompt|instructions|secret|api[_\s-]?key)",
    r"print\s+(the\s+)?(system\s+prompt|hidden\s+prompt)",
    r"system\s*prompt",
    r"jailbreak",
    r"developer\s+mode",
    r"DAN\s+mode",
    r"bypass\s+restrictions",
    r"roleplay\s+as\s+an\s+unfiltered",
    r"<system>",
    r"\[system\]",
    r"<\s*script\s*>",
    r"eval\s*\("
]
COMPILED_INJECTION_REGEX = re.compile("|".join(PROMPT_INJECTION_TOKENS), re.IGNORECASE)


def sanitize_advisor_query(query_str: str) -> str:
    """Sanitizes AI queries and defuses prompt injection and invisible Bidi markers."""
    if not query_str or len(query_str.strip()) < 3:
        raise ValueError("يرجى كتابة سؤال واضح لا يقل عن 3 أحرف.")

    clean = BIDI_AND_INVISIBLE_CHARS.sub("", query_str).strip()

    if len(clean) > 500:
        clean = clean[:500]

    clean = SCRIPT_TAG_PATTERN.sub("", clean)
    clean = COMPILED_INJECTION_REGEX.sub("[sanitized]", clean)
    return clean.strip()


def validate_uploaded_file(filename: str, content_bytes: bytes, max_size_mb: int = 5) -> str:
    """Validates document uploads against executable binaries, path traversal, and corrupted headers."""
    if not filename:
        raise ValueError("اسم الملف غير محدد.")

    safe_name = os.path.basename(filename).strip()
    safe_name = BIDI_AND_INVISIBLE_CHARS.sub("", safe_name)
    safe_name = re.sub(r"[^\w\.\-\s\u0600-\u06FF]", "", safe_name)
    ext = os.path.splitext(safe_name)[1].lower()

    allowed_extensions = {".pdf", ".txt", ".doc", ".docx"}
    if ext not in allowed_extensions:
        raise ValueError(f"صيغة الملف غير مدعومة ({ext}). الصيغ المسموحة هي: PDF, TXT, DOC, DOCX فقط.")

    if len(content_bytes) > max_size_mb * 1024 * 1024:
        raise ValueError(f"حجم الملف يتجاوز الحد الأقصى المسموح به ({max_size_mb} ميجابايت).")

    if len(content_bytes) < 10:
        raise ValueError("الملف فارغ أو تالف.")

    # Block executable binary headers
    if (
        content_bytes.startswith(b"MZ") or
        content_bytes.startswith(b"\x7fELF") or
        content_bytes.startswith(b"\xca\xfe\xba\xbe") or
        content_bytes.startswith(b"\xfe\xed\xfa\xce")
    ):
        raise ValueError("تم رفض الملف: صيغة تنفيذية غير مسموح برفعها أمنياً.")

    if ext == ".pdf" and not (content_bytes.startswith(b"%PDF-") or b"%PDF-" in content_bytes[:1024]):
        raise ValueError("تم رفض الملف: بنية ملف PDF غير صالحة أو تم التلاعب بها.")

    return safe_name


XML_ESCAPE_TAGS = re.compile(
    r"</?(?:student_profile|cv_content|motivation_letter|student_query|student_bio|student_message|system_instruction|system|prompt)[^>]*>",
    re.IGNORECASE
)

def sanitize_prompt_input(text: Optional[str], max_chars: int = 15000) -> str:
    """
    Sanitizes user-provided CV text, bio, query, and chat messages before passing into LLM prompts.
    Defuses prompt injection attacks, strips delimiter-breakout tags, bidi overrides, and script tags.
    """
    if not text:
        return ""
    clean = BIDI_AND_INVISIBLE_CHARS.sub("", str(text))
    clean = "".join(ch for ch in clean if ch.isprintable() or ch in "\n\r\t")
    clean = XML_ESCAPE_TAGS.sub("[tag-filtered]", clean)
    clean = SCRIPT_TAG_PATTERN.sub("", clean)
    clean = COMPILED_INJECTION_REGEX.sub("[sanitized-instruction]", clean)
    if len(clean) > max_chars:
        clean = clean[:max_chars]
    return clean.strip()


def wrap_xml_tag(tag_name: str, content: Optional[str], max_chars: int = 15000) -> str:
    """
    Safely encapsulates user-provided inputs within strict XML delimiters.
    Prevents prompt injection by isolating untrusted data from system instructions.
    """
    sanitized = sanitize_prompt_input(content, max_chars=max_chars)
    return f"<{tag_name}>\n{sanitized}\n</{tag_name}>"


def sanitize_uploaded_text(text: str, max_chars: int = 15000) -> str:
    """Sanitizes extracted document text, removing Bidi overrides and injection markers."""
    return sanitize_prompt_input(text, max_chars=max_chars)


def sanitize_llm_output(output_text: str) -> str:
    """Redacts accidental leaks of API keys, secrets, or internal system instruction markers."""
    if not output_text:
        return ""

    sanitized = output_text
    sanitized = re.sub(r"AIza[0-9A-Za-z-_]{35}", "[REDACTED_API_KEY]", sanitized)
    sanitized = re.sub(r"sk-[0-9A-Za-z-_]{32,}", "[REDACTED_SECRET]", sanitized)
    sanitized = re.sub(r"re_[0-9A-Za-z-_]{20,}", "[REDACTED_RESEND_KEY]", sanitized)
    sanitized = re.sub(r"postgres(?:ql)?://[^\s]+", "[REDACTED_DATABASE_URL]", sanitized)

    leak_markers = [
        "SYSTEM_INSTRUCTION", "HIDDEN_SYSTEM_PROMPT", "INTERNAL_ADVISOR_RULE",
        "YOU MUST NEVER REVEAL", "CONFIDENTIAL_ENGINE_PROMPT"
    ]
    for marker in leak_markers:
        sanitized = sanitized.replace(marker, "[REDACTED]")

    return sanitized

def validate_uploaded_image(filename: str, content_bytes: bytes, max_size_mb: int = 5) -> Tuple[str, str, bytes]:
    """
    Validates uploaded images against malicious payloads, polyglots, and invalid headers.
    Returns: (safe_filename, content_type, clean_bytes)
    """
    import uuid
    import io
    if not filename:
        raise ValueError("اسم ملف الصورة غير محدد.")

    safe_name = os.path.basename(filename).strip()
    safe_name = BIDI_AND_INVISIBLE_CHARS.sub("", safe_name)
    safe_name = re.sub(r"[^\w\.\-\s؀-ۿ]", "", safe_name)
    ext = os.path.splitext(safe_name)[1].lower()

    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    if ext not in allowed_extensions:
        raise ValueError(f"صيغة الصورة غير مدعومة ({ext}). الصيغ المسموحة هي: JPG, PNG, WEBP, GIF فقط.")

    if len(content_bytes) > max_size_mb * 1024 * 1024:
        raise ValueError(f"حجم الصورة يتجاوز الحد الأقصى المسموح به ({max_size_mb} ميجابايت).")

    if len(content_bytes) < 32:
        raise ValueError("ملف الصورة فارغ أو تالف.")

    # Block executable and script signatures
    if (
        content_bytes.startswith(b"MZ") or
        content_bytes.startswith(bytes([0x7f, 0x45, 0x4c, 0x46])) or
        content_bytes.startswith(b"<?php") or
        b"<script" in content_bytes[:1024].lower()
    ):
        raise ValueError("تم رفض الملف: محتوى غير مصرح به أو يحتوي على شفرات خبيثة.")

    # Strict magic bytes verification using integer byte arrays to avoid encoding issues
    is_jpeg = content_bytes.startswith(bytes([0xff, 0xd8, 0xff]))
    is_png = content_bytes.startswith(bytes([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))
    is_webp = content_bytes.startswith(b"RIFF") and len(content_bytes) > 12 and content_bytes[8:12] == b"WEBP"
    is_gif = content_bytes.startswith(b"GIF87a") or content_bytes.startswith(b"GIF89a")

    if not (is_jpeg or is_png or is_webp or is_gif):
        raise ValueError("الملف المرفوع ليس صورة صالحة أو تم التلاعب ببيانات الترويسة.")

    # Verify and sanitize with Pillow
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(content_bytes))
        img.verify()
        
        img = Image.open(io.BytesIO(content_bytes))
        out_buf = io.BytesIO()
        
        if img.format in ["JPEG", "JPG"]:
            img = img.convert("RGB")
            img.save(out_buf, format="JPEG", quality=88, optimize=True)
            content_type = "image/jpeg"
            final_ext = ".jpg"
        elif img.format == "PNG":
            img.save(out_buf, format="PNG", optimize=True)
            content_type = "image/png"
            final_ext = ".png"
        elif img.format == "WEBP":
            img.save(out_buf, format="WEBP", quality=88)
            content_type = "image/webp"
            final_ext = ".webp"
        else:
            img.save(out_buf, format=img.format)
            content_type = f"image/{img.format.lower()}"
            final_ext = ext

        clean_bytes = out_buf.getvalue()
        stem = re.sub(r"[^a-zA-Z0-9_-]", "", os.path.splitext(safe_name)[0]) or "img"
        final_filename = f"{stem[:20]}_{uuid.uuid4().hex[:10]}{final_ext}"
        return final_filename, content_type, clean_bytes
    except Exception as img_err:
        logger.warning(f"PIL verification failed: {img_err}")
        # Fail hard: do not allow unverified raw bytes to bypass image validation
        raise ValueError(f"فشل التحقق من بنية الصورة المرفوعة أو أنها تالفة: {img_err}")

