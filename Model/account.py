
import hashlib
import hmac
import random
import secrets


PASSWORD_ITERATIONS = 310_000
NATO_PHONETIC_NAMES = (
    "Alpha",
    "Bravo",
    "Charlie",
    "Delta",
    "Echo",
    "Foxtrot",
    "Golf",
    "Hotel",
    "India",
    "Juliett",
    "Kilo",
    "Lima",
    "Mike",
    "November",
    "Oscar",
    "Papa",
    "Quebec",
    "Romeo",
    "Sierra",
    "Tango",
    "Uniform",
    "Victor",
    "Whiskey",
    "X-ray",
    "Yankee",
    "Zulu",
)


def clean_username(username):
    name = username.strip()
    if not name:
        raise ValueError("Enter a username.")
    if len(name) > 20:
        raise ValueError("Usernames must be 20 characters or fewer.")
    if not all(char.isalnum() or char in " _-" for char in name):
        raise ValueError("Use only letters, numbers, spaces, hyphens, or underscores.")
    return name


def clean_password(password):
    if len(password) < 8:
        raise ValueError("Use a password with at least 8 characters.")
    if len(password) > 128:
        raise ValueError("Passwords must be 128 characters or fewer.")
    return password


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )


def create_credentials(password):
    salt = secrets.token_bytes(16)
    return salt.hex(), hash_password(password, salt).hex()


def verify_password(password, salt_hex, saved_hash_hex):
    entered_hash = hash_password(password, bytes.fromhex(salt_hex)).hex()
    return hmac.compare_digest(entered_hash, saved_hash_hex)


def random_server_name():
    return random.choice(NATO_PHONETIC_NAMES)
