from apps.assets.models import Asset


def configure_site_name_field(field, known_site_names=None):
    field.widget.attrs.setdefault("class", "form-input")
    field.widget.attrs["list"] = "site-name-options"
    field.widget.attrs["placeholder"] = "e.g. Main Office, Warehouse B"
    field.help_text = "Which site or location group this asset belongs to."


def get_known_site_names(request=None):
    from apps.assets.models import Asset

    names = set(
        Asset.objects.exclude(site_name="")
        .values_list("site_name", flat=True)
        .distinct()
    )
    if request is not None:
        session_key = request.session.get("scan_session_key")
        if session_key:
            meta = request.session.get("scan_sessions_meta", {}).get(session_key, {})
            site = (meta.get("site_name") or "").strip()
            if site:
                names.add(site)
    return sorted(names, key=str.lower)
