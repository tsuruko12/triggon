class InvalidArgumentError(ValueError):
    """Raised when invalid arguments are passed."""


class UnregisteredLabelError(KeyError):
    """Raised when a label is not registered."""
    def __init__(self, label: str, orig_label: str | None = None):
        super().__init__(label)
        self.label = label
        self.orig_label = orig_label

    def __str__(self):
        msg = f"label {self.label!r} is not registered"
        if self.orig_label is None or not self.orig_label.startswith("*"):
            return msg
        return f"{msg}: {self.orig_label!r}"


class UpdateError(Exception):
    """Raised when a registered variable or attribute cannot be updated."""
    def __init__(self, name: str, err: Exception):
        super().__init__(name, err)
        self.name = name
        self.err = err

    def __str__(self):
        return f"failed to update {self.name!r}: {self.err}"


class FrameAccessError(Exception):
    """Raised when the current execution frame cannot be accessed."""
    def __init__(self) -> None:
        super().__init__("failed to access the current execution frame")
