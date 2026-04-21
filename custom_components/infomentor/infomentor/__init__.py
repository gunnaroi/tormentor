"""InfoMentor Python Library package.

Keep package import lightweight; import heavy submodules explicitly where needed.

The concrete client and exception classes are re-exported here so that
standalone test scripts (and external consumers) can write
``from infomentor import InfoMentorClient`` without needing to know the
submodule layout.
"""

from .client import InfoMentorClient
from .exceptions import (
	InfoMentorAPIError,
	InfoMentorAuthError,
	InfoMentorConnectionError,
	InfoMentorDataError,
)

__version__ = "1.0.0"
__all__ = [
	"InfoMentorClient",
	"InfoMentorAPIError",
	"InfoMentorAuthError",
	"InfoMentorConnectionError",
	"InfoMentorDataError",
	"client",
	"auth",
	"models",
	"exceptions",
]