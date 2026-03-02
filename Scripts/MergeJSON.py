import os
import json

def merge_jsons():
    # Make sure we use resolving paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, 'Data', 'Output')
    json_dir = os.path.join(base_dir, 'Data', 'JSON')

    # Ensure the destination directory exists
    os.makedirs(json_dir, exist_ok=True)

    if not os.path.exists(output_dir):
        print(f"Directory not found: {output_dir}")
        return

    # Go through each subfolder in Data/Output
    for folder_name in sorted(os.listdir(output_dir)):
        folder_path = os.path.join(output_dir, folder_name)

        if os.path.isdir(folder_path):
            merged_data = []
            
            # Keep track of JSON files found
            json_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.json')])
            if not json_files:
                continue

            for file_name in json_files:
                file_path = os.path.join(folder_path, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                        
                        # Add a reference to the source file if it's a dictionary
                        if isinstance(file_data, dict):
                            file_data['_source_file'] = file_name
                        elif isinstance(file_data, list):
                            # Add source info to each item if it's a list
                            for item in file_data:
                                if isinstance(item, dict):
                                    item['_source_file'] = file_name
                                    
                        merged_data.append(file_data)
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode {file_path} - Skipping.")
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

            # Define the final merged file path
            merged_file_path = os.path.join(json_dir, f"{folder_name}.json")
            
            # Write out the concatenated JSON
            with open(merged_file_path, 'w', encoding='utf-8') as mf:
                json.dump(merged_data, mf, indent=4)
                
            print(f"Merged {len(json_files)} files into {merged_file_path}")

if __name__ == '__main__':
    merge_jsons()
