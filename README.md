# Switch It Up

Switch It Up is a fashion virtual-wardrobe and stylist marketplace prototype.

The app idea:

- users sign in and set size, height, waist, shoe size, and fit preferences
- users upload photos of clothes into a virtual wardrobe
- the app creates a virtual body/lookalike styling canvas
- a production version can use a guided 360 body video to improve avatar sizing
- normal users can ask stylists to remix existing clothes or suggest replacements
- stylists can build credibility through posts, likes, comments, followers, and helped clients
- malls/shops can list clothes, and stylists can send wishlist outfits to users
- competitions let multiple stylists submit outfits for a paid prize

## MVP Features

- Normal/stylist account toggle
- Wardrobe photo-card simulation
- Virtual-you outfit preview
- Style request workflow
- Stylist marketplace cards
- Mall wishlist panel
- Social proof feed
- Styling competition card
- Python style-matching engine with tests
- CSV sample style report
- GitHub Pages demo

## Run

```bash
python3 -m http.server 5180
```

Open:

```text
http://127.0.0.1:5180
```

## Test

```bash
python3 -m unittest discover -s tests -v
```

## Export Report

```bash
PYTHONPATH=. python3 tools/export_sample_report.py
```

## Production Notes

A real production version would need consent-based body image capture, secure photo storage, product catalog integrations, payments, identity verification for stylists and malls, moderation, privacy controls, and clear AI safety rules.
