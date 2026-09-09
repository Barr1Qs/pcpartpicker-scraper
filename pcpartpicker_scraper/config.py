"""
Configuration module for PCPartPicker Scraper.
Defines target categories, URLs, and key specifications.
"""

CATEGORIES_CONFIG = {
    "cpu": {
        "name": "CPU",
        "url": "https://pcpartpicker.com/products/cpu/",
        "spec_keys": [
            "Core Count",
            "Performance Core Clock",
            "Performance Core Boost Clock",
            "Microarchitecture",
            "TDP",
            "Integrated Graphics",
        ],
    },
    "motherboard": {
        "name": "Motherboard",
        "url": "https://pcpartpicker.com/products/motherboard/",
        "spec_keys": [
            "Socket / CPU",
            "Form Factor",
            "Memory Max",
            "Memory Slots",
            "Color",
        ],
    },
    "memory": {
        "name": "Memory",
        "url": "https://pcpartpicker.com/products/memory/",
        "spec_keys": [
            "Speed",
            "Modules",
            "Price / GB",
            "Color",
            "First Word Latency",
            "CAS Latency",
        ],
    },
    "storage": {
        "name": "Storage",
        "url": "https://pcpartpicker.com/products/internal-hard-drive/",
        "spec_keys": [
            "Capacity",
            "Price / GB",
            "Type",
            "Cache",
            "Form Factor",
            "Interface",
        ],
    },
    "video-card": {
        "name": "Video Card",
        "url": "https://pcpartpicker.com/products/video-card/",
        "spec_keys": [
            "Chipset",
            "Memory",
            "Core Clock",
            "Boost Clock",
            "Color",
            "Length",
        ],
    },
    "power-supply": {
        "name": "Power Supply",
        "url": "https://pcpartpicker.com/products/power-supply/",
        "spec_keys": [
            "Type",
            "Efficiency Rating",
            "Wattage",
            "Modular",
            "Color",
        ],
    },
}

DEFAULT_OUTPUT_DIR = "./pcpartpicker_data"
DEFAULT_DELAY_MIN = 1.8
DEFAULT_DELAY_MAX = 3.2
DEFAULT_VIEWPORT = {"width": 1280, "height": 800}
