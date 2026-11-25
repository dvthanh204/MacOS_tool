"""
Module: ribbon_policy_mac.py
Microsoft Office Fluent UI Ribbon Policy Injector - Tối ưu cho macOS & Cross-Platform
Vô hiệu hóa triệt để SAVE AS và COPY trong PowerPoint trên MacBook (Microsoft PowerPoint for Mac):
1. CHO PHÉP CHỈNH SỬA & LƯU BÀI GIẢNG:
   - FileSave (Cmd+S trên Mac, nút Lưu): HOÀN TOÀN ĐƯỢC PHÉP ĐỂ ĐỒNG BỘ VÀO FILE MÃ HÓA
   - Text Editing, Shape, Animation, Slide Insert/Delete: HOÀN TOÀN ĐƯỢC PHÉP
   - Paste (Cmd+V): HOÀN TOÀN ĐƯỢC PHÉP
2. CẤM TUYỆT ĐỐI SAVE AS (KHÔNG CHO PHÉP LƯU RA FILE MỚI):
   - Khóa toàn bộ lệnh Save As, Save a Copy, Export, Print
   - Ẩn toàn bộ tab Save As, Save a Copy, Export, Share, Print trong Backstage (Menu File)
3. CẤM TUYỆT ĐỐI COPY & CUT:
   - Khóa Copy, Cut, Duplicate trên thanh công cụ Ribbon và Context Menu
4. TỐI ƯU HÓA CHO MACBOOK (MACOS):
   - Xóa bỏ danh sách phông chữ nhúng Windows (embeddedFontLst) để tránh hộp thoại cảnh báo
     "This presentation contains embedded fonts" gây khó chịu trên PowerPoint for Mac.
"""

import io
import re
import zipfile
import xml.etree.ElementTree as ET

RELATIONSHIP_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CUSTOMUI14_REL_TYPE = "http://schemas.microsoft.com/office/2007/relationships/ui/extensibility"
CUSTOMUI14_TARGET = "customUI/customUI14.xml"

CUSTOMUI_REL_TYPE = "http://schemas.microsoft.com/office/2006/relationships/ui/extensibility"
CUSTOMUI_TARGET = "customUI/customUI.xml"


def generate_ribbon_xml_14(block_save_as: bool = True, block_copy: bool = True, block_print: bool = True) -> str:
    """Tạo Ribbon XML cho Office 2010/2013/2016/2019/2021/365 và Office for Mac"""
    commands = []
    backstage_tabs = []
    context_menus = []

    if block_copy:
        commands.extend([
            '    <!-- VÔ HIỆU HÓA HOÀN TOÀN COPY & CUT -->',
            '    <command idMso="Copy" enabled="false"/>',
            '    <command idMso="Cut" enabled="false"/>',
        ])
        context_menus.extend([
            '    <contextMenu idMso="ContextMenuText">',
            '      <button idMso="Copy" visible="false"/>',
            '      <button idMso="Cut" visible="false"/>',
            '    </contextMenu>',
            '    <contextMenu idMso="ContextMenuShape">',
            '      <button idMso="Copy" visible="false"/>',
            '      <button idMso="Cut" visible="false"/>',
            '    </contextMenu>',
            '    <contextMenu idMso="ContextMenuThumbnail">',
            '      <button idMso="Copy" visible="false"/>',
            '      <button idMso="SlideDuplicate" visible="false"/>',
            '    </contextMenu>',
        ])

    if block_save_as:
        commands.extend([
            '    <!-- VÔ HIỆU HÓA HOÀN TOÀN CÁC LỆNH SAVE AS & EXPORT -->',
            '    <command idMso="FileSaveAs" enabled="false"/>',
            '    <command idMso="FileSaveAsMenu" enabled="false"/>',
            '    <command idMso="SaveAs" enabled="false"/>',
            '    <command idMso="ExportMenu" enabled="false"/>',
            '    <command idMso="FileSaveACopy" enabled="false"/>',
            '    <command idMso="FileSaveAsPdfOrXps" enabled="false"/>',
            '    <command idMso="FileExport" enabled="false"/>',
            '    <command idMso="FileExportAsPdf" enabled="false"/>',
        ])
        backstage_tabs.extend([
            '    <!-- ẨN HOÀN TOÀN CÔNG CỤ SAVE AS & EXPORT TRONG MENU FILE (BACKSTAGE) -->',
            '    <tab idMso="TabSave" visible="false"/>',
            '    <button idMso="FileSaveAs" visible="false"/>',
            '    <tab idMso="TabPublish" visible="false"/>',
            '    <tab idMso="TabShare" visible="false"/>',
            '    <tab idMso="TabExport" visible="false"/>',
            '    <button idMso="ShareDocument" visible="false"/>',
        ])

    if block_print:
        commands.extend([
            '    <!-- VÔ HIỆU HÓA PRINT -->',
            '    <command idMso="FilePrint" enabled="false"/>',
            '    <command idMso="FilePrintQuick" enabled="false"/>',
            '    <command idMso="FilePrintMenu" enabled="false"/>',
        ])
        backstage_tabs.extend([
            '    <tab idMso="TabPrint" visible="false"/>',
        ])

    commands_str = "\n".join(commands)
    backstage_str = f"  <backstage>\n" + "\n".join(backstage_tabs) + "\n  </backstage>" if backstage_tabs else ""
    context_str = f"  <contextMenus>\n" + "\n".join(context_menus) + "\n  </contextMenus>" if context_menus else ""

    parts = [f"  <commands>\n{commands_str}\n  </commands>"]
    if backstage_str:
        parts.append(backstage_str)
    if context_str:
        parts.append(context_str)

    body = "\n".join(parts)
    return f"""<customUI xmlns="http://schemas.microsoft.com/office/2009/07/customui">
{body}
</customUI>"""


def generate_ribbon_xml_07(block_save_as: bool = True, block_copy: bool = True, block_print: bool = True) -> str:
    """Tạo Ribbon XML tương thích Office 2007/2008 legacy"""
    commands = []
    if block_copy:
        commands.extend([
            '    <command idMso="Copy" enabled="false"/>',
            '    <command idMso="Cut" enabled="false"/>',
        ])
    if block_save_as:
        commands.extend([
            '    <command idMso="FileSaveAs" enabled="false"/>',
            '    <command idMso="FileSaveAsMenu" enabled="false"/>',
            '    <command idMso="SaveAs" enabled="false"/>',
            '    <command idMso="ExportMenu" enabled="false"/>',
            '    <command idMso="FileSaveACopy" enabled="false"/>',
        ])
    if block_print:
        commands.extend([
            '    <command idMso="FilePrint" enabled="false"/>',
            '    <command idMso="FilePrintQuick" enabled="false"/>',
            '    <command idMso="FilePrintMenu" enabled="false"/>',
        ])

    commands_str = "\n".join(commands)
    return f"""<customUI xmlns="http://schemas.microsoft.com/office/2006/01/customui">
  <commands>
{commands_str}
  </commands>
</customUI>"""


def clean_mac_incompatibilities(filename: str, content: bytes) -> bytes:
    """
    Loại bỏ các thành phần XML gây lỗi font trên macOS:
    Khi tạo bài thuyết trình trên Windows, font hệ thống Windows nhúng vào file
    gây ra hộp thoại cảnh báo 'Embedded Font Restricted' trên Mac.
    Hàm này làm sạch phần này giúp mở trên MacBook mượt mà 100%.
    """
    try:
        if filename == "ppt/presentation.xml":
            text = content.decode("utf-8", errors="ignore")
            text = re.sub(r'<p:embeddedFontLst>.*?</p:embeddedFontLst>', '', text, flags=re.DOTALL)
            text = re.sub(r'<p:embeddedFontLst\b[^>]*/>', '', text)
            return text.encode("utf-8")
        elif filename == "ppt/_rels/presentation.xml.rels":
            text = content.decode("utf-8", errors="ignore")
            text = re.sub(r'<Relationship[^>]*relationships/font[^>]*/>', '', text)
            return text.encode("utf-8")
    except Exception:
        pass
    return content


def inject_ribbon_policy(
    source_pptx_bytes: bytes,
    block_save_as: bool = True,
    block_copy: bool = True,
    block_print: bool = True,
    clean_fonts_for_mac: bool = True
) -> bytes:
    """
    Tiêm chính sách bảo mật Fluent UI Ribbon XML vào cấu trúc file PowerPoint OpenXML (.pptx/.pptm)
    Bảo đảm:
    - Vô hiệu hóa Save As, Save a Copy, Export, Print
    - Vô hiệu hóa Copy/Cut
    - Giữ nguyên FileSave (Ctrl+S / Cmd+S), Paste (Ctrl+V / Cmd+V) và Chỉnh sửa nội dung
    """
    if not (block_save_as or block_copy or block_print):
        return source_pptx_bytes

    xml14 = generate_ribbon_xml_14(block_save_as, block_copy, block_print)
    xml07 = generate_ribbon_xml_07(block_save_as, block_copy, block_print)

    input_buffer = io.BytesIO(source_pptx_bytes)
    output_buffer = io.BytesIO()

    try:
        with zipfile.ZipFile(input_buffer, "r") as zin, zipfile.ZipFile(output_buffer, "w", zipfile.ZIP_DEFLATED) as zout:
            rels_updated = False

            for item in zin.infolist():
                # Bỏ qua các file customUI cũ để ghi đè bản mới
                if item.filename in ("customUI/customUI14.xml", "customUI/customUI.xml"):
                    continue

                # Bỏ qua font nhúng Windows nếu cần dọn dẹp cho Mac
                if clean_fonts_for_mac and item.filename.startswith("ppt/fonts/"):
                    continue

                content = zin.read(item.filename)

                if clean_fonts_for_mac:
                    content = clean_mac_incompatibilities(item.filename, content)

                if item.filename == "_rels/.rels":
                    try:
                        ET.register_namespace("", RELATIONSHIP_NS)
                        root = ET.fromstring(content)

                        has_rel14 = False
                        has_rel07 = False
                        for rel in root.findall(f"{{{RELATIONSHIP_NS}}}Relationship"):
                            if rel.get("Type") == CUSTOMUI14_REL_TYPE:
                                rel.set("Target", CUSTOMUI14_TARGET)
                                has_rel14 = True
                            elif rel.get("Type") == CUSTOMUI_REL_TYPE:
                                rel.set("Target", CUSTOMUI_TARGET)
                                has_rel07 = True

                        r_ids = []
                        for rel in root.findall(f"{{{RELATIONSHIP_NS}}}Relationship"):
                            rid = rel.get("Id", "")
                            if rid.startswith("rId"):
                                try:
                                    r_ids.append(int(rid[3:]))
                                except ValueError:
                                    pass
                        next_id = max(r_ids) + 1 if r_ids else 1

                        if not has_rel14:
                            new_rel = ET.SubElement(root, f"{{{RELATIONSHIP_NS}}}Relationship")
                            new_rel.set("Id", f"rIdCustomUI14_{next_id}")
                            new_rel.set("Type", CUSTOMUI14_REL_TYPE)
                            new_rel.set("Target", CUSTOMUI14_TARGET)
                            next_id += 1

                        if not has_rel07:
                            new_rel = ET.SubElement(root, f"{{{RELATIONSHIP_NS}}}Relationship")
                            new_rel.set("Id", f"rIdCustomUI07_{next_id}")
                            new_rel.set("Type", CUSTOMUI_REL_TYPE)
                            new_rel.set("Target", CUSTOMUI_TARGET)

                        content = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                        rels_updated = True
                    except Exception:
                        pass

                zout.writestr(item, content)

            if not rels_updated:
                root = ET.Element(f"{{{RELATIONSHIP_NS}}}Relationships")
                new_rel = ET.SubElement(root, f"{{{RELATIONSHIP_NS}}}Relationship")
                new_rel.set("Id", "rIdCustomUI14_1")
                new_rel.set("Type", CUSTOMUI14_REL_TYPE)
                new_rel.set("Target", CUSTOMUI14_TARGET)

                new_rel07 = ET.SubElement(root, f"{{{RELATIONSHIP_NS}}}Relationship")
                new_rel07.set("Id", "rIdCustomUI07_2")
                new_rel07.set("Type", CUSTOMUI_REL_TYPE)
                new_rel07.set("Target", CUSTOMUI_TARGET)

                content = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                zout.writestr("_rels/.rels", content)

            # Thêm các file customUI vào package
            zout.writestr(CUSTOMUI14_TARGET, xml14.encode("utf-8"))
            zout.writestr(CUSTOMUI_TARGET, xml07.encode("utf-8"))

        return output_buffer.getvalue()

    except Exception as e:
        print(f"[Ribbon Policy Error] Không thể tiêm Ribbon XML: {e}")
        return source_pptx_bytes
