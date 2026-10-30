"""Exceptions raised by limen."""


class LimenError(Exception):
    """Base class for every limen error."""


class ProviderError(LimenError):
    """The provider could not produce answers. ``Policy.on_failure`` decides what happens next."""


class ProviderUnavailable(ProviderError):
    """Transient: connection failure, timeout, rate limit, overload or server error."""


class ProviderRequestError(ProviderError):
    """The provider rejected the request; resending it unchanged will not help."""


class StateTooLarge(ProviderRequestError):
    """The prepared state exceeds the provider's request size limit, so it was never sent.

    Treated like the 413 the server would have returned.
    """


class PolicyError(LimenError):
    """A policy does not fit the question set it was applied to. This is a programmer error."""
