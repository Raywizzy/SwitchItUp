# Test Plan

Run:

```bash
python3 -m unittest discover -s tests -v
```

Run full app:

```bash
python3 server.py
```

Manual checks:

- API health check returns JSON at `http://127.0.0.1:5180/api/health`.
- Role toggle changes account mode.
- Wardrobe Wear buttons update the virtual outfit.
- Style Me generates a stylist request response.
- Mall wishlist button updates the request panel.
- Add Photo adds a wardrobe item.
- Refreshing after backend actions keeps saved JSON state.
- Mobile layout remains usable.
