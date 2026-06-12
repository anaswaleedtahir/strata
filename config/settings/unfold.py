from django.templatetags.static import static

UNFOLD = {
    "SITE_TITLE": "RealmKey Admin",
    "SITE_HEADER": "RealmKey",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/svg+xml",
            "href": lambda request: static("images/favicon.svg"),
        },
    ],
    "COLORS": {
        "primary": {
            "50": "250 245 255",
            "100": "243 244 255",
            "200": "216 207 255",
            "300": "192 190 255",
            "400": "165 155 255",
            "500": "139 122 255",
            "600": "120 84 255",
            "700": "102 58 255",
            "800": "85 36 255",
            "900": "70 13 255",
        },
    },
}
