import re
import sys
import os

def clean_case_content_in_file(filepath):
    """Reads a file, cleans its content according to specified rules, and overwrites it."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        modified_content = content

        # Rule 1: Remove "指导案例 号：" or "指导性案例 号：" (replace with a space)
        modified_content = re.sub(r"指导(性)?案例\s*号：", " ", modified_content)

        # Rule 2: Remove time/ID strings. This covers:
        # - YYYY-MM-DD-XXX-XXX (standalone ID)
        # - YYYY-MM-DD-XXX-XXX NNN (ID followed by one number)
        # - YYYY-MM-DD-XXX-XXX NNN NNN (ID followed by two numbers)
        # Regex: optional leading/trailing space, the ID pattern, optionally followed by one or two numbers.
        id_pattern_core = r"\d{4}-\d{1,2}-\d{1,2}-\d{3}-\d{3}"
        numbers_after_id_pattern = r"(\s+\d+(?:\s+\d+)?)?"
        pattern_to_remove_ids = rf'\s*({id_pattern_core}{numbers_after_id_pattern})\s*'
        modified_content = re.sub(pattern_to_remove_ids, ' ', modified_content)
        
        # Remove multiple consecutive spaces that might have been created by replacements
        modified_content = re.sub(r'\s{2,}', ' ', modified_content).strip()
        # Also, specifically handle cases where a line might now be just whitespace due to removal
        # and we want to remove such empty lines or lines that became just spaces.
        lines = modified_content.split('\n')
        cleaned_lines = [line for line in lines if line.strip()] # Keep lines that are not just whitespace
        modified_content = '\n'.join(cleaned_lines)

        if modified_content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            print(f"成功：文件 '{filepath}' 的内容已清理并覆盖保存。")
        else:
            print(f"信息：文件 '{filepath}' 的内容无需清理，未作修改。")
            
    except FileNotFoundError:
        print(f"错误：文件 '{filepath}' 未找到。")
    except Exception as e:
        print(f"处理文件 '{filepath}' 时发生错误: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python clean_single_all_cases_file.py <文件路径>")
        print("示例: python clean_single_all_cases_file.py 行政案例/all_cases.txt")
        sys.exit(1)
    
    file_to_clean = sys.argv[1]
    
    if not os.path.isfile(file_to_clean):
        print(f"错误: 指定的文件路径 '{file_to_clean}' 不是一个有效的文件。")
        sys.exit(1)
        
    print(f"正在清理文件: {file_to_clean}")
    clean_case_content_in_file(file_to_clean) 