# Product Spec

## Roles

- Normal user: builds wardrobe, creates virtual self, requests styling help, buys wishlist items, posts outfits.
- Stylist/influencer: paid or free styling, specialty tags, portfolio posts, followers, client history, competitions.
- Mall/shop: paid company registration, product listings, inventory, wishlist purchase flow.

## Main Flows

1. Sign in and create size profile.
2. Upload wardrobe photos.
3. Create virtual body/lookalike.
4. Dress virtual self from wardrobe.
5. Ask stylist for help with existing clothes, partial replacements, or full outfit rebuild.
6. Stylist uses user wardrobe plus mall inventory to create wishlist.
7. User accepts, buys, or discards wishlist.
8. Purchased items enter wardrobe in the stylist's outfit order.
9. Users post outfits, like, comment, message, and follow stylists.
10. Users can open paid competitions for multiple stylists.

## Frontend MVP Scope

- Responsive app shell with dark navigation rail, setup progress, wardrobe rail, virtual styling canvas, stylist request form, stylist marketplace, mall wishlist, social feed, and competition panel.
- Backend-aware UI for role switching, wardrobe filtering, adding wardrobe photos, applying clothes to the virtual body, marking 360 scan captured, sending stylist requests, and accepting/discarding wishlist items.
- Screenshots are stored in `assets/screenshots/dashboard.png` and `assets/screenshots/mobile-dashboard.png`.

## Backend MVP Scope

- `server.py` runs the static frontend and API from one local server.
- `src/backend.py` stores app data in `data/app_state.json` and exposes service methods for profile role, wardrobe, selected outfit, scan capture, style requests, and wishlist decisions.
- The backend reuses the rule-based style engine to create real outfit plans from the saved wardrobe.
- GitHub Pages still works as a static frontend and falls back to demo state when `/api/state` is unavailable.

## Future Integrations

- Managed database
- Real authentication and sessions
- Object storage for wardrobe photos and scan videos
- Camera/body scan
- Guided 360 body video capture for avatar generation and outfit sizing
- Clothing segmentation
- Product catalog APIs
- Payments and escrow
- Messaging
- Moderation
- Creator analytics

## 360 Avatar Capture Notes

A production version can let a user record a short 360 body video to create a
more accurate avatar for outfit sizing. The safe flow should include:

- explicit consent before capture
- guidance for lighting, fitted clothing, distance from camera, and full-body framing
- front, side, back, and slow-turn views
- body landmark detection and measurement extraction
- privacy controls for deleting scans and disabling stylist access
- secure storage and encryption for body images/videos
- clear disclaimer that generated sizing is an estimate, not a tailoring guarantee
