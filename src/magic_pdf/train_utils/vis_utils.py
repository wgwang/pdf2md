from src.magic_pdf.libs.commons import fitz
import os
from src.magic_pdf.libs.coordinate_transform import get_scale_ratio


def draw_model_output(
    raw_pdf_doc: fitz.Document, paras_dict_arr: list[dict], save_path: str
):
    """
    在page上画出bbox，保存到save_path
    """
    """
    
        # {0: 'title',  # 标题
    # 1: 'figure', # 图片
    #  2: 'plain text',  # 文本
    #  3: 'header',      # 页眉
    #  4: 'page number', # 页码
    #  5: 'footnote',    # 脚注
    #  6: 'footer',      # 页脚
    #  7: 'table',       # 表格
    #  8: 'table caption',  # 表格描述
    #  9: 'figure caption', # 图片描述
    #  10: 'equation',      # 公式
    #  11: 'full column',   # 单栏
    #  12: 'sub column',    # 多栏
    #  13: 'embedding',     # 嵌入公式
    #  14: 'isolated'}      # 单行公式
    
    """

    color_map = {
        "body": fitz.pdfcolor["green"],
        "non_body": fitz.pdfcolor["red"],
    }
    """
    {"layout_dets": [], "subfield_dets": [], "page_info": {"page_no": 22, "height": 1650, "width": 1275}}
    """
    for i, page in enumerate(raw_pdf_doc):
        v = paras_dict_arr[i]
        page_idx = v["page_info"]["page_no"]
        width = v["page_info"]["width"]
        height = v["page_info"]["height"]

        horizontal_scale_ratio, vertical_scale_ratio = get_scale_ratio(
            paras_dict_arr[i], page
        )

        for order, block in enumerate(v["layout_dets"]):
            L = block["poly"][0] / horizontal_scale_ratio
            U = block["poly"][1] / vertical_scale_ratio
            R = block["poly"][2] / horizontal_scale_ratio
            D = block["poly"][5] / vertical_scale_ratio
            # L += pageL          # 有的页面，artBox偏移了。不在（0,0）
            # R += pageL
            # U += pageU
            # D += pageU
            L, R = min(L, R), max(L, R)
            U, D = min(U, D), max(U, D)
            bbox = [L, U, R, D]
            color = color_map["body"]
            if block["category_id"] in (3, 4, 5, 6, 0):
                color = color_map["non_body"]

            rect = fitz.Rect(bbox)
            page.draw_rect(rect, fill=None, width=0.5, overlay=True, color=color)

    parent_dir = os.path.dirname(save_path)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
    raw_pdf_doc.save(save_path)


def debug_show_bbox(
    raw_pdf_doc: fitz.Document,
    page_idx: int,
    bboxes: list,
    droped_bboxes: list,
    expect_drop_bboxes: list,
    save_path: str,
    expected_page_id: int,
):
    """
    以覆盖的方式写个临时的pdf，用于debug
    """
    if page_idx != expected_page_id:
        return

    if os.path.exists(save_path):
        # 删除已经存在的文件
        os.remove(save_path)
    # 创建一个新的空白 PDF 文件
    doc = fitz.open("")

    width = raw_pdf_doc[page_idx].rect.width
    height = raw_pdf_doc[page_idx].rect.height
    new_page = doc.new_page(width=width, height=height)

    shape = new_page.new_shape()
    for bbox in bboxes:
        # 原始box画上去
        rect = fitz.Rect(*bbox[0:4])
        shape = new_page.new_shape()
        shape.draw_rect(rect)
        shape.finish(
            color=fitz.pdfcolor["red"], fill=fitz.pdfcolor["blue"], fill_opacity=0.2
        )
        shape.finish()
        shape.commit()

    for bbox in droped_bboxes:
        # 原始box画上去
        rect = fitz.Rect(*bbox[0:4])
        shape = new_page.new_shape()
        shape.draw_rect(rect)
        shape.finish(color=None, fill=fitz.pdfcolor["yellow"], fill_opacity=0.2)
        shape.finish()
        shape.commit()

    for bbox in expect_drop_bboxes:
        # 原始box画上去
        rect = fitz.Rect(*bbox[0:4])
        shape = new_page.new_shape()
        shape.draw_rect(rect)
        shape.finish(color=fitz.pdfcolor["red"], fill=None)
        shape.finish()
        shape.commit()

    # shape.insert_textbox(fitz.Rect(200, 0, 600, 20), f"total bboxes: {len(bboxes)}", fontname="helv", fontsize=12,
    #                      color=(0, 0, 0))
    # shape.finish(color=fitz.pdfcolor['black'])
    # shape.commit()

    parent_dir = os.path.dirname(save_path)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    doc.save(save_path)
    doc.close()


def debug_show_page(
    page,
    bboxes1: list,
    bboxes2: list,
    bboxes3: list,
):
    save_path = "./tmp/debug.pdf"
    if os.path.exists(save_path):
        # 删除已经存在的文件
        os.remove(save_path)
    # 创建一个新的空白 PDF 文件
    doc = fitz.open("")

    width = page.rect.width
    height = page.rect.height
    new_page = doc.new_page(width=width, height=height)

    shape = new_page.new_shape()
    for bbox in bboxes1:
        # 原始box画上去
        rect = fitz.Rect(*bbox[0:4])
        shape = new_page.new_shape()
        shape.draw_rect(rect)
        shape.finish(
            color=fitz.pdfcolor["red"], fill=fitz.pdfcolor["blue"], fill_opacity=0.2
        )
        shape.finish()
        shape.commit()

    for bbox in bboxes2:
        # 原始box画上去
        rect = fitz.Rect(*bbox[0:4])
        shape = new_page.new_shape()
        shape.draw_rect(rect)
        shape.finish(color=None, fill=fitz.pdfcolor["yellow"], fill_opacity=0.2)
        shape.finish()
        shape.commit()

    for bbox in bboxes3:
        # 原始box画上去
        rect = fitz.Rect(*bbox[0:4])
        shape = new_page.new_shape()
        shape.draw_rect(rect)
        shape.finish(color=fitz.pdfcolor["red"], fill=None)
        shape.finish()
        shape.commit()

    parent_dir = os.path.dirname(save_path)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    doc.save(save_path)
    doc.close()


def draw_layout_bbox_on_page(
    raw_pdf_doc: fitz.Document, paras_dict: dict, header, footer, pdf_path: str
):
    """
    在page上画出bbox，保存到save_path
    """
    # 检查文件是否存在
    is_new_pdf = False
    if os.path.exists(pdf_path):
        # 打开现有的 PDF 文件
        doc = fitz.open(pdf_path)
    else:
        # 创建一个新的空白 PDF 文件
        is_new_pdf = True
        doc = fitz.open("")

    for k, v in paras_dict.items():
        page_idx = v["page_idx"]
        layouts = v["layout_bboxes"]
        page = doc[page_idx]
        shape = page.new_shape()
        for order, layout in enumerate(layouts):
            border_offset = 1
            rect_box = layout["layout_bbox"]
            layout_label = layout["layout_label"]
            fill_color = fitz.pdfcolor["pink"] if layout_label == "U" else None
            rect_box = [
                rect_box[0] + 1,
                rect_box[1] - border_offset,
                rect_box[2] - 1,
                rect_box[3] + border_offset,
            ]
            rect = fitz.Rect(*rect_box)
            shape.draw_rect(rect)
            shape.finish(color=fitz.pdfcolor["red"], fill=fill_color, fill_opacity=0.4)
            """
            draw order text on layout box
            """
            font_size = 10
            shape.insert_text(
                (rect_box[0] + 1, rect_box[1] + font_size),
                f"{order}",
                fontsize=font_size,
                color=(0, 0, 0),
            )

        """画上footer header"""
        if header:
            shape.draw_rect(fitz.Rect(header))
            shape.finish(color=None, fill=fitz.pdfcolor["black"], fill_opacity=0.2)
        if footer:
            shape.draw_rect(fitz.Rect(footer))
            shape.finish(color=None, fill=fitz.pdfcolor["black"], fill_opacity=0.2)

        shape.commit()

    if is_new_pdf:
        doc.save(pdf_path)
    else:
        doc.saveIncr()
    doc.close()


@DeprecationWarning
def draw_layout_on_page(
    raw_pdf_doc: fitz.Document, page_idx: int, page_layout: list, pdf_path: str
):
    """
    把layout的box用红色边框花在pdf_path的page_idx上
    """

    def draw(shape, layout, fill_color=fitz.pdfcolor["pink"]):
        border_offset = 1
        rect_box = layout["layout_bbox"]
        layout_label = layout["layout_label"]
        sub_layout = layout["sub_layout"]
        if len(sub_layout) == 0:
            fill_color = fill_color if layout_label == "U" else None
            rect_box = [
                rect_box[0] + 1,
                rect_box[1] - border_offset,
                rect_box[2] - 1,
                rect_box[3] + border_offset,
            ]
            rect = fitz.Rect(*rect_box)
            shape.draw_rect(rect)
            shape.finish(color=fitz.pdfcolor["red"], fill=fill_color, fill_opacity=0.2)
            # if layout_label=='U':
            #     bad_boxes = layout.get("bad_boxes", [])
            #     for bad_box in bad_boxes:
            #         rect = fitz.Rect(*bad_box)
            #         shape.draw_rect(rect)
            #         shape.finish(color=fitz.pdfcolor['red'], fill=fitz.pdfcolor['red'], fill_opacity=0.2)
        # else:
        #     rect = fitz.Rect(*rect_box)
        #     shape.draw_rect(rect)
        #     shape.finish(color=fitz.pdfcolor['blue'])

        for sub_layout in sub_layout:
            draw(shape, sub_layout)
        shape.commit()

    # 检查文件是否存在
    is_new_pdf = False
    if os.path.exists(pdf_path):
        # 打开现有的 PDF 文件
        doc = fitz.open(pdf_path)
    else:
        # 创建一个新的空白 PDF 文件
        is_new_pdf = True
        doc = fitz.open("")

    page = doc[page_idx]
    shape = page.new_shape()
    for order, layout in enumerate(page_layout):
        draw(shape, layout, fitz.pdfcolor["yellow"])

    # shape.insert_textbox(fitz.Rect(200, 0, 600, 20), f"total bboxes: {len(layout)}", fontname="helv", fontsize=12,
    #                      color=(0, 0, 0))
    # shape.finish(color=fitz.pdfcolor['black'])
    # shape.commit()

    parent_dir = os.path.dirname(pdf_path)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    if is_new_pdf:
        doc.save(pdf_path)
    else:
        doc.saveIncr()
    doc.close()
