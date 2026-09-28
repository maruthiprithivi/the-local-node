# Brand artwork

Three directions are available in `concepts/`: Signal, Workshop, and Atlas. Each has a clean background and a `-banner.jpg` preview with editable text added by `render.py`. The backgrounds came from Gemini; `generate.mjs` stores their prompts and can make fresh variants with `GEMINI_API_KEY` set in your environment. Never put the key in this repository.

The source backgrounds are 16:9, so they can be cropped for a GitHub repository preview or a YouTube thumbnail. Keep titles and faces as separate layers: a YouTube channel banner has a narrow central safe area, while a thumbnail needs a short, high contrast title. Regenerate the clean background first, then place text for each format in a design tool or with `render.py`.

To redraw the supplied title previews, install Pillow and run `python3 assets/brand/render.py` from the repository root. The supplied images are ready to use without these tools.
