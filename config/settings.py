"""
从环境变量读取配置；支持 .env 文件（python-dotenv）。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# 数据库：postgresql://用户:密码@host:端口/数据库名
# 本机默认无密码示例：postgresql://当前系统用户名@localhost:5432/stock_agents
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/stock_agents")

# LLM / 搜索 API（按实际使用的服务后续补充）
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
