import re
import os

def clean_date_like_ids_in_file(file_path):
    """
    Reads a file, removes lines that solely consist of a date-like ID pattern
    (e.g., YYYY-MM-D-XXX-XXX), and overwrites the file with the cleaned content.
    """
    # Regex pattern:
    # ^ : Asserts the start of a line (when re.MULTILINE is used).
    # \d{4}-\d{1,2}-\d{1,2}-\d{3}-\d{3} : Matches the date-like ID pattern.
    #     \d{4}    - four digits (year)
    #     \d{1,2}  - one or two digits (month)
    #     \d{1,2}  - one or two digits (day)
    #     \d{3}    - three digits
    #     \d{3}    - three digits
    # \r?\n? : Matches an optional carriage return and an optional newline.
    #          This ensures that the line is removed, whether it's followed by a newline
    #          or if it's the last line of the file without a trailing newline.
    # We must be careful to only remove lines that *only* contain this pattern.
    pattern_to_remove_line = r"^(\d{4}-\d{1,2}-\d{1,2}-\d{3}-\d{3})\s*\r?\n"

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace matched lines with an empty string
        # re.MULTILINE is crucial here to make ^ match the start of each line
        modified_content = re.sub(pattern_to_remove_line, "", content, flags=re.MULTILINE)

        # Handle the case where the last line matches and has no trailing newline
        # This regex looks for a line matching the pattern at the very end of the string.
        pattern_for_last_line = r"\n(\d{4}-\d{1,2}-\d{1,2}-\d{3}-\d{3})\s*$"
        modified_content = re.sub(pattern_for_last_line, "", modified_content)
        
        # A final check for a file that *only* contains the pattern and nothing else
        pattern_only_line = r"^(\d{4}-\d{1,2}-\d{1,2}-\d{3}-\d{3})\s*$"
        if re.fullmatch(pattern_only_line, content.strip()): # strip() to handle potential trailing newline in original
            modified_content = ""


        if modified_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            print(f"成功：已从 '{file_path}' 文件中删除指定的ID行。")
            
            if not modified_content.strip():
                 print(f"警告：文件 '{file_path}' 在清理后为空或只包含空白字符。")
        else:
            print(f"信息：在 '{file_path}' 文件中未找到匹配的ID行。文件内容未更改。")

    except FileNotFoundError:
        print(f"错误：文件 '{file_path}' 未找到。")
    except Exception as e:
        print(f"处理文件 '{file_path}' 时发生错误：{e}")

if __name__ == "__main__":
    # The script is specifically designed for "民事案例/all_cases.txt" as per the request.
    # Construct the full path relative to the script's assumed execution directory.
    # It's assumed this script will be in the root of your project,
    # and "民事案例" is a subdirectory.
    
    workspace_dir = os.getcwd() 
    directory_name = "民事案例"
    file_name = "all_cases.txt"
    
    # Correctly join paths for the target directory and file
    target_directory_path = os.path.join(workspace_dir, directory_name)
    file_to_clean = os.path.join(target_directory_path, file_name)

    # Check if the target directory exists before proceeding
    if not os.path.isdir(target_directory_path):
        # Try to create the directory if it doesn't exist, as it might be a relative path issue
        try:
            os.makedirs(target_directory_path, exist_ok=True)
            print(f"信息：目录 '{target_directory_path}' 不存在，已创建。")
            # Check if the file exists after creating the directory
            if not os.path.isfile(file_to_clean):
                print(f"错误：文件 '{file_to_clean}' 在新创建的目录中未找到。请确保文件存在于该位置。")
            else:
                print(f"正在处理文件: {file_to_clean}")
                clean_date_like_ids_in_file(file_to_clean)
        except OSError as e:
            print(f"错误：创建目录 '{target_directory_path}' 失败: {e}")
            print("请确保脚本从正确的项目根目录运行，或者手动创建目标目录。")

    elif not os.path.isfile(file_to_clean):
        print(f"错误：文件 '{file_to_clean}' 未找到。")
    else:
        print(f"正在处理文件: {file_to_clean}")
        clean_date_like_ids_in_file(file_to_clean) 