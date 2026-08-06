"""
/// <summary>
/// Prompt templates for semantic extraction of entities, relationships, and rules (ArioNex Semantic Extractor Prompt Templates)
/// </summary>
"""

ENTITY_EXTRACTION_TEMPLATE = """You are an expert knowledge graph engineer. Your task is to extract entities and their relationships from the given TEXT.

First, identify all key entities in the text. For each entity, extract:
- name: The name of the entity (use the exact name from the text, preferably in Persian if the text is in Persian).
- type: The category of the entity (e.g., ORGANIZATION, PERSON, CONCEPT, LOCATION, PRODUCT, EVENT, DATE, etc.).
- description: A brief description of what this entity is based on the context.

Second, identify relationships between the extracted entities. For each relationship, extract:
- source: The name of the source entity.
- target: The name of the target entity.
- relationship: The type of relationship/action connecting them (e.g., OWNS, EMPLOYEE_OF, LOCATED_IN, REGULATES, PART_OF, HAS_CONDITION, etc. - in English uppercase).
- description: A brief description explaining how they are related.

You MUST respond strictly with a valid JSON object. Do not include any explanation, markdown formatting blocks (like ```json), or extra text outside the JSON.

TEXT:
{text}

JSON Format:
{{
  "entities": [
    {{
      "name": "Entity Name",
      "type": "ORGANIZATION",
      "description": "Entity description"
    }}
  ],
  "relationships": [
    {{
      "source": "Source Entity Name",
      "target": "Target Entity Name",
      "relationship": "OWNS",
      "description": "Relationship description"
    }}
  ]
}}
"""

RULE_EXTRACTION_TEMPLATE = """You are an expert compliance and policy auditor. Your task is to identify and extract all business rules, policies, constraints, regulations, and compliance clauses from the given TEXT.

For each rule/clause identified, extract:
- rule_code: A short identifier or reference code (e.g., POLICY-1, RULE-2, or actual codes like SECTION-4.2 if mentioned).
- clause: The exact statement or precise formulation of the rule/constraint in Persian.
- type: The category of the rule (e.g., CONSTRAINT, POLICY, PREREQUISITE, EXCEPTION, FINE).
- description: A brief explanation of the rule's scope and implications.

You MUST respond strictly with a valid JSON object. Do not include any explanation, markdown formatting blocks (like ```json), or extra text outside the JSON.

TEXT:
{text}

JSON Format:
{{
  "rules": [
    {{
      "rule_code": "RULE-1",
      "clause": "متن بند قانونی یا شرط انطباق",
      "type": "POLICY",
      "description": "توضیح شرط"
    }}
  ]
}}
"""
