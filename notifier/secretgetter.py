from typing import Optional

import keyring


def get_secret(scope: str, name: str) -> Optional[str]:
    """Retrieves a secret."""
    return keyring.get_password(scope, name)
