"""Утилиты безопасности для валидации и санитизации входных данных."""
import re
import html
from typing import Optional


def sanitize_input(text: str, max_length: Optional[int] = None) -> str:
    """
    Санитизировать пользовательский ввод для предотвращения XSS-атак.
    
    Args:
        text: Текст для санитизации
        max_length: Опциональная максимальная длина
        
    Returns:
        Санитизированный текст
    """
    if not text:
        return ""
    
    # Удалить null-байты
    text = text.replace("\x00", "")
    
    # Экранировать HTML для предотвращения XSS
    text = html.escape(text)
    
    # Убрать пробелы по краям
    text = text.strip()
    
    # Ограничить максимальную длину
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Проверить надежность пароля.
    
    Требования:
    - Минимум 8 символов
    - Хотя бы одна заглавная буква
    - Хотя бы одна строчная буква
    - Хотя бы одна цифра
    - Хотя бы один специальный символ
    
    Args:
        password: Пароль для проверки
        
    Returns:
        Кортеж (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Пароль должен содержать минимум 8 символов"
    
    if not re.search(r"[A-Z]", password):
        return False, "Пароль должен содержать хотя бы одну заглавную букву"
    
    if not re.search(r"[a-z]", password):
        return False, "Пароль должен содержать хотя бы одну строчную букву"
    
    if not re.search(r"\d", password):
        return False, "Пароль должен содержать хотя бы одну цифру"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Пароль должен содержать хотя бы один специальный символ"
    
    return True, ""


def validate_email_format(email: str) -> bool:
    """
    Проверить формат email с помощью регулярного выражения.
    
    Args:
        email: Email-адрес для проверки
        
    Returns:
        True если валиден, False в противном случае
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def sanitize_filename(filename: str) -> str:
    """
    Санитизировать имя файла для предотвращения directory traversal и других атак.
    
    Args:
        filename: Исходное имя файла
        
    Returns:
        Санитизированное имя файла
    """
    # Удалить компоненты пути
    filename = filename.split("/")[-1].split("\\")[-1]
    
    # Удалить опасные символы
    filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
    
    # Ограничить длину
    if len(filename) > 255:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:250] + (f".{ext}" if ext else "")
    
    return filename


def check_sql_injection_pattern(text: str) -> bool:
    """
    Проверить наличие распространенных паттернов SQL-инъекций.
    
    Args:
        text: Текст для проверки
        
    Returns:
        True если найден подозрительный паттерн, False в противном случае
    """
    suspicious_patterns = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bSELECT\b.*\bFROM\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bUPDATE\b.*\bSET\b)",
        r"(--|#|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"('|;|--|/\*|\*/)",
    ]
    
    text_upper = text.upper()
    for pattern in suspicious_patterns:
        if re.search(pattern, text_upper, re.IGNORECASE):
            return True
    
    return False

