import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
log_dir = os.path.join(BASE_DIR, "logs")

os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "talentflow.log") # 将日志名改为 talentflow.log

# 自定义 logger
logger = logging.getLogger("talentflow") # 修改 logger 名称
logger.setLevel(logging.INFO)

# 防止重复添加 handler
if not logger.handlers:
    # 格式化器：时间 - 记录器名称 - 级别 - [文件名:行号] - 信息
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # 文件输出：最大 10MB，保留 5 个备份
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)