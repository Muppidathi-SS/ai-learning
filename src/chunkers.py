import re
from typing import List, Dict, Any

class StructureAwareChunker:
    """
    Strategy 2: Structure-Aware Markdown Chunker (Beginner Implementation)
    
    This chunker respects Markdown structure:
    1. Splits documents by section headers (#, ##, ###).
    2. Keeps entire parameter tables and code blocks intact inside their sections.
    3. Prepends the section header hierarchy to every chunk so context is never lost.
    """
    def __init__(self, tight_param_split: bool = False):
        self.tight_param_split = tight_param_split

    def _extract_anchor(self, header_text: str) -> str:
        """Helper to create a clean HTML-style anchor ID (e.g. '### Client.send()' -> 'clientsend')"""
        clean = re.sub(r'[^\w\s-]', '', header_text.lower()).strip()
        return re.sub(r'[-\s]+', '-', clean)

    def chunk(self, text: str, doc_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        lines = text.split('\n')
        
        doc_title = doc_metadata.get("page_id", "Doc")
        current_h1 = ""
        current_h2 = ""
        current_h3 = ""
        
        sections = []
        current_section = {"headers": [], "lines": []}
        
        in_code_fence = False
        
        # Step 1: Group lines into sections by Markdown headers (#, ##, ###)
        for line in lines:
            # Track whether we are inside a ``` code block so we don't split on headers inside code
            if line.strip().startswith("```"):
                in_code_fence = not in_code_fence

            header_match = re.match(r'^(#{1,4})\s+(.+)$', line)
            if header_match and not in_code_fence:
                level = len(header_match.group(1))
                header_title = header_match.group(2).strip()
                
                # Save previous section if it contains lines
                if current_section["lines"]:
                    sections.append(current_section)
                
                # Update current header hierarchy level
                if level == 1:
                    current_h1 = header_title
                    current_h2 = ""
                    current_h3 = ""
                elif level == 2:
                    current_h2 = header_title
                    current_h3 = ""
                elif level >= 3:
                    current_h3 = header_title

                hierarchy = [h for h in [current_h1, current_h2, current_h3] if h]
                current_section = {
                    "headers": hierarchy,
                    "anchor": self._extract_anchor(header_title),
                    "lines": [line]
                }
            else:
                current_section["lines"].append(line)

        # Append last remaining section
        if current_section["lines"]:
            sections.append(current_section)

        # Step 2: Format each section into a chunk with header context attached
        chunk_idx = 0
        for sec in sections:
            sec_text = "\n".join(sec["lines"]).strip()
            if not sec_text:
                continue

            # Build header context string e.g. "[client_v3 | Section: Client Reference (v3) > Methods > Client.send()]"
            hierarchy_str = " > ".join(sec["headers"]) if sec["headers"] else doc_title
            context_header = f"[{doc_title} | Section: {hierarchy_str}]\n"
            full_content = context_header + sec_text
            
            chunk_metadata = doc_metadata.copy()
            chunk_metadata["section"] = hierarchy_str
            chunk_metadata["anchor"] = sec.get("anchor", "top")
            
            chunk_id = f"{doc_metadata['sdk_version']}_{doc_metadata['page_id']}_struct_{chunk_idx:03d}"
            
            chunks.append({
                "chunk_id": chunk_id,
                "content": full_content,
                "metadata": chunk_metadata,
                "strategy": "structure_aware"
            })
            chunk_idx += 1

        return chunks
