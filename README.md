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

- Production-style responsive frontend shell
- Apple-inspired glass app layout with sidebar, setup progress, virtual styling canvas, and compact controls
- Interactive wardrobe filters, selected fit state, 360 scan completion state, and stylist request state
- Normal/stylist account toggle
- Wardrobe photo-card simulation
- Virtual-you outfit preview
- Style request workflow
- Local JSON backend API with persistent profile, wardrobe, scan, role, style request, wishlist, stylist upgrade, social, messaging, mall registration, and competition state
- Real wardrobe, mall, stylist, and social feed images stored in `assets/photos/`
- Stylist marketplace cards
- Mall wishlist panel
- Social proof feed
- Styling competition card
- Python style-matching engine with tests
- CSV sample style report
- GitHub Pages demo

## Run

Full app with backend:

```bash
python3 server.py
```

Open:

```text
http://127.0.0.1:5180
```

Static frontend only:

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

## API

- `GET /api/health`
- `GET /api/state`
- `POST /api/profile/role`
- `POST /api/profile/measurements`
- `POST /api/stylist/upgrade`
- `POST /api/wardrobe`
- `POST /api/outfit/select`
- `POST /api/scan`
- `POST /api/style-requests`
- `POST /api/wishlist`
- `POST /api/social/posts`
- `POST /api/social/react`
- `POST /api/messages`
- `POST /api/mall/register`
- `POST /api/competitions`
- `POST /api/competitions/entries`
- `POST /api/stylists/follow`
- `POST /api/reset`

## Live Deployment

Live app:

```text
https://switchitup.vercel.app
```

Deployment files:

- `vercel.json` routes `/api/*` to the Python serverless entrypoint in `api/index.py`
- `api/index.py` reuses the local backend handler
- `app.js` reads the optional `<meta name="switchitup-api-base">` value and automatically points GitHub Pages to `https://switchitup.vercel.app`
- `server.py` uses local JSON by default and switches to Supabase persistence when `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are configured

Supabase setup:

1. Create the table with `supabase/schema.sql`.
2. Set Vercel environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - optional `SWITCHITUP_SUPABASE_TABLE`, default `switchitup_state`
   - optional `SWITCHITUP_STATE_ID`, default `production`
3. Redeploy Vercel.

Until Supabase is configured, Vercel uses `/tmp` JSON state as a live MVP fallback.

## Backend Hardening

- Atomic JSON writes with schema migration for newly added state keys
- Supabase/Postgres JSONB state adapter for hosted persistence
- Request body size limit for upload-heavy JSON requests
- Security headers for local API responses
- Configurable data path, host, port, and CORS origin through environment variables
- Upload validation for PNG, JPEG, and WebP data URLs, including size and file signature checks
- Input validation for measurements, stylist plans, mall emails, competition prizes, and social actions
- Unit coverage for wardrobe uploads, style requests, wishlist actions, social posts, messages, mall registration, competitions, follows, and measurement updates

## Image Credits

Image sources are documented in `docs/image-credits.md`.

## Export Report

```bash
PYTHONPATH=. python3 tools/export_sample_report.py
```

## Production Notes

The current app is a functional full-stack MVP with a local JSON backend. A real public production version would replace the JSON store with a managed database, add consent-based body image capture, secure photo storage, product catalog integrations, payments, identity verification for stylists and malls, moderation, privacy controls, and clear AI safety rules.
