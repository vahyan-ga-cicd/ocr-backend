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
        "ISSUED", "INFORMATION", "SHRI", "LATE", "SMT", "DETAILS AS ON",
        "ENROLMENT", "AADHAA", "UNIQUE", "AUTHORITY"
    ]

    # Denial list for informational boilerplate (case-insensitive)
    address_deny_list = [
        "AADHAAR HELPS", "GOVERNMENT BENEFITS", "KEEP YOUR MOBILE", "EMAIL ID UPDATED",
        "DATE OF BIRTH/DOB:", "MALE/ MALE", "MALE / MALE", "FEMALE / FEMALE", 
        "YOUR AADHAAR NO", "AADHAAR NUMBER", "INFORMATION", "DETAILS AS ON",
        "ADDRESS SHOULD BE UPDATED", "AUTHORITY OF INDIA", "SHOULD BE UPDATED",
        "AFTER EVERY 10 YEARS", "ENROLMENT", "UNIQUE IDENTIFICATION",
        "S/O", "W/O", "D/O", "C/O"
    ]

    potential_names = []

    # Pre-scan for DOB to help find Name
    dob_line_index = -1
    for i, line in enumerate(text_lines):
        if any(k in line.upper() for k in ["DOB:", "BIRTH:", "DOB", "YEAR"]):
            dob_line_index = i
            break

    for i, line in enumerate(text_lines):
        line = line.strip()
        if not line: continue
        upper_line = line.upper()

        # ID Numbers
        if is_pan and not result["fields"]["pan_number"]:
            match = re.search(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', upper_line)
            if match: result["fields"]["pan_number"] = match.group(0)
        
        if is_aadhar and not result["fields"]["aadhar_number"]:
            # Flexible spaces: handles 9627 7431 8215 or 9627 74318215 or 962774318215
            match = re.search(r'\d{4}\s*\d{4}\s*\d{4}', upper_line)
            if match: result["fields"]["aadhar_number"] = match.group(0)

        # --- Name Detection (Improved) ---
        if result["fields"]["name"] is None:
            # Look for lines that look like a name
            # 1. Must be length 5+ 
            # 2. Must be uppercase/spaces/dots
            if re.match(r'^[A-Z\s\.]{5,50}$', upper_line) and len(line.split()) >= 2:
                if not any(k in upper_line for k in noise_keywords):
                    # Discard fragments (like "H R H" or "X Y Z")
                    single_letters = [w for w in line.split() if len(w) == 1]
                    if len(single_letters) >= 2:
                        continue
                        
                    priority = 0
                    
                    # Context Check: Near DOB
                    if dob_line_index != -1 and abs(i - dob_line_index) <= 2:
                        priority = 3
                    
                    # Context Check: Immediately after "TO"
                    if i > 0 and "TO" in text_lines[i-1].upper():
                        priority = 5
                    
                    # Context Check: Immediately before "S/O" or "W/O" or "C/O"
                    if i < len(text_lines) - 1 and any(k in text_lines[i+1].upper() for k in ["S/O", "W/O", "C/O"]):
                        priority = 5
                        
                    potential_names.append({"text": line, "priority": priority})

        # --- REFINED DOB LOGIC (Strict) ---
        if not result["fields"]["dob_or_age"]:
            if any(k in upper_line for k in ["DOB", "BIRTH", "YEAR", "जन्म"]):
                dob_match = re.search(r'(\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}|\d{4})', upper_line)
                if dob_match: result["fields"]["dob_or_age"] = dob_match.group(0)

        # --- Gender ---
        if not result["fields"]["gender"]:
            if "MALE" in upper_line and "FEMALE" not in upper_line: result["fields"]["gender"] = "Male"
            elif "FEMALE" in upper_line: result["fields"]["gender"] = "Female"

        # --- ADDRESS EXTRACTION (Cleaned) ---
        if not address_started:
            if "ADDRESS" in upper_line or "पता" in upper_line:
                address_started = True
                split_line = re.split(r'ADDRESS[:\s]*', line, flags=re.IGNORECASE)
                if len(split_line) > 1 and split_line[1].strip():
                    addr_part = split_line[1].strip()
                    if not any(deny in addr_part.upper() for deny in address_deny_list):
                        address_lines.append(addr_part)
                continue
            
            # Secondary trigger: Relation markers (if address hasn't started yet)
            # Using regex for S/O, W/O, D/O, C/O with optional spaces/colons
            elif re.search(r'\b[SWDC]/O\s*[:\s]*', upper_line):
                address_started = True
                # Start address but ignore the S/O line as requested by the user
                continue

        if address_started:
            # Stop condition
            if re.search(r'\d{4} \d{4} \d{4}', upper_line) or re.search(r'\b\d{6}\b', upper_line):
                if re.search(r'\b\d{6}\b', upper_line):
                    # Include the line with pincode if it's the pincode line
                    if not any(deny in upper_line for deny in address_deny_list):
                        address_lines.append(line)
                address_started = False
            else:
                # Filter out legal boilerplate
                if not any(deny in upper_line for deny in address_deny_list):
                    if not any(k in upper_line for k in noise_keywords):
                        # Don't grab lines that are just numbers (like ID numbers)
                        if not re.match(r'^\d+\s\d+\s\d+$', line):
                            address_lines.append(line)

    # Assign Name (Pick highest priority)
    if potential_names:
        potential_names.sort(key=lambda x: x['priority'], reverse=True)
        result["fields"]["name"] = potential_names[0]["text"]

    if address_lines:
        # Final Surgical Cleanup for Address
        final_address_lines = []
        for addr_line in address_lines:
            cleaned = addr_line
            # Strip forbidden phrases (case-insensitive)
            for deny in address_deny_list:
                # Use regex for word-boundary or partial cleanup
                cleaned = re.sub(re.escape(deny), "", cleaned, flags=re.IGNORECASE)
            
            # Clean up dangling commas and extra spaces
            cleaned = re.sub(r'^\W+|\W+$', '', cleaned).strip()
            # Remove "SHOULD BE UPDATED IN" and similar fragments if they weren't caught
            cleaned = re.sub(r'(?i)SHOULD\s+BE\s+UPDATED.*$', '', cleaned).strip()
            
            if cleaned and len(cleaned) > 2:
                final_address_lines.append(cleaned)
        
        result["fields"]["address"] = ", ".join(final_address_lines)

    return result
