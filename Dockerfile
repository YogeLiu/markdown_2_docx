# 使用 Python 3.11 slim 作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production

# 复制 requirements.txt（提前复制以利用缓存）
COPY requirements.txt .

# 安装所有依赖（合并为一个 RUN 减少镜像层数）
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
    # Pandoc
    pandoc \
    # WeasyPrint 依赖
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    # XeLaTeX (PDF 导出)
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-lang-chinese \
    # 中文字体
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/* \
    # 安装 Python 依赖
    && pip install --no-cache-dir --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt \
    && pip install --no-cache-dir --index-url https://pypi.tuna.tsinghua.edu.cn/simple pymdown-extensions pygments gunicorn

# 复制应用文件
COPY app.py .
COPY convert_md_to_docx.py .
COPY pygments.theme .
COPY reference.docx .

# 暴露端口
EXPOSE 8055

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:8055", "--workers", "2", "--timeout", "120", "app:app"]
