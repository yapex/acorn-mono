#!/usr/bin/env python3
"""
CNINFO 公告下载工具

从巨潮资讯网下载 A 股上市公司公告，包括：
- 年度报告
- 招股说明书
- 上市公告书
- 债券募集说明书

Usage:
    cninfo <stock_code> [options]

Examples:
    # 下载年报
    cninfo 600519
    cninfo 600519 --type annual --years 10
    
    # 下载招股书
    cninfo 600519 --type ipo
    
    # 下载所有可用文档
    cninfo 300750 --type all
"""

from scrapling import Fetcher  # type: ignore[import-untyped]
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal
import os

try:
    from ..config import get_default_download_dir
except ImportError:
    from config import get_default_download_dir

# 创建 scrapling fetcher 实例
fetcher = Fetcher()


# 公告类型定义
AnnouncementType = Literal['annual', 'ipo', 'listing', 'bond', 'all']

# 公告类型配置
ANNOUNCEMENT_CONFIGS = {
    'annual': {
        'name': '年度报告',
        'search_key': '年度报告',
        'exclude': ['半年度', '摘要', '英文', '补充'],
        'include': ['年度报告'],
        'years': True,  # 支持年份筛选
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


def get_org_id(stock_code: str) -> str:
    """根据股票代码生成 orgId"""
    code = stock_code.strip()
    
    if code.startswith(('600', '601', '603', '605')):
        return f'gssh0{code}'
    elif code.startswith(('000', '001', '002', '003')):
        return f'gssz0{code}'
    elif code.startswith('8'):
        return f'gsbj{code}'
    elif code.startswith(('300', '301')):
        return get_chi_next_org_id(code)
    else:
        raise ValueError(f"无法识别的股票代码格式：{code}")


def get_plate(stock_code: str) -> str:
    """根据股票代码判断市场板块"""
    code = stock_code.strip()
    if code.startswith(('600', '601', '603', '605')):
        return 'sh'
    else:
        return 'sz'


def get_column(stock_code: str) -> str:
    """获取 column 参数"""
    plate = get_plate(stock_code)
    return 'sse' if plate == 'sh' else 'szse'


def fetch_announcements(stock_code: str, org_id: str, page_num: int = 1, 
                       page_size: int = 30, search_key: str = '') -> dict:
    """获取公告列表"""
    url = 'https://www.cninfo.com.cn/new/hisAnnouncement/query'
    
    data = {
        'stock': f'{stock_code},{org_id}',
        'tabName': 'fulltext',
        'pageSize': page_size,
        'pageNum': page_num,
        'column': get_column(stock_code),
        'category': '',
        'plate': get_plate(stock_code),
        'seDate': '',
        'searchkey': search_key,
        'secid': '',
        'sortName': 'announcementTime',
        'sortType': 'desc',
        'isHLtitle': 'true'
    }
    
    headers = {
        'Referer': f'https://www.cninfo.com.cn/new/disclosure/stock?stockCode={stock_code}&orgId={org_id}',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    # 使用 scrapling 发送请求
    response = fetcher.post(url, data=data, headers=headers, timeout=30)
    
    return response.json()


def get_chi_next_org_id(stock_code: str) -> str:
    """获取创业板的 orgId"""
    import re
    
    # 尝试 1: 使用 scrapling 发送 HTTP 请求
    url = f'https://www.cninfo.com.cn/new/disclosure/stock?stockCode={stock_code}'
    
    try:
        response = fetcher.get(url, timeout=10)
        html = response.text
        match = re.search(r'orgId[=:]\s*["\']?([a-zA-Z0-9]+)["\']?', html)
        if match:
            org_id = match.group(1)
            if org_id.startswith('GD'):
                return org_id
    except Exception:
        pass
    
    known_chi_next = {
        '300750': 'GD165627',  # 宁德时代
        '300059': 'GD165626',  # 东方财富
        '300124': 'GD165630',  # 汇川技术
    }
    
    if stock_code in known_chi_next:
        return known_chi_next[stock_code]
    
    raise ValueError(
        f"无法获取创业板 orgId，请手动提供。\n"
        f"访问 https://www.cninfo.com.cn/new/disclosure/stock?stockCode={stock_code}\n"
        f"从 URL 中复制 orgId 参数"
    )


def filter_announcement(title: str, config: dict) -> bool:
    """
    筛选公告
    
    Args:
        title: 公告标题
        config: 公告类型配置
        
    Returns:
        是否应该包含该公告
    """
    clean_title = title.replace('<em>', '').replace('</em>', '')
    
    # 检查排除关键字
    if any(x in clean_title for x in config['exclude']):
        return False
    
    # 检查必须包含关键字
    if not any(x in clean_title for x in config['include']):
        return False
    
    return True


def extract_year(title: str, current_year: int) -> Optional[int]:
    """从标题中提取年份"""
    clean_title = title.replace('<em>', '').replace('</em>', '')
    
    for y in range(2015, current_year + 1):
        if f'{y}年' in clean_title:
            return y
    
    return None


def fetch_documents(stock_code: str, doc_type: AnnouncementType, 
                   years: int = 10, target_year: Optional[int] = None) -> list[dict]:
    """
    获取指定类型的公告文档
    
    Args:
        stock_code: 股票代码
        doc_type: 文档类型 (annual/ipo/listing/bond)
        years: 年份范围（仅对年报有效）
        target_year: 指定具体年份（仅对年报有效，如 2024）
        
    Returns:
        文档列表
    """
    org_id = get_org_id(stock_code)
    current_year = datetime.now().year
    
    # 如果指定了具体年份，优先使用 target_year
    if target_year is not None:
        start_year = target_year
    else:
        start_year = current_year - years
    
    documents = []
    
    # 确定要获取的类型
    if doc_type == 'all':
        types_to_fetch = ['annual', 'ipo', 'listing', 'bond']
    else:
        types_to_fetch = [doc_type]
    
    for dtype in types_to_fetch:
        config = ANNOUNCEMENT_CONFIGS[dtype]
        page = 1
        max_pages = 10
        
        while page <= max_pages:
            result = fetch_announcements(stock_code, org_id, page_num=page, 
                                        page_size=30, search_key=config['search_key'])
            
            announcements = result.get('announcements', [])
            if not announcements:
                break
            
            for a in announcements:
                title = a['announcementTitle']
                
                # 筛选公告
                if not filter_announcement(title, config):
                    continue
                
                # 对于年报，检查年份
                report_year = None
                if config['years']:
                    report_year = extract_year(title, current_year)
                    if not report_year:
                        continue
                    # 如果指定了具体年份，只保留该年份的年报
                    if target_year is not None:
                        if report_year != target_year:
                            continue
                    elif report_year < start_year:
                        continue
                
                # 构建文档信息
                adjunct_url = a['adjunctUrl']
                pdf_url = f"https://static.cninfo.com.cn/{adjunct_url}"
                
                doc = {
                    'type': dtype,
                    'type_name': config['name'],
                    'title': title.replace('<em>', '').replace('</em>', ''),
                    'date': datetime.fromtimestamp(a['announcementTime'] / 1000).strftime('%Y-%m-%d'),
                    'pdf_url': pdf_url,
                }
                
                if report_year:
                    doc['year'] = report_year
                
                documents.append(doc)
            
            if not result.get('hasMore', False):
                break
            
            page += 1
    
    # 排序：年报按年份，其他按日期
    if doc_type in ['annual', 'all']:
        # 年报按年份去重并排序
        if doc_type == 'annual':
            seen_years = set()
            unique_docs = []
            for d in documents:
                if d.get('year') not in seen_years:
                    seen_years.add(d['year'])
                    unique_docs.append(d)
            documents = unique_docs
        documents.sort(key=lambda x: x.get('year', 0), reverse=True)
    else:
        # 其他类型按日期排序
        documents.sort(key=lambda x: x['date'], reverse=True)
    
    return documents


def generate_filename(stock_code: str, company_name: str, year: Optional[int], 
                     doc_type: str) -> str:
    """
    生成文件名（参考港股财报命名格式）
    
    格式：{股票代码}_{公司名}_{年份}_{文档类型}.pdf
    示例：000001_平安银行_2024_an.pdf
    """
    type_code = ANNOUNCEMENT_CONFIGS.get(doc_type, {}).get('code', doc_type)
    year_str = f"_{year}" if year else ""
    
    # 清理公司名中的特殊字符
    safe_name = company_name.replace('/', '_').replace('\\', '_')
    safe_name = safe_name.replace(' ', '').replace('"', '').replace("'", '')
    
    return f"{stock_code}_{safe_name}{year_str}_{type_code}.pdf"


def download_pdf(url: str, save_path: Path) -> bool:
    """下载 PDF 文件"""
    try:
        headers = {
            'Referer': 'https://www.cninfo.com.cn/',
        }
        
        # 使用 scrapling 下载 PDF
        response = fetcher.get(url, headers=headers, timeout=120)
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'wb') as f:
            f.write(response.body)
        
        return True
    except Exception as e:
        print(f"下载失败：{e}")
        return False


def download_documents(stock_code: str, company_name: str,
                      output_dir: Optional[str] = None,
                      doc_type: AnnouncementType = 'annual',
                      years: int = 10, dry_run: bool = False,
                      target_year: Optional[int] = None,
                      skip_existing: bool = True) -> list[dict]:
    """
    下载指定股票的文档
    
    Args:
        stock_code: 股票代码（必需）
        company_name: 公司名（必需，用于生成文件名）
        output_dir: 输出目录，None 则使用默认目录
        doc_type: 文档类型
        years: 年份范围
        dry_run: 仅获取链接不下载
        target_year: 指定具体年份（如 2024）
        skip_existing: 是否跳过已存在的文件
        
    Returns:
        文档列表，包含下载结果
    """
    # 使用默认下载目录
    if output_dir is None:
        output_dir = get_default_download_dir()
    
    type_name = ANNOUNCEMENT_CONFIGS.get(doc_type, {}).get('name', '文档')
    print(f"正在获取 {stock_code} 的{type_name}...")
    
    documents = fetch_documents(stock_code, doc_type, years, target_year)
    
    if not documents:
        print("未找到符合条件的文档")
        return []
    
    print(f"找到 {len(documents)} 份文档:\n")
    
    if dry_run or output_dir is None:
        # 仅显示链接
        for doc in documents:
            year_str = f"{doc.get('year', '')}年 " if doc.get('year') else ""
            print(f"{year_str}| {doc['date']}")
            print(f"  [{doc['type_name']}] {doc['title']}")
            print(f"  {doc['pdf_url']}")
            print()
        return documents
    
    # 下载文件
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"开始下载到：{output_path.absolute()}\n")
    
    for doc in documents:
        year = doc.get('year')
        filename = generate_filename(stock_code, company_name, year, doc_type)
        save_path = output_path / filename
        
        # 检查文件是否已存在
        if skip_existing and save_path.exists():
            size_mb = save_path.stat().st_size / 1024 / 1024
            print(f"跳过 {doc['type_name']} ({year}年)... 已存在 ({size_mb:.1f}MB)")
            doc['downloaded'] = True
            doc['save_path'] = str(save_path)
            continue
        
        print(f"下载 {doc['type_name']} ({year}年)...", end=" ")
        
        if download_pdf(doc['pdf_url'], save_path):
            size_mb = save_path.stat().st_size / 1024 / 1024
            print(f"OK ({size_mb:.1f}MB)")
            doc['downloaded'] = True
            doc['save_path'] = str(save_path)
        else:
            print("FAILED")
            doc['downloaded'] = False
            doc['save_path'] = None
    
    downloaded = sum(1 for d in documents if d.get('downloaded'))
    print(f"\n完成！共下载 {downloaded}/{len(documents)} 份文件")
    
    return documents


# 注意：命令行接口已迁移到 skills.cninfo_downloader.cli
# 本文件现在作为纯库使用
