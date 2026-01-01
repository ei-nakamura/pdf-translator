"""Test redact without fill to preserve background"""
import fitz

# Open source PDF
doc = fitz.open(r'c:\Users\inani\Documents\src\pdf-translator\Google_Prompting_repaired.pdf')
page = doc[0]

# Test: Add redact without fill (None)
# This should remove text but preserve the background
bbox = (152, 41, 460, 69)  # Google Prompting Essentials title
rect = fitz.Rect(*bbox)

# Try without fill
page.add_redact_annot(rect, fill=False)
page.apply_redactions()

# Now write new text
tw = fitz.TextWriter(page.rect)
font_path = r"C:\Windows\Fonts\meiryo.ttc"
font = fitz.Font(fontfile=font_path)
tw.append((152, 60), "Google プロンプティング エッセンシャル", font=font, fontsize=20)
tw.write_text(page, color=(0, 0, 0))

doc.save("test_redact_no_fill.pdf")
doc.close()
print("Saved to test_redact_no_fill.pdf")
