from flask import Flask, request, render_template, send_from_directory
import fitz  # PyMuPDF
import re
from io import BytesIO
import os

app = Flask(__name__)

# Regular expressions to detect Aadhaar numbers, phone numbers, birthdates, and PAN card numbers
aadhaar_regex = r'\b\d{4}\s?\d{4}\s?\d{4}\b'
phone_regex = r'\b\d{10}\b'  # Simple regex for 10-digit phone numbers
birthdate_regex = r'\b\d{2}/\d{2}/\d{4}\b'  # Simple regex for MM/DD/YYYY birthdates
pan_regex = r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'  # Simple regex for PAN card numbers

def mask_aadhaar(text):
    """Mask the first 8 digits of an Aadhaar number."""
    def masker(match):
        return 'XXXXXXXX' + match.group()[-4:]  # Masks first 8 digits, shows last 4 digits
    return re.sub(aadhaar_regex, masker, text)

def mask_phone(text):
    """Mask a phone number."""
    def masker(match):
        return 'XXXXXXXXXX'  # Masks the entire phone number
    return re.sub(phone_regex, masker, text)

def mask_birthdate(text):
    """Mask a birthdate."""
    def masker(match):
        return 'XX/XX/XXXX'  # Masks the entire birthdate
    return re.sub(birthdate_regex, masker, text)

def mask_pan(text):
    """Mask a PAN card number."""
    def masker(match):
        return match.group(0)[:5] + 'XXXX'  # Mask last 4 characters of PAN
    return re.sub(pan_regex, masker, text)

def is_aadhaar_card(text):
    """Determine if the document is an Aadhaar card based on content analysis."""
    return re.search(aadhaar_regex, text) is not None

def is_pan_card(text):
    """Determine if the document is a PAN card based on content analysis."""
    return re.search(pan_regex, text) is not None

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files.get('file')
        doc_type = request.form.get('docType')

        if file is None or file.filename == '':
            return render_template('no_file.html')

        original_pdf = BytesIO(file.read())
        
        # Check if the file is empty
        if original_pdf.getvalue() == b'':
            return 'Uploaded file is empty', 400

        try:
            pdf_document = fitz.open(stream=original_pdf, filetype="pdf")
        except Exception as e:
            return f'Error opening PDF file: {e}', 400
        
        output_pdf = BytesIO()
        detected_aadhaar = False
        detected_pan = False

        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text = page.get_text("dict")

            if doc_type == 'aadhaar':
                for block in text["blocks"]:
                    if block["type"] == 0:  # This block is text
                        for line in block["lines"]:
                            for span in line["spans"]:
                                span_text = span["text"]
                                if is_aadhaar_card(span_text):
                                    detected_aadhaar = True
                                    break
                            if detected_aadhaar:
                                break
                        if detected_aadhaar:
                            break

            elif doc_type == 'pan':
                for block in text["blocks"]:
                    if block["type"] == 0:  # This block is text
                        for line in block["lines"]:
                            for span in line["spans"]:
                                span_text = span["text"]
                                if is_pan_card(span_text):
                                    detected_pan = True
                                    break
                            if detected_pan:
                                break
                        if detected_pan:
                            break

            # Mask the document if conditions are met
            if (doc_type == 'aadhaar' and detected_aadhaar) or \
               (doc_type == 'pan' and detected_pan) or \
               doc_type not in ['aadhaar', 'pan']:

                for block in text["blocks"]:
                    if block["type"] == 0:  # This block is text
                        for line in block["lines"]:
                            for span in line["spans"]:
                                span_text = span["text"]
                                
                                # Detect the area for masking
                                rect = fitz.Rect(span["bbox"])
                                
                                if re.search(aadhaar_regex, span_text):
                                    # Draw white rectangle over the original text
                                    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                                    # Insert masked text at the exact position
                                    masked_text = mask_aadhaar(span_text)
                                    page.insert_text((rect.x0, rect.y1), masked_text, fontsize=span["size"], color=(0, 0, 0))
                                
                                if re.search(phone_regex, span_text):
                                    # Draw white rectangle over the original text
                                    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                                    # Insert masked text at the exact position
                                    masked_text = mask_phone(span_text)
                                    page.insert_text((rect.x0, rect.y1), masked_text, fontsize=span["size"], color=(0, 0, 0))
                                
                                if re.search(birthdate_regex, span_text):
                                    # Draw white rectangle over the original text
                                    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                                    # Insert masked text at the exact position
                                    masked_text = mask_birthdate(span_text)
                                    page.insert_text((rect.x0, rect.y1), masked_text, fontsize=span["size"], color=(0, 0, 0))
                                
                                if re.search(pan_regex, span_text):
                                    # Draw white rectangle over the original text
                                    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                                    # Insert masked text at the exact position
                                    masked_text = mask_pan(span_text)
                                    page.insert_text((rect.x0, rect.y1), masked_text, fontsize=span["size"], color=(0, 0, 0))

        pdf_document.save(output_pdf, deflate=True)
        output_pdf.seek(0)

        # Save the masked PDF
        masked_path = 'static/masked_document.pdf'
        with open(masked_path, 'wb') as f:
            f.write(output_pdf.read())

        if (doc_type == 'aadhaar' and not detected_aadhaar) or (doc_type == 'pan' and not detected_pan):
            return render_template('no_document.html')

        return render_template('masked_preview.html')

    return render_template('index.html')

if __name__ == '__main__':
    # Ensure 'static' directory exists
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(debug=True)
