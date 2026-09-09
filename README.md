# PCPartPicker Full Hardware Scraper

A high-performance, modular Python scraper engineered to bypass Cloudflare bot protections and cleanly extract necessary hardware specifications from [PCPartPicker](https://pcpartpicker.com).

## Supported Components

1. **CPU**: Core Count, Base & Boost Clocks, Microarchitecture, TDP, Integrated Graphics
2. **Motherboard**: Socket / CPU, Form Factor, Memory Max, Memory Slots, Color
3. **Memory**: Speed, Modules, Price / GB, Color, Latencies (First Word & CAS)
4. **Storage**: Capacity, Price / GB, Type (SSD/HDD), Cache, Form Factor, Interface
5. **Video Card**: Chipset, VRAM Capacity, Core & Boost Clocks, Color, Length
6. **Power Supply**: Type, Efficiency Rating, Wattage, Modular, Color

*All components also capture: ID, Name, Current Price, Rating, Review Count, and Product URL.*

## Project Structure

```
pcpartpicker-scraper/
├── .gitignore
├── README.md
├── requirements.txt
├── main.py                       # CLI entry point
└── pcpartpicker_scraper/
    ├── __init__.py
    ├── config.py                 # Category mappings & defaults
    ├── browser.py                # Browser context & Cloudflare Turnstile handling
    ├── parser.py                 # HTML table parsing & specification extraction
    ├── storage.py                # Checkpointing (resumability) & JSON/CSV exporters
    └── scraper.py                # Main orchestrator engine
```

## Anti-Bot & Cloudflare Countermeasures

- **Persistent Browser Context**: Preserves `cf_clearance` cookies and session credentials.
- **Natural Fingerprint**: Strips `navigator.webdriver` via `--disable-blink-features=AutomationControlled` without introducing detectable sandbox discrepancies.
- **In-Page Hash Navigation**: Triggers internal `/qapi/product/category/` calls directly inside the browser using `#page=N` hash changes with real CSRF tokens.
- **Coordinate-based Challenge Resolver**: Automatically clicks Turnstile checkboxes if presented.
- **Jitter & Rate Limiting**: Random delay (1.8s - 3.2s) between pages.
- **Checkpointing / Resumability**: Tracks completed pages in `scraper_state.json` and streams to `.jsonl`. Can be safely stopped and resumed anytime.

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## Usage

### Scrape All Categories
```bash
python main.py --categories all
```

### Scrape Specific Categories
```bash
python main.py --categories cpu video-card
```

### Test Run (Limited Pages)
```bash
python main.py --categories cpu motherboard --max-pages 2
```

### Custom Output Directory & Timing
```bash
python main.py --output-dir ./my_data --delay-min 2.0 --delay-max 4.0
```

## Output Formats

Data is saved to `--output-dir` (default: `./pcpartpicker_data`):
- `<category>.csv`: Flattened tabular format.
- `<category>.json`: Full structured JSON list.
- `<category>.jsonl`: Real-time streaming output.
- `scraper_state.json`: Checkpoint progress tracker.
