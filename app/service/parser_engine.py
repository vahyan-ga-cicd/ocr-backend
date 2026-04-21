import re

# --- Constants & Keywords ---
NOISE_KEYWORDS = [
    "FATHER", "INDIA", "GOVERNMENT", "TAX", "ADDRESS", "DATE", "BIRTH", 
    "ACCOUNT", "NUMBER", "MALE", "FEMALE", "SIGNATURE", "DEPARTMENT", 
    "INCOME", "HINDI", "ENGLISH", "GOVT", "OF", "CARD", "PERMANENT", 
    "ISSUED", "INFORMATION", "SHRI", "LATE", "SMT", "DETAILS AS ON",
    "ENROLMENT", "AADHAA", "UNIQUE", "AUTHORITY"
]

ADDRESS_DENY_LIST = [
    "AADHAAR HELPS", "GOVERNMENT BENEFITS", "KEEP YOUR MOBILE", "EMAIL ID UPDATED",
    "DATE OF BIRTH/DOB:", "MALE/ MALE", "MALE / MALE", "FEMALE / FEMALE", 
    "YOUR AADHAAR NO", "AADHAAR NUMBER", "INFORMATION", "DETAILS AS ON",
    "ADDRESS SHOULD BE UPDATED", "AUTHORITY OF INDIA", "SHOULD BE UPDATED",
    "AFTER EVERY 10 YEARS", "ENROLMENT", "UNIQUE IDENTIFICATION",
    "S/O", "W/O", "D/O", "C/O"
]

def parse_extracted_text(text_lines: list[str]) -> dict:
    """Main entry point for parsing extracted text from documents."""
    full_text = " ".join(text_lines).upper()
    print("Parsing document...")
    
    result = {
        "document_type": _detect_document_type(full_text),
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

    # Common extraction for all types
    _extract_generic_fields(text_lines, result)
    
    # Specific cleanup based on type
    if result["document_type"] == "Aadhaar Card":
        _extract_aadhaar_address(text_lines, result)
    
    return result

def _detect_document_type(full_text: str) -> str:
    if "INCOME TAX DEPARTMENT" in full_text or re.search(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', full_text):
        return "PAN Card"
    if "UNIQUE IDENTIFICATION" in full_text or "AADHAAR" in full_text or re.search(r'\d{4} \d{4} \d{4}', full_text):
        return "Aadhaar Card"
    if "ELECTION COMMISSION" in full_text or "VOTER" in full_text:
        return "Voter ID"
    return "Unknown"

def _extract_generic_fields(text_lines: list[str], result: dict):
    """Extracts common fields like ID numbers, Name, DOB, and Gender."""
    doc_type = result["document_type"]
    potential_names = []
    
    # Help name detection by finding DOB first
    dob_index = -1
    for i, line in enumerate(text_lines):
        if any(k in line.upper() for k in ["DOB", "BIRTH", "YEAR"]):
            dob_index = i
            break

    for i, line in enumerate(text_lines):
        line = line.strip()
        if not line: continue
        upper_line = line.upper()

        # 1. ID Numbers
        if doc_type == "PAN Card" and not result["fields"]["pan_number"]:
            match = re.search(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', upper_line)
            if match: result["fields"]["pan_number"] = match.group(0)
        
        if doc_type == "Aadhaar Card" and not result["fields"]["aadhar_number"]:
            match = re.search(r'\d{4}\s*\d{4}\s*\d{4}', upper_line)
            if match: result["fields"]["aadhar_number"] = match.group(0)

        # 2. Name Detection
        if not result["fields"]["name"]:
            if re.match(r'^[A-Z\s\.]{5,50}$', upper_line) and len(line.split()) >= 2:
                if not any(k in upper_line for k in NOISE_KEYWORDS):
                    # Discard fragments
                    if len([w for w in line.split() if len(w) == 1]) < 2:
                        priority = 0
                        if dob_index != -1 and abs(i - dob_index) <= 2: priority = 3
                        if i > 0 and "TO" in text_lines[i-1].upper(): priority = 5
                        if i < len(text_lines)-1 and any(k in text_lines[i+1].upper() for k in ["S/O", "W/O", "C/O"]): priority = 5
                        potential_names.append({"text": line, "priority": priority})

        # 3. DOB
        if not result["fields"]["dob_or_age"]:
            if any(k in upper_line for k in ["DOB", "BIRTH", "YEAR", "जन्म"]):
                match = re.search(r'(\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}|\d{4})', upper_line)
                if match: result["fields"]["dob_or_age"] = match.group(0)

        # 4. Gender
        if not result["fields"]["gender"]:
            if "MALE" in upper_line and "FEMALE" not in upper_line: result["fields"]["gender"] = "Male"
            elif "FEMALE" in upper_line: result["fields"]["gender"] = "Female"

    if potential_names:
        potential_names.sort(key=lambda x: x['priority'], reverse=True)
        result["fields"]["name"] = potential_names[0]["text"]

def _extract_aadhaar_address(text_lines: list[str], result: dict):
    """Speclialized logic for Aadhaar address extraction."""
    address_lines = []
    started = False
    
    for i, line in enumerate(text_lines):
        upper_line = line.upper()
        
        if not started:
            if "ADDRESS" in upper_line or "पता" in upper_line:
                started = True
                split = re.split(r'ADDRESS[:\s]*', line, flags=re.IGNORECASE)
                if len(split) > 1 and split[1].strip():
                    address_lines.append(split[1].strip())
                continue
            elif re.search(r'\b[SWDC]/O\s*[:\s]*', upper_line):
                started = True
                continue # Skip the relation line itself
        
        if started:
            # Stop if we hit a full Aadhaar number or another pincode line after content
            if re.search(r'\d{4} \d{4} \d{4}', upper_line) or re.search(r'\b\d{6}\b', upper_line):
                if re.search(r'\b\d{6}\b', upper_line):
                    address_lines.append(line)
                break
            
            # Clean and append
            if not any(d in upper_line for d in ADDRESS_DENY_LIST) and not any(k in upper_line for k in NOISE_KEYWORDS):
                if not re.match(r'^\d+\s\d+\s\d+$', line):
                    address_lines.append(line)

    # Final cleanup
    cleaned_address = []
    for addr in address_lines:
        for deny in ADDRESS_DENY_LIST:
            addr = re.sub(re.escape(deny), "", addr, flags=re.IGNORECASE)
        addr = re.sub(r'^\W+|\W+$', '', addr).strip()
        addr = re.sub(r'(?i)SHOULD\s+BE\s+UPDATED.*$', '', addr).strip()
        if len(addr) > 2:
            cleaned_address.append(addr)
            
    result["fields"]["address"] = ", ".join(cleaned_address)
