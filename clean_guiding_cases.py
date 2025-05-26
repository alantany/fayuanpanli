import os
import re
import shutil

def sanitize_filename(name):
    """Cleans and shortens a string to be a valid filename."""
    # 移除 "【" 和 "】" 及其内部内容（如果仅为空格或特定标记）
    name = re.sub(r"【.*?】", "", name).strip()
    
    # 进一步清理，移除路径非法字符
    name = re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9_（）()、·\s-]', '', name)
    # 移除首尾可能存在的破折号或空格
    name = name.strip(" -_")
    # 将多个空格替换为单个空格
    name = re.sub(r'\s+', ' ', name).strip()
    
    # 截断文件名以避免过长，同时保留可读性
    return name[:60] # 截断到60个字符

def clean_and_rename_case_file(filepath, target_dir):
    """Cleans the content of a single case file and renames it."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content

        # 1. 去掉 "指导案例 号：" 或 "指导性案例 号：" (替换为空格，避免意外合并)
        content = re.sub(r"指导(性)?案例\s*号：", " ", content)

        # 2. 去掉时间信息，例如 "2020-18-2-001-001 141 1" (替换为空格)
        # 正则表达式：匹配可选的前导空格，然后是日期ID模式，然后是至少一个空格，数字，可选的(空格，数字)，可选的尾随空格
        pattern_to_remove = r'\s*\d{4}-\d{1,2}-\d{1,2}-\d{3}-\d{3}\s+\d+(?:\s+\d+)?\s*'
        content = re.sub(pattern_to_remove, ' ', content)
        
        # 移除可能由替换产生的多个连续空格
        content = re.sub(r'\s{2,}', ' ', content).strip()

        # 提取新的文件名 【】指导案例 号：支某 等诉北京市永定河管 2020-18-2-001-001 141 1 理处生命权、健康权、身体权纠纷案
        # 清理后的内容应该是 【】 支某 等诉北京市永定河管 理处生命权、健康权、身体权纠纷案
        # 文件名应该是 "支某 等诉北京市永定河管 理处生命权、健康权、身体权纠纷案"
        
        # 首先尝试从清理后的内容中提取
        # 我们期望的格式是 【可能为空或空格】实际标题案
        title_match = re.search(r'【.*?】(.*?案)', content, re.DOTALL)
        new_filename_base = "cleaned_case"
        
        if title_match:
            extracted_title = title_match.group(1).strip()
            # 进一步清理，移除可能由上述替换引入的前导/尾随杂质，直到第一个有效字符
            extracted_title = re.sub(r"^[^\u4e00-\u9fa5A-Za-z0-9]+", "", extracted_title)
            if extracted_title:
                new_filename_base = sanitize_filename(extracted_title)
        
        if not new_filename_base or new_filename_base == "cleaned_case": # 如果提取失败或为空
            # 尝试从原始文件名中获取一些提示，以防万一
            original_basename = os.path.splitext(os.path.basename(filepath))[0]
            new_filename_base = sanitize_filename(original_basename + "_cleaned")

        new_filename = f"{new_filename_base}.txt"
        new_filepath = os.path.join(target_dir, new_filename)

        # 防止文件名冲突
        counter = 1
        temp_new_filepath = new_filepath
        while os.path.exists(temp_new_filepath) and temp_new_filepath != filepath:
            name_part, extension = os.path.splitext(new_filename)
            temp_new_filepath = os.path.join(target_dir, f"{name_part}_{counter}{extension}")
            counter += 1
        new_filepath = temp_new_filepath

        # 将清理后的内容写回（如果内容有变或文件名要变）
        if content != original_content or new_filepath != filepath:
            with open(filepath, 'w', encoding='utf-8') as f: # 先写回原文件
                f.write(content)
            print(f"内容已清理: '{os.path.basename(filepath)}'")

            if new_filepath != filepath:
                try:
                    os.rename(filepath, new_filepath)
                    print(f"重命名: '{os.path.basename(filepath)}' -> '{os.path.basename(new_filepath)}'")
                except OSError as e:
                    print(f"错误：无法重命名文件 '{filepath}' 到 '{new_filepath}': {e}")
            elif content == original_content:
                 print(f"信息：文件 '{os.path.basename(filepath)}' 内容未变且无需重命名。")
        else:
            print(f"信息：文件 '{os.path.basename(filepath)}' 无需改动。")
            
    except Exception as e:
        print(f"处理文件 '{filepath}' 时发生错误: {e}")

def process_directory(directory_path):
    """Processes all .txt files in the given directory."""
    if not os.path.isdir(directory_path):
        print(f"错误：目录 '{directory_path}' 不存在。")
        return

    print(f"正在处理目录: {directory_path}")
    processed_count = 0
    for filename in os.listdir(directory_path):
        if filename.endswith(".txt"):
            filepath = os.path.join(directory_path, filename)
            clean_and_rename_case_file(filepath, directory_path) # Pass directory_path as target_dir
            processed_count += 1
    
    if processed_count == 0:
        print(f"在目录 '{directory_path}' 中未找到 .txt 文件进行处理。")
    else:
        print(f"处理完成。共处理了 {processed_count} 个 .txt 文件。")

if __name__ == "__main__":
    # workspace_dir = os.getcwd() # Assuming the script is run from the workspace root
    # target_directory_name = "指导案"
    # directory_to_process = os.path.join(workspace_dir, target_directory_name)
    
    # 更直接的方式，如果脚本就放在工作区根目录
    directory_to_process = "指导案" 

    process_directory(directory_to_process) 