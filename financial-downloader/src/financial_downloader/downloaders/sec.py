"""US Stock (SEC EDGAR) financial report downloader.

从美国 SEC EDGAR 数据库下载美股上市公司财报。
使用 sec-edgar-downloader 库，默认下载 HTML 格式（易读）。

下载的文件结构:
    sec-edgar-filings/{ticker}/{form}/{accession_number}/
        ├── full-submission.txt      (SGML 原始格式)
        └── primary-document.htm     (HTML 易读格式) ← 我们使用这个

最终重命名为统一格式:
    downloads/{code}_{name}_{year}_{type}.htm
"""

import time
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Optional
import os
import shutil

from loguru import logger

from .base import BaseDownloader, DownloadResult


# ── 常量 ──────────────────────────────────────────────

DEFAULT_SEC_USER_AGENT = "Test Company test@example.com"

DOC_TYPE_CONFIGS = {
    "20-F": {"name": "20-F 年报", "description": "外国发行人年报"},
    "10-K": {"name": "10-K 年报", "description": "美国公司年报"},
    "10-Q": {"name": "10-Q 季报", "description": "季度报告"},
    "8-K": {"name": "8-K 重大事件", "description": "重大事件公告"},
}

DOC_TYPE_SUFFIX = {
    "20-F": "20F",
    "10-K": "10K",
    "10-Q": "10Q",
    "8-K": "8K",
}


# ── SEC 下载器 ──────────────────────────────────────────


class SecDownloader(BaseDownloader):
    """美股公告下载器 - 从 SEC EDGAR 下载。"""

    market = "us"
    SUPPORTED_TYPES = list(DOC_TYPE_CONFIGS.keys())

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        sec_user_agent: Optional[str] = None,
    ):
        """初始化下载器。"""
        super().__init__(output_dir)
        
        if sec_user_agent is None:
            sec_user_agent = DEFAULT_SEC_USER_AGENT
        
        self.sec_user_agent = sec_user_agent
        self._downloader = None

    @property
    def downloader(self):
        """懒加载 sec-edgar-downloader。"""
        if self._downloader is None:
            try:
                from sec_edgar_downloader import Downloader
                
                parts = self.sec_user_agent.split()
                if len(parts) >= 2:
                    company_name = parts[0]
                    email = parts[-1]
                else:
                    company_name = "TestCompany"
                    email = "test@example.com"
                
                self._downloader = Downloader(
                    company_name=company_name,
                    email_address=email,
                    download_folder=str(self.output_dir),
                )
            except ImportError:
                raise ImportError(
                    "sec-edgar-downloader 未安装，请运行：uv add sec-edgar-downloader"
                )
        
        return self._downloader

    def _get_default_output_dir(self) -> Path:
        """获取默认输出目录。"""
        return Path.home() / "workspace" / "acorn-mono" / "downloads"

    def get_supported_types(self) -> list[str]:
        """返回支持的文档类型。"""
        return self.SUPPORTED_TYPES

    def validate_code(self, code: str) -> bool:
        """验证美股代码格式。"""
        if not code or not code.strip():
            return False

        code = code.strip().upper()
        
        import re
        if not re.match(r'^[A-Z][A-Z0-9-]{0,4}$', code):
            return False

        if len(code) < 2:
            return False

        return True

    def validate_cik(self, cik: str) -> bool:
        """验证 CIK 格式。"""
        if not cik or not cik.strip():
            return False

        cik = cik.strip()
        
        import re
        if not re.match(r'^\d{6,10}$', cik):
            return False

        return True

    def get_supported_forms(self) -> list[str]:
        """返回支持的 SEC 表单类型。"""
        try:
            return self.downloader.supported_forms
        except Exception:
            return list(DOC_TYPE_CONFIGS.keys())

    def download(
        self,
        code: str,
        name: str,
        years: int = 10,
        year: Optional[int] = None,
        doc_type: str = "20-F",
        dry_run: bool = False,
        skip_existing: bool = True,
    ) -> DownloadResult:
        """
        下载美股公告（默认下载 HTML 格式）。

        Args:
            code: 股票代码或 CIK（如 TCOM 或 0001269238）
            name: 公司名（用于文件名）
            years: 下载最近多少年
            year: 指定具体年份
            doc_type: 文档类型（20-F, 10-K, 10-Q, 8-K）
            dry_run: 是否仅列出链接
            skip_existing: 是否跳过已下载文件

        Returns:
            DownloadResult 结果对象
        """
        result = DownloadResult(success=False)

        is_cik = code.strip().isdigit()
        if is_cik:
            if not self.validate_cik(code):
                result.add_error(f"无效的 CIK：{code}")
                return result
        else:
            if not self.validate_code(code):
                result.add_error(f"无效的股票代码：{code}")
                return result

        if doc_type not in self.SUPPORTED_TYPES:
            result.add_error(f"不支持的文档类型：{doc_type}")
            return result

        try:
            from datetime import date
            
            if year:
                after_date = date(year, 1, 1)
                before_date = date(year, 12, 31)
            else:
                before_date = date.today()
                after_date = before_date - timedelta(days=365 * years)

            logger.info(f"正在下载 {code} 的{DOC_TYPE_CONFIGS.get(doc_type, {}).get('name', doc_type)}...")

            if dry_run:
                logger.info(f"干跑模式：验证 {code} 的{doc_type}下载")
                result.metadata["count"] = 0
                result.metadata["dry_run"] = True
                result.success = True
                return result

            # 下载 HTML 格式（固定 download_details=True）
            count = self.downloader.get(
                form=doc_type,
                ticker_or_cik=code,
                after=after_date.isoformat(),
                before=before_date.isoformat(),
                download_details=True,  # 固定下载 HTML 格式
            )

            # 处理下载的文件
            base_dir = self.output_dir / "sec-edgar-filings" / code / doc_type
            
            if not base_dir.exists():
                result.metadata["count"] = count
                result.success = True
                return result

            # 遍历所有 accession directories
            downloaded = 0
            failed = 0
            skipped = 0

            for accession_dir in base_dir.iterdir():
                if not accession_dir.is_dir():
                    continue

                # 找到 HTML 文件
                html_file = None
                for f in accession_dir.iterdir():
                    if f.suffix.lower() in ['.htm', '.html']:
                        html_file = f
                        break

                if not html_file:
                    logger.warning(f"未找到 HTML 文件：{accession_dir}")
                    failed += 1
                    continue

                # 从 accession number 提取年份（格式：YYYYMMDD-...）
                accession_num = accession_dir.name
                try:
                    # accession number 格式：0001193125-25-078429
                    # 第二部分 (25) 是年份的后两位
                    year_part = accession_num.split('-')[1][:2]
                    filing_year = 2000 + int(year_part)
                    # SEC 文件通常在次年提交，所以财报年份 = filing_year - 1
                    doc_year = filing_year - 1
                except (ValueError, IndexError):
                    doc_year = datetime.now().year

                # 生成统一文件名（保留原始扩展名，不带点）
                # 美股 20-F/10-K 都是年报，统一用 "annual"
                ext = html_file.suffix.lstrip('.')
                filename = self.generate_filename(code, name, doc_year, "annual", extension=ext)
                save_path = self.output_dir / filename

                # 检查是否已存在
                if skip_existing and save_path.exists():
                    logger.info(f"跳过已下载：{filename}")
                    skipped += 1
                    result.add_file(save_path)
                    continue

                # 复制并重命名
                try:
                    shutil.copy2(html_file, save_path)
                    result.add_file(save_path)
                    downloaded += 1
                    logger.debug(f"下载成功：{save_path}")
                except Exception as e:
                    logger.error(f"复制失败 {html_file}: {e}")
                    failed += 1

            # 清理临时目录
            try:
                shutil.rmtree(base_dir.parent.parent)  # 删除 sec-edgar-filings/{code}
            except Exception as e:
                logger.warning(f"清理临时目录失败：{e}")

            result.metadata["count"] = count
            result.metadata["downloaded"] = downloaded
            result.metadata["failed"] = failed
            result.metadata["skipped"] = skipped
            result.success = failed == 0

            logger.info(f"下载完成：成功 {downloaded}, 失败 {failed}, 跳过 {skipped}")

        except Exception as e:
            logger.exception(f"下载过程出错：{e}")
            result.add_error(str(e))

        return result
    def download_20f(
        self,
        code: str,
        name: str,
        years: int = 10,
        dry_run: bool = False,
    ) -> DownloadResult:
        """下载 20-F 年报（外国发行人）。"""
        return self.download(
            code=code,
            name=name,
            years=years,
            doc_type="20-F",
            dry_run=dry_run,
        )

    def download_10k(
        self,
        code: str,
        name: str,
        years: int = 10,
        dry_run: bool = False,
    ) -> DownloadResult:
        """下载 10-K 年报（美国公司）。"""
        return self.download(
            code=code,
            name=name,
            years=years,
            doc_type="10-K",
            dry_run=dry_run,
        )
