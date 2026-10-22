"""Logger filters that keep client-controlled or personal data out of logs.

Attached to specific loggers in ``LOGGING`` (logger-level filters, so they
also apply to pytest's caplog):

* ``django.security.csrf``: Django's rejection message embeds the raw
  ``Origin``/``Referer`` value in the reason. The record is rewritten to
  ``Forbidden (CSRF): <path>``.
* ``django.request``: with DEBUG off, ``exc_info`` (traceback and exception
  message) is replaced by the exception class name.
"""

import logging

from django.conf import settings


class SensitiveRecordFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.name == "django.security.csrf":
            args = record.args if isinstance(record.args, tuple) else ()
            path = args[-1] if len(args) >= 2 else "-"
            record.msg = "Forbidden (CSRF): %s"
            record.args = (path,)
        elif record.name == "django.request" and record.exc_info and not settings.DEBUG:
            exc_type = record.exc_info[0]
            name = exc_type.__name__ if exc_type is not None else "Exception"
            record.msg = f"{record.getMessage()} [{name}]"
            record.args = ()
            record.exc_info = None
            record.exc_text = None
        return True
