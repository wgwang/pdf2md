"""
这里实现2个click命令：
第一个：
 接收一个完整的s3路径，例如：s3://llm-pdf-text/pdf_ebook_and_paper/pre-clean-mm-markdown/v014/part-660420b490be-000008.jsonl?bytes=0,81350
    1）根据~/magic-pdf.json里的ak,sk等，构造s3cliReader读取到这个jsonl的对应行，返回json对象。
    2）根据Json对象里的pdf的s3路径获取到他的ak,sk,endpoint，构造出s3cliReader用来读取pdf
    3）从magic-pdf.json里读取到本地保存图片、Md等的临时目录位置,构造出LocalImageWriter，用来保存截图
    4）从magic-pdf.json里读取到本地保存图片、Md等的临时目录位置,构造出LocalIRdWriter，用来读写本地文件
    
    最后把以上步骤准备好的对象传入真正的解析API
    
第二个：
  接收1）pdf的本地路径。2）模型json文件（可选）。然后：
    1）根据~/magic-pdf.json读取到本地保存图片、md等临时目录的位置，构造出LocalImageWriter，用来保存截图
    2）从magic-pdf.json里读取到本地保存图片、Md等的临时目录位置,构造出LocalIRdWriter，用来读写本地文件
    3）根据约定，根据pdf本地路径，推导出pdf模型的json，并读入
    

效果：
python magicpdf.py json-command --json  s3://llm-pdf-text/scihub/xxxx.json?bytes=0,81350
python magicpdf.py pdf-command --pdf  /home/llm/Downloads/xxxx.pdf --model /home/llm/Downloads/xxxx.json  或者 python magicpdf.py --pdf  /home/llm/Downloads/xxxx.pdf
"""

import os
import json as json_parse
import click
from loguru import logger
from pathlib import Path
from src.magic_pdf.libs.version import __version__

from src.magic_pdf.libs.MakeContentConfig import DropMode, MakeMode
from src.magic_pdf.libs.draw_bbox import draw_layout_bbox, draw_span_bbox
from src.magic_pdf.pipe.UNIPipe import UNIPipe
from src.magic_pdf.pipe.OCRPipe import OCRPipe
from src.magic_pdf.pipe.TXTPipe import TXTPipe
from src.magic_pdf.libs.path_utils import (
    parse_s3path,
    parse_s3_range_params,
    remove_non_official_s3_args,
)
from src.magic_pdf.libs.config_reader import (
    get_local_dir,
    get_s3_config,
)
from src.magic_pdf.rw.S3ReaderWriter import S3ReaderWriter
from src.magic_pdf.rw.DiskReaderWriter import DiskReaderWriter
from src.magic_pdf.rw.AbsReaderWriter import AbsReaderWriter
import csv
import copy
import src.magic_pdf.model as model_config

parse_pdf_methods = click.Choice(["ocr", "txt", "auto"])


def prepare_env(pdf_file_name, method):
    local_parent_dir = os.path.join(get_local_dir(), "magic-pdf", pdf_file_name, method)

    local_image_dir = os.path.join(str(local_parent_dir), "images")
    local_md_dir = local_parent_dir
    os.makedirs(local_image_dir, exist_ok=True)
    os.makedirs(local_md_dir, exist_ok=True)
    return local_image_dir, local_md_dir


def write_to_csv(csv_file_path, csv_data):
    with open(csv_file_path, mode="a", newline="", encoding="utf-8") as csvfile:
        # 创建csv writer对象
        csv_writer = csv.writer(csvfile)
        # 写入数据
        csv_writer.writerow(csv_data)
    logger.info(f"数据已成功追加到 '{csv_file_path}'")


def do_parse(
        pdf_file_name,
        pdf_bytes,
        model_list,
        parse_method,
        f_draw_span_bbox=True,
        f_draw_layout_bbox=True,
        f_dump_md=True,
        f_dump_middle_json=True,
        f_dump_model_json=True,
        f_dump_orig_pdf=True,
        f_dump_content_list=True,
        f_make_md_mode=MakeMode.MM_MD,
):
    orig_model_list = copy.deepcopy(model_list)

    local_image_dir, local_md_dir = prepare_env(pdf_file_name, parse_method)
    logger.info(f"local output dir is {local_md_dir}")
    logger.info(f"local image dir is {local_md_dir}")
    image_writer, md_writer = DiskReaderWriter(local_image_dir), DiskReaderWriter(local_md_dir)
    image_dir = str(os.path.basename(local_image_dir))

    if parse_method == "auto":
        jso_useful_key = {"_pdf_type": "", "model_list": model_list}
        pipe = UNIPipe(pdf_bytes, jso_useful_key, image_writer, is_debug=True)
    elif parse_method == "txt":
        pipe = TXTPipe(pdf_bytes, model_list, image_writer, is_debug=True)
    elif parse_method == "ocr":
        pipe = OCRPipe(pdf_bytes, model_list, image_writer, is_debug=True)
    else:
        logger.error("unknown parse method")
        exit(1)

    pipe.pipe_classify()

    """如果没有传入有效的模型数据，则使用内置model解析"""
    if len(model_list) == 0:
        if model_config.__use_inside_model__:
            pipe.pipe_analyze()
            orig_model_list = copy.deepcopy(pipe.model_list)
        else:
            logger.error("need model list input")
            exit(1)

    pipe.pipe_parse()
    pdf_info = pipe.pdf_mid_data["pdf_info"]
    if f_draw_layout_bbox:
        draw_layout_bbox(pdf_info, pdf_bytes, local_md_dir)
    if f_draw_span_bbox:
        draw_span_bbox(pdf_info, pdf_bytes, local_md_dir)

    md_content = pipe.pipe_mk_markdown(image_dir, drop_mode=DropMode.NONE, md_make_mode=f_make_md_mode)
    if f_dump_md:
        """写markdown"""
        md_writer.write(
            content=md_content,
            path=f"{pdf_file_name}.md",
            mode=AbsReaderWriter.MODE_TXT,
        )

    if f_dump_middle_json:
        """写middle_json"""
        md_writer.write(
            content=json_parse.dumps(pipe.pdf_mid_data, ensure_ascii=False, indent=4),
            path=f"{pdf_file_name}_middle.json",
            mode=AbsReaderWriter.MODE_TXT,
        )

    if f_dump_model_json:
        """写model_json"""
        md_writer.write(
            content=json_parse.dumps(orig_model_list, ensure_ascii=False, indent=4),
            path=f"{pdf_file_name}_model.json",
            mode=AbsReaderWriter.MODE_TXT,
        )

    if f_dump_orig_pdf:
        """写源pdf"""
        md_writer.write(
            content=pdf_bytes,
            path=f"{pdf_file_name}_origin.pdf",
            mode=AbsReaderWriter.MODE_BIN,
        )

    content_list = pipe.pipe_mk_uni_format(image_dir, drop_mode=DropMode.NONE)
    if f_dump_content_list:
        """写content_list"""
        md_writer.write(
            content=json_parse.dumps(content_list, ensure_ascii=False, indent=4),
            path=f"{pdf_file_name}_content_list.json",
            mode=AbsReaderWriter.MODE_TXT,
        )


@click.group()
@click.version_option(__version__, "--version", "-v", help="显示版本信息")
@click.help_option("--help", "-h", help="显示帮助信息")
def cli():
    pass


@cli.command()
@click.option("--json", type=str, help="输入一个S3路径")
@click.option(
    "--method",
    type=parse_pdf_methods,
    help="指定解析方法。txt: 文本型 pdf 解析方法， ocr: 光学识别解析 pdf, auto: 程序智能选择解析方法",
    default="auto",
)
@click.option("--inside_model", type=click.BOOL, default=False, help="使用内置模型测试")
@click.option("--model_mode", type=click.STRING, default="full",
              help="内置模型选择。lite: 快速解析，精度较低，full: 高精度解析，速度较慢")
def json_command(json, method, inside_model, model_mode):
    model_config.__use_inside_model__ = inside_model
    model_config.__model_mode__ = model_mode

    if not json.startswith("s3://"):
        logger.error("usage: magic-pdf json-command --json s3://some_bucket/some_path")
        exit(1)

    def read_s3_path(s3path):
        bucket, key = parse_s3path(s3path)

        s3_ak, s3_sk, s3_endpoint = get_s3_config(bucket)
        s3_rw = S3ReaderWriter(
            s3_ak, s3_sk, s3_endpoint, "auto", remove_non_official_s3_args(s3path)
        )
        may_range_params = parse_s3_range_params(s3path)
        if may_range_params is None or 2 != len(may_range_params):
            byte_start, byte_end = 0, None
        else:
            byte_start, byte_end = int(may_range_params[0]), int(may_range_params[1])
            byte_end += byte_start - 1
        return s3_rw.read_jsonl(
            remove_non_official_s3_args(s3path),
            byte_start,
            byte_end,
            AbsReaderWriter.MODE_BIN,
        )

    jso = json_parse.loads(read_s3_path(json).decode("utf-8"))
    s3_file_path = jso.get("file_location")
    if s3_file_path is None:
        s3_file_path = jso.get("path")
    pdf_file_name = Path(s3_file_path).stem
    pdf_data = read_s3_path(s3_file_path)

    do_parse(
        pdf_file_name,
        pdf_data,
        jso["doc_layout_result"],
        method,
    )


@cli.command()
@click.option("--local_json", type=str, help="输入一个本地jsonl路径")
@click.option(
    "--method",
    type=parse_pdf_methods,
    help="指定解析方法。txt: 文本型 pdf 解析方法， ocr: 光学识别解析 pdf, auto: 程序智能选择解析方法",
    default="auto",
)
@click.option("--inside_model", type=click.BOOL, default=False, help="使用内置模型测试")
@click.option("--model_mode", type=click.STRING, default="full",
              help="内置模型选择。lite: 快速解析，精度较低，full: 高精度解析，速度较慢")
def local_json_command(local_json, method, inside_model, model_mode):
    model_config.__use_inside_model__ = inside_model
    model_config.__model_mode__ = model_mode

    def read_s3_path(s3path):
        bucket, key = parse_s3path(s3path)

        s3_ak, s3_sk, s3_endpoint = get_s3_config(bucket)
        s3_rw = S3ReaderWriter(
            s3_ak, s3_sk, s3_endpoint, "auto", remove_non_official_s3_args(s3path)
        )
        may_range_params = parse_s3_range_params(s3path)
        if may_range_params is None or 2 != len(may_range_params):
            byte_start, byte_end = 0, None
        else:
            byte_start, byte_end = int(may_range_params[0]), int(may_range_params[1])
            byte_end += byte_start - 1
        return s3_rw.read_jsonl(
            remove_non_official_s3_args(s3path),
            byte_start,
            byte_end,
            AbsReaderWriter.MODE_BIN,
        )

    with open(local_json, "r", encoding="utf-8") as f:
        for json_line in f:
            jso = json_parse.loads(json_line)

            s3_file_path = jso.get("file_location")
            if s3_file_path is None:
                s3_file_path = jso.get("path")
            pdf_file_name = Path(s3_file_path).stem
            pdf_data = read_s3_path(s3_file_path)
            do_parse(
                pdf_file_name,
                pdf_data,
                jso["doc_layout_result"],
                method,
            )


@cli.command()
@click.option(
    "--pdf", type=click.Path(exists=True), required=True,
    help='pdf file path, support local/list, list file need end with ".list"')
@click.option("--model", type=click.Path(exists=True), help="模型的路径")
@click.option(
    "--method",
    type=parse_pdf_methods,
    help="指定解析方法。txt: 文本型 pdf 解析方法， ocr: 光学识别解析 pdf, auto: 程序智能选择解析方法",
    default="auto",
)
@click.option("--inside_model", type=click.BOOL, default=False, help="使用内置模型测试")
@click.option("--model_mode", type=click.STRING, default="full",
              help="内置模型选择。lite: 快速解析，精度较低，full: 高精度解析，速度较慢")
def pdf_command(pdf, model, method, inside_model, model_mode):
    model_config.__use_inside_model__ = inside_model
    model_config.__model_mode__ = model_mode

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

    def parse_doc(doc_path):
        try:
            file_name = str(Path(doc_path).stem)
            pdf_data = read_fn(doc_path)
            jso = json_parse.loads(get_model_json(model, doc_path))

            do_parse(
                file_name,
                pdf_data,
                jso,
                method,
            )

        except Exception as e:
            logger.exception(e)

    if not pdf:
        logger.error(f"Error: Missing argument '--pdf'.")
        exit(f"Error: Missing argument '--pdf'.")
    else:
        '''适配多个文档的list文件输入'''
        if pdf.endswith(".list"):
            with open(pdf, "r") as f:
                for line in f.readlines():
                    line = line.strip()
                    parse_doc(line)
        else:
            '''适配单个文档的输入'''
            parse_doc(pdf)


if __name__ == "__main__":
    """
    python magic_pdf/cli/magicpdf.py json-command --json s3://llm-pdf-text/pdf_ebook_and_paper/manual/v001/part-660407a28beb-000002.jsonl?bytes=0,63551
    """
    cli()
