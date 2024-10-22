from loguru import logger

from src.magic_pdf.libs.MakeContentConfig import DropMode, MakeMode
from src.magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from src.magic_pdf.rw.AbsReaderWriter import AbsReaderWriter
from src.magic_pdf.libs.json_compressor import JsonCompressor
from src.magic_pdf.pipe.AbsPipe import AbsPipe
from src.magic_pdf.user_api import parse_txt_pdf


class TXTPipe(AbsPipe):

    def __init__(self, pdf_bytes: bytes, model_list: list, image_writer: AbsReaderWriter, is_debug: bool = False):
        super().__init__(pdf_bytes, model_list, image_writer, is_debug)

    def pipe_classify(self):
        pass

    def pipe_analyze(self):
        self.model_list = doc_analyze(self.pdf_bytes, ocr=False)

    def pipe_parse(self):
        self.pdf_mid_data = parse_txt_pdf(self.pdf_bytes, self.model_list, self.image_writer, is_debug=self.is_debug)

    def pipe_mk_uni_format(self, img_parent_path: str, drop_mode=DropMode.WHOLE_PDF):
        result = super().pipe_mk_uni_format(img_parent_path, drop_mode)
        logger.info("txt_pipe mk content list finished")
        return result

    def pipe_mk_markdown(self, img_parent_path: str, drop_mode=DropMode.WHOLE_PDF, md_make_mode=MakeMode.MM_MD):
        result = super().pipe_mk_markdown(img_parent_path, drop_mode, md_make_mode)
        logger.info(f"txt_pipe mk {md_make_mode} finished")
        return result
