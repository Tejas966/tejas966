# Setup (5 minutes)

1. On GitHub, open your profile repo **Tejas966/Tejas966**. If you already have `tejas966`, rename it to match your username exactly, or create `Tejas966`.
2. Upload everything from this folder to the repo root (keep the folder structure, including `.github/workflows`). `dist/face.svg` is already rendered from your photo; `dist/stats.svg` is created by the first workflow run.
3. Open the **Actions** tab, choose **update-profile**, then **Run workflow**. After that, stats refresh every 6 hours and whenever you change `assets/` or `scripts/`.
4. Optional: to count private contributions, create a classic personal access token with `read:user`, add it as a repo secret named `STATS_TOKEN`.
5. Pin your best repos: profile → **Customize your pins** → capstone, QuickPay, SatarkAI.

## Change the face

Replace `assets/face.png` and re-run the workflow. Best results: front-facing, face filling the frame, plain background, no phone covering the face. Options: `--cols 120` for more detail, `--invert yes|no|auto`, `--seconds 5` for slower typing.

## Preview locally

    pip install pillow
    python scripts/ascii_face.py
    python scripts/stats.py --demo    # fake data; real data needs GH_LOGIN and GH_TOKEN
