"""
NOTE:
Processing OCR images from PDFs is inherently a difficult and resource-intensive task. 
The process involves converting PDF pages to images, running OCR to extract text, 
and then analyzing or cleaning the extracted data. This workflow can be extremely slow, 
especially for scanned documents or PDFs with high page counts or complex layouts.

Some factors contributing to the difficulty:
1. **OCR Accuracy**: OCR tools may struggle with low-quality scans, unusual fonts, or handwritten text.
2. **Performance**: Processing is computationally expensive and memory-intensive, particularly for large PDFs.
3. **Error Handling**: Extracted text may require significant post-processing to clean and structure properly.

Considerations for improving performance in future iterations:
- Use multiprocessing or distributed computing frameworks like Dask or Apache Spark.
- Optimize image preprocessing to improve OCR accuracy (e.g., resizing, thresholding, or de-skewing).
- Experiment with alternative OCR tools or APIs for better performance.
- Use specialized software to handle OCR and PDF processing.

Despite these challenges, this script is designed to give an idea of how some complicated it can be to enrich the
dataset with completion data from well files.
"""
from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
from pytesseract import image_to_string
from PIL import Image

import pandas as pd
import os
import re
import glob
import random 

def convert_pdf_to_images(pdf_path, output_folder=None):
    """
    Converts all pages of a PDF to images.
    
    Parameters:
        pdf_path (str): Path to the PDF file.
        output_folder (str, optional): Folder to save images (optional).
        
    Returns:
        list: List of PIL Image objects for each page.
    """
    images = convert_from_path(pdf_path, fmt='png', output_folder=output_folder)
    return images

# Python virtual env was having a difficult time finding it in my path
os.environ["PATH"] += os.pathsep + r"C:\Program Files\poppler-24.08.0\Library\bin"
# Set the path to Tesseract OCR executable 
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\alley\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def extract_file_number(file_path):
    """
    Extracts the file number from the PDF file path.

    Parameters:
        file_path (str): Path to the PDF file.

    Returns:
        str: Extracted file number.
    """
    base_name = os.path.basename(file_path)  # Get the file name (e.g., W10450.pdf)
    return base_name.lstrip("W").rstrip(".pdf")  # Extract the number after 'W' and before '.pdf'

def ocr_image(image):
    """
    Performs OCR on the given image.
    
    Parameters:
        image (PIL.Image): Image object to process with OCR.

    Returns:
        str: OCR result as text.
    """
    return image_to_string(image)

def clean_row(row):
    """
    Cleans a row of text to remove unwanted characters and normalize the format.
    
    Parameters:
        row (str): Raw OCR text row.
        
    Returns:
        str: Cleaned row.
    """
    # Remove non-alphanumeric characters except spaces and numbers
    row = re.sub(r"[^\w\s./]", "", row)

    # Remove standalone dots or periods (but keep valid decimals)
    row = re.sub(r"\s\.\s", " ", row)
    # Remove underscores
    row = row.replace("_", "")

    # Strip leading/trailing spaces
    return row.strip()

# find the target page
def find_target_page(images, keywords):
    """
    Finds the target page containing specified keywords.
    
    Parameters:
        images (list): List of PIL Image objects.
        keywords (list of str): Keywords to search for in OCR text.
        
    Returns:
        PIL.Image: Image of the identified page.
    """
    for index, image in enumerate(images):       

        ocr_text = ocr_image(image)
        #if any(keyword in ocr_text for keyword in keywords):
        if "Bakken" in ocr_text and "Sand Frac" in ocr_text and "Stages" in ocr_text and "Proppant" in ocr_text:
            print(f"Target page found: Page {index + 1}")            
            return image, ocr_text
        
    raise ValueError("No target page found with the specified keywords.")
def is_numeric(value):
    """
    Checks if a value is numeric.
    
    Parameters:
        value (str): The value to check.
    
    Returns:
        bool: True if the value is numeric, False otherwise.
    """
    try:
        float(value)
        return True
    except ValueError:
        return False

# parse the ocr text

def parse_completion_data(ocr_text, verbose=False):
    """
    Parses OCR text to extract completion data into a structured format.
    
    Parameters:
        ocr_text (str): OCR result as text.

    Returns:
        pd.DataFrame: Parsed data in a structured format.
    """
    # Split OCR text into lines
    lines = ocr_text.split("\n")
    # Filter rows that contain relevant keywords
    filtered_rows = [line for line in lines if "Bakken" in line or "Sand Frac" in line]
    parsed_data = []

    # Define a dictionary to hold field names and values
    current_record = {}

    # Loop through lines, pairing header lines with value lines
    for i, row in enumerate(filtered_rows):
        line = row.strip()  # Clean up whitespace
        line = clean_row(line)
        
        # Detect if this line is a header line
        if "Bakken"in line:
            
            tokens = line.split()            
            if len(tokens) >= 7:
                current_record = {}
                if len(tokens) > 0:
                    current_record["Date"] = tokens[0] if "/" in tokens[0] else None                     
                    current_record["Formation"] = tokens[1] if tokens[1].isalpha() else None                        
                    current_record["Top (Ft)"] = tokens[2] if tokens[2].isdigit() else None                        
                    current_record["Bottom (Ft)"] = tokens[3] if tokens[3].isdigit() else None                       
                    current_record["Stages"] = tokens[4].strip("()") if tokens[4].isdigit() and int(tokens[4]) < 100 else None                      
                    current_record["Volume"] = tokens[5] if tokens[5].replace(".", "").isdigit() and float(tokens[5]) > 30000 else None                       
                    current_record["Volume Units"] = tokens[6] if tokens[6].isalpha() else None

            else: 
                current_record = {}

                current_record["Volume Units"] = tokens[len(tokens)-1] if tokens[len(tokens)-1].isalpha() else None
                if len(tokens) > 0:
                    current_record["Date"] = tokens[0] if "/" in tokens[0] else None

                if len(tokens) > 1:
                    current_record["Formation"] = tokens[1] if tokens[1].isalpha() else None                                                

                if len(tokens) >= 4:
                    if(
                        (tokens[4].isdigit())
                        and (int(tokens[4]) < 100) 
                    ):
                        current_record["Stages"] = (min(int(tokens[4].strip("()")),int(tokens[3],int(tokens[2]))))
                    else:
                        None
                if len(tokens) > 2:
                    current_record["Top (Ft)"] = tokens[2] if int(tokens[3]) > int(tokens[2])  else None
                if len(tokens) >= 3:
                    if (
                        tokens[3].isdigit() 
                        and (current_record.get("Top (Ft)") is None or int(current_record.get("Top (Ft)")) < int(tokens[3]))
                        and int(tokens[3]) < 30000
                    ):
                        current_record["Bottom (Ft)"] = tokens[3]    
                    else:
                        current_record["Bottom (Ft)"] = tokens[2]
                
                
                
                if len(tokens) >= 5:
                    current_record["Volume"] = tokens[len(tokens)-2] if  float(tokens[len(tokens)-2]) > 30000 else None                   

        elif "Sand Frac" in line:
            tokens = line.split()
            current_record.update ({
                "Type Treatment": "Sand Frac",
                "Lbs Proppant": tokens[2] if len(tokens) > 1 and tokens[2].replace(".", "").isdigit() else None,
                "Max Pressure (PSI)": tokens[3] if len(tokens) > 2 and tokens[3].replace(".", "").isdigit() else None,
                "Max Rate (BBLS/Min)": tokens[4] if len(tokens) > 3 and tokens[4].replace(".", "").isdigit() else None,
            })
        
    if current_record:
        parsed_data.append(current_record)
                    
    return pd.DataFrame(parsed_data)

# pipeline 
def extract_completion_data_from_pdf(pdf_path):
    """
    Extracts completion data from a PDF file.
    
    Parameters:
        pdf_path (str): Path to the PDF file.

    Returns:
        pd.DataFrame: Structured completion data.
    """
    try:
        # Extract file number 
        file_number = extract_file_number(pdf_path)

        # Step 1: Convert PDF to images
        images = convert_pdf_to_images(pdf_path)

        # Step 2: Find the target page
        keywords = ["Proppant"]
        target_image, ocr_text = find_target_page(images, keywords)

        # Step 3: Parse OCR text into structured data
        completion_data = parse_completion_data(ocr_text)
        print(completion_data.head())
        completion_data["File_Number"] = file_number

        return completion_data
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of failure



files = glob.glob("data/raw/well_files/*.pdf",recursive=True)
files_dev = random.sample(files,10)

all_data = []
    
for file in files:
    try:
        # Extract data from the current PDF
        df = extract_completion_data_from_pdf(file)
        
        # Append the DataFrame to the list
        all_data.append(df)
    except Exception as e:
        print(f"Error processing {file}: {e}")

# Combine all DataFrames into a single DataFrame
combined_df = pd.concat(all_data, ignore_index=True)