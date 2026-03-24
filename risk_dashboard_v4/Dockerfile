# 基于官方 Python 3.11 slim 镜像
FROM python:3.11-slim-bookworm

# 设置工作目录
WORKDIR /app

# 用非交互模式安装 apt 包
ENV DEBIAN_FRONTEND=noninteractive

# 先安装系统级构建依赖、科学计算库依赖与 graphviz（如果你不需要 graphviz 可去掉）
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     gcc     g++     gfortran     libatlas-base-dev     libopenblas-dev     liblapack-dev     libblas-dev     libffi-dev     libssl-dev     libxml2-dev     libxslt1-dev     graphviz     ca-certificates     wget     curl     && rm -rf /var/lib/apt/lists/*

# 复制 requirements（注意文件名 requirements.txt）
COPY requirements.txt .

# 升级 pip 并安装 Python 依赖
RUN pip install --upgrade pip setuptools wheel     && pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app.py .

# 暴露 streamlit 默认端口
EXPOSE 8501

# 可选：设置环境变量以让 streamlit 输出更多日志（方便调试）
ENV STREAMLIT_SERVER_HEADLESS=true
ENV PYTHONUNBUFFERED=1

# 启动命令
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
