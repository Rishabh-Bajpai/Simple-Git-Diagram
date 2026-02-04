import re
import logging

logger = logging.getLogger(__name__)

def clean_mermaid_code(raw_code: str, diagram_type: str = 'flowchart') -> str:
    # 1. Extract from code blocks
    match = re.search(r"```mermaid\s*(.*?)\s*```", raw_code, re.DOTALL)
    if match:
        code = match.group(1)
    else:
        # Fallback regex for plain blocks or just content
        match_plain = re.search(r"```\s*(.*?)\s*```", raw_code, re.DOTALL)
        code = match_plain.group(1) if match_plain else raw_code

    code = code.strip()

    # 1.1 Fix concatenated keywords
    # Log matches for debugging
    concatenated_matches = re.findall(r'([a-z0-9])(classDef|class|click|subgraph|state|graph|flowchart)\b', code, flags=re.IGNORECASE)
    if concatenated_matches:
        logger.info(f"Found concatenated keywords: {concatenated_matches}")
        
    code = re.sub(r'([a-z0-9])(classDef|class|click|subgraph|state|graph|flowchart)\b', r'\1\n\2', code, flags=re.IGNORECASE)
    

    if concatenated_matches:
        logger.info(f"Code after split fix: {code[0:200]}...")

    # 1.3 Fix keywords split across lines (e.g., "sub\ngraph" -> "subgraph")
    code = re.sub(r'\bsub\s*\n\s*graph\b', 'subgraph', code, flags=re.IGNORECASE)
    code = re.sub(r'\bend\s*\n\s*subgraph\b', 'end\nsubgraph', code, flags=re.IGNORECASE)
    code = re.sub(r'\bclass\s*\n\s*Def\b', 'classDef', code, flags=re.IGNORECASE)
    
    # 1.4 Fix ]end or )end patterns (missing newline before 'end')
    code = re.sub(r'([\]\)])end\b', r'\1\nend', code, flags=re.IGNORECASE)

    # 1.5 Enforce Diagram Header
    # Check if a valid header already exists (ignoring comments)
    header_pattern = r'^\s*(?:%%.*\n)*\s*(flowchart|graph|classDiagram|stateDiagram|stateDiagram-v2|C4Context)'
    match = re.search(header_pattern, code, flags=re.MULTILINE)
    
    if not match:
        # No header found, prepend based on type
        if diagram_type == 'class':
            code = "classDiagram\n" + code
        elif diagram_type == 'state':
            code = "stateDiagram-v2\n" + code
        else:
            # Default to flowchart TD for c4/flowchart
            code = "flowchart TD\n" + code
            
    # Ensure newline after header if it was on same line as content
    logger.info(f"BEFORE header newline fix (first 200 chars): {code[:200]}")
    code = re.sub(r'^(\s*)(flowchart\s+\w+|graph\s+\w+|classDiagram|stateDiagram|stateDiagram-v2|C4Context)[^\S\r\n]+', r'\1\2\n', code, flags=re.MULTILINE)
    logger.info(f"AFTER header newline fix (first 200 chars): {code[:200]}")
    
    # 2. Remove "syntax error" causing artifacts (incomplete lines)
    # Remove incomplete class definitions (:::)
    code = re.sub(r':::\s*$', '', code, flags=re.MULTILINE)
    
    # Debug: Log lines containing classDef before fix
    classdef_lines_before = [l for l in code.split('\n') if 'classdef' in l.lower()]
    logger.debug(f"CLASSDEF lines BEFORE fix: {classdef_lines_before}")
    
    # Also log lines that START WITH fill/stroke/color (these might be split from classDef)
    fillstroke_lines = [l for l in code.split('\n') if l.strip().startswith(('fill:', 'fill:#', 'stroke:', 'stroke:#', 'color:', 'color:#'))]
    logger.debug(f"FILL/STROKE lines (might be split from classDef): {fillstroke_lines}")
    
    # Fix classDef split across lines: join "classDef name\nfill:..." into one line
    # The LLM sometimes puts fill: on the next line WITHOUT leading whitespace
    # Using \n\s* to match newline + zero or more spaces
    code = re.sub(r'(classDef\s+\w+)\s*\n\s*(fill:#)', r'\1 \2', code, flags=re.IGNORECASE)
    code = re.sub(r'(classDef\s+\w+)\s*\n\s*(stroke:#)', r'\1 \2', code, flags=re.IGNORECASE)
    code = re.sub(r'(classDef\s+\w+)\s*\n\s*(color:#)', r'\1 \2', code, flags=re.IGNORECASE)
    
    # Fix classDef name concatenated with fill:/stroke:/color: (missing space)
    # e.g., "classDef frontendfill:#" -> "classDef frontend fill:#"
    # Uses backtracking: match word chars, then force match of fill/stroke/color + :#  
    # The regex engine will backtrack to find where 'fill' starts within the word
    code = re.sub(r'([a-zA-Z]+)(fill:#)', r'\1 \2', code, flags=re.IGNORECASE)
    code = re.sub(r'([a-zA-Z]+)(stroke:#)', r'\1 \2', code, flags=re.IGNORECASE)
    code = re.sub(r'([a-zA-Z]+)(color:#)', r'\1 \2', code, flags=re.IGNORECASE)
    
    # Debug: Log lines containing classDef after join fix
    classdef_lines_after = [l for l in code.split('\n') if 'classdef' in l.lower()]
    logger.debug(f"CLASSDEF lines AFTER join fix (should now have fill:#): {classdef_lines_after}")
    
    # Remove bare classDef
    code = re.sub(r'^\s*classDef\s*$', '', code, flags=re.MULTILINE)
    # Remove incomplete classDef lines
    code = re.sub(r'^\s*classDef\s+\w+\s*$', '', code, flags=re.MULTILINE)
    # Remove trailing commas in classDef
    code = re.sub(r'(classDef.*),\s*$', r'\1', code, flags=re.MULTILINE)


    # 3. Fix common newline issues (Concatenated keywords)
    # Log first 500 chars to see where issues might be
    logger.debug(f"BEFORE fixes (first 500): {code[:500] if len(code) > 500 else code}")
    
    # Fix ]endsubgraph_name or )endsubgraph_name -> ]\nend or )\nend
    code = re.sub(r'(\]|\))endsubgraph_\w*', r'\1\nend', code, flags=re.IGNORECASE)
    
    # Fix hallucinated "named" end tags standalone (e.g., endsubgraph_frontend -> end)
    code = re.sub(r'endsubgraph_\w+', '\nend', code, flags=re.IGNORECASE)
    
    # Also catch case where ] is directly followed by end (no space)
    code = re.sub(r'\]end\b', ']\nend', code, flags=re.IGNORECASE)
    
    logger.debug(f"AFTER endsubgraph fix (first 500): {code[:500] if len(code) > 500 else code}")
    
    # Ensure 'end' is always on its own line (preceded by newline)
    # Match: any non-whitespace followed by optional whitespace and 'end' at end of line
    code = re.sub(r'(\]|\))\s*end\s*$', r'\1\nend', code, flags=re.MULTILINE | re.IGNORECASE)
    
    # Fix "endsubgraph" -> "end\nsubgraph" (concatenation without underscore)
    code = re.sub(r'endsubgraph', 'end\nsubgraph', code, flags=re.IGNORECASE)
    # Fix "endclick" -> "end\nclick"
    code = re.sub(r'endclick', 'end\nclick', code, flags=re.IGNORECASE)
    # Fix "endclassDef" -> "end\nclassDef"
    code = re.sub(r'endclassDef', 'end\nclassDef', code, flags=re.IGNORECASE)
    
    # Fix potentially concatenated "_blankend" -> "_blank\nend"
    code = re.sub(r'_blankend', '_blank\nend', code, flags=re.IGNORECASE)
    
    # Fix missing href keyword (required for some diagram types)
    # click ID "URL" -> click ID href "URL"
    code = re.sub(r'click\s+([\w\-]+)\s+"(http[^"]+)"', r'click \1 href "\2"', code, flags=re.IGNORECASE)

    # Force add _blank to click directives if missing
    # Matches: click NodeID href "URL" [ "Tooltip" ]
    code = re.sub(r'(click\s+[\w\-]+\s+href\s+"[^"]+"(?:\s+"[^"]+")?)\s*$', r'\1 _blank', code, flags=re.MULTILINE)
    
    # Fix quote-keyword concatenation (e.g., "...url"click) - done AFTER href injection
    # to catch any new patterns created by the href transformation
    code = re.sub(r'(")(classDef|class|click|subgraph|state|graph|flowchart)', r'\1\n\2', code, flags=re.IGNORECASE)
    
    # SPECIAL HANDLE: State Diagrams often don't support tooltips/_blank in strict parser
    if diagram_type == 'state':
        # Strip everything after the URL (Tooltip, _blank) for state diagrams
        # Keep: click ID href "URL"
        code = re.sub(r'(click\s+[\w\-]+\s+href\s+"[^"]+")(?:.*)$', r'\1', code, flags=re.MULTILINE)
    
    # Ensure 'end' is usually followed by newline if followed by a word
    # IMPORTANT: Use word boundary \b to avoid matching 'end' inside words like 'frontend'
    code = re.sub(r'\bend\s+([a-zA-Z])', r'end\n\1', code)

    return code
