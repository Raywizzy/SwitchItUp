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
- Live API health check returns JSON at `https://switchitup.vercel.app/api/health`.
- Role toggle changes account mode.
- Upgrade buttons create an active stylist application and switch the account to stylist mode.
- Wardrobe Wear buttons update the virtual outfit.
- Style Me generates a stylist request response.
- Mall wishlist button updates the request panel.
- Add Photo adds a wardrobe item.
- Post Fit creates a persisted social feed post.
- Open Competition creates a persisted styling competition.
- Refreshing after backend actions keeps saved JSON state.
- GitHub Pages loads the hosted API instead of falling back to the static demo.
- Supabase-backed state store seeds, migrates, and upserts state without network calls in unit tests.
- Mobile layout remains usable.

Backend unit coverage:

- profile role and measurements
- wardrobe creation and image upload validation
- outfit selection
- scan capture
- style request validation and plan persistence
- wishlist accept/discard behavior
- stylist upgrade application
- social posts and comments
- messages
- mall registration
- competition creation and entry submission
- stylist follow/unfollow behavior
- Supabase state store fallback seeding and migration behavior
