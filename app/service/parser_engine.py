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
    if any(k in full_text for k in ["GOODS AND SERVICES TAX", "GSTIN", "FORM GST"]): return "GST Document"
    if any(k in full_text for k in ["TAX DEDUCTED AT SOURCE", "TDS", "NON-DEDUCTION"]): return "TDS/SD Document"

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

    # 5. PAN Card
    if any(k in full_text for k in ["INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER"]) or re.search(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', full_text):
        return "PAN Card"
    
    return "Unknown"

def _extract_pan_details(text_lines: list[str], result: dict):
    full_text = " ".join(text_lines).upper()
    match = re.search(r'([A-Z]{5}[0-9]{4}[A-Z]{1})', full_text)
    if match: result["fields"]["pan_number"] = match.group(1)

def _extract_aadhaar_details(text_lines: list[str], result: dict):
    full_text = " ".join(text_lines).upper()
    # Flexible 12-digit detection (supports spaces, hyphens, or no separators)
    match = re.search(r'\b(\d{4}[\s-]?\d{4}[\s-]?\d{4})\b|\b(\d{12})\b', full_text)
    if match:
        num = (match.group(1) or match.group(2)).replace(" ", "").replace("-", "")
        result["fields"]["aadhar_number"] = num
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
    
    # Try looking for keyword first in no-space text, allowing some noise
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

    # 3. Account Number: prioritize patterns near keywords
    # Handle "A/c No", "Account No", "A/C:", etc.
    acc_patterns = [
        r'(?:A/C|ACCOUNT|ACC|SB)\s*(?:NO|NUMBER)?[:\s/]*(\d{9,18})',
        r'(\d{9,18})\s*(?:A/C|ACCOUNT|ACC|SB)',
    ]
    for pattern in acc_patterns:
        acc_match = re.search(pattern, raw_full)
        if acc_match:
            result["fields"]["account_number"] = acc_match.group(1)
            break
            
    if not result["fields"]["account_number"]:
        # Fallback: look for 9-18 digit strings that aren't phone numbers, ifsc, or micr-like (bottom of cheque)
        # Phone numbers usually start with 6-9 and are 10 digits
        potential = re.findall(r'\b\d{9,18}\b', raw_full)
        for p in potential:
            # Basic heuristic: avoid likely phone numbers and short sequences
            if len(p) == 10 and p.startswith(("6", "7", "8", "9")):
                continue
            # Avoid likely IFSC (already captured) or other known patterns
            if p == result["fields"]["ifsc_code"]:
                continue
            result["fields"]["account_number"] = p
            break

def _extract_tax_doc_details(text_lines: list[str], result: dict):
    full_doc = " ".join(text_lines)
    
    # Try more comprehensive patterns for GST/TDS addresses
    # Pattern 1: Look for "Address of Principal Place of Business" or similar
    # Added (?:\s*OF\s*BUSINESS)? and ADDRESS\s*OF\s*THE\s*PERSON to keywords
    gst_addr_pattern = r'(?:ADDRESS\s*OF\s*PRINCIPAL\s*PLACE(?:\s*OF\s*BUSINESS)?|PRINCIPAL\s*PLACE\s*OF\s*BUSINESS|REGISTERED\s*OFFICE\s*ADDRESS|ADDRESS\s*OF\s*THE\s*PERSON)[:\s]*\s*([^.]{10,300}?(?:\d{6}|PIN|INDIA|TAMIL|TN|KERALA|KARNATAKA|MAHARASHTRA|DELHI)[^.]{0,20})'
    match = re.search(gst_addr_pattern, full_doc, re.IGNORECASE)
    
    if not match:
        # Pattern 2: Generic "Address" or "N/O" (sometimes seen in OCR of Care Of)
        match = re.search(r'(?:N/O|ADDRESS)[:\s]*\s*([^.]{10,250}?(?:\d{6}|PIN|INDIA|TAMIL|TN|NAMAKKAL)[^.]{0,20})', full_doc, re.IGNORECASE)

    if match:
        addr = match.group(1).strip()
        # Filter out common junk at start of address
        addr = re.sub(r'^[I,]\s*[^,]+,\s*[SWDC]/O\s*[^,]+,\s*', '', addr, flags=re.IGNORECASE)
        # Remove trailing noise like "Date of issue" or "PAN of..."
        addr = re.sub(r'\s+(?:DATE|PAN|REGISTRATION|PLACE|TIME|NAME|GSTIN|FORM).*$', '', addr, flags=re.IGNORECASE)
        # Remove multiple spaces
        addr = re.sub(r'\s+', ' ', addr)
        result["fields"]["address"] = addr
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
