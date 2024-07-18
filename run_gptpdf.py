#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  :run_gptpdf.py
# @Time      :2024/07/18 14:35:07
# @Author    :Wangjian

import os
from src.gptpdf import parse_pdf

file_path = './docs/1973-02-化肥厂厂房合并设计.pdf'
filename = os.path.basename(file_path)

content, all_rect_images = parse_pdf(
    pdf_path=file_path,
    output_dir = f'./output/gptpdf/{filename}',
    model = 'gpt-4o',
    api_key= "sk-xxxxxxxxxxxxxxxxxxx",
    base_url= "https://api.openai.com/v1"
    )