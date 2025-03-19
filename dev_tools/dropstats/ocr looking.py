import os
import re

def search_ocr_in_folder(folder_path, output_file):
    try:
        # Get a list of all files ending with 'alas.txt' in the folder
        files_to_read = [f for f in os.listdir(folder_path) if f.endswith('alas.txt')]

        if not files_to_read:
            print(f"No files ending with 'alas.txt' found in {folder_path}.")
            return

        # Open the output file for writing
        with open(output_file, 'w', encoding='utf-8') as outfile:
            outfile.write("Lines containing 'OCR_OIL' and 'OCR_COIN':\n")

            # Process each file
            for file_name in files_to_read:
                file_path = os.path.join(folder_path, file_name)
                with open(file_path, 'r', encoding='utf-8') as infile:
                    lines = infile.readlines()

                # Find lines containing 'OCR_OIL', 'OCR_COIN', or headers
                ocr_lines = []
                max_ocr_length = 0  # Track the maximum length of OCR lines

                for line in lines:
                    line = line.strip()

                    # # Check for 'OCR_OIL' or 'OCR_COIN'
                    # if 'OCR_OIL' in line or 'OCR_COIN' in line:
                    #     ocr_lines.append(line)
                    #     # Update the maximum OCR line length
                    #     max_ocr_length = max(max_ocr_length, len(line))
                    if 'OCR_COIN' in line:
                        ocr_lines.append(line)
                        max_ocr_length = max(max_ocr_length, len(line))   

                    # Check for headers
                    elif is_header(line):
                            ocr_lines.append(trim_header(line, max_ocr_length))

                if ocr_lines:
                    outfile.write(f"\nResults from {file_name}:\n")
                    outfile.write("\n".join(ocr_lines))
                    outfile.write("\n")

        print(f"Results written to {output_file}")

    except FileNotFoundError:
        print(f"Error: The folder '{folder_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


def is_header(line):
    """
    Check if a line is a header based on specific rules:
    - Starts and ends with special characters (e.g., '═', '─').
    - Contains specific keywords ('BATTLE', 'HARD', 'CAMPAIGN').
    - Matches the pattern 'x-y', where x is 1-15 and y is 1-4.
    - Matches the pattern 'CP', where C is one letter and P is a single digit.
    """
    # Check if the line starts and ends with special characters
    if not (line.startswith('═') and line.endswith('═')) and \
       not (line.startswith('─') and line.endswith('─')):
        return False

    # Check if the line contains specific keywords
    if 'BATTLE' in line or 'HARD' in line or 'CAMPAIGN' in line:
        return True

    # Check for the 'x-y' pattern, where x is 1-15 and y is 1-4
    if re.search(r'\b(1[0-5]|[1-9])-[1-4]\b', line):
        return True

    # Check for the 'CP' pattern, where C is one letter and P is a single digit
    if re.search(r'\b[A-Za-z]\d\b', line):
        return True

    return False

def trim_header(line, max_length):
    """
    Trim the header line to match the length of the longest OCR line.
    """
    # Extract the left and right line symbols
    left_symbols = re.match(r'^([═─]+)', line)
    right_symbols = re.search(r'([═─]+)$', line)

    # Extract the middle content (variables or text)
    middle_content = re.sub(r'^[═─]+|[═─]+$', '', line).strip()

    # Calculate the desired length for the trimmed symbols
    # Ensure the total length of the header does not exceed the max_length
    if max_length > 0:
        # Calculate the length of the middle content
        middle_length = len(middle_content)
        # Calculate the remaining length for the symbols
        remaining_length = max_length - middle_length
        # Ensure the remaining length is at least 6 (3 symbols on each side)
        remaining_length = max(remaining_length, 6)
        # Split the remaining length equally between left and right symbols
        symbol_length = remaining_length // 2
    else:
        # Default to 3 symbols if no OCR lines are found
        symbol_length = 3

    # Trim the left and right line symbols to the calculated length
    if left_symbols:
        left_trimmed = left_symbols.group(1)[:symbol_length]  # First N symbols
    else:
        left_trimmed = ''

    if right_symbols:
        right_trimmed = right_symbols.group(1)[:symbol_length]  # First N symbols
    else:
        right_trimmed = ''

    # Combine the trimmed symbols and middle content
    return f"{left_trimmed} {middle_content} {right_trimmed}".strip()


# Specify the folder path and output file path
folder_path = './log'  # Replace with your folder path
output_file = './dev_tools/dropstats/output.txt'  # Replace with your desired output file path

# Run the function
search_ocr_in_folder(folder_path, output_file)