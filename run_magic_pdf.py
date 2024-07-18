#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  :run.py
# @Time      :2024/07/18 13:54:39
# @Author    :Wangjian
import os
import json
from pathlib import Path
from loguru import logger

from src.magic_pdf.rw.S3ReaderWriter import S3ReaderWriter
from src.magic_pdf.rw.DiskReaderWriter import DiskReaderWriter
from src.magic_pdf.rw.AbsReaderWriter import AbsReaderWriter

from src.magic_pdf.cli.magicpdf import do_parse


def read_fn(path):
    disk_rw = DiskReaderWriter(os.path.dirname(path))
    return disk_rw.read(os.path.basename(path), AbsReaderWriter.MODE_BIN)
    

def get_model_json(model_path, doc_path):
    # 这里处理pdf和模型相关的逻辑
    if model_path is None:
        file_name_without_extension, extension = os.path.splitext(doc_path)
        if extension == ".pdf":
            model_path = file_name_without_extension + ".json"
        else:
            raise Exception("pdf_path input error")
        if not os.path.exists(model_path):
            logger.warning(
                f"not found json {model_path} existed"
            )
            # 本地无模型数据则调用内置paddle分析，先传空list，在内部识别到空list再调用paddle
            model_json = "[]"
        else:
            model_json = read_fn(model_path).decode("utf-8")
    else:
        model_json = read_fn(model_path).decode("utf-8")

    return model_json
    
    
def parse_doc(doc_path, model=None, method='auto'):
    """解析pdf文档

    Args:
        doc_path (_type_): 文档路径
        model (_type_): 模型的路径, None则使用默认模型
        method (_type_):指定解析方法。txt: 文本型 pdf 解析方法， ocr: 光学识别解析 pdf, auto: 程序智能选择解析方法
    """
    try:
        file_name = str(Path(doc_path).stem)
        pdf_data = read_fn(doc_path)
        model_list = json.loads(get_model_json(model, doc_path))

        do_parse(
            pdf_file_name=file_name,
            pdf_bytes=pdf_data,
            model_list=model_list,
            parse_method=method,
        )

    except Exception as e:
        logger.exception(e)


if __name__ == "__main__":
    parse_doc(doc_path='./docs/1973-02-化肥厂厂房合并设计.pdf')