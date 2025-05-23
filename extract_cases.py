import os
import pdfplumber
import re
import sys
import string

def clean_page(text):
    # 去除页眉三行
    lines = text.split('\n')
    # 检查前3行是否为页眉内容
    if len(lines) >= 3 and all(s in lines[i] for i, s in enumerate([
        '本汇编材料免费下载', '声明：仅用于个人学习', '汇编人：浙江金道'])):
        lines = lines[3:]
    # 去除多余空格
    lines = [line.strip() for line in lines if line.strip()]
    return '\n'.join(lines)

def extract_full_text(pdf_path, start_page=143):
    with pdfplumber.open(pdf_path) as pdf:
        texts = []
        for i in range(start_page, len(pdf.pages)):
            page_text = pdf.pages[i].extract_text() or ''
            page_text = clean_page(page_text)
            texts.append(page_text)
        full_text = '\n'.join(texts)
    return full_text

def extract_all_cases(txt_path, out_dir):
    with open(txt_path, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # 修改后的切分逻辑：
    # 我们假设每个案例都以 "【" 开头。
    # 我们首先在每个 "【" 字符处分割文本，除了第一个（如果文本以 "【" 开头）。
    # 这样，列表中的每个元素（除了可能为空的第一个元素）都代表一个以 "【" 开头的案例。
    
    # 确保文本中至少有一个 "【"
    if '【' not in full_text:
        print(f"警告: 在文件 {txt_path} 中未找到案件起始标志 '【'。无法切分案例。")
        # 创建一个包含整个文本的case，以防是一个单独的长文本案例
        os.makedirs(out_dir, exist_ok=True)
        sanitized_name = "case_0"
        # 尝试从文本中提取一个合适的文件名
        first_line = full_text.split('\n', 1)[0]
        # 清理文件名中的非法字符，并截断
        temp_name = re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9_（）()、·-]', '', first_line)
        if temp_name:
            sanitized_name = temp_name[:50] if len(temp_name) > 50 else temp_name

        with open(os.path.join(out_dir, f"{sanitized_name}.txt"), 'w', encoding='utf-8') as f:
            f.write(full_text)
        print(f"已将整个文件内容保存为单个案例到 {out_dir}/{sanitized_name}.txt")
        return

    raw_cases = full_text.split('【')
    cases = []
    
    # 第一个元素如果为空或者不包含有效的案件内容（例如，如果原文不是以'【'开头），则忽略
    # 或者，如果原文以 '【' 开头，则第一个元素是空的，第二个元素是第一个案件（不带'【'）
    # 为了统一处理，我们将 '【' 加回到每个案件的开头。
    
    current_case_content = ""
    if not full_text.startswith('【') and raw_cases[0].strip():
        # 如果文本不是以 "【" 开头，且第一个分割块有内容，
        # 这种情况理论上不应该发生，如果我们的假设（案件以【开头）是正确的。
        # 但作为一种容错，我们可以选择将其保存或忽略。这里选择忽略。
        print(f"警告: 文件 {txt_path} 的开头部分不符合预期的案件格式（不是以 '【' 开始）。该部分将被忽略。")
        start_index = 1
    else:
        # 如果文本以 "【" 开头, raw_cases[0] 将是空字符串
        start_index = 1 # 从第二个元素开始，因为它代表第一个案件的内容（不含【）

    for i in range(start_index, len(raw_cases)):
        if raw_cases[i].strip(): #确保不是空字符串
             cases.append('【' + raw_cases[i].strip()) # 将 "【" 加回去，并去除两端空白

    if not cases:
        print(f"警告: 文件 {txt_path} 中虽然找到了 '【'，但未能成功切分出任何有效案例。")
        # 类似上面的处理，保存整个文件为一个案例
        os.makedirs(out_dir, exist_ok=True)
        sanitized_name = "case_0_after_split_attempt"
        first_line = full_text.split('\n', 1)[0]
        temp_name = re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9_（）()、·-]', '', first_line)
        if temp_name:
            sanitized_name = temp_name[:50] if len(temp_name) > 50 else temp_name
        
        with open(os.path.join(out_dir, f"{sanitized_name}.txt"), 'w', encoding='utf-8') as f:
            f.write(full_text)
        print(f"已将整个文件内容保存为单个案例到 {out_dir}/{sanitized_name}.txt")
        return

    os.makedirs(out_dir, exist_ok=True)
    used_names = set()
    
    for idx, case_text in enumerate(cases, 1):
        # 提取案例名，从 "【" 和 "】" 之间提取，然后取 "】" 之后到 "案" 字的部分
        # 去掉换行、空格、特殊符号，最长50字符
        title_match = re.search(r'【(.*?)】([\s\S]*?案)', case_text, re.DOTALL)
        case_title_for_filename = f"case_{idx}" # 默认文件名

        if title_match:
            part1 = title_match.group(1).replace('\n', '').strip()
            part2 = title_match.group(2).replace('\n', '').strip()
            combined_title = f"{part1}_{part2}" if part1 and part2 else part1 if part1 else part2
            
            # 清理特殊符号
            cleaned_title = re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9_（）()、·-]', '', combined_title)
            
            # 截断过长
            case_title_for_filename = cleaned_title[:50] if len(cleaned_title) > 50 else cleaned_title
            if not case_title_for_filename: # 如果清理后为空
                 case_title_for_filename = f"case_{idx}_cleaned_empty"
        else:
            # 如果上面的正则匹配不到，尝试一个更简单的，只取 "【" 和 "】" 之间的
            simple_title_match = re.search(r'【(.*?)】', case_text)
            if simple_title_match:
                extracted_part = simple_title_match.group(1).replace('\n', '').strip()
                cleaned_title = re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9_（）()、·-]', '', extracted_part)
                case_title_for_filename = cleaned_title[:50] if len(cleaned_title) > 50 else cleaned_title
                if not case_title_for_filename: # 如果清理后为空
                    case_title_for_filename = f"case_{idx}_simple_cleaned_empty"
            # else case_title_for_filename 保持为 "case_{idx}"
            
        filename = f'{case_title_for_filename}.txt'
        
        # 防止重名
        original_filename = filename
        counter = 1
        while filename in used_names:
            name_part, extension = os.path.splitext(original_filename)
            filename = f'{name_part}_{counter}{extension}'
            counter += 1
        used_names.add(filename)

        with open(os.path.join(out_dir, filename), 'w', encoding='utf-8') as f:
            f.write(case_text) # case_text 已经包含了 '【'
            
    print(f'已提取 {len(cases)} 个案例到 {out_dir}/')

def process_pdf(pdf_file, start_page, out_dir):
    dir_name = pdf_file.replace('.pdf', '')
    os.makedirs(dir_name, exist_ok=True)
    # 1. 整体保存为txt
    full_text = extract_full_text(pdf_file, start_page=start_page)
    txt_path = os.path.join(dir_name, 'all_cases.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    print(f'已将PDF正文整体保存为 {txt_path}')
    # 2. 分割案例
    cases_dir = os.path.join(dir_name, out_dir)
    extract_all_cases(txt_path, cases_dir)

def main():
    if len(sys.argv) == 2 and sys.argv[1].endswith('.txt'):
        # 只分割已存在的all_cases.txt
        txt_path = sys.argv[1]
        out_dir = os.path.join(os.path.dirname(txt_path), 'cases')
        extract_all_cases(txt_path, out_dir)
        return
    if len(sys.argv) < 3:
        print('用法:')
        print('  1. 提取PDF: python extract_cases.py <pdf文件名> <正文起始页(从1开始)>')
        print('  2. 分割TXT: python extract_cases.py <all_cases.txt>')
        print('示例: python extract_cases.py 民事案件.pdf 189')
        print('示例: python extract_cases.py 民事案例/all_cases.txt')
        return
    pdf_file = sys.argv[1]
    start_page = int(sys.argv[2]) - 1  # 转为0起始
    process_pdf(pdf_file, start_page=start_page, out_dir='cases')

if __name__ == '__main__':
    main() 