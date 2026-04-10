---
id: "018"
title: "Social Media Facebook Instagram Twitter LIVE"
stage: green
date: "2026-03-23"
surface: agent
model: claude-sonnet-4-6
feature: gold-tier
branch: main
user: Syed Abdullah Zaidi
command: "implement facebook instagram twitter selenium poster like linkedin"
labels: ["gold-tier", "facebook", "instagram", "twitter", "selenium", "live"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - golden_tier_external_world/actions/facebook/poster.py
  - golden_tier_external_world/actions/facebook/__init__.py
  - golden_tier_external_world/actions/instagram/poster.py
  - golden_tier_external_world/actions/instagram/__init__.py
  - golden_tier_external_world/actions/twitter/poster.py
  - golden_tier_external_world/actions/twitter/__init__.py
  - run_social_live.py
tests:
  - python -c "from golden_tier_external_world.actions.facebook.poster import SeleniumFacebookPoster; from golden_tier_external_world.actions.twitter.poster import SeleniumTwitterPoster; from golden_tier_external_world.actions.instagram.poster import SeleniumInstagramPoster"
---

## Prompt

credentials ready hai .env me dekho or implement karo ye saar kaam bhi wesy hi hona chahiye jisy humny linkdin ka kiya hai matlb nazar araha tha kia kaam kar rahy hai asy hi

## Response

LinkedIn Selenium pattern ko follow karte hue 3 social media posters implement kiye:

**SeleniumFacebookPoster:**
- login(): Chrome headless=False, facebook.com pe email/pass se login
- post(): "What's on your mind?" box JS text walker se dhundta hai (same as LinkedIn), modal editor find, text type, React events dispatch, Post click
- Screenshots: facebook_login.png, facebook_feed.png, facebook_modal.png, facebook_typed.png, facebook_posted.png

**SeleniumTwitterPoster:**
- login(): x.com/i/flow/login, 2-step (email → Next → password → Log in), unusual activity check handle karta hai
- tweet(): data-testid="tweetTextarea_0" compose box, data-testid="tweetButtonInline" Post button, 280 char limit handle
- Screenshots: twitter_step1.png, twitter_home.png, twitter_typed.png, twitter_posted.png

**SeleniumInstagramPoster:**
- login(): instagram.com/accounts/login, cookie popup + save login popup dismiss, headless=False
- post(): "Create" button dhundta hai, file input ke through image upload, multiple Next clicks (crop steps), caption field, Share button
- Auto-generates image via Pillow if no image_path given (installed: Pillow 12.1.1)
- Screenshots at every step

**run_social_live.py:** 3-step demo — Facebook → Twitter → Instagram, same HITL simulation, full summary

**Packages installed:** Pillow 12.1.1
