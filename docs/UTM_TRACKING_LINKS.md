# UTM Tracking Links — StoreMD

Tous les liens de distribution StoreMD avec UTM prêts à copier-coller.
Base URL : `https://storemd.vercel.app`

Les events `page_view` et `install_start` capturés par `backend/app/api/routes/tracking.py` parsent ces paramètres et les propagent jusqu'à la ligne `merchants` à l'install. L'admin dashboard (`/dashboard/admin/analytics`) les agrège par source et campagne.

> **Convention globale** — tout en minuscules, `snake_case`, jamais d'espaces, jamais d'accents. Les valeurs qui contiennent plusieurs mots sont séparées par `_`.

---

## 1. Twitter / X — `utm_source=twitter`

| Placement | Lien |
|-----------|------|
| Bio | `https://storemd.vercel.app/?utm_source=twitter&utm_medium=bio&utm_campaign=profile&utm_content=bio_link` |
| Post organique (feature drop) | `https://storemd.vercel.app/?utm_source=twitter&utm_medium=organic&utm_campaign=feature_launch&utm_content=post` |
| Thread | `https://storemd.vercel.app/?utm_source=twitter&utm_medium=organic&utm_campaign=thread&utm_content=thread_cta` |
| Reply (engagement) | `https://storemd.vercel.app/?utm_source=twitter&utm_medium=organic&utm_campaign=reply&utm_content=reply_cta` |
| Ads — traffic campaign | `https://storemd.vercel.app/?utm_source=twitter&utm_medium=paid&utm_campaign=ads_traffic&utm_content=ad_variant_a` |
| Ads — conversion campaign | `https://storemd.vercel.app/?utm_source=twitter&utm_medium=paid&utm_campaign=ads_install&utm_content=ad_variant_a` |

---

## 2. LinkedIn — `utm_source=linkedin`

| Placement | Lien |
|-----------|------|
| Bio (Featured link) | `https://storemd.vercel.app/?utm_source=linkedin&utm_medium=bio&utm_campaign=profile&utm_content=featured` |
| Post organique | `https://storemd.vercel.app/?utm_source=linkedin&utm_medium=organic&utm_campaign=post&utm_content=cta_post` |
| Article LinkedIn | `https://storemd.vercel.app/?utm_source=linkedin&utm_medium=organic&utm_campaign=article&utm_content=article_cta` |
| Commentaire | `https://storemd.vercel.app/?utm_source=linkedin&utm_medium=organic&utm_campaign=comment&utm_content=comment_cta` |
| DM (outreach 1-to-1) | `https://storemd.vercel.app/?utm_source=linkedin&utm_medium=dm&utm_campaign=outreach&utm_content=dm_share` |
| Ads — sponsored content | `https://storemd.vercel.app/?utm_source=linkedin&utm_medium=paid&utm_campaign=ads_sponsored&utm_content=ad_variant_a` |
| Ads — message ads | `https://storemd.vercel.app/?utm_source=linkedin&utm_medium=paid&utm_campaign=ads_inmail&utm_content=ad_variant_a` |

---

## 3. Reddit — `utm_source=reddit`

| Placement | Lien |
|-----------|------|
| r/shopify — post | `https://storemd.vercel.app/?utm_source=reddit&utm_medium=organic&utm_campaign=r_shopify&utm_content=post` |
| r/shopify — commentaire | `https://storemd.vercel.app/?utm_source=reddit&utm_medium=organic&utm_campaign=r_shopify&utm_content=comment` |
| r/ecommerce — post | `https://storemd.vercel.app/?utm_source=reddit&utm_medium=organic&utm_campaign=r_ecommerce&utm_content=post` |
| r/ecommerce — commentaire | `https://storemd.vercel.app/?utm_source=reddit&utm_medium=organic&utm_campaign=r_ecommerce&utm_content=comment` |
| r/entrepreneur — post | `https://storemd.vercel.app/?utm_source=reddit&utm_medium=organic&utm_campaign=r_entrepreneur&utm_content=post` |
| r/entrepreneur — commentaire | `https://storemd.vercel.app/?utm_source=reddit&utm_medium=organic&utm_campaign=r_entrepreneur&utm_content=comment` |

---

## 4. TikTok — `utm_source=tiktok`

| Placement | Lien |
|-----------|------|
| Bio | `https://storemd.vercel.app/?utm_source=tiktok&utm_medium=bio&utm_campaign=profile&utm_content=bio_link` |
| Vidéo organique | `https://storemd.vercel.app/?utm_source=tiktok&utm_medium=organic&utm_campaign=video&utm_content=video_cta` |
| Ads — traffic | `https://storemd.vercel.app/?utm_source=tiktok&utm_medium=paid&utm_campaign=ads_traffic&utm_content=ad_variant_a` |
| Ads — conversion | `https://storemd.vercel.app/?utm_source=tiktok&utm_medium=paid&utm_campaign=ads_install&utm_content=ad_variant_a` |

---

## 5. YouTube — `utm_source=youtube`

| Placement | Lien |
|-----------|------|
| Bio (About / Channel link) | `https://storemd.vercel.app/?utm_source=youtube&utm_medium=bio&utm_campaign=channel&utm_content=about_link` |
| Description vidéo | `https://storemd.vercel.app/?utm_source=youtube&utm_medium=organic&utm_campaign=video_description&utm_content=description_link` |
| Commentaire épinglé | `https://storemd.vercel.app/?utm_source=youtube&utm_medium=organic&utm_campaign=pinned_comment&utm_content=comment_cta` |
| Community post | `https://storemd.vercel.app/?utm_source=youtube&utm_medium=organic&utm_campaign=community_post&utm_content=community_cta` |
| End screen / card | `https://storemd.vercel.app/?utm_source=youtube&utm_medium=organic&utm_campaign=video_endscreen&utm_content=endscreen_cta` |

---

## 6. Instagram — `utm_source=instagram`

| Placement | Lien |
|-----------|------|
| Bio (link-in-bio) | `https://storemd.vercel.app/?utm_source=instagram&utm_medium=bio&utm_campaign=profile&utm_content=bio_link` |
| Story (sticker link) | `https://storemd.vercel.app/?utm_source=instagram&utm_medium=organic&utm_campaign=story&utm_content=story_sticker` |
| Reels caption | `https://storemd.vercel.app/?utm_source=instagram&utm_medium=organic&utm_campaign=reels&utm_content=caption_cta` |
| Ads — feed | `https://storemd.vercel.app/?utm_source=instagram&utm_medium=paid&utm_campaign=ads_feed&utm_content=ad_variant_a` |
| Ads — stories | `https://storemd.vercel.app/?utm_source=instagram&utm_medium=paid&utm_campaign=ads_stories&utm_content=ad_variant_a` |

---

## 7. Facebook — `utm_source=facebook`

| Placement | Lien |
|-----------|------|
| Page (about / link) | `https://storemd.vercel.app/?utm_source=facebook&utm_medium=bio&utm_campaign=page&utm_content=about_link` |
| Post organique | `https://storemd.vercel.app/?utm_source=facebook&utm_medium=organic&utm_campaign=post&utm_content=post_cta` |
| Groupe Shopify merchants | `https://storemd.vercel.app/?utm_source=facebook&utm_medium=organic&utm_campaign=group_shopify&utm_content=group_post` |
| Groupe ecommerce | `https://storemd.vercel.app/?utm_source=facebook&utm_medium=organic&utm_campaign=group_ecommerce&utm_content=group_post` |
| Ads — traffic | `https://storemd.vercel.app/?utm_source=facebook&utm_medium=paid&utm_campaign=ads_traffic&utm_content=ad_variant_a` |
| Ads — conversion | `https://storemd.vercel.app/?utm_source=facebook&utm_medium=paid&utm_campaign=ads_install&utm_content=ad_variant_a` |

---

## 8. Email — `utm_source=email`

| Placement | Lien |
|-----------|------|
| Newsletter — header CTA | `https://storemd.vercel.app/?utm_source=email&utm_medium=newsletter&utm_campaign=weekly_digest&utm_content=header_cta` |
| Newsletter — footer CTA | `https://storemd.vercel.app/?utm_source=email&utm_medium=newsletter&utm_campaign=weekly_digest&utm_content=footer_cta` |
| Cold email — merchant outreach | `https://storemd.vercel.app/?utm_source=email&utm_medium=cold&utm_campaign=merchant_outreach&utm_content=cta_main` |
| Cold email — agency outreach | `https://storemd.vercel.app/?utm_source=email&utm_medium=cold&utm_campaign=agency_outreach&utm_content=cta_main` |
| Partenariat / co-marketing | `https://storemd.vercel.app/?utm_source=email&utm_medium=partner&utm_campaign=partnership&utm_content=partner_cta` |

---

## 9. Product Hunt — `utm_source=producthunt`

| Placement | Lien |
|-----------|------|
| Launch day — page Product Hunt | `https://storemd.vercel.app/?utm_source=producthunt&utm_medium=referral&utm_campaign=launch_day&utm_content=ph_listing` |
| Launch day — first comment (maker) | `https://storemd.vercel.app/?utm_source=producthunt&utm_medium=referral&utm_campaign=launch_day&utm_content=ph_maker_comment` |
| Post-launch — gallery | `https://storemd.vercel.app/?utm_source=producthunt&utm_medium=referral&utm_campaign=post_launch&utm_content=ph_gallery` |

---

## 10. Communautés — `utm_source=<community>`

| Placement | Lien |
|-----------|------|
| Shopify Community (forums) | `https://storemd.vercel.app/?utm_source=shopify_community&utm_medium=organic&utm_campaign=forum_post&utm_content=post_cta` |
| IndieHackers — post | `https://storemd.vercel.app/?utm_source=indiehackers&utm_medium=organic&utm_campaign=post&utm_content=post_cta` |
| IndieHackers — milestone | `https://storemd.vercel.app/?utm_source=indiehackers&utm_medium=organic&utm_campaign=milestone&utm_content=milestone_cta` |
| Hacker News — Show HN | `https://storemd.vercel.app/?utm_source=hackernews&utm_medium=organic&utm_campaign=show_hn&utm_content=hn_post` |
| Hacker News — commentaire | `https://storemd.vercel.app/?utm_source=hackernews&utm_medium=organic&utm_campaign=comment&utm_content=hn_comment` |
| Dev.to — article | `https://storemd.vercel.app/?utm_source=devto&utm_medium=organic&utm_campaign=article&utm_content=article_cta` |
| Dev.to — commentaire | `https://storemd.vercel.app/?utm_source=devto&utm_medium=organic&utm_campaign=comment&utm_content=comment_cta` |

---

## 11. QR Code — `utm_source=qrcode`

| Placement | Lien |
|-----------|------|
| Events — conférence | `https://storemd.vercel.app/?utm_source=qrcode&utm_medium=offline&utm_campaign=event_conference&utm_content=qr_badge` |
| Events — meetup | `https://storemd.vercel.app/?utm_source=qrcode&utm_medium=offline&utm_campaign=event_meetup&utm_content=qr_flyer` |
| Salon Shopify / e-com | `https://storemd.vercel.app/?utm_source=qrcode&utm_medium=offline&utm_campaign=tradeshow&utm_content=qr_booth` |
| Sticker / goodie | `https://storemd.vercel.app/?utm_source=qrcode&utm_medium=offline&utm_campaign=sticker&utm_content=qr_swag` |

> **Astuce** — génère le QR code à partir de l'URL finale (incluant UTM) pour que le scan préserve l'attribution.

---

## 12. Signature email — `utm_source=signature`

| Placement | Lien |
|-----------|------|
| Signature personnelle (founder) | `https://storemd.vercel.app/?utm_source=signature&utm_medium=email&utm_campaign=founder_signature&utm_content=signature_link` |
| Signature support | `https://storemd.vercel.app/?utm_source=signature&utm_medium=email&utm_campaign=support_signature&utm_content=signature_link` |
| Signature team | `https://storemd.vercel.app/?utm_source=signature&utm_medium=email&utm_campaign=team_signature&utm_content=signature_link` |

---

## Convention de nommage

Toutes les valeurs sont `lowercase_snake_case`. Pas d'espaces, pas d'accents, pas de majuscules, pas de caractères spéciaux hors `_` et `-`.

| Paramètre | Rôle | Valeurs canoniques |
|-----------|------|--------------------|
| `utm_source` | D'où vient le visiteur (plateforme) | `twitter`, `linkedin`, `reddit`, `tiktok`, `youtube`, `instagram`, `facebook`, `email`, `producthunt`, `shopify_community`, `indiehackers`, `hackernews`, `devto`, `qrcode`, `signature` |
| `utm_medium` | Type de canal | `bio`, `organic`, `paid`, `newsletter`, `cold`, `partner`, `dm`, `referral`, `offline`, `email` |
| `utm_campaign` | Initiative / groupe | `profile`, `post`, `thread`, `reply`, `comment`, `article`, `feature_launch`, `ads_traffic`, `ads_install`, `ads_feed`, `ads_stories`, `r_shopify`, `r_ecommerce`, `r_entrepreneur`, `group_shopify`, `group_ecommerce`, `video_description`, `pinned_comment`, `community_post`, `video`, `reels`, `story`, `weekly_digest`, `merchant_outreach`, `agency_outreach`, `partnership`, `launch_day`, `post_launch`, `forum_post`, `milestone`, `show_hn`, `event_conference`, `event_meetup`, `tradeshow`, `sticker`, `founder_signature`, `support_signature`, `team_signature` |
| `utm_content` | Créatif / placement précis (A/B) | `bio_link`, `post`, `post_cta`, `thread_cta`, `reply_cta`, `comment_cta`, `cta_post`, `cta_main`, `featured`, `dm_share`, `story_sticker`, `caption_cta`, `header_cta`, `footer_cta`, `about_link`, `description_link`, `endscreen_cta`, `community_cta`, `ad_variant_a`, `ad_variant_b`, `ph_listing`, `ph_maker_comment`, `ph_gallery`, `hn_post`, `hn_comment`, `article_cta`, `milestone_cta`, `qr_badge`, `qr_flyer`, `qr_booth`, `qr_swag`, `signature_link`, `partner_cta` |
| `utm_term` | Mot-clé / cible (réservé aux ads paid) | `keyword_<mot>`, `audience_<name>` |

### Règles

1. **Jamais de `utm_source` manquant** — un lien sans source pollue les rapports (tout tombe dans `(direct)`).
2. **`utm_medium` reste dans la liste canonique** — n'invente pas de nouvelle valeur sans l'ajouter ici d'abord.
3. **`utm_content` sert pour l'A/B** — change-le pour chaque variante créative (`ad_variant_a` vs `ad_variant_b`) afin de mesurer laquelle convertit.
4. **`utm_term` uniquement pour les ads** — ne l'utilise pas sur de l'organique, sinon le dashboard ads/organic est biaisé.
5. **Préserve l'ordre** — `source → medium → campaign → content → term` (question d'hygiène, pas obligatoire).
6. **Un lien = une campagne** — ne recycle pas un lien organique en ads, tu perds la granularité.

### Où ça atterrit

- **Capture** — `frontend/src/app/layout.tsx` charge le tracker `/tracking/pageview` avec `utm_*` en query params.
- **Persistance** — `backend/app/api/routes/tracking.py` écrit dans `page_views`.
- **Install attribution** — `backend/app/api/routes/auth.py` copie les UTM du state Redis vers la colonne `merchants.utm_*` sur le premier callback OAuth.
- **Agrégation** — `backend/app/api/routes/admin.py::admin_analytics` produit `visits_by_source`, `visits_by_campaign`, et le tableau funnel `landing_visits → cta_clicks → install_starts → install_completes → paid_conversions`.
- **Affichage** — `frontend/src/app/(dashboard)/dashboard/admin/analytics/page.tsx`.
