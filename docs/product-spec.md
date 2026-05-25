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

## Future Integrations

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
