"""Test auto-fitting text to bbox"""
import fitz

def fit_text_to_bbox(text, font, bbox, max_font_size=24, min_font_size=6):
    """
    Calculate font size that fits text within bbox.
    Returns (font_size, lines) where lines is the wrapped text.
    """
    x0, y0, x1, y1 = bbox
    width = x1 - x0
    height = y1 - y0

    for font_size in range(int(max_font_size), int(min_font_size) - 1, -1):
        lines = []
        current_line = ""

        for char in text:
            test_line = current_line + char
            text_width = font.text_length(test_line, fontsize=font_size)

            if text_width <= width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char

        if current_line:
            lines.append(current_line)

        # Check if all lines fit in height
        line_height = font_size * 1.2
        total_height = len(lines) * line_height

        if total_height <= height:
            return font_size, lines

    # Return minimum size even if it doesn't fit
    return min_font_size, lines


# Test with a sample text
doc = fitz.open(r'c:\Users\inani\Documents\src\pdf-translator\Google_Prompting_repaired.pdf')
page = doc[0]

font_path = r"C:\Windows\Fonts\meiryo.ttc"
font = fitz.Font(fontfile=font_path)

# Title bbox: (152, 41, 460, 69) - width:309, height:29
# Original: "Google Prompting Essentials" (27 chars)
# Translated: "Google プロンプティング エッセンシャル"

original_text = "Google Prompting Essentials"
translated_text = "Google プロンプティング エッセンシャル"
bbox = (152, 41, 460, 69)

print(f"Original text: {original_text} ({len(original_text)} chars)")
print(f"Translated text: {translated_text} ({len(translated_text)} chars)")
print(f"Bbox: width={bbox[2]-bbox[0]:.0f}, height={bbox[3]-bbox[1]:.0f}")
print()

# Calculate original text width at size 24 (approx original size)
orig_width = font.text_length(original_text, fontsize=24)
trans_width = font.text_length(translated_text, fontsize=24)
print(f"Original width at 24pt: {orig_width:.0f}")
print(f"Translated width at 24pt: {trans_width:.0f}")
print()

# Fit text
font_size, lines = fit_text_to_bbox(translated_text, font, bbox, max_font_size=24)
print(f"Fitted font size: {font_size}")
print(f"Lines: {lines}")
print()

# Apply redact and write
rect = fitz.Rect(*bbox)
page.add_redact_annot(rect, fill=False)
page.apply_redactions()

# Write text
tw = fitz.TextWriter(page.rect)
y = bbox[1] + font_size  # Start at baseline
for line in lines:
    tw.append((bbox[0], y), line, font=font, fontsize=font_size)
    y += font_size * 1.2

tw.write_text(page, color=(0, 0, 0))

doc.save("test_auto_fit.pdf")
doc.close()
print("Saved to test_auto_fit.pdf")
