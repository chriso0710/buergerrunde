#!/usr/bin/env python3
"""
Resolve merge conflicts in location files.
Strategy:
- Frontmatter: take remote coords/address/image, keep our title/category/website cleanups
- Body: if remote has significantly different (hand-written) content, take remote and re-clean
- Body: if remote is just AI text with links re-added, keep ours
- Always remove Kontaktinfos, Referenzen, etc. sections from final result
"""

import os
import re
import subprocess

LOCATIONS_DIR = '_locations'

def get_ours_theirs(filepath):
    """Extract ours and theirs versions from a conflicted file."""
    with open(filepath, 'r') as f:
        content = f.read()

    # We need to reconstruct ours and theirs from conflict markers
    # This is complex, so let's use git show
    basename = os.path.basename(filepath)
    relpath = f'_locations/{basename}'

    try:
        ours = subprocess.check_output(['git', 'show', f':2:{relpath}'], stderr=subprocess.DEVNULL).decode('utf-8')
    except:
        ours = None
    try:
        theirs = subprocess.check_output(['git', 'show', f':3:{relpath}'], stderr=subprocess.DEVNULL).decode('utf-8')
    except:
        theirs = None

    return ours, theirs

def parse_file(content):
    """Parse a location file into frontmatter dict and body string."""
    m = re.match(r'^---\n(.*?\n)---\n?(.*)', content, re.DOTALL)
    if not m:
        return {}, content
    fm_text = m.group(1)
    body = m.group(2)

    # Simple frontmatter parsing
    fm = {}
    fm['_raw'] = fm_text
    for key in ['title', 'latitude', 'longitude', 'category', 'description', 'address', 'website', 'image', 'image_copyright', 'generated_by', 'generated_at', 'notes']:
        match = re.search(rf'^({key}):\s*(.*?)(?=\n\S|\n$|\Z)', fm_text, re.MULTILINE | re.DOTALL)
        if match:
            fm[key] = match.group(2).strip()

    return fm, body

def clean_address(addr):
    """Clean address: remove PLZ, Baden-Württemberg, etc."""
    if not addr:
        return '""'
    addr = addr.strip().strip('"').strip("'")
    if not addr:
        return '""'
    addr = re.sub(r',?\s*79194.*', '', addr)
    addr = re.sub(r',?\s*(Baden[-–‑]?Württemberg|Deutschland).*', '', addr, flags=re.IGNORECASE)
    addr = addr.strip().strip(',').strip()
    if addr.lower() in ['heuweiler', 'heuweiler.', '']:
        return '""'
    return addr

def clean_title(title):
    """Remove (Heuweiler) and , Heuweiler suffixes."""
    title = title.strip().strip('"')
    title = re.sub(r'\s*\(Heuweiler\)\s*$', '', title)
    # Don't remove ", Heuweiler" if it was already removed in ours
    if title.endswith(', Heuweiler'):
        title = title[:-len(', Heuweiler')]
    return title

def clean_body(text):
    """Clean body text (same as cleanup script)."""
    # Remove citation links
    text = re.sub(r'\s*\(\[([^\]]*)\]\([^)]+\)\)', '', text)
    # Convert inline links to plain text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove standalone URLs
    text = re.sub(r'\s*https?://\S+', '', text)
    # Remove phone patterns
    text = re.sub(r'[;,]?\s*(Tel\.?|Telefon)\s*(\([^)]*\))?\s*:?\s*[\+\d\s\-/()]+(?=[\s,;.\n]|$)', '', text)
    # Remove Adresse: lines
    text = re.sub(r'[-*]?\s*Adresse:\s*[^\n]+', '', text)
    # Remove E-Mail: lines (but keep contextual email mentions)
    text = re.sub(r'[-*]?\s*E[-‑]?[Mm]ail[^:\n]*:\s*\S+@\S+[^\n]*', '', text)
    # Remove Fax: lines
    text = re.sub(r'[-*]?\s*Fax:\s*[^\n]+', '', text)
    # Remove orphaned bullet points
    text = re.sub(r'\n\s*[-*]\s*\n', '\n', text)
    text = re.sub(r'\n\s*[-*]\s*$', '', text)
    # Clean punctuation-only lines
    text = re.sub(r'\n\s*[,;.]\s*\n', '\n', text)
    # Clean double spaces
    text = re.sub(r'  +', ' ', text)
    # Clean multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text

REMOVE_SECTION_PATTERNS = [
    r'(Wichtige\s+)?Kontaktinfos',
    r'Referenzen.*',
    r'Quellen\s*/?\s*Referenzen.*',
    r'Referenzen\s+zu\s+Quellen.*',
    r'Geo[-\s]?[Kk]oordinaten.*',
    r'Anmerkung\s+zu\s+Geo.*',
    r'Koordinaten.*(?:Hinweis|Adresse).*',
    r'Hinweise\s+zur\s+Lage.*',
    r'Besonderer\s+Hinweis.*',
    r'Sportheim.*',
]

HEADING_MAP = {
    r'Beschreibung(\s+des\s+Ortes)?$': 'Beschreibung',
    r'Bedeutung\s*/?\s*(Verwendungszweck)?(\s+für\s+Heuweiler)?$': 'Bedeutung',
    r'Bedeutung\s+für\s+Heuweiler$': 'Bedeutung',
    r'Besonderheiten\s*(oder\s+interessante\s+Fakten|/\s*interessante\s+Fakten)?$': 'Besonderheiten',
    r'Besonderheiten\s*/\s*interessante\s+Fakten$': 'Besonderheiten',
    r'Geschichte$': 'Geschichte',
    r'Öffnungszeiten\s*/\s*Nutzung$': 'Öffnungszeiten / Nutzung',
}

def should_remove_section(heading):
    for pat in REMOVE_SECTION_PATTERNS:
        if re.match(pat, heading.strip(), re.IGNORECASE):
            return True
    return False

def standardize_heading(heading):
    text = heading.strip()
    for pat, repl in HEADING_MAP.items():
        if re.match(pat, text, re.IGNORECASE):
            return repl
    return text

def process_body(body):
    """Process body: remove sections, standardize headings, clean text."""
    has_headings = bool(re.search(r'^####\s+', body, re.MULTILINE))
    if not has_headings:
        return '\n' + clean_body(body).strip() + '\n'

    segments = re.split(r'(^####\s+.+$)', body, flags=re.MULTILINE)
    result_parts = []
    i = 0
    while i < len(segments):
        if i == 0:
            pre = clean_body(segments[0]).strip()
            if pre:
                result_parts.append(pre + '\n')
            i += 1
        else:
            heading_line = segments[i]
            content = segments[i + 1] if i + 1 < len(segments) else ''
            hm = re.match(r'^####\s+(.+)$', heading_line)
            if not hm:
                i += 2
                continue
            ht = hm.group(1).strip()
            if should_remove_section(ht):
                i += 2
                continue
            std = standardize_heading(ht)
            cleaned = clean_body(content).strip()
            if cleaned:
                result_parts.append(f'\n#### {std}\n\n{cleaned}\n')
            i += 2

    result = '\n'.join(result_parts) if result_parts else ''
    result = re.sub(r'\n{3,}', '\n\n', result).rstrip()
    return '\n' + result + '\n' if result.strip() else '\n'

def is_hand_written(theirs_body, ours_body):
    """Detect if theirs has hand-written content (significantly different from ours)."""
    # If theirs body is much shorter or much longer, it's likely rewritten
    # Also check if theirs has content not present in ours
    theirs_clean = re.sub(r'\s+', ' ', clean_body(theirs_body)).strip()
    ours_clean = re.sub(r'\s+', ' ', ours_body).strip()

    # Simple heuristic: if less than 50% overlap, consider it hand-written
    theirs_words = set(theirs_clean.lower().split())
    ours_words = set(ours_clean.lower().split())
    if not ours_words:
        return bool(theirs_words)
    overlap = len(theirs_words & ours_words) / max(len(ours_words), 1)
    return overlap < 0.6

def merge_file(filepath):
    """Merge a conflicted file."""
    ours_content, theirs_content = get_ours_theirs(filepath)
    if not ours_content or not theirs_content:
        print(f"  SKIP (can't get versions): {os.path.basename(filepath)}")
        return

    ours_fm, ours_body = parse_file(ours_content)
    theirs_fm, theirs_body = parse_file(theirs_content)

    # Build merged frontmatter
    # Start with ours as base
    merged_fm = ours_fm['_raw']

    # Take theirs coordinates if they have them and differ
    for field in ['latitude', 'longitude']:
        if field in theirs_fm and theirs_fm[field]:
            theirs_val = theirs_fm[field]
            ours_val = ours_fm.get(field, '')
            if theirs_val != ours_val:
                if field in ours_fm and ours_fm[field]:
                    merged_fm = re.sub(
                        rf'^{field}:.*$', f'{field}: {theirs_val}',
                        merged_fm, flags=re.MULTILINE
                    )
                else:
                    # Add after the other coord or after address
                    if field == 'latitude':
                        # Add before longitude or after address
                        if 'longitude' in ours_fm:
                            merged_fm = re.sub(r'^(longitude:)', f'latitude: {theirs_val}\n\\1', merged_fm, flags=re.MULTILINE)
                        else:
                            merged_fm = re.sub(r'^(address:.*$)', f'\\1\nlatitude: {theirs_val}', merged_fm, flags=re.MULTILINE)
                    elif field == 'longitude':
                        merged_fm = re.sub(r'^(latitude:.*$)', f'\\1\nlongitude: {theirs_val}', merged_fm, flags=re.MULTILINE)

    # Take theirs address if more specific, but clean it
    if 'address' in theirs_fm:
        theirs_addr = clean_address(theirs_fm['address'])
        ours_addr = ours_fm.get('address', '""').strip().strip('"').strip("'")
        if theirs_addr != '""' and (not ours_addr or ours_addr == '""'):
            merged_fm = re.sub(r'^address:.*$', f'address: {theirs_addr}', merged_fm, flags=re.MULTILINE)

    # Take theirs image if we don't have one
    if 'image' in theirs_fm:
        theirs_img = theirs_fm['image'].strip().strip('"').strip("'")
        ours_img = ours_fm.get('image', '').strip().strip('"').strip("'")
        if theirs_img and not ours_img:
            merged_fm = re.sub(r'^image:.*$', f'image: {theirs_img}', merged_fm, count=1, flags=re.MULTILINE)

    # Take theirs description if it's shorter/better (hand-written)
    if 'description' in theirs_fm:
        theirs_desc = theirs_fm['description'].strip().strip('"')
        ours_desc = ours_fm.get('description', '').strip().strip('"')
        # If theirs is significantly different and not just reformatted
        if theirs_desc and theirs_desc != ours_desc:
            theirs_words = set(theirs_desc.lower().split())
            ours_words = set(ours_desc.lower().split())
            overlap = len(theirs_words & ours_words) / max(len(ours_words), 1) if ours_words else 0
            if overlap < 0.6:
                # Theirs has a different description - take it
                # Replace in merged_fm
                merged_fm = re.sub(
                    r'^description:.*?(?=\n\S)',
                    f'description: "{theirs_desc}"\n',
                    merged_fm, flags=re.MULTILINE | re.DOTALL
                )

    # Keep our title (cleaned), category, website
    # These are already correct in ours

    # Fix title from theirs if ours cleaned it but theirs has (Heuweiler) pattern
    # Our title should already be clean, so just ensure
    title_match = re.search(r'^title:\s*(.*)$', merged_fm, re.MULTILINE)
    if title_match:
        t = title_match.group(1).strip().strip('"')
        cleaned_t = clean_title(t)
        if cleaned_t != t:
            merged_fm = re.sub(r'^title:.*$', f'title: "{cleaned_t}"', merged_fm, flags=re.MULTILINE)

    # Ensure category is unquoted
    merged_fm = re.sub(r'^(category:)\s*"(.*?)"', r'\1 \2', merged_fm, flags=re.MULTILINE)

    # Decide on body
    if is_hand_written(theirs_body, ours_body):
        # Theirs has hand-written content - take it but clean
        body = process_body(theirs_body)
        source = "theirs (hand-written, cleaned)"
    else:
        # Keep our cleaned body
        body = ours_body
        source = "ours (already cleaned)"

    # Reassemble
    result = f'---\n{merged_fm}---{body}'

    with open(filepath, 'w') as f:
        f.write(result)

    print(f"  {os.path.basename(filepath)}: {source}")

def main():
    # Get list of conflicted files
    result = subprocess.check_output(['git', 'diff', '--name-only', '--diff-filter=U']).decode().strip()
    files = [f for f in result.split('\n') if f.strip()]

    print(f"Resolving {len(files)} conflicted files...\n")

    for f in sorted(files):
        try:
            merge_file(f)
        except Exception as e:
            print(f"  ERROR {f}: {e}")

    print(f"\nDone!")

if __name__ == '__main__':
    main()
