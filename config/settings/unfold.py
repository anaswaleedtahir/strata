from django.templatetags.static import static

UNFOLD = {
    "SITE_TITLE": "Strata Admin",
    "SITE_HEADER": "Strata",
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
            "50": "237 241 244",
            "100": "213 222 230",
            "200": "171 189 208",
            "300": "120 150 175",
            "400": "78 115 144",
            "500": "52 88 113",
            "600": "27 51 71",
            "700": "22 40 57",
            "800": "17 30 44",
            "900": "12 21 31",
        },
    },
}
