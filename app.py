import os
import re
import tempfile

from flask import Flask, render_template, request, send_file, make_response, jsonify
import markdown  # 用于预览时把 markdown 转为 HTML
import pypandoc  # 用于导出 docx/pdf

# 需要安装的依赖：
# pip install pygments pymdown-extensions

try:
    from weasyprint import HTML

    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False

app = Flask(__name__)


@app.route("/")
def index():
    """
    展示首页
    """
    return render_template("index.html")


@app.route("/preview", methods=["POST"])
def preview():
    """
    将用户输入的Markdown先预处理，再转为HTML。
    """
    md_text = request.form.get("markdown_input", "")

    # 保证 \[...\] 公式的前后有空行
    md_text = re.sub(r"([^\n])(\s*)\\\[(.*?)\\\]([^\n])", r"\1\n\n\\[\3\\]\n\n\4", md_text, flags=re.DOTALL)
    md_text = re.sub(r"^(\s*)\\\[(.*?)\\\](\s*)(?=\n|$)", r"\n\\[\2\\]\n", md_text, flags=re.MULTILINE | re.DOTALL)

    # Markdown 转 HTML
    html = markdown.markdown(
        md_text,
        extensions=["fenced_code", "codehilite", "tables", "nl2br", "pymdownx.arithmatex"],
        extension_configs={
            "codehilite": {
                "linenums": False,
                "guess_lang": False,
            },
            "pymdownx.arithmatex": {"generic": True, "preview": False},
        },
    )

    return html


@app.route("/export", methods=["POST"])
def export():
    """
    导出文件为 docx 或 pdf。
    """
    md_text = request.form.get("markdown_input", "")
    export_type = request.args.get("type", "docx")

    # 替换 \[1mm] => \vspace{1mm}
    md_text = re.sub(r"\\\[1mm\]", r"\\vspace{1mm}", md_text)

    # 同样为 \[...\] 公式加空行
    md_text = re.sub(r"([^\n])(\s*)\\\[(.*?)\\\]([^\n])", r"\1\n\n\\[\3\\]\n\n\4", md_text, flags=re.DOTALL)
    md_text = re.sub(r"^(\s*)\\\[(.*?)\\\](\s*)(?=\n|$)", r"\n\\[\2\\]\n", md_text, flags=re.MULTILINE | re.DOTALL)

    # 保留原始LaTeX公式，不做额外处理
    cleaned_md = re.sub(r'<span class="arithmatex">(.*?)</span>', r"\1", md_text)
    # 将行级公式由 \( \) => $ $
    cleaned_md = re.sub(r"\\\(", r"$", cleaned_md)
    cleaned_md = re.sub(r"\\\)", r"$", cleaned_md)
    # 将块级公式 \[ \] => $$ $$
    cleaned_md = re.sub(r"\\\[", r"$$", cleaned_md)
    cleaned_md = re.sub(r"\\\]", r"$$", cleaned_md)

    # 处理 $ formula $ => $formula$ (去除$与公式之间的空格)
    # 使用负向断言避免匹配 $$ 块级公式
    cleaned_md = re.sub(r"(?<!\$)\$ +(.+?) +\$(?!\$)", r"$\1$", cleaned_md)

    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f_in:
        f_in.write(cleaned_md.encode("utf-8"))
        md_path = f_in.name

    output_file = md_path + "." + export_type

    # 增加 +raw_tex+tex_math_double_backslash
    # 移除 --mathml，减少对LaTeX命令的干扰
    # Explicitly define input format with extensions
    input_format = "markdown+raw_tex+tex_math_dollars+tex_math_double_backslash"

    extra_args_for_pdf = [
        "--pdf-engine=xelatex",
        "-V",
        "mainfont=Noto Sans CJK SC",
        "--highlight-style=pygments",
    ]
    extra_args_for_docx = [
        "--highlight-style=pygments",
        "--reference-doc=reference.docx",
    ]

    try:
        if export_type == "docx":
            pypandoc.convert_file(md_path, "docx", format=input_format, outputfile=output_file, extra_args=extra_args_for_docx)
            resp = make_response(send_file(output_file, as_attachment=True, download_name="output.docx"))
            resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        elif export_type == "pdf":
            pypandoc.convert_file(md_path, "pdf", format=input_format, outputfile=output_file, extra_args=extra_args_for_pdf)
            resp = make_response(send_file(output_file, as_attachment=True, download_name="output.pdf"))
            resp.headers["Content-Type"] = "application/pdf"

        else:
            os.remove(md_path)
            return "未知的导出类型", 400

    except Exception as e:
        os.remove(md_path)
        if os.path.exists(output_file):
            os.remove(output_file)
        return jsonify({"error": str(e)}), 500

    os.remove(md_path)
    return resp


if __name__ == "__main__":
    app.run(debug=True, port=8055)
