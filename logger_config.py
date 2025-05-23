import logging
from pathlib import Path
from datetime import datetime
import os


class LoggerConfig:
    @staticmethod
    def setup_logger(logger_name: str, log_dir: str = 'logs') -> logging.Logger:
        """设置日志记录器

        Args:
            logger_name: 日志记录器名称
            log_dir: 日志文件存储目录

        Returns:
            logging.Logger: 配置好的日志记录器
        """
        # 创建日志目录
        log_dir = Path(log_dir)
        log_dir.mkdir(exist_ok=True, parents=True)

        # 生成日志文件名，格式：logger_name_YYYYMMDD.log
        log_file = log_dir / f"{logger_name}_{datetime.now():%Y%m%d}.log"

        # 获取或创建日志记录器
        logger = logging.getLogger(logger_name)
        if logger.hasHandlers():
            return logger

        logger.setLevel(logging.DEBUG)

        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 设置日志格式
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    @staticmethod
    def handle_error(logger: logging.Logger, error_type: str, error_msg: str, exception: Exception = None) -> str:
        """统一的错误处理方法
        Args:
            logger: 日志记录器
            error_type: 错误类型
            error_msg: 错误信息
            exception: 异常对象（可选）
        Returns:
            str: 格式化的错误信息
        """
        error_detail = f"{error_type}: {error_msg}"
        if exception:
            error_detail += f" - {str(exception)}"

        logger.error(error_detail)
        return error_detail

    @staticmethod
    def cleanup_old_logs(log_dir: str, days_to_keep: int = 7):
        """清理旧的日志文件

        Args:
            log_dir: 日志文件目录
            days_to_keep: 保留的天数
        """
        log_dir = Path(log_dir)
        if not log_dir.exists():
            return

        current_time = datetime.now().timestamp()
        for log_file in log_dir.glob('*.log'):
            file_age = current_time - os.path.getmtime(log_file)
            if file_age > days_to_keep * 24 * 3600:
                try:
                    log_file.unlink()
                except Exception as e:
                    print(f"清理日志文件失败: {log_file} - {e}")