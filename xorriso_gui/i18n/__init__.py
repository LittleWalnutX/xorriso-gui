import json
import os

_translations = {}
_current = "en"


def load_translations():
    global _translations
    base = os.path.dirname(__file__)
    for lang in ("en", "ja"):
        path = os.path.join(base, f"{lang}.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                _translations[lang] = json.load(f)


def set_language(lang):
    global _current
    if lang in _translations:
        _current = lang


def get_language():
    return _current


def tr(key, default=None):
    if _current in _translations and key in _translations[_current]:
        return _translations[_current][key]
    return default if default is not None else key


def languages():
    return list(_translations.keys())