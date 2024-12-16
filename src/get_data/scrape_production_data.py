
import os
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd

# URLs
BASE_URL = "https://www.dmr.nd.gov/oilgas/findwellsvw.asp"
PRODUCTION_URL = "https://www.dmr.nd.gov/oilgas/basic/getwellprod.asp"

def get_operators():
    """Fetch the list of operators from the dropdown menu."""
    response = requests.get(BASE_URL)
    if response.status_code != 200:
        raise Exception(f"Failed to access {BASE_URL}, status code {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")
    operator_dropdown = soup.find("select", {"name": "ddmOperator"})
    options = operator_dropdown.find_all("option")

    operators = {option.text.strip(): option["value"].strip() for option in options if option["value"]}
    print(f"Found {len(operators)} operators.")
    return operators

def get_file_numbers(operator_value):
    """Fetch file numbers for a specific operator."""
    payload = {"ddmOperator": operator_value}
    response = requests.post(BASE_URL, data=payload)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch file numbers for operator {operator_value}")

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"summary": "Well Log search results table"})
    rows = table.find_all("tr")[1:]  # Skip header row

    file_numbers = []
    for row in rows:
        cols = row.find_all("td")
        if cols:
            file_number = cols[0].text.strip()
            file_numbers.append(file_number)

    print(f"Found {len(file_numbers)} file numbers for operator.")
    return file_numbers

def parse_well_metadata(metadata_tag):
    """
    Parse metadata directly from a BeautifulSoup Tag object.
    Args:
        metadata_tag: BeautifulSoup Tag object containing the metadata.
    Returns:
        dict: Parsed metadata as key-value pairs.
    """
    metadata = {}
    
    # Find the main <div> containing the metadata
    div = metadata_tag.find("div")
    if not div:
        return metadata  # Return empty if no metadata is found
    inner_html = metadata_tag.decode_contents()
    NDIC_regex = re.compile(r"'?([\w\s]+):\s*'?\s*,?\s*<b>(?:<span.*?>)?(.*?)(?:</span>)?</b>", re.VERBOSE)     
    # Apply the regex
    matches = NDIC_regex.findall(inner_html)
    # Convert matches to dictionary
    result = {key.strip(): value.strip() for key, value in matches}

    return result

def get_production_data(file_number):
    """
    Submit file number and scrape production data.
    """
    payload = {"FileNumber": file_number}
    response = requests.post(PRODUCTION_URL, data=payload)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch production data for File No: {file_number}")

    soup = BeautifulSoup(response.text, "html.parser")
    # Locate production data rows
    table = soup.find("table", {"summary": "Well data content table"})  # Find production table
    if not table:
        print(f"No production data found for File No: {file_number}")
        return []
    
    rows = table.find_all("tr")
    first_row = rows[0].find_all("td")    
    metadata_tag = first_row[0] if len(first_row) >= 1 else None    
    #parse well header metadata
    try:
        well_header_data = parse_well_metadata(metadata_tag)
        well_header_data["FileNumber"] = file_number
    except Exception as e:
         print(f"Error parsing file: {file_number}, error: {e}")
    # Extract production data    
    production_data = []
    for row in rows[1:]:
        cols = [col.text.strip() for col in row.find_all("td")]
        production_data.append([file_number] + cols)

    return well_header_data, production_data

def main():
    # Ensure output directory exists     
    os.makedirs("data/raw", exist_ok=True)    
    # Get available operators
    operators = get_operators()
    print("Available Operators:")
    for name in operators.keys():
        print(f"- {name}")
    
    # user select an operator
    while True:
        operator_name = input("Enter the operator name from the list above: ").strip()
        if operator_name in operators:
            break
        print("Invalid operator name. Please select from the list provided.")
    operator_value = operators.get(operator_name)
    if not operator_value:
        raise Exception(f"Operator {operator_name} not found.")
    print(f"Fetching data for operator: {operator_name}")
    # Get all file numbers
    file_numbers = get_file_numbers(operator_value)    
    # Initialize a list to store all data
    all_well_header_data = []
    all_production_data = []
    
    for file_number in file_numbers:
        print(f"Fetching production data for File No: {file_number}")
        well_data,production_data = get_production_data(file_number)
        if well_data:
            all_well_header_data.append(well_data)
        all_production_data.extend(production_data)

    # Convert to DataFrame
    #import pdb; pdb.set_trace()
    welldata_df = pd.DataFrame(all_well_header_data)
    production_columns = ["File Number", "Pool", "Date", "Days", "BBLS Oil", "Runs", "BBLS Water", "MCF Prod", "MCF Sold", "Vent/Flare"]
    production_df = pd.DataFrame(all_production_data, columns=production_columns)
    
    # Save to CSV
    output_file = "data/raw/ndic_production_data.csv"
    production_df.to_csv("data/raw/ndic_production_data.csv", index=False)
    welldata_df.to_csv("data/raw/ndic_wellheader_data.csv", index=False)
    print(f"Data saved to {output_file}")

if __name__ == "__main__":
    main()