#!/usr/bin/env python3
"""
批量创建客户 - 智能匹配Excel列头，自动处理各种格式
"""
import json
import sys
import os
import urllib.request
import urllib.parse
import ssl
import re
import xml.etree.ElementTree as ET
from auth import get_token, refresh_token  # 使用认证模块

API_HOST = "https://api.wojiacloud.cn"
PID = "319c23c4c60e4def9959c776c32ca7f9"

# 字段映射配置 - 多种可能的列名
FIELD_MAPPING = {
    'name': ['客户名称', 'name', '姓名', '客户', '企业名称', '公司名称', '联系人'],
    'phone': ['手机号', 'phone', '电话', 'mobile', '联系方式', '手机', '联系电话'],
    'type': ['客户类型', 'type', '类型', '客户性质'],
    'certType': ['证件类型', 'certType', '证件', '证书类型'],
    'certNo': ['证件号码', 'certNo', '证件号', '证号', '身份证号'],
    'sex': ['性别', 'sex'],
    'nation': ['民族', 'nation', '族'],
    'birthday': ['生日', 'birthday', '出生日期', '出生年月'],
    'email': ['邮箱', 'email', '电子邮件', 'mail'],
    'description': ['客户描述', 'description', '描述', '备注'],
    'category': ['客户性质', 'category'],
    'authCode': ['财务编码', 'authCode', '编码', '客户编码'],
    'province': ['省份', 'province', '省'],
    'city': ['城市', 'city', '市'],
    'area': ['区域', 'area', '区', '县'],
    'address': ['地址', 'address', '详细地址', '住址', '联系地址'],
    'residenceAddress': ['户籍地址', 'residenceAddress'],
    'brand': ['品牌', 'brand'],
    'taxpayerType': ['纳税人类型', 'taxpayerType', '纳税类型'],
    'custMakeOutName': ['开票名称', 'custMakeOutName', '开票抬头', '发票抬头'],
    'specInvCountryTaxCode': ['纳税人识别码', 'specInvCountryTaxCode', '税号'],
    'businessAddress': ['税务地址', 'businessAddress'],
    'businessPhone': ['税务电话', 'businessPhone'],
    'bankName': ['开户行', 'bankName'],
    'bankCount': ['银行账号', 'bankCount', '账号'],
    'billingType': ['开票类型', 'billingType', '发票类型'],
}

# 值转换映射
VALUE_MAPPING = {
    'type': {
        '个人': 'P', '个人客户': 'P', 'P': 'P', '自然人': 'P',
        '企业': 'E', '企业客户': 'E', '公司': 'E', 'E': 'E', '单位': 'E',
        '政府': 'G', '政府机构': 'G', 'G': 'G', '机关': 'G',
        '个体户': 'S', '个体': 'S', 'S': 'S',
        '其他': 'O', 'O': 'O',
        '临时': 'T', 'T': 'T', '租户': 'T'
    },
    'certType': {
        '大陆身份证': '0101', '身份证': '0101', '0101': '0101',
        '军官证': '0102', '0102': '0102',
        '港澳台': '0103', '0103': '0103',
        '护照': '0104', '0104': '0104',
        '台胞证': '0111', '0111': '0111',
        '香港身份证': '0112', '0112': '0112',
        '营业执照': '0105', '0105': '0105',
        '税务登记号': '0106', '0106': '0106',
        '组织机构代码': '0107', '0107': '0107',
        '社会信用代码': '0108', '社会信用号码': '0108', '0108': '0108',
        '其他': '0199', '0199': '0199'
    },
    'sex': {
        '男': '0', '0': '0', '先生': '0',
        '女': '1', '1': '1', '女士': '1'
    },
    'category': {
        '无': '-1', '-1': '-1',
        '内部客户': '0', '内部': '0', '0': '0',
        '外部客户': '1', '外部': '1', '1': '1',
        '关联客户': '2', '关联': '2', '2': '2'
    },
    'taxpayerType': {
        '一般纳税人': '0', '一般': '0', '0': '0',
        '小规模纳税人': '1', '小规模': '1', '1': '1'
    }
}

def match_header(headers):
    """智能匹配列头"""
    mapping = {}
    for field, possible_names in FIELD_MAPPING.items():
        for header in headers:
            header_clean = header.strip().replace(' ', '')
            for name in possible_names:
                name_clean = name.strip().replace(' ', '')
                if header_clean == name_clean or name_clean in header_clean or header_clean in name_clean:
                    mapping[field] = header
                    break
            if field in mapping:
                break
    return mapping

def convert_value(field, value):
    """转换字段值"""
    if value is None or str(value).strip() == '':
        return None
    
    val = str(value).strip()
    
    # 处理数值类型
    if field in ['phone', 'certNo', 'bankCount']:
        try:
            if '.' in val:
                val = str(int(float(val)))
        except:
            pass
    
    # 枚举值映射
    if field in VALUE_MAPPING:
        return VALUE_MAPPING[field].get(val, val)
    
    # 生日格式转换 (2001.1.1 -> 2001-01-01)
    if field == 'birthday':
        try:
            val = val.replace('.', '-').replace('/', '-')
            parts = val.split('-')
            year = parts[0]
            month = parts[1].zfill(2) if len(parts) > 1 else '01'
            day = parts[2].zfill(2) if len(parts) > 2 else '01'
            return f"{year}-{month}-{day}"
        except:
            return None
    
    return val

def fix_customer(customer, index):
    """修复客户数据"""
    ctype = customer.get('type')
    
    # 企业客户必须用营业执照
    if ctype == 'E':
        customer['certType'] = '0105'
        if not customer.get('certNo') or len(str(customer.get('certNo',''))) < 10:
            customer['certNo'] = f'91440300MA{index:08d}'
    
    # 个人/个体户需要手机号
    if ctype in ['P', 'S'] and not customer.get('phone'):
        customer['phone'] = str(13000000000 + index)
    
    return customer

def read_excel_xml(file_path):
    """读取Excel (兼容没有pandas的情况)"""
    import zipfile
    import tempfile
    
    # 解压Excel
    with zipfile.ZipFile(file_path, 'r') as z:
        # 读取sharedStrings.xml
        try:
            strings_xml = z.read('xl/sharedStrings.xml').decode('utf-8')
        except KeyError:
            strings_xml = '<sst></sst>'
        
        # 读取sheet1
        try:
            sheet_xml = z.read('xl/worksheets/sheet1.xml').decode('utf-8')
        except KeyError:
            return [], {}
    
    # 解析sharedStrings
    root = ET.fromstring(strings_xml)
    ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    strings = []
    for si in root.findall('.//main:si', ns):
        t = si.find('.//main:t', ns)
        if t is not None and t.text:
            strings.append(t.text)
    
    # 解析sheet1
    cells = {}
    for match in re.finditer(r'<c r="([A-Z]+)(\d+)"[^>]*><v>(\d+)</v></c>', sheet_xml):
        col, row, val = match.groups()
        cells[f"{col}{row}"] = int(val)
    
    return cells, strings

def create_customer(customers_list):
    """批量创建客户"""
    # 获取token
    token = get_token()
    url = f"{API_HOST}/api/customers/sSave?access_token={token}"
    
    params = {
        "projectID": PID,
        "list": customers_list
    }
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(params).encode(),
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    
    result = json.loads(urllib.request.urlopen(req, context=ctx).read())
    return result

def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("批量创建客户工具 - 智能处理各种格式")
        print("=" * 60)
        print("")
        print("用法:")
        print("  python3 create_customers.py <excel或csv文件>")
        print("")
        print("自动处理:")
        print("  - 生日格式: 2001.1.1 → 2001-01-01")
        print("  - 企业客户自动使用营业执照")
        print("  - 个人客户缺少手机号自动生成")
        print("")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)
    
    print(f"读取文件: {file_path}")
    
    # 尝试用pandas，失败则用xml解析
    try:
        import pandas as pd
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.csv':
            df = pd.read_csv(file_path, encoding='utf-8')
        else:
            df = pd.read_excel(file_path)
        headers = df.columns.tolist()
        header_map = match_header(headers)
        
        print(f"表头识别: {list(header_map.keys())}")
        
        customers = []
        for _, row in df.iterrows():
            customer = {}
            for field, header in header_map.items():
                val = row.get(header)
                if pd.notna(val):
                    customer[field] = convert_value(field, val)
            
            if customer.get('name'):
                if 'type' not in customer:
                    customer['type'] = 'P'
                customers.append(customer)
        
    except ImportError:
        # 使用XML解析
        cells, strings = read_excel_xml(file_path)
        
        if not cells:
            print("❌ 无法读取Excel文件")
            sys.exit(1)
        
        # 获取列头
        header_map = {}
        for col in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            key = f'{col}1'
            if key in cells:
                idx = cells[key]
                if idx < len(strings):
                    header_name = strings[idx]
                    for field, names in FIELD_MAPPING.items():
                        if header_name in names:
                            header_map[field] = col
                            break
        
        print(f"列头映射: {header_map}")
        
        # 解析数据
        customers = []
        row = 2
        while True:
            if f'A{row}' not in cells:
                break
            
            customer = {}
            for field, col in header_map.items():
                key = f'{col}{row}'
                if key in cells:
                    idx = cells[key]
                    if idx < len(strings):
                        val = convert_value(field, strings[idx])
                        if val:
                            customer[field] = val
            
            if customer.get('name'):
                if 'type' not in customer:
                    customer['type'] = 'P'
                customers.append(customer)
            
            row += 1
    
    print(f"共解析 {len(customers)} 条数据")
    
    # 修复数据
    for i, c in enumerate(customers):
        customers[i] = fix_customer(c, i)
    
    print(f"准备导入 {len(customers)} 个客户...")
    
    # 分批创建
    batch_size = 50
    total = len(customers)
    success_count = 0
    
    for i in range(0, total, batch_size):
        batch = customers[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        
        print(f"导入第 {batch_num}/{total_batches} 批 ({len(batch)} 条)...")
        
        result = create_customer(batch)
        
        if result.get('success'):
            insert = int(result.get('data', {}).get('insertCount', 0))
            update = int(result.get('data', {}).get('updateCount', 0))
            success_count += insert + update
            print(f"  ✅ 新增 {insert}, 更新 {update}")
        else:
            print(f"  ❌ 失败: {result.get('msg', '未知错误')}")
    
    print("")
    print("=" * 50)
    print(f"✅ 完成! 成功: {success_count} 条")
    print("=" * 50)

if __name__ == "__main__":
    main()
