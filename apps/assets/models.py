import io
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Asset(models.Model):
    class BarcodeType(models.TextChoices):
        QR = "qr", "QR Code"
        CODE128 = "code128", "Code 128"
        CODE39 = "code39", "Code 39"
        EAN13 = "ean13", "EAN-13"

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    asset_number = models.PositiveIntegerField(unique=True, null=True, blank=True, db_index=True)
    barcode_value = models.CharField(max_length=128, unique=True, db_index=True)
    barcode_type = models.CharField(
        max_length=20,
        choices=BarcodeType.choices,
        default=BarcodeType.QR,
    )

    product_name = models.CharField(max_length=255)
    serial_number = models.CharField(max_length=128, blank=True)
    model_number = models.CharField(max_length=128, blank=True)
    location = models.CharField(max_length=255, blank=True)
    comments = models.TextField(blank=True)
    photo = models.ImageField(upload_to="assets/photos/", blank=True, null=True)

    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assets_created",
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["asset_number", "-created_at"]

    def __str__(self):
        return f"{self.product_name} ({self.barcode_value})"

    @classmethod
    def generate_barcode_value(cls):
        return f"AT-{uuid.uuid4().hex[:12].upper()}"

    def get_scan_url(self, request=None):
        from django.urls import reverse
        path = reverse("scan:register", kwargs={"barcode": self.barcode_value})
        if request:
            return request.build_absolute_uri(path)
        return path

    def save(self, *args, **kwargs):
        if not self.barcode_value:
            self.barcode_value = self.generate_barcode_value()
        if self.asset_number is None:
            from django.db.models import Max

            current_max = Asset.objects.aggregate(m=Max("asset_number"))["m"] or 0
            self.asset_number = current_max + 1
        super().save(*args, **kwargs)
