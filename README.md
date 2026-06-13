# Teams-Style Initials Placeholder Generator

Command-line Python app that generates avatar placeholder images similar to the default profile placeholders in Teams, Outlook, and other M365 apps.

## What It Generates

- 1,764 PNG files (42 × 42 initial combinations)
- Covers the 26 basic Latin letters plus 16 common French accented letters (À, Â, Æ, Ç, È, É, Ê, Ë, Î, Ï, Ô, Œ, Ù, Û, Ü, Ÿ)
- Filenames like `AA_fb6c917a-4235-4fb1-a406-1db84c6ca8dd.png`, `ÉÇ_fb6c917a-4235-4fb1-a406-1db84c6ca8dd.png`, etc.
- Transparent RGBA background with smooth anti-aliased circle edges (4× supersampling)
- 21 background colors from the Fluent UI `PersonaInitialsColor` palette, deterministically assigned via MD5 hash

## Requirements

- Python 3.9+
- Pillow
- NumPy

## Setup

```powershell
python -m pip install -r requirements.txt
```

## Usage

```powershell
python generate_placeholders.py
```

Optional arguments:

```powershell
python generate_placeholders.py --output-dir output --size 256 --font-size 102 --circle-padding 0
```

Options:

- `--output-dir`: Output folder for PNG files (default: `output`)
- `--size`: Square image size in pixels (default: `256`)
- `--font-size`: Initials font size (default: `102`)
- `--font-path`: Path to a custom `.ttf`/`.ttc` font
- `--circle-padding`: Padding before drawing circle (default: `0`)

## Example

```powershell
python generate_placeholders.py --output-dir generated --size 320 --font-size 128
```

After running, inspect the output directory for all generated images.

## Detecting Generated Placeholders

When these images are uploaded as O365/Teams profile pictures, Exchange re-encodes them as JPEG. The `detect_placeholder.py` script can identify whether a downloaded profile photo is one of the generated placeholders — even after JPEG re-encoding — without needing to know the user's initials.

```powershell
python detect_placeholder.py photo1.jpg photo2.jpg
```

Add `--verbose` for detailed detection info:

```powershell
python detect_placeholder.py downloaded_photo.jpg --verbose
```

The script uses structural analysis (dark corners, palette color matching, color uniformity, and white text detection) to determine if an image matches the pattern of our generated placeholders. It outputs a confidence score and a `PLACEHOLDER` / `NOT placeholder` verdict.

### PowerShell workflow for admins

```powershell
# Download a user's profile photo from Exchange Online
Connect-ExchangeOnline
Get-UserPhoto -Identity "user@domain.com" |
  ForEach-Object { [System.IO.File]::WriteAllBytes("photo.jpg", $_.PictureData) }

# Check if it's a generated placeholder
python detect_placeholder.py photo.jpg
```

## Disclaimer

This project is not affiliated with, supported by, or endorsed by Microsoft. It is provided on an "as is" basis without warranty of any kind.

## License

This project is licensed under the [MIT License](LICENSE).
