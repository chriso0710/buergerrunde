#!/usr/bin/env python3
"""
Bulk cleanup of Heuweiler location files.
- Remove inline links from body text
- Standardize headings
- Remove Kontaktinfos/Referenzen/Geo-Koordinaten sections
- Shorten address in frontmatter
- Clean title (remove "(Heuweiler)" suffixes)
- Remove phone numbers and addresses from body
- Add standard headings to entries without headings
"""

import os
import re
import glob

LOCATIONS_DIR = '/Users/co/projects/buergerrunde/_locations'

# Section heading patterns to REMOVE entirely
REMOVE_SECTION_PATTERNS = [
    r'(Wichtige\s+)?Kontaktinfos',
    r'Referenzen.*',
    r'Geo[-\s]?[Kk]oordinaten.*',
    r'Besonderer\s+Hinweis.*',
]

# Heading standardization: pattern -> replacement
HEADING_STANDARDIZATION = [
    (r'Beschreibung(\s+des\s+Ortes)?$', 'Beschreibung'),
    (r'Bedeutung\s*/?\s*Verwendungszweck(\s+für\s+Heuweiler)?$', 'Bedeutung'),
    (r'Besonderheiten\s*(oder\s+interessante\s+Fakten|/\s*interessante\s+Fakten)?$', 'Besonderheiten'),
    (r'Geschichte$', 'Geschichte'),
]


def should_remove_section(heading_text):
    """Check if a section should be removed based on its heading."""
    text = heading_text.strip()
    for pattern in REMOVE_SECTION_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    return False


def standardize_heading(heading_text):
    """Standardize a heading to one of the four standard forms."""
    text = heading_text.strip()
    for pattern, replacement in HEADING_STANDARDIZATION:
        if re.match(pattern, text, re.IGNORECASE):
            return replacement
    return text


def clean_text(text):
    """Clean body text: remove links, phones, addresses, etc."""
    # 1. Remove citation links: ([text](url)) or ( [text](url) )
    text = re.sub(r'\s*\(\[([^\]]*)\]\([^)]+\)\)', '', text)

    # 2. Convert remaining inline links to plain text: [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # 3. Remove standalone URLs (http/https)
    text = re.sub(r'\s*https?://\S+', '', text)

    # 4. Remove phone patterns in body
    # "Tel. 07666 91345-0", "Telefon: +49 7666 ...", "Tel.: (07666) ..."
    text = re.sub(r'[;,]?\s*(Tel\.?|Telefon)\s*(\([^)]*\))?\s*:?\s*[\+\d\s\-/()]+(?=[\s,;.\n]|$)', '', text)

    # 5. Remove "Adresse:" lines
    text = re.sub(r'[-*]?\s*Adresse:\s*[^\n]+', '', text)

    # 6. Remove "E-Mail:" lines
    text = re.sub(r'[-*]?\s*E[-‑]?[Mm]ail[^:\n]*:\s*\S+@\S+[^\n]*', '', text)

    # 7. Remove "Öffnungszeiten" lines
    text = re.sub(r'[-*]?\s*Öffnungszeiten[^\n]*', '', text)

    # 8. Remove "Fax:" lines
    text = re.sub(r'[-*]?\s*Fax:\s*[^\n]+', '', text)

    # 9. Remove standalone "Hinweis:" / "(Anmerkung:" paragraphs
    text = re.sub(r'\n+(?:Hinweis\b|Anmerkung\b|\(Anmerkung\b)[^\n]*(?:\n(?![#\n]).*)*', '\n', text)

    # 10. Remove "Weitere Hinweise:" paragraphs
    text = re.sub(r'\n+Weitere\s+Hinweise:[^\n]*(?:\n(?![#\n]).*)*', '\n', text)

    # 11. Clean up orphaned bullet points (lines that are just "- " or "* " after content removal)
    text = re.sub(r'\n\s*[-*]\s*\n', '\n', text)
    text = re.sub(r'\n\s*[-*]\s*$', '', text)

    # 12. Clean up lines that are just whitespace or punctuation
    text = re.sub(r'\n\s*[,;.]\s*\n', '\n', text)

    # 13. Clean up double spaces
    text = re.sub(r'  +', ' ', text)

    # 14. Clean up multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text


def shorten_address(addr):
    """Shorten address to just street + house number."""
    if not addr:
        return '""'

    # Remove quotes
    addr = addr.strip().strip('"').strip("'")

    if not addr:
        return '""'

    # Remove PLZ and everything after: ", 79194 ..."
    addr = re.sub(r',?\s*79194.*', '', addr)
    # Remove "Baden-Württemberg" and "Deutschland"
    addr = re.sub(r',?\s*(Baden[-–‑]?Württemberg|Deutschland).*', '', addr, flags=re.IGNORECASE)
    # Remove known prefixes
    addr = re.sub(r'^"?Gemeindeverwaltung\s+Heuweiler\s*,\s*', '', addr)
    addr = re.sub(r'^"?Kommandant:\s*', '', addr)
    # Remove "Dorfplatz, " prefix when followed by actual street address
    addr = re.sub(r'^Dorfplatz\s*,\s*(?=\w+straße)', '', addr)

    addr = addr.strip().strip(',').strip()

    # If only town name remains, empty it
    if addr.lower() in ['heuweiler', 'heuweiler.']:
        return '""'

    return addr


def process_frontmatter(fm_text):
    """Process frontmatter: shorten address, clean title, fix category quoting."""
    # Shorten address
    def replace_address(match):
        val = match.group(1)
        shortened = shorten_address(val)
        return f'address: {shortened}'
    fm_text = re.sub(r'^(address:)\s*(.*)$', lambda m: f'address: {shorten_address(m.group(2))}', fm_text, flags=re.MULTILINE)

    # Clean title: remove "(Heuweiler)" or "(AltName, Heuweiler)" suffixes
    def replace_title(match):
        line = match.group(0)
        line = re.sub(r'\s*\(Heuweiler\)', '', line)
        line = re.sub(r'\s*\([^,)]+,\s*Heuweiler\)', '', line)
        return line
    fm_text = re.sub(r'^title:.*$', replace_title, fm_text, flags=re.MULTILINE)

    # Fix quoted category to unquoted
    fm_text = re.sub(r'^(category:)\s*"(.*?)"', r'\1 \2', fm_text, flags=re.MULTILINE)

    return fm_text


def extract_description_from_frontmatter(fm_text):
    """Extract the description field value from frontmatter text."""
    match = re.search(r'^description:\s*(.*?)(?:\n\S|\n$)', fm_text, re.MULTILINE | re.DOTALL)
    if match:
        desc = match.group(1).strip()
        # Handle multi-line description (continuation lines start with spaces)
        desc = re.sub(r'\n\s+', ' ', desc)
        desc = desc.strip().strip('"').strip("'")
        return desc
    return ''


def process_body(body, fm_text=''):
    """Process body content: remove sections, standardize headings, clean text."""
    # Check if body has any #### headings
    has_headings = bool(re.search(r'^####\s+', body, re.MULTILINE))

    if not has_headings:
        # Short-format entry (no headings) - restructure
        text = body.strip()
        if text:
            text = clean_text(text).strip()
            desc = extract_description_from_frontmatter(fm_text)
            parts = []
            if desc:
                parts.append(f'#### Beschreibung\n\n{desc}\n')
            parts.append(f'#### Geschichte\n\n{text}\n')
            return '\n' + '\n'.join(parts)
        return '\n'

    # Split body into sections based on #### headings
    segments = re.split(r'(^####\s+.+$)', body, flags=re.MULTILINE)

    result_parts = []
    i = 0
    while i < len(segments):
        if i == 0:
            # Text before first heading
            pre_text = clean_text(segments[0]).strip()
            if pre_text:
                result_parts.append(pre_text + '\n')
            i += 1
        else:
            heading_line = segments[i]
            content = segments[i + 1] if i + 1 < len(segments) else ''

            # Extract heading text (after ####)
            heading_match = re.match(r'^####\s+(.+)$', heading_line)
            if not heading_match:
                i += 2
                continue

            heading_text = heading_match.group(1).strip()

            # Check if section should be removed
            if should_remove_section(heading_text):
                i += 2
                continue

            # Standardize heading
            std_heading = standardize_heading(heading_text)

            # Clean content
            cleaned = clean_text(content).strip()

            if cleaned:
                result_parts.append(f'\n#### {std_heading}\n\n{cleaned}\n')

            i += 2

    result = '\n'.join(result_parts) if result_parts else ''

    # Final cleanup
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = result.rstrip()

    return '\n' + result + '\n' if result.strip() else '\n'


def process_file(filepath):
    """Process a single location file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split at --- markers
    match = re.match(r'^---\n(.*?\n)---\n?(.*)', content, re.DOTALL)
    if not match:
        print(f"  SKIP (no frontmatter): {os.path.basename(filepath)}")
        return

    frontmatter = match.group(1)
    body = match.group(2)

    # Process
    new_fm = process_frontmatter(frontmatter)
    new_body = process_body(body, new_fm)

    # Reassemble
    result = f'---\n{new_fm}---{new_body}'

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(result)


def main():
    files = sorted(glob.glob(os.path.join(LOCATIONS_DIR, '*.md')))
    print(f"Processing {len(files)} location files...\n")

    for filepath in files:
        filename = os.path.basename(filepath)
        print(f"  {filename}")
        try:
            process_file(filepath)
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\nDone! Processed {len(files)} files.")


if __name__ == '__main__':
    main()
