import re

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from apps.assets.barcode_utils import assets_pdf_bytes


class EmailNotConfiguredError(Exception):
    pass


def email_is_configured() -> bool:
    return bool(getattr(settings, "EMAIL_HOST_USER", "") and getattr(settings, "EMAIL_HOST_PASSWORD", ""))


def _safe_filename(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_").lower()
    return slug or "site_report"


def send_site_asset_report(*, site_name: str, recipient: str, assets, sender_name: str = "") -> int:
    if not email_is_configured():
        raise EmailNotConfiguredError(
            "Gmail is not configured. Add EMAIL_HOST_USER and EMAIL_HOST_PASSWORD to your .env file."
        )

    count = assets.count()
    title = f"Asset Report — {site_name}"
    pdf_bytes = assets_pdf_bytes(assets, title=title)
    generated = timezone.localtime(timezone.now()).strftime("%B %d, %Y at %I:%M %p %Z")
    from_label = sender_name or settings.DEFAULT_FROM_EMAIL

    body = (
        f"Hello,\n\n"
        f"Attached is the asset inventory report for {site_name}.\n\n"
        f"Total items: {count}\n"
        f"Generated: {generated}\n"
        f"Sent by: {from_label}\n\n"
        f"This message was sent from your asset tracking system.\n"
    )

    email = EmailMessage(
        subject=title,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    email.attach(f"{_safe_filename(site_name)}_assets.pdf", pdf_bytes, "application/pdf")
    return email.send(fail_silently=False)
