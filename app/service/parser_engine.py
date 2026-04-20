import re

def parse_extracted_text(text_lines: list[str]) -> dict:
   
    full_text = " ".join(text_lines).upper()
    print("full_text",full_text)
    result = {
        "document_type": "Unknown",
        "fields": {
            "name": None,
            "pan_number": None,
            "aadhar_number": None,
            "voter_id": None,
            "dob_or_age": None,
            "gender": None,
            "address": None
        }
    }

    #  Detect Document Type
    is_pan = "INCOME TAX DEPARTMENT" in full_text or re.search(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', full_text)
    is_aadhar = "UNIQUE IDENTIFICATION" in full_text or "AADHAAR" in full_text or re.search(r'\d{4} \d{4} \d{4}', full_text)
    is_voter = "ELECTION COMMISSION" in full_text or "VOTER" in full_text
    
    if is_pan: result["document_type"] = "PAN Card"
    elif is_aadhar: result["document_type"] = "Aadhaar Card"
    elif is_voter: result["document_type"] = "Voter ID"

    #  Main Extraction Loop
    address_lines = []
    address_started = False
    
    noise_keywords = [
        "FATHER", "INDIA", "GOVERNMENT", "TAX", "ADDRESS", "DATE", "BIRTH", 
        "ACCOUNT", "NUMBER", "MALE", "FEMALE", "SIGNATURE", "DEPARTMENT", 
        "INCOME", "HINDI", "ENGLISH", "GOVT", "OF", "CARD", "PERMANENT", 
        "ISSUED", "INFORMATION", "SHRI", "LATE", "SMT", "DETAILS AS ON"
    ]

    potential_names = []

    for i, line in enumerate(text_lines):
        line = line.strip()
        if not line: continue
        upper_line = line.upper()

        # ID Numbers
        if is_pan and not result["fields"]["pan_number"]:
            match = re.search(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', upper_line)
            if match: result["fields"]["pan_number"] = match.group(0)
        
        if is_aadhar and not result["fields"]["aadhar_number"]:
            match = re.search(r'\d{4} \d{4} \d{4}', upper_line)
            if match: result["fields"]["aadhar_number"] = match.group(0)

        # --- Name Detection ---
        if result["fields"]["name"] is None:
            if re.match(r'^[A-Z\s\.]{3,50}$', upper_line) and len(line.split()) >= 2:
                if not any(k in upper_line for k in noise_keywords):
                    potential_names.append(line)

        # --- REFINED DOB LOGIC (Strict) ---
        if not result["fields"]["dob_or_age"]:
            # Only pick date if line has birth-related keywords
            if any(k in upper_line for k in ["DOB", "BIRTH", "YEAR", "जन्म"]):
                dob_match = re.search(r'(\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}|\d{4})', upper_line)
                if dob_match: result["fields"]["dob_or_age"] = dob_match.group(0)

        # --- Gender ---
        if not result["fields"]["gender"]:
            if "MALE" in upper_line and "FEMALE" not in upper_line: result["fields"]["gender"] = "Male"
            elif "FEMALE" in upper_line: result["fields"]["gender"] = "Female"

        # --- ADDRESS EXTRACTION (Cleaned) ---
        if "ADDRESS" in upper_line or "पता" in upper_line:
            address_started = True
            # Check if address starts on the same line
            split_line = re.split(r'ADDRESS[:\s]*', line, flags=re.IGNORECASE)
            if len(split_line) > 1 and split_line[1].strip():
                addr_part = split_line[1].strip()
                if "DETAILS AS ON" not in addr_part.upper():
                    address_lines.append(addr_part)
            continue

        if address_started:
            # Stop condition: Aadhaar Number or End of Document
            if re.search(r'\d{4} \d{4} \d{4}', upper_line):
                address_started = False
            else:
                # Filter out vertical noise like "Details as on..."
                if "DETAILS AS ON" not in upper_line and not re.match(r'^\d{2}/\d{2}/\d{4}$', line):
                    address_lines.append(line)
                
                # If we find a 6-digit Pincode, it's usually the end of the address
                if re.search(r'\b\d{6}\b', upper_line):
                    address_started = False

    # Assign Name
    if not result["fields"]["name"] and potential_names:
        result["fields"]["name"] = potential_names[0]

    if address_lines:
        result["fields"]["address"] = ", ".join(address_lines)

    return result
