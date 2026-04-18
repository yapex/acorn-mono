"""HKEX (Hong Kong) financial report downloader.

从港交所披露易 (HKEXnews) 下载港股上市公司年报。
"""

import json
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseDownloader, DownloadResult

# ── 常量 ──────────────────────────────────────────────

HKEX_BASE_URL = "https://www1.hkexnews.hk"
HKEX_PREFIX_URL = f"{HKEX_BASE_URL}/search/prefix.do"
HKEX_SEARCH_URL = f"{HKEX_BASE_URL}/search/titlesearch.xhtml"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": HKEX_BASE_URL,
    "Referer": f"{HKEX_BASE_URL}/search/titlesearch.xhtml?lang=zh",
}

# 文档类型配置
DOC_TYPE_CONFIGS = {
    "annual": {
        "name": "年报",
        "keywords": ["年報", "年报", "Annual Report"],
        "exclude": ["ESG", "環境", "社會", "Sustainability", "中期", "中期報告"],
        "t1code": "40000",
    },
    "esg": {
        "name": "ESG 报告",
        "keywords": ["ESG", "環境", "社會", "Sustainability", "環境、社會"],
        "exclude": [],
        "t1code": "40000",
    },
    "financial": {
        "name": "财务报表",
        "keywords": ["業績", "业绩", "財務", "财务", "Financial"],
        "exclude": ["年報", "Annual Report"],
        "t1code": "40000",
    },
}

# 文档类型后缀映射
DOC_TYPE_SUFFIX = {
    "annual": "an",
    "esg": "esg",
    "financial": "fs",
    "circular": "ci",
    "prospectus": "ip",
}


# ── 港股下载器 ──────────────────────────────────────────


class HkexDownloader(BaseDownloader):
    """港股公告下载器 - 从港交所披露易下载。"""

    market = "hk"
    SUPPORTED_TYPES = list(DOC_TYPE_CONFIGS.keys()) + ["all"]

    def __init__(self, output_dir: Optional[Path] = None):
        """初始化下载器。"""
        super().__init__(output_dir)
        self.client = httpx.Client(headers=HEADERS, timeout=30.0, follow_redirects=True)

    def _get_default_output_dir(self) -> Path:
        """获取默认输出目录。"""
        return Path.home() / "workspace" / "acorn-mono" / "downloads"

    def get_supported_types(self) -> list[str]:
        """返回支持的文档类型。"""
        return self.SUPPORTED_TYPES

    def validate_code(self, code: str) -> bool:
        """验证港股代码格式。"""
        if not code or not code.strip():
            return False

        code = code.strip()
        if not code.isdigit():
            return False

        if len(code) not in [4, 5]:
            return False

        code_num = int(code)
        return 1 <= code_num <= 99999

    def get_stock_id(self, stock_code: str, market: str = "SEHK", lang: str = "ZH") -> str:
        """将股票代码转换为 HKEX 的 stockId。"""
        url = (
            f"{HKEX_PREFIX_URL}?callback=callback&lang={lang.upper()}"
            f"&type=A&name={stock_code}&market={market}"
        )

        response = self.client.get(url)
        response.raise_for_status()

        match = re.search(r"\((.+)\)", response.text)
        if not match:
            raise ValueError("无法解析 stockId 响应")

        data = json.loads(match.group(1))
        stock_info = data.get("stockInfo", [])

        if not stock_info:
            raise ValueError(f"找不到股票代码 {stock_code}")

        return str(stock_info[0]["stockId"])

    def search_documents(
        self,
        stock_code: str,
        stock_id: str,
        t1code: str = "",
        from_date: str = "",
        to_date: str = "",
        lang: str = "ZH",
        market: str = "SEHK",
    ) -> list[dict]:
        """搜索指定股票的文档列表。"""
        if not to_date:
            to_date = date.today().strftime("%Y%m%d")
        if not from_date:
            from_date = date.today().replace(year=date.today().year - 20).strftime("%Y%m%d")

        data = {
            "lang": lang.upper(),
            "category": "0",
            "market": market,
            "searchType": "0",
            "documentType": "",
            "t1code": t1code,
            "t2Gcode": "",
            "t2code": "",
            "stockId": stock_id,
            "from": from_date,
            "to": to_date,
            "MB-Daterange": "0",
        }

        response = self.client.post(HKEX_SEARCH_URL, data=data)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        if not table:
            return []

        documents = []
        rows = table.find_all("tr")

        for row in rows:
            cols = row.find_all(["th", "td"])
            if len(cols) < 3:
                continue

            link_tag = row.find("a", href=True)
            if not link_tag:
                doc_link_div = row.find("div", class_="doc-link")
                if doc_link_div:
                    link_tag = doc_link_div.find("a", href=True)

            if not link_tag:
                continue

            href = link_tag.get("href", "")
            if not href:
                continue

            if href.startswith("http"):
                pdf_url = href
            elif href.startswith("/"):
                pdf_url = f"{HKEX_BASE_URL}{href}"
            else:
                pdf_url = urljoin(response.url, href)

            date_text = ""
            row_text = row.get_text()
            date_match = re.search(r"(\d{2}/\d{2}/\d{4})", row_text)
            if date_match:
                date_text = date_match.group(1)

            title = link_tag.get_text(strip=True)
            if not title:
                title = cols[-1].get_text(strip=True) if cols else ""

            documents.append({
                "title": title,
                "date": date_text,
                "href": pdf_url,
                "stock_code": stock_code,
            })

        return documents

    def filter_annual_reports(
        self,
        documents: list[dict],
        years: int = 10,
        target_year: Optional[int] = None,
    ) -> list[dict]:
        """筛选年报。"""
        current_year = datetime.now().year
        start_year = target_year if target_year else (current_year - years)

        filtered = []

        for doc in documents:
            title = doc["title"]

            if any(kw in title for kw in ["ESG", "環境", "社會", "Sustainability", "可持續"]):
                continue

            if not any(kw in title for kw in ["年報", "年报", "年度報告", "年度报告", "Annual Report"]):
                continue

            doc_year = None
            date_str = doc.get("date", "")
            if date_str:
                try:
                    doc_date = datetime.strptime(date_str, "%d/%m/%Y")
                    doc_year = doc_date.year
                except ValueError:
                    pass

            if doc_year:
                if target_year:
                    if doc_year != target_year:
                        continue
                elif doc_year < start_year:
                    continue

            filtered.append(doc)

        filtered.sort(key=lambda x: self._extract_year_from_doc(x), reverse=True)
        return filtered

    def _extract_year_from_doc(self, doc: dict) -> int:
        """从文档信息中提取财报年份。"""
        title = doc.get("title", "")

        import re
        match = re.search(r"(20\d{2})", title)
        if match:
            year = int(match.group(1))
            current_year = datetime.now().year
            if year < current_year:
                return year

        return 0

    def filter_documents_by_type(
        self,
        documents: list[dict],
        doc_type: str,
        years: int = 10,
        target_year: Optional[int] = None,
    ) -> list[dict]:
        """根据文档类型筛选。"""
        if doc_type == "annual":
            return self.filter_annual_reports(documents, years, target_year)

        config = DOC_TYPE_CONFIGS.get(doc_type, {})
        keywords = config.get("keywords", [])
        exclude = config.get("exclude", [])

        filtered = []
        for doc in documents:
            title = doc["title"]

            if any(kw in title for kw in exclude):
                continue

            if keywords and not any(kw in title for kw in keywords):
                continue

            filtered.append(doc)

        return filtered

    def download_pdf(self, pdf_url: str, save_path: Path) -> bool:
        """下载 PDF 文件。"""
        try:
            response = self.client.get(pdf_url)
            response.raise_for_status()

            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(response.content)

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
        """下载港股公告。"""
        result = DownloadResult(success=False)

        if not self.validate_code(code):
            result.add_error(f"无效的港股代码：{code}")
            return result

        if doc_type not in self.SUPPORTED_TYPES:
            result.add_error(f"不支持的文档类型：{doc_type}")
            return result

        try:
            logger.info(f"正在获取 {code} 的 stockId...")
            stock_id = self.get_stock_id(code)

            t1code = DOC_TYPE_CONFIGS.get(doc_type, {}).get("t1code", "")

            logger.info(f"正在搜索 {code} 的文档...")
            documents = self.search_documents(
                stock_code=code,
                stock_id=stock_id,
                t1code=t1code,
            )

            if not documents:
                logger.warning("未找到符合条件的文档")
                result.metadata["count"] = 0
                result.success = True
                return result

            filtered_docs = self.filter_documents_by_type(
                documents, doc_type, years, year
            )

            if not filtered_docs:
                logger.warning("筛选后未找到文档")
                result.metadata["count"] = 0
                result.success = True
                return result

            result.metadata["count"] = len(filtered_docs)
            result.metadata["documents"] = filtered_docs

            if dry_run:
                logger.info(f"找到 {len(filtered_docs)} 份文档（仅列出，未下载）")
                result.success = True
                return result

            logger.info(f"开始下载到：{self.output_dir}")
            downloaded = 0
            failed = 0
            skipped = 0

            for doc in filtered_docs:
                doc_year = self._extract_year_from_doc(doc)
                if not doc_year:
                    doc_year = datetime.now().year

                filename = self.generate_filename(code, name, doc_year, doc_type)
                save_path = self.output_dir / filename

                if skip_existing and save_path.exists():
                    logger.info(f"跳过已下载：{filename}")
                    skipped += 1
                    result.add_file(save_path)
                    continue

                if self.download_pdf(doc["href"], save_path):
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
