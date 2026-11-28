"""
Module: ribbon_policy_mac.py
Microsoft Office Fluent UI Ribbon Policy Injector - Tối ưu cho macOS & Cross-Platform
Vô hiệu hóa triệt để SAVE AS, COPY, DUPLICATE và EXPORT trong PowerPoint trên MacBook (Microsoft PowerPoint for Mac):
1. CHO PHÉP CHỈNH SỬA & LƯU BÀI GIẢNG (IN-PLACE SAVE):
   - FileSave (Cmd+S trên Mac, nút Lưu): HOÀN TOÀN ĐƯỢC PHÉP ĐỂ ĐỒNG BỘ VÀO FILE MÃ HÓA
   - Text Editing, Shape, Animation, Slide Insert/Delete: HOÀN TOÀN ĐƯỢC PHÉP
   - Paste (Cmd+V): HOÀN TOÀN ĐƯỢC PHÉP
2. CẤM TUYỆT ĐỐI SAVE AS (KHÔNG THỂ LƯU RA FILE MỚI TRÊN MAC):
   - Khóa toàn bộ các lệnh idMso: FileSaveAs, FileSaveCopyAs, FileSaveACopy, SaveACopy, SaveACopyOnline,
     SaveAs, SaveAsMenu, FileSaveAsMenu, ExportMenu, FileExport, FileExportAsPdf, DuplicatePresentation,
     FileDuplicate, SaveAsTemplate, FileSaveAsTemplate, PublishSlides, ShareDocument...
   - Ẩn hoàn toàn trên thanh công cụ Quick Access Toolbar (QAT) qua <qat><documentControls>
   - Ẩn hoàn toàn trong Menu File (Backstage) qua <backstage>
3. CẤM TUYỆT ĐỐI COPY & CUT:
   - Khóa Copy, Cut, SlideDuplicate trên thanh công cụ Ribbon và Context Menu chuột phải
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
    """Tạo Ribbon XML toàn diện cho Office 2010-365 và Office for Mac (macOS)"""
    commands = []
    backstage_tabs = []
    context_menus = []
    qat_controls = []

    if block_copy:
        commands.extend([
            '    <!-- VÔ HIỆU HÓA HOÀN TOÀN COPY, CUT & DUPLICATE -->',
            '    <command idMso="Copy" enabled="false"/>',
            '    <command idMso="Cut" enabled="false"/>',
            '    <command idMso="SlideDuplicate" enabled="false"/>',
            '    <command idMso="DuplicatePresentation" enabled="false"/>',
            '    <command idMso="FileDuplicate" enabled="false"/>',
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
            '      <button idMso="Cut" visible="false"/>',
            '      <button idMso="SlideDuplicate" visible="false"/>',
            '    </contextMenu>',
            '    <contextMenu idMso="ContextMenuFrame">',
            '      <button idMso="Copy" visible="false"/>',
            '      <button idMso="Cut" visible="false"/>',
            '    </contextMenu>',
        ])

    if block_save_as:
        commands.extend([
            '    <!-- VÔ HIỆU HÓA TOÀN BỘ CÁC LỆNH SAVE AS, SAVE A COPY, DUPLICATE & EXPORT -->',
            '    <command idMso="FileSaveAs" enabled="false"/>',
            '    <command idMso="FileSaveCopyAs" enabled="false"/>',
            '    <command idMso="FileSaveACopy" enabled="false"/>',
            '    <command idMso="SaveACopy" enabled="false"/>',
            '    <command idMso="SaveACopyOnline" enabled="false"/>',
            '    <command idMso="SaveAs" enabled="false"/>',
            '    <command idMso="SaveAsMenu" enabled="false"/>',
            '    <command idMso="FileSaveAsMenu" enabled="false"/>',
            '    <command idMso="FileSaveAsWord" enabled="false"/>',
            '    <command idMso="FileSaveAsPdfOrXps" enabled="false"/>',
            '    <command idMso="FileExport" enabled="false"/>',
            '    <command idMso="FileExportAsPdf" enabled="false"/>',
            '    <command idMso="ExportMenu" enabled="false"/>',
            '    <command idMso="PublishSlides" enabled="false"/>',
            '    <command idMso="PublishToDoc" enabled="false"/>',
            '    <command idMso="DuplicatePresentation" enabled="false"/>',
            '    <command idMso="FileDuplicate" enabled="false"/>',
            '    <command idMso="SaveAsPicture" enabled="false"/>',
            '    <command idMso="SaveAsTemplate" enabled="false"/>',
            '    <command idMso="FileSaveAsTemplate" enabled="false"/>',
            '    <command idMso="SaveObjectAs" enabled="false"/>',
            '    <command idMso="SaveSlideAsImage" enabled="false"/>',
            '    <command idMso="FileSendAsAttachment" enabled="false"/>',
            '    <command idMso="FileEmailAsPdfAttachment" enabled="false"/>',
            '    <command idMso="FileEmailAsXpsAttachment" enabled="false"/>',
            '    <command idMso="FileShare" enabled="false"/>',
            '    <command idMso="ShareDocument" enabled="false"/>',
            '    <command idMso="FilePackageForCD" enabled="false"/>',
            '    <command idMso="FileSaveToWeb" enabled="false"/>',
            '    <command idMso="SaveToSkyDrive" enabled="false"/>',
            '    <command idMso="SaveToCloud" enabled="false"/>',
            '    <command idMso="SaveToSharePoint" enabled="false"/>',
            '    <command idMso="AutoSave" enabled="false"/>',
        ])
        backstage_tabs.extend([
            '    <!-- ẨN HOÀN TOÀN CÔNG CỤ SAVE AS & EXPORT TRONG MENU FILE (BACKSTAGE) -->',
            '    <tab idMso="TabSave" visible="false"/>',
            '    <tab idMso="TabSaveACopy" visible="false"/>',
            '    <button idMso="FileSaveAs" visible="false"/>',
            '    <button idMso="FileSaveCopyAs" visible="false"/>',
            '    <button idMso="SaveACopy" visible="false"/>',
            '    <button idMso="FileSaveACopy" visible="false"/>',
            '    <button idMso="FileExport" visible="false"/>',
            '    <button idMso="FileSendAsAttachment" visible="false"/>',
            '    <tab idMso="TabPublish" visible="false"/>',
            '    <tab idMso="TabShare" visible="false"/>',
            '    <tab idMso="TabExport" visible="false"/>',
            '    <button idMso="ShareDocument" visible="false"/>',
        ])
        qat_controls.extend([
            '        <!-- ẨN HOÀN TOÀN CÁC NÚT SAVE AS, SAVE A COPY & EXPORT TRÊN THANH CÔNG CỤ (QAT) -->',
            '        <control idMso="FileSaveAs" visible="false"/>',
            '        <control idMso="FileSaveCopyAs" visible="false"/>',
            '        <control idMso="FileSaveACopy" visible="false"/>',
            '        <control idMso="SaveACopy" visible="false"/>',
            '        <control idMso="SaveACopyOnline" visible="false"/>',
            '        <control idMso="SaveAs" visible="false"/>',
            '        <control idMso="FileSaveAsMenu" visible="false"/>',
            '        <control idMso="ExportMenu" visible="false"/>',
            '        <control idMso="FileExport" visible="false"/>',
            '        <control idMso="FileExportAsPdf" visible="false"/>',
            '        <control idMso="PublishSlides" visible="false"/>',
            '        <control idMso="DuplicatePresentation" visible="false"/>',
            '        <control idMso="FileDuplicate" visible="false"/>',
            '        <control idMso="SaveAsTemplate" visible="false"/>',
            '        <control idMso="FileSaveAsTemplate" visible="false"/>',
            '        <control idMso="AutoSave" visible="false"/>',
            '        <control idMso="FileShare" visible="false"/>',
            '        <control idMso="ShareDocument" visible="false"/>',
            '        <control idMso="FileSendAsAttachment" visible="false"/>',
        ])

    if block_print:
        commands.extend([
            '    <!-- VÔ HIỆU HÓA PRINT -->',
            '    <command idMso="FilePrint" enabled="false"/>',
            '    <command idMso="FilePrintQuick" enabled="false"/>',
            '    <command idMso="FilePrintMenu" enabled="false"/>',
            '    <command idMso="PrintPreviewAndPrint" enabled="false"/>',
        ])
        backstage_tabs.extend([
            '    <tab idMso="TabPrint" visible="false"/>',
        ])
        qat_controls.extend([
            '        <control idMso="FilePrint" visible="false"/>',
            '        <control idMso="FilePrintQuick" visible="false"/>',
        ])

    commands_str = "\n".join(commands)
    backstage_str = f"  <backstage>\n" + "\n".join(backstage_tabs) + "\n  </backstage>" if backstage_tabs else ""
    context_str = f"  <contextMenus>\n" + "\n".join(context_menus) + "\n  </contextMenus>" if context_menus else ""
    
    qat_str = ""
    if qat_controls:
        qat_body = "\n".join(qat_controls)
        qat_str = f"  <ribbon startFromScratch=\"false\">\n    <qat>\n      <documentControls>\n{qat_body}\n      </documentControls>\n    </qat>\n  </ribbon>"

    parts = [f"  <commands>\n{commands_str}\n  </commands>"]
    if qat_str:
        parts.append(qat_str)
    if backstage_str:
        parts.append(backstage_str)
    if context_str:
        parts.append(context_str)

    body = "\n".join(parts)
    return f"""<customUI xmlns="http://schemas.microsoft.com/office/2009/07/customui">
{body}
</customUI>"""


def generate_ribbon_xml_07(block_save_as: bool = True, block_copy: bool = True, block_print: bool = True) -> str:
    """Tạo Ribbon XML cho Office 2007 và chuẩn tương thích cũ"""
    commands = []
    qat_controls = []

    if block_copy:
        commands.extend([
            '    <command idMso="Copy" enabled="false"/>',
            '    <command idMso="Cut" enabled="false"/>',
            '    <command idMso="SlideDuplicate" enabled="false"/>',
        ])

    if block_save_as:
        commands.extend([
            '    <command idMso="FileSaveAs" enabled="false"/>',
            '    <command idMso="FileSaveCopyAs" enabled="false"/>',
            '    <command idMso="FileSaveACopy" enabled="false"/>',
            '    <command idMso="SaveACopy" enabled="false"/>',
            '    <command idMso="SaveACopyOnline" enabled="false"/>',
            '    <command idMso="SaveAs" enabled="false"/>',
            '    <command idMso="SaveAsMenu" enabled="false"/>',
            '    <command idMso="FileSaveAsMenu" enabled="false"/>',
            '    <command idMso="ExportMenu" enabled="false"/>',
            '    <command idMso="FileExport" enabled="false"/>',
            '    <command idMso="DuplicatePresentation" enabled="false"/>',
            '    <command idMso="FileDuplicate" enabled="false"/>',
            '    <command idMso="SaveAsTemplate" enabled="false"/>',
            '    <command idMso="FileSaveAsTemplate" enabled="false"/>',
            '    <command idMso="FileShare" enabled="false"/>',
            '    <command idMso="ShareDocument" enabled="false"/>',
            '    <command idMso="FileSendAsAttachment" enabled="false"/>',
            '    <command idMso="AutoSave" enabled="false"/>',
        ])
        qat_controls.extend([
            '        <control idMso="FileSaveAs" visible="false"/>',
            '        <control idMso="FileSaveCopyAs" visible="false"/>',
            '        <control idMso="SaveACopy" visible="false"/>',
            '        <control idMso="ExportMenu" visible="false"/>',
            '        <control idMso="FileExport" visible="false"/>',
            '        <control idMso="DuplicatePresentation" visible="false"/>',
        ])

    if block_print:
        commands.extend([
            '    <command idMso="FilePrint" enabled="false"/>',
            '    <command idMso="FilePrintQuick" enabled="false"/>',
            '    <command idMso="FilePrintMenu" enabled="false"/>',
        ])
        qat_controls.extend([
            '        <control idMso="FilePrint" visible="false"/>',
        ])

    commands_str = "\n".join(commands)
    qat_str = ""
    if qat_controls:
        qat_body = "\n".join(qat_controls)
        qat_str = f"  <ribbon startFromScratch=\"false\">\n    <qat>\n      <documentControls>\n{qat_body}\n      </documentControls>\n    </qat>\n  </ribbon>"

    parts = [f"  <commands>\n{commands_str}\n  </commands>"]
    if qat_str:
        parts.append(qat_str)

    body = "\n".join(parts)
    return f"""<customUI xmlns="http://schemas.microsoft.com/office/2006/01/customui">
{body}
</customUI>"""


def clean_mac_incompatibilities(filename: str, content: bytes) -> bytes:
    """Làm sạch các thuộc tính Windows không tương thích trên PowerPoint for Mac"""
    if filename.endswith(".xml") or filename.endswith(".rels"):
        try:
            text = content.decode("utf-8")
            # 1. Loại bỏ thẻ embeddedFontLst gây thông báo lỗi font nhúng trên Mac
            if "<p:embeddedFontLst" in text:
                text = re.sub(r"<p:embeddedFontLst.*?</p:embeddedFontLst>", "", text, flags=re.DOTALL)
            elif "<embeddedFontLst" in text:
                text = re.sub(r"<embeddedFontLst.*?</embeddedFontLst>", "", text, flags=re.DOTALL)
            return text.encode("utf-8")
        except Exception:
            return content
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
    - Xóa bỏ và vô hiệu hóa triệt để Save As, Save a Copy, Export, Duplicate trên cả Ribbon, QAT và Backstage
    - Vô hiệu hóa Copy/Cut trên Ribbon và Context Menu
    - Giữ nguyên FileSave (Cmd+S / Ctrl+S), Paste (Cmd+V / Ctrl+V) và Chỉnh sửa nội dung
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
