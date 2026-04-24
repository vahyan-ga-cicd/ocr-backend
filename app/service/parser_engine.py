import re

# --- Constants & Keywords ---
NOISE_KEYWORDS = [
    "FATHER", "INDIA", "GOVERNMENT", "TAX", "ADDRESS", "DATE", "BIRTH", 
    "ACCOUNT", "NUMBER", "MALE", "FEMALE", "SIGNATURE", "DEPARTMENT", 
    "INCOME", "HINDI", "ENGLISH", "GOVT", "OF", "CARD", "PERMANENT", 
    "ISSUED", "INFORMATION", "SHRI", "LATE", "SMT", "DETAILS AS ON",
    "ENROLMENT", "AADHAA", "UNIQUE", "AUTHORITY", "VEHICLE", "REGISTRATION",
    "CERTIFICATE", "CHASSIS", "ENGINE", "FUEL", "EMISSION", "OWNER"
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
    # Clean lines first: remove very short or empty lines
    text_lines = [l.strip() for l in text_lines if len(l.strip()) > 1]
    full_text = " ".join(text_lines).upper()
    print(f"Parsing complex document (length: {len(full_text)})...") 
    
    doc_type = _detect_document_type(full_text)
    
    result = {
        "document_type": doc_type,
        "fields": {
            "name": None,
            "pan_number": None,
            "aadhar_number": None,
            "vehicle_number": None,
            "chassis_number": None,
            "motor_number": None,
            "bank_name": None,
            "account_number": None,
            "ifsc_code": None,
            "address": None
        }
    }

    # Specific extraction based on type
    if doc_type == "PAN Card":
        _extract_pan_details(text_lines, result)
    elif doc_type in ["Aadhaar Card", "Aadhaar Back"]:
        _extract_aadhaar_details(text_lines, result)
    elif doc_type in ["RC Front", "RC Back"]:
        _extract_rc_details(text_lines, result)
    elif doc_type in ["Cancelled Check", "Bank Passbook"]:
        _extract_bank_details(text_lines, result)
    elif doc_type in ["GST Document", "TDS/SD Document"]:
        _extract_tax_doc_details(text_lines, result)
    else:
        _extract_generic_fields(text_lines, result)
    
    # Final cleanup of all fields
    for key in result["fields"]:
        if isinstance(result["fields"][key], str):
            result["fields"][key] = result["fields"][key].strip(", ").strip()
            if result["fields"][key] == "": result["fields"][key] = None

    return result

def _detect_document_type(full_text: str) -> str:
    # 1. Banking (Prioritized as keywords are highly specific)
    if any(k in full_text for k in ["CANCELLED", "IFS CODE", "IFSC", "PAYABLE AT PAR", "CHEQUE", "NEFT", "RTGS", "MICR"]): 
        return "Cancelled Check"
    if "PASSBOOK" in full_text: return "Bank Passbook"
    if "STATE BANK" in full_text and any(k in full_text for k in ["A/C", "ACCOUNT", "NO."]): 
        return "Cancelled Check"

    # 2. GST / TDS detection
    if any(k in full_text for k in ["GOODS AND SERVICES TAX", "GSTIN", "FORM GST", "TAXABLE PERSON"]): 
        return "GST Document"
    if any(k in full_text for k in ["TAX DEDUCTED AT SOURCE", "TDS", "NON-DEDUCTION", "DECLARATION", "SECTION 194C", "DEDUCTOR", "TAN", "CHALLAN", "QUARTER", "197(1)"]): 
        return "TDS/SD Document"

    # 3. RC detection with fuzzy matching support
    if any(k in full_text for k in ["REGISTRATION CERTIFICATE", "REGN.NUMBER", "OWNER NAME", "CHASSIS"]):
        if "FORM 23" in full_text and "ORIGINAL" not in full_text: return "RC Back"
        if "HYPOTHECATED" in full_text: return "RC Back"
        return "RC Front"
    
    # 4. Aadhaar detection (Strengthened to avoid misidentifying long numbers)
    has_aadhaar_keyword = any(k in full_text for k in ["AADHAAR", "UNIQUE IDENTIFICATION"])
    has_aadhaar_pattern = re.search(r'\d{4}[\s-]?\d{4}[\s-]?\d{4}', full_text)
    
    if has_aadhaar_keyword or (has_aadhaar_pattern and any(k in full_text for k in ["GOVERNMENT", "INDIA", "MALE", "FEMALE", "DOB", "YEAR", "पत्ता"])):
        if any(k in full_text for k in ["ADDRESS", "पत्ता", "PIN", "DIST"]) or re.search(r'\b[SWDC]/O\b', full_text):
            return "Aadhaar Back"
        return "Aadhaar Card"

    # 5. PAN Card (Check this last because PAN numbers appear on many other documents like GST/TDS)
    if any(k in full_text for k in ["INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER"]) or re.search(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', full_text):
        return "PAN Card"
    
    return "Unknown"

def _extract_pan_details(text_lines: list[str], result: dict):
    full_text = " ".join(text_lines).upper()
    match = re.search(r'([A-Z]{5}[0-9]{4}[A-Z]{1})', full_text)
    if match: result["fields"]["pan_number"] = match.group(1)
    
    # Name extraction for PAN (Usually line 2 or 3, before Father's name)
    for i, line in enumerate(text_lines):
        if i < 4:
            if any(k in line.upper() for k in ["INCOME", "DEPARTMENT", "GOVT", "INDIA", "CARD"]): continue
            if re.search(r'^[A-Z\s\.]+$', line.upper()) and len(line) > 3:
                result["fields"]["name"] = line.strip()
                break

def _extract_aadhaar_details(text_lines: list[str], result: dict):
    full_text = " ".join(text_lines).upper()
    # Flexible 12-digit detection
    match = re.search(r'\b(\d{4}[\s-]?\d{4}[\s-]?\d{4})\b|\b(\d{12})\b', full_text)
    if match:
        num = (match.group(1) or match.group(2)).replace(" ", "").replace("-", "")
        result["fields"]["aadhar_number"] = num
    
    # Name extraction for Aadhaar Front
    for i, line in enumerate(text_lines):
        if i < 5:
            if any(k in line.upper() for k in ["GOVERNMENT", "INDIA", "MALE", "FEMALE", "DOB", "YEAR", "PUNJAB", "UNIQUE"]): continue
            if re.search(r'^[A-Z\s\.]+$', line.upper()) and len(line) > 3:
                result["fields"]["name"] = line.strip()
                break

    # Address
    _extract_aadhaar_address(text_lines, result)

def _extract_rc_details(text_lines: list[str], result: dict):
    full_text = " ".join(text_lines).upper()
    
    # 1. Name
    for i, line in enumerate(text_lines):
        upper = line.upper()
        if any(k in upper for k in ["OWNER NAME", "OWNERNAME", "O NAME"]):
            val = re.split(r'(?:OWNER\s*NAME|O\s*NAME)[:\s]*', line, flags=re.IGNORECASE)[-1].strip()
            if len(val) > 3: result["fields"]["name"] = val
            elif i + 1 < len(text_lines): result["fields"]["name"] = text_lines[i+1].strip()
            break
            
    # 2. Vehicle Number
    reg_match = re.search(r'\b([A-Z]{2}\s?\d{2}\s?[A-Z]{1,2}\s?\d{4})\b', full_text)
    if reg_match: result["fields"]["vehicle_number"] = reg_match.group(1).replace(" ", "")
    
    # 3. Chassis Number (Allowing spaces, then stripping)
    chassis_pattern = r'(?:CHASSIS|CHAS)\s*(?:NO|NUMBER)?[:\s]*([A-Z0-9\s]{15,25})'
    chassis_match = re.search(chassis_pattern, full_text)
    if chassis_match:
        val = chassis_match.group(1).replace(" ", "").strip()
        # Aggressively strip common prefix noise
        val = re.sub(r'^(?:OWNER|CHASSIS|CHAS|NO|NUMBER|DETAILS|DATE)+', '', val)
        if len(val) >= 10: result["fields"]["chassis_number"] = val

    # 4. Engine/Motor Number
    motor_pattern = r'(?:ENGINE|MOTOR|ENG)\s*(?:NO|NUMBER)?[:\s/]*([A-Z0-9\s]{5,20})'
    motor_match = re.search(motor_pattern, full_text)
    if motor_match:
        val = motor_match.group(1).replace(" ", "").strip()
        # Aggressively strip common prefix noise
        val = re.sub(r'^(?:MOTOR|ENGINE|ENG|NO|NUMBER|DETAILS|DATE)+', '', val)
        if len(val) >= 5: result["fields"]["motor_number"] = val

    # 5. Fallback for Chassis/Motor if still missing (Look for likely candidates in all lines)
    if not result["fields"]["chassis_number"]:
        # Find any line that looks like a 17-char chassis number
        for line in text_lines:
            clean = line.replace(" ", "").upper()
            if len(clean) == 17 and re.match(r'^[A-Z0-9]{17}$', clean):
                result["fields"]["chassis_number"] = clean
                break

    if not result["fields"]["motor_number"]:
        # Look for 6-12 digit alphanumeric strings that aren't the chassis or vehicle number
        for line in text_lines:
            clean = line.replace(" ", "").upper()
            if 6 <= len(clean) <= 12 and re.match(r'^[A-Z0-9]{6,12}$', clean):
                if clean != result["fields"]["chassis_number"] and clean != result["fields"]["vehicle_number"]:
                    result["fields"]["motor_number"] = clean
                    break

def _extract_bank_details(text_lines: list[str], result: dict):
    full_text_no_space = " ".join(text_lines).upper().replace(" ", "")
    raw_full = " ".join(text_lines).upper()
    
    # 1. IFSC Code (4 alpha + 1 alpha/digit + 6 alpha/digit)
    # 5th char is '0', but OCR misreads it as O, D, Q, U, C, etc.
    ifsc_pattern = r'([A-Z]{4}[0ODQUC][A-Z0-9]{6})'
    
   
    ifsc_match = re.search(r'(?:IFSC|IFSCODE|IFS|CODE|IFSCODE).{0,15}?' + ifsc_pattern, full_text_no_space)
    if ifsc_match:
        val = ifsc_match.group(1)
        if val[4] != '0': val = val[:4] + '0' + val[5:]
        result["fields"]["ifsc_code"] = val
    else:
        # Global search in no-space text (more robust than raw text with \b)
        global_match = re.search(ifsc_pattern, full_text_no_space)
        if global_match:
            val = global_match.group(1)
            if val[4] != '0': val = val[:4] + '0' + val[5:]
            result["fields"]["ifsc_code"] = val

    # 2. Bank Name
    for b in ["STATE BANK", "HDFC", "ICICI", "AXIS", "CANARA", "PUNJAB NATIONAL", "INDIAN BANK", "BARODA", "UNION BANK", "KOTAK", "INDUSIND", "YES BANK", "FEDERAL BANK"]:
        if b in raw_full: 
            if b == "STATE BANK": result["fields"]["bank_name"] = "State Bank of India"
            elif b == "BARODA": result["fields"]["bank_name"] = "Bank of Baroda"
            elif "BANK" not in b: result["fields"]["bank_name"] = f"{b} Bank"
            else: result["fields"]["bank_name"] = b
            break

    # 3. Account Number: Advanced multi-line fuzzy matching
    # Priority 1: Labels that are definitely the main Account Number box (Exclude CURRENT/SAVINGS here)
    acc_patterns = [
        r'(?<!CURRENT\s)(?<!SAVINGS\s)(?:A[\/\.\s]?C|ACCOUNT|ACC|SB|खा[\.\s]*सं|A1C|ALC)[\s\.\:\/\-\|]*([\d\s\-]{9,22})',
        r'([\d\s\-]{9,22})[\s\.\:\/\-\|]*(?<!CURRENT\s)(?<!SAVINGS\s)(?:A[\/\.\s]?C|ACCOUNT|ACC|SB|खा[\.\s]*सं|A1C|ALC)'
    ]
    
    best_match = None
    for pattern in acc_patterns:
        # Using a case-insensitive search but excluding CURRENT/SAVINGS
        acc_match = re.search(pattern, raw_full, re.IGNORECASE)
        if acc_match:
            val = re.sub(r'[\s\-]', '', acc_match.group(1))
            if 9 <= len(val) <= 18:
                best_match = val
                break

    # Priority 2: Look for 11-digit numbers starting with 3 or 4 (SBI) near ANY relevant keyword
    if not best_match:
        potentials = re.findall(r'[\d\s\-]{9,22}', raw_full)
        for p in potentials:
            clean_p = re.sub(r'[\s\-]', '', p)
            if len(clean_p) == 11 and clean_p.startswith(("3", "4")):
                pos = raw_full.find(p)
                surrounding = raw_full[max(0, pos-80):min(len(raw_full), pos+len(p)+80)]
                if any(k in surrounding for k in ["A/C", "ACC", "ACCOUNT", "खा", "CURRENT", "SAVING"]):
                    best_match = clean_p
                    break
    
    # Priority 3: Last resort - CURRENT/SAVINGS labels
    if not best_match:
        last_resort = re.search(r'(?:CURRENT|SAVINGS)[\s\.\/]*(?:A/C|ACCOUNT)?[\s\.\:\/\-\|]*([\d\s\-]{9,22})', raw_full)
        if last_resort:
            val = re.sub(r'[\s\-]', '', last_resort.group(1))
            if 9 <= len(val) <= 18: best_match = val

    # If no label match, look for any 11-digit number near an A/C label
    if not best_match:
        # Find all 9-18 digit sequences
        potentials = re.findall(r'\b[\d\s\-]{9,22}\b', raw_full)
        for p in potentials:
            clean_p = re.sub(r'[\s\-]', '', p)
            if 9 <= len(clean_p) <= 18:
                # Check if "A/C" or "ACCOUNT" or "खा. सं." is within 50 characters of this number
                pos = raw_full.find(p)
                surrounding = raw_full[max(0, pos-60):min(len(raw_full), pos+len(p)+60)]
                if any(k in surrounding for k in ["A/C", "ACC", "ACCOUNT", "खा. सं.", "खा.सं."]):
                    # Special priority for numbers starting with 3 or 4 (SBI common)
                    if clean_p.startswith(("3", "4")):
                        best_match = clean_p
                        break
                    if not best_match: best_match = clean_p

    if best_match:
        result["fields"]["account_number"] = best_match
            
    if not result["fields"]["account_number"]:
        # Fallback: look for 9-18 digit strings...
        potential = re.findall(r'\b\d{9,18}\b', raw_full)
        for p in potential:
            if len(p) == 10 and p.startswith(("6", "7", "8", "9")): continue
            if p == result["fields"]["ifsc_code"]: continue
            result["fields"]["account_number"] = p
            break

def _extract_tax_doc_details(text_lines: list[str], result: dict):
    full_doc = " ".join(text_lines)
    
    # Try more comprehensive patterns for GST/TDS addresses
    # Pattern 1: Look for "Address of Principal Place of Business" or similar
    gst_addr_pattern = r'(?:ADDRESS\s*OF\s*PRINCIPAL\s*PLACE(?:\s*OF\s*BUSINESS)?|PRINCIPAL\s*PLACE\s*OF\s*BUSINESS|REGISTERED\s*OFFICE\s*ADDRESS|ADDRESS\s*OF\s*THE\s*PERSON|ADDRESS\s*OF\s*THE\s*DEDUCTOR|DEDUCTOR\s*ADDRESS|PREMISES|LOCATED\s*AT)[:\s]*\s*([^\n\r]{10,450}?(?:\d{6}|PIN|INDIA|TAMIL|TN|KERALA|KARNATAKA|MAHARASHTRA|DELHI|NAMAKKAL|MUMBAI|CHENNAI|BANGALORE)[^\n\r]{0,30})'
    match = re.search(gst_addr_pattern, full_doc, re.IGNORECASE)
    
    if not match:
        # Pattern 2: Generic "Address" or "N/O" or "LOCATED AT" (Removed [^.] constraint to allow periods in names/titles)
        match = re.search(r'(?:N/O|ADDRESS|LOCATED\s*AT|OFFICE)[:\s]*\s*([^\n\r]{10,450}?(?:\d{6}|PIN|INDIA|TAMIL|TN|NAMAKKAL|MUMBAI|CHENNAI|BANGALORE)[^\n\r]{0,30})', full_doc, re.IGNORECASE)

    if match:
        addr = match.group(1).strip()
        # Filter out common junk at start of address
        addr = re.sub(r'^(?:BHARAT\s*STAGE|STAGE|CLASS\s*OF\s*VEHICLE|EMISSION|OWNER|I,)\s*[^,]*[,\s]*', '', addr, flags=re.IGNORECASE)
        # Remove trailing noise like "Date of issue" or "PAN of..." or legal jargon
        addr = re.sub(r'[.\s]*\(?HERE\s*IN\s*AFT.*$', '', addr, flags=re.IGNORECASE)
        addr = re.sub(r'[.\s]*(?:DO\s*HEREBY|MAKE\s*THE\s*FOLLOWING|DATE|PAN|REGISTRATION|PLACE|TIME|NAME|GSTIN|FORM).*$', '', addr, flags=re.IGNORECASE)
        
        # Remove multiple spaces and final cleanup
        addr = re.sub(r'\s+', ' ', addr)
        result["fields"]["address"] = addr.strip(". ,(")
    else:
        # Fallback to multi-line search if keyword search failed
        _extract_aadhaar_address(text_lines, result)

def _extract_generic_fields(text_lines: list[str], result: dict):
    full_text = " ".join(text_lines).upper()
    if not result["fields"]["pan_number"]:
        m = re.search(r'([A-Z]{5}[0-9]{4}[A-Z]{1})', full_text)
        if m: result["fields"]["pan_number"] = m.group(1)
    if not result["fields"]["aadhar_number"]:
        m = re.search(r'(\d{4}\s?\d{4}\s?\d{4})', full_text)
        if m: result["fields"]["aadhar_number"] = m.group(1).replace(" ", "")

def _extract_aadhaar_address(text_lines: list[str], result: dict):
    addr_parts = []
    collecting = False
    temp_noise = [k for k in NOISE_KEYWORDS if k != "ADDRESS"]
    
    for line in text_lines:
        upper = line.upper()
        # Look for Aadhaar number pattern on any line as fallback
        aadhaar_match = re.search(r'\b(\d{4}\s?\d{4}\s?\d{4})\b|\b(\d{12})\b', upper)
        if aadhaar_match and not result["fields"]["aadhar_number"]:
            result["fields"]["aadhar_number"] = (aadhaar_match.group(1) or aadhaar_match.group(2)).replace(" ", "")

        if not collecting:
            if any(k in upper for k in ["ADDRESS", "पत्ता", "N/O", "PLACE OF BUSINESS", "REGISTERED OFFICE"]):
                collecting = True
                part = re.split(r'(?:ADDRESS|पत्ता|N/O|PLACE OF BUSINESS|REGISTERED OFFICE)[:\s]*', line, flags=re.IGNORECASE)[-1].strip()
                if len(part) > 3: addr_parts.append(part)
                continue
            if re.search(r'\b[SWDC]/O\s*[:\s]*', upper):
                collecting = True
                addr_parts.append(line)
                continue
        if collecting:
            if aadhaar_match: break # Stop at Aadhaar number line
            if any(d in upper for d in ADDRESS_DENY_LIST): continue
            if not any(k in upper for k in temp_noise):
                if len(line.strip()) > 2: addr_parts.append(line.strip())
            if re.search(r'\d{6}', upper): # Likely pincode, end of block
                pass 

    if addr_parts: result["fields"]["address"] = ", ".join(addr_parts)
