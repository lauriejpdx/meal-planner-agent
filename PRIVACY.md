# Privacy Policy — Weekly Meal Planner

_Last updated: November 8, 2026_

Weekly Meal Planner is a personal, single-user tool built and operated by the owner of this repository. It is not offered to the public.

## What data it accesses
The agent runs in the owner's own logged-in Chrome browser (Claude in Chrome). It reads the owner's saved Pinterest pins and Instagram saves, recipe pages, and Whole Foods (Amazon) and Instacart search results and carts. It uses no API keys or access tokens. Weather comes from Open-Meteo and Zippopotam by ZIP code.

## What it changes
After the owner approves a plan, it only adds items to the owner's Whole Foods and Instacart carts. It never checks out, pays, posts, comments, likes, or saves anything.

## Storage and sharing
- The recipe index is cached in the browser's local storage. The profile, pantry, and weekly plans stay in local `data/` and `output/` folders, which are excluded from this repository.
- Recipe and grocery content is sent to an AI model provider (Anthropic) solely to generate the meal plan.
- Nothing is sold, shared, or disclosed to third parties.

## Data deletion
The owner can delete the local folders and clear the browser's site data at any time.

## Contact
For questions, open an issue in this repository.
