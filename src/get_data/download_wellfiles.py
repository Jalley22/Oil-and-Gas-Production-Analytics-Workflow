import os
import requests
import pandas as pd

def get_pdf_url(file_number):
    """
    Constructs the URL for a given well file number.
    """
    prefix = str(file_number)[:2]  # First two digits of the file number
    return f"https://www.dmr.nd.gov/oilgas/basic/bwfiles/{prefix}/W{file_number}.pdf"

def download_pdf(file_number, output_dir):
    """
    Downloads the PDF for a given well file number and saves it to the output directory.
    """
    url = get_pdf_url(file_number)
    response = requests.get(url, stream=True)

    if response.status_code == 200:
        output_path = os.path.join(output_dir, f"W{file_number}.pdf")
        with open(output_path, "wb") as pdf_file:
            pdf_file.write(response.content)
        print(f"Downloaded: {output_path}")
    else:
        print(f"Failed to download {file_number}: HTTP {response.status_code}")

def main(file_numbers, output_dir="data/raw/well_files/"):
    """
    Main function to automate PDF downloads for multiple well file numbers.
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Download PDFs for all file numbers
    for file_number in file_numbers:
        download_pdf(file_number, output_dir)

# Example usage
well_header_df = pd.read_csv('./data/raw/ndic_wellheader_data.csv')
file_numbers = sorted(well_header_df['NDIC File No'].unique())  
main(file_numbers)
