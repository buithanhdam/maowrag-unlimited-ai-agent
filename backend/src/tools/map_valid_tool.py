from datetime import datetime

def map_valid_date_range(start_date: str, end_date: str) -> tuple[str, str]:
    """
    Validates a date range by checking if the current date falls between the start and end dates.
    
    Args:
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
    
    Returns:
        tuple[str, str]: A tuple containing the original dates if valid, or (None, None) if invalid.
                         Invalid cases include: parsing errors or when current date is outside range.
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        now = datetime.now()
        
        if start <= now <= end:
            return start_date, end_date
        return None, None
    except ValueError:
        return None, None

def map_valid_container_types(container_codes: list[str] = []) -> dict[str, str]:
    """
    Validates a list of container type codes against standard container type specifications.
    
    Args:
        container_codes (list[str]): List of container codes to validate (e.g., ["20'GP", "40'HC", "40'RF"]).
    
    Returns:
        dict[str, str]: Dictionary mapping input codes to validated codes.
                        Valid codes remain the same, invalid codes map to None.
                        Valid codes follow the pattern: {size}{type} where:
                        - size is one of: 20, 25, 30, 35, 40, 45
                        - type is one of: GP (General Purpose), HC (High Cube), RF (Refrigerated)
    """
    code_numbers = [20, 25, 30, 35, 40, 45]
    code_names = ["GP", "HC", "RF"]
    valid_codes = [f"{code_number}{code_name}" for code_number in code_numbers for code_name in code_names]
    
    result_mapping = {}
    for code in container_codes:
        clean_code = code.replace("'", "")
        if clean_code in valid_codes:
            code_to_map = clean_code
        else:
            code_to_map = None
        result_mapping[code] = code_to_map
    
    return result_mapping