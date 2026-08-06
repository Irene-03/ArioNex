import json
import re
import logging

logger = logging.getLogger("arionex.toggleable_services")

def _clean_and_parse_json(text: str) -> dict:
    """
    /// <summary>
    /// Clean and safely parse the language model output as valid JSON, with recovery for broken JSON
    /// </summary>
    """
    cleaned = text.strip()
    # Remove markdown code blocks
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned)
    cleaned = cleaned.strip()
    
    try:
        return json.loads(cleaned)
    except Exception as std_json_err:
        try:
            try:
                from json_repair import repair_json
                repaired = repair_json(cleaned)
            except ImportError:
                logger.warning("json_repair module not installed. Falling back to standard string representation.")
                repaired = cleaned
            return json.loads(repaired)
        except Exception as repair_err:
            logger.error(f"Failed to parse and repair JSON. Standard error: {str(std_json_err)}. Repair error: {str(repair_err)}")
            raise repair_err
