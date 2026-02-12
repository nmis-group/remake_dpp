import pypdfium2 as pdfium

# Load a document
pdf = pdfium.PdfDocument("/mnt/c/Users/yyb19161/Documents/Self-Certification_Form.pdf")

# Loop over pages and render
for i in range(len(pdf)):
    page = pdf[i]
    image = page.render(scale=2).to_pil()
    image.save(f"output2_{i:03d}.jpg")