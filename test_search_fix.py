#!/usr/bin/env python3
"""
测试搜索修复的脚本
"""

import re

def test_keyword_extraction():
    """测试关键词提取功能"""
    query = "找一篇正当防卫的案例"
    
    # 改进分词逻辑，支持中文分词
    # 移除标点符号，分割成词
    clean_query = re.sub(r'[^\w\s]', ' ', query)
    
    # 中文分词：按字符分割，然后组合有意义的词组
    words = []
    for word in clean_query.split():
        word = word.strip()
        if word:
            # 对于中文，按字符分割
            if re.search(r'[\u4e00-\u9fff]', word):
                # 中文词，按字符分割
                chars = list(word)
                # 组合2-4个字符的词组
                for i in range(len(chars)):
                    for j in range(i+2, min(i+5, len(chars)+1)):
                        if j-i >= 2:
                            words.append(''.join(chars[i:j]))
            else:
                # 英文词，直接添加
                words.append(word)
    
    print(f"Split words: {words}")
    
    # 定义常见的法律关键词
    legal_keywords = {
        '刑事': ['刑事', '犯罪', '盗窃', '诈骗', '故意', '正当防卫', '防卫过当', '故意伤害', '故意杀人', '抢劫', '强奸', '猥亵', '贪污', '受贿', '挪用公款'],
    }
    
    # 停用词
    stop_words = {'案例', '案件', '纠纷案', '某某', '诉', '的', '了', '与', '和', '找', '一篇', '一个', '这个', '那个', '什么', '怎么', '如何', '为什么', '因为', '所以', '但是', '然后', '最后', '首先', '其次', '再次', '另外', '还有', '以及', '或者', '还是', '不是', '没有', '可以', '应该', '必须', '需要', '想要', '希望', '觉得', '认为', '知道', '了解', '明白', '清楚', '详细', '具体', '一般', '通常', '经常', '总是', '从不', '很少', '有时', '偶尔', '经常', '总是', '从不', '很少', '有时', '偶尔'}
    
    # 提取关键词
    expanded_keywords = set()
    
    # 添加原始词汇（过滤掉停用词）
    for word in words:
        if len(word) >= 2 and word not in stop_words:
            expanded_keywords.add(word)
    
    # 扩展关键词 - 基于同义词
    for word in words:
        for category, synonyms in legal_keywords.items():
            if word in synonyms or any(synonym in word for synonym in synonyms):
                expanded_keywords.update(synonyms)
                print(f"Expanded '{word}' with category '{category}': {synonyms}")
                break
    
    # 特殊处理
    query_lower = query.lower()
    if '正当防卫' in query_lower:
        expanded_keywords.update(['正当防卫', '防卫', '防卫过当', '故意伤害', '故意杀人', '刑事'])
    
    keywords_list = list(expanded_keywords)
    print(f"Original query: {query}")
    print(f"Final expanded keywords ({len(keywords_list)}): {keywords_list}")
    
    return keywords_list

if __name__ == "__main__":
    print("测试关键词提取功能...")
    keywords = test_keyword_extraction()
    print(f"提取的关键词: {keywords}")
    
    # 测试是否包含"正当防卫"
    if "正当防卫" in keywords:
        print("✅ 成功提取到'正当防卫'关键词")
    else:
        print("❌ 未能提取到'正当防卫'关键词") 