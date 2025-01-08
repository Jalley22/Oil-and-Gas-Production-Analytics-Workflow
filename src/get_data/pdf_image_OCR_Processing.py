import os
import logging
from multiprocessing import Pool
from pdf2image import convert_from_path  # Example library for PDF to image conversion
from PIL import Image  # For saving images
import pytesseract  # For OCR

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_file_number(path):
    """Extract a unique identifier or file number from the path."""
    return os.path.splitext(os.path.basename(path))[0]

def convert_pdf_to_images(pdf_path):
    """Convert PDF pages to images."""
    return convert_from_path(pdf_path)

def find_target_page(images, keywords):
    """Find the target page by performing OCR and matching keywords."""
    for image in images:
        ocr_text = pytesseract.image_to_string(image)
        if any(keyword in ocr_text for keyword in keywords):
            return image, ocr_text
    return None, None

def save_target_image(path):
    try:
        # Extract file number
        file_number = extract_file_number(path)

        # Step 1: Convert PDF to images
        images = convert_pdf_to_images(path)

        # Step 2: Find the target page
        keywords = ["Proppant"]
        target_image, ocr_text = find_target_page(images, keywords)

        if target_image:
            # Save the target image
            output_path = f"{file_number}.png"
            target_image.save(output_path, "PNG")
            logging.info(f"Saved target image for {path} as {output_path}")
        else:
            logging.warning(f"No target page found in {path}")

    except Exception as e:
        logging.error(f"Error processing {path}: {e}", exc_info=True)

def process_files_in_parallel(file_list):
    """Process a list of files in parallel."""
    with Pool() as pool:
        pool.map(save_target_image, file_list)

if __name__ == "__main__":
    # Define the list of files to process
    files_dev = ["example1.pdf", "example2.pdf"]  

    # Process files in parallel
    process_files_in_parallel(files_dev)
