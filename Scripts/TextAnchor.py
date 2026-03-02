import json
import os
import difflib

def normalize_polygon(polygon):
    # Returns [x1, y1, x2, y2, x3, y3, x4, y4] regardless of input format
    if len(polygon) == 8 and isinstance(polygon[0], (int, float)):
        return polygon
    elif len(polygon) == 4 and isinstance(polygon[0], dict):
        res = []
        for pt in polygon:
            res.extend([pt.get('x', 0), pt.get('y', 0)])
        return res
    return polygon

def calculate_quadrant(bounding_box, width, height):
    # bounding_box might be [x1, y1, x2, y2, x3, y3, x4, y4] or [{'x':..,'y':..},..]
    normalized = normalize_polygon(bounding_box)
    xs = normalized[0::2]
    ys = normalized[1::2]
    
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    
    half_w = width / 2.0
    half_h = height / 2.0
    
    if cx < half_w and cy < half_h:
        return 1 # Top-Left
    elif cx >= half_w and cy < half_h:
        return 2 # Top-Right
    elif cx < half_w and cy >= half_h:
        return 3 # Bottom-Left
    else:
        return 4 # Bottom-Right

def generate_text_anchors(item_name, azure_data):
    if not item_name:
        return None
        
    item_name_clean = item_name.strip().lower()
    
    best_overall_ratio = 0
    best_match_info = None
    
    for doc in azure_data:
        # Determine original document name
        source_file = doc.get('_source_file', '')
        doc_name = source_file.replace('.json', '.pdf') if source_file.endswith('.json') else source_file
        
        candidates = []
        for item in doc.get('paragraphs', []):
            for region in item.get('bounding_regions', []):
                candidates.append((item.get('content', ''), region.get('polygon'), region.get('pageNumber')))
                
        for page in doc.get('pages', []):
            page_number = page.get('page_number')
            for line in page.get('lines', []):
                candidates.append((line.get('content', ''), line.get('polygon'), page_number))
                
        if not candidates:
            continue
            
        for content, polygon, page_number in candidates:
            if not content or not polygon or not page_number:
                continue
                
            content_clean = content.strip().lower()
            if content_clean == item_name_clean:
                ratio = 1.0
            elif item_name_clean in content_clean:
                # Add a small bonus to sequence matcher if it's a substring to prioritize good substrings
                ratio = 0.9 + (len(item_name_clean) / max(len(content_clean), 1)) * 0.1
            else:
                ratio = difflib.SequenceMatcher(None, item_name_clean, content_clean).ratio()
                
            if ratio > best_overall_ratio:
                best_overall_ratio = ratio
                best_match_info = {
                    'content': content,
                    'polygon': polygon,
                    'page_number': page_number,
                    'doc_name': doc_name,
                    'doc': doc
                }
                
                # If perfect match found, we can break early for this document
                if ratio == 1.0:
                    break
                    
        if best_overall_ratio == 1.0:
            break
            
    if best_match_info and best_overall_ratio >= 0.6:
        # Get dimensions for the matched page
        doc = best_match_info['doc']
        page_number = best_match_info['page_number']
        width, height = None, None
        for page in doc.get('pages', []):
            if page.get('page_number') == page_number:
                width = page.get('width')
                height = page.get('height')
                break
                
        quadrant = None
        polygon = best_match_info['polygon']
        if width is not None and height is not None and polygon:
            quadrant = calculate_quadrant(polygon, width, height)
            
        return {
            "anchor": best_match_info['content'],
            "page_index": page_number,
            "quadrant": quadrant,
            "bounding_box": normalize_polygon(polygon),
            "meta_page_idx": {
                "page_index": page_number,
                "document": best_match_info['doc_name']
            }
        }
        
    return None

def main():
    try:
        with open('Data/Tickets/29212/extract.json', 'r') as f:
            extract_data = json.load(f)
            
        with open('Data/JSON/29212.json', 'r') as f:
            azure_data = json.load(f)
            
        for section in extract_data.get('menu_sections', []):
            for item in section.get('menu_items', []):
                item_name = item.get('name')
                if item_name:
                    new_anchors = generate_text_anchors(item_name, azure_data)
                    if new_anchors:
                        item['text_anchors'] = new_anchors
                    
        # Output to new filename
        output_path = 'Data/Tickets/29212/extract_enriched.json'
        with open(output_path, 'w') as f:
            json.dump(extract_data, f, indent=4)
        print(f"Success! Data saved to {output_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
