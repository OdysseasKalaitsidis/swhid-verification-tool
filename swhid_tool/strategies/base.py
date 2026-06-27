# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class VerificationStrategy(ABC):
    @abstractmethod
    def resolve(self, name: str, version: str, qualifiers: Dict[str, str]) -> Dict[str, Any]:
        """
        Resolves the package to a SWHID and returns a findings dictionary.
        """
        pass
