"""A-share (CNINFO) financial report downloader.

从巨潮资讯网下载 A 股上市公司公告。
参考现有 cninfo_downloader skill 实现。
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import httpx
from loguru import logger

from .base import BaseDownloader, DownloadResult

# ── 常量 ──────────────────────────────────────────────

CNINFO_BASE_URL = "https://www.cninfo.com.cn"
CNINFO_QUERY_URL = f"{CNINFO_BASE_URL}/new/hisAnnouncement/query"

# 创建 httpx 客户端
client = httpx.Client(timeout=30.0, follow_redirects=True)
client.headers.update({
    'Referer': CNINFO_BASE_URL,
    'X-Requested-With': 'XMLHttpRequest',
})

# 公告类型定义
AnnouncementType = Literal['annual', 'ipo', 'listing', 'bond', 'all']

# 公告类型配置
ANNOUNCEMENT_CONFIGS = {
    'annual': {
        'name': '年度报告',
        'search_key': '年度报告',
        'exclude': ['半年度', '摘要', '英文', '补充'],
        'include': ['年度报告'],
        'years': True,
        'code': 'an',
    },
    'ipo': {
        'name': '招股说明书',
        'search_key': '招股说明书',
        'exclude': ['摘要', '英文', '法律意见书'],
        'include': ['招股说明书'],
        'years': False,
        'code': 'ipo',
    },
    'listing': {
        'name': '上市公告书',
        'search_key': '上市公告书',
        'exclude': ['摘要', '英文'],
        'include': ['上市公告书'],
        'years': False,
        'code': 'listing',
    },
    'bond': {
        'name': '债券募集说明书',
        'search_key': '募集说明书',
        'exclude': ['摘要', '英文', '法律意见书'],
        'include': ['募集说明书'],
        'years': False,
        'code': 'bond',
    },
}

# 已知的创业板 orgId 映射
KNOWN_CHI_NEXT = {
    "300750": "GD165627",  # 宁德时代
    "300059": "GD165626",  # 东方财富
    "300124": "GD165630",  # 汇川技术
}


# ── A 股下载器 ──────────────────────────────────────────


class CninfoDownloader(BaseDownloader):
    """A 股公告下载器 - 从巨潮资讯网下载。"""

    market = "cn"
    SUPPORTED_TYPES = list(ANNOUNCEMENT_CONFIGS.keys()) + ["all"]

    def __init__(self, output_dir: Optional[Path] = None):
        """初始化下载器。"""
        super().__init__(output_dir)
        # 使用全局 fetcher 实例（参考现有 skill）

    def _get_default_output_dir(self) -> Path:
        """获取默认输出目录。"""
        # 默认到 acorn-mono/downloads
        return Path.home() / "workspace" / "acorn-mono" / "downloads"

    def get_supported_types(self) -> list[str]:
        """返回支持的文档类型。"""
        return self.SUPPORTED_TYPES

    def validate_code(self, code: str) -> bool:
        """验证 A 股股票代码格式。"""
        if not code or not code.strip():
            return False

        code = code.strip()
        if not code.isdigit() or len(code) != 6:
            return False

        valid_prefixes = ("600", "601", "603", "605", "000", "001", "002", "003", "300", "301", "8")
        return code.startswith(valid_prefixes)

    def get_org_id(self, stock_code: str) -> str:
        """根据股票代码生成 orgId。"""
        code = stock_code.strip()

        if code.startswith(("600", "601", "603", "605")):
            return f"gssh0{code}"
        elif code.startswith(("000", "001", "002", "003")):
            return f"gssz0{code}"
        elif code.startswith("8"):
            return f"gsbj{code}"
        elif code.startswith(("300", "301")):
            return self._get_chi_next_org_id(code)
        else:
            raise ValueError(f"无法识别的股票代码：{code}")

    def _get_chi_next_org_id(self, stock_code: str) -> str:
        """获取创业板 orgId。"""
        if stock_code in KNOWN_CHI_NEXT:
            return KNOWN_CHI_NEXT[stock_code]

        url = f"{CNINFO_BASE_URL}/new/disclosure/stock?stockCode={stock_code}"
        try:
            response = client.get(url, timeout=10)
            match = re.search(r'orgId[=:]\s*["\']?([a-zA-Z0-9]+)["\']?', response.text)
            if match:
                org_id = match.group(1)
                if org_id.startswith("GD"):
                    return org_id
        except Exception:
            pass

        raise ValueError(f"无法获取创业板 orgId: {stock_code}")

    def get_plate(self, stock_code: str) -> str:
        """获取市场板块（sh/sz）。"""
        if stock_code.strip().startswith(("600", "601", "603", "605")):
            return "sh"
        return "sz"

    def get_column(self, stock_code: str) -> str:
        """获取 column 参数（sse/szse）。"""
        return "sse" if self.get_plate(stock_code) == "sh" else "szse"

    def fetch_announcements(
        self,
        stock_code: str,
        org_id: str,
        page_num: int = 1,
        page_size: int = 30,
        search_key: str = "",
    ) -> list[dict]:
        """获取公告列表（参考现有 skill 实现）。"""
        data = {
            "stock": f"{stock_code},{org_id}",
            "tabName": "fulltext",
            "pageSize": page_size,
            "pageNum": page_num,
            "column": self.get_column(stock_code),
            "category": "",
            "plate": self.get_plate(stock_code),
            "seDate": "",
            "searchkey": search_key,
            "secid": "",
            "sortName": "announcementTime",
            "sortType": "desc",
            "isHLtitle": "true",
        }

        # 使用 httpx 发送请求
        response = client.post(CNINFO_QUERY_URL, data=data)
        result = response.json()
        return result.get("announcements", [])

    def filter_announcement(self, title: str, config: dict) -> bool:
        """筛选公告。"""
        clean_title = title.replace("<em>", "").replace("</em>", "")

        # 检查排除关键字
        if any(x in clean_title for x in config["exclude"]):
            return False

        # 检查必须包含关键字
        if not any(x in clean_title for x in config["include"]):
            return False

        # 额外排除：半年度
        if "半年度" in clean_title:
            return False

        return True

    def extract_year(self, title: str, current_year: int) -> Optional[int]:
        """从标题中提取年份（使用正则表达式）。"""
        clean_title = title.replace("<em>", "").replace("</em>", "")

        # 使用正则表达式匹配年份（如 2024 年）
        import re
        match = re.search(r'(20\d{2})\s*年', clean_title)
        if match:
            year = int(match.group(1))
            if 2015 <= year <= current_year:
                return year

        return None

    def fetch_documents(
        self,
        stock_code: str,
        doc_type: str,
        years: int = 10,
        target_year: Optional[int] = None,
    ) -> list[dict]:
        """获取指定类型的公告文档。"""
        org_id = self.get_org_id(stock_code)
        current_year = datetime.now().year

        if target_year is not None:
            start_year = target_year
        else:
            start_year = current_year - years

        documents = []

        if doc_type == "all":
            types_to_fetch = list(ANNOUNCEMENT_CONFIGS.keys())
        else:
            types_to_fetch = [doc_type]

        for dtype in types_to_fetch:
            config = ANNOUNCEMENT_CONFIGS[dtype]
            page = 1
            max_pages = 10

            while page <= max_pages:
                announcements = self.fetch_announcements(
                    stock_code, org_id, page_num=page, search_key=config["search_key"]
                )

                if not announcements:
                    break

                for a in announcements:
                    title = a["announcementTitle"]

                    if not self.filter_announcement(title, config):
                        continue

                    report_year = None
                    if config.get("years"):
                        report_year = self.extract_year(title, current_year)
                        if not report_year:
                            continue

                        if target_year is not None:
                            if report_year != target_year:
                                continue
                        elif report_year < start_year:
                            continue

                    adjunct_url = a["adjunctUrl"]
                    # 使用 static.cninfo.com.cn 而不是 www.cninfo.com.cn
                    pdf_url = f"https://static.cninfo.com.cn/{adjunct_url}"

                    doc = {
                        "type": dtype,
                        "type_name": config["name"],
                        "title": title.replace("<em>", "").replace("</em>", ""),
                        "date": datetime.fromtimestamp(a["announcementTime"] / 1000).strftime("%Y-%m-%d"),
                        "pdf_url": pdf_url,
                    }

                    if report_year:
                        doc["year"] = report_year

                    documents.append(doc)

                page += 1

        documents.sort(key=lambda x: x.get("year", 0), reverse=True)
        return documents

    def download_pdf(self, pdf_url: str, save_path: Path) -> bool:
        """下载 PDF 文件（参考现有 skill 实现）。"""
        try:
            # 使用 httpx 下载 PDF
            response = client.get(pdf_url)

            save_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            with open(save_path, 'wb') as f:
                f.write(response.content)

            logger.debug(f"下载成功：{save_path}")
            return True
        except Exception as e:
            logger.error(f"下载失败 {pdf_url}: {e}")
            return False

    def download(
        self,
        code: str,
        name: str,
        years: int = 10,
        year: Optional[int] = None,
        doc_type: str = "annual",
        dry_run: bool = False,
        skip_existing: bool = True,
    ) -> DownloadResult:
        """下载 A 股公告。"""
        result = DownloadResult(success=False)

        if not self.validate_code(code):
            result.add_error(f"无效的股票代码：{code}")
            return result

        if doc_type not in self.SUPPORTED_TYPES:
            result.add_error(f"不支持的文档类型：{doc_type}")
            return result

        try:
            logger.info(f"正在获取 {code} 的{ANNOUNCEMENT_CONFIGS.get(doc_type, {}).get('name', '文档')}...")
            documents = self.fetch_documents(code, doc_type, years, year)

            if not documents:
                logger.warning("未找到符合条件的文档")
                result.metadata["count"] = 0
                result.success = True
                return result

            result.metadata["count"] = len(documents)
            result.metadata["documents"] = documents

            if dry_run:
                logger.info(f"找到 {len(documents)} 份文档（仅列出，未下载）")
                result.success = True
                return result

            logger.info(f"开始下载到：{self.output_dir}")
            downloaded = 0
            failed = 0
            skipped = 0

            for doc in documents:
                doc_year = doc.get("year", datetime.now().year)
                filename = self.generate_filename(code, name, doc_year, doc_type)
                save_path = self.output_dir / filename

                # 检查是否已存在
                if skip_existing and save_path.exists():
                    logger.info(f"跳过已下载：{filename}")
                    skipped += 1
                    result.add_file(save_path)
                    continue

                if self.download_pdf(doc["pdf_url"], save_path):
                    result.add_file(save_path)
                    downloaded += 1
                else:
                    result.add_error(f"下载失败：{doc['title']}")
                    failed += 1

                time.sleep(0.5)

            result.metadata["downloaded"] = downloaded
            result.metadata["failed"] = failed
            result.metadata["skipped"] = skipped
            result.success = failed == 0

            logger.info(f"下载完成：成功 {downloaded}, 失败 {failed}, 跳过 {skipped}")

        except Exception as e:
            logger.exception(f"下载过程出错：{e}")
            result.add_error(str(e))

        return result
