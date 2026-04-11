"""
V33.0 发票服务集成测试
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import db
from business_common.invoice_service import InvoiceService, invoice_service


class TestInvoiceService:
    """发票服务测试"""

    def setup_method(self):
        """测试前准备"""
        self.service = InvoiceService()

    def test_service_health_check(self):
        """测试服务健康检查"""
        result = self.service.health_check()
        assert result is not None
        assert 'db_status' in result or 'service_name' in result

    def test_generate_invoice_no(self):
        """测试发票号生成"""
        invoice_no = self.service._generate_invoice_no()
        assert invoice_no is not None
        assert invoice_no.startswith('INV')
        assert len(invoice_no) == 24

    def test_title_types(self):
        """测试抬头类型配置"""
        assert 'personal' in self.service.TITLE_TYPES
        assert 'enterprise' in self.service.TITLE_TYPES
        assert self.service.TITLE_TYPES['personal'] == '个人'
        assert self.service.TITLE_TYPES['enterprise'] == '企业'

    def test_invoice_types(self):
        """测试发票类型配置"""
        assert 'electronic' in self.service.INVOICE_TYPES
        assert 'paper' in self.service.INVOICE_TYPES

    def test_invoice_status(self):
        """测试发票状态配置"""
        assert self.service.STATUS_PENDING == 'pending'
        assert self.service.STATUS_APPROVED == 'approved'
        assert self.service.STATUS_ISSUED == 'issued'
        assert self.service.STATUS_REJECTED == 'rejected'
        assert self.service.STATUS_CANCELLED == 'cancelled'

    def test_tax_rates(self):
        """测试税率配置"""
        assert 0.06 in self.service.TAX_RATES.values()
        assert 0.03 in self.service.TAX_RATES.values()
        assert self.service.DEFAULT_TAX_RATE == 0.06


class TestInvoiceTitleCRUD:
    """发票抬头CRUD测试"""

    def setup_method(self):
        """测试前准备"""
        self.service = InvoiceService()
        self.test_user_id = 'test_user_001'
        self.test_ec_id = 1
        self.test_project_id = 1

    def test_create_personal_title(self):
        """测试创建个人抬头"""
        result = self.service.create_title(
            user_id=self.test_user_id,
            title_type='personal',
            title_name='张三',
            ec_id=self.test_ec_id,
            project_id=self.test_project_id
        )
        assert result is not None
        if result.get('success'):
            assert 'title_id' in result

    def test_create_enterprise_title(self):
        """测试创建企业抬头"""
        result = self.service.create_title(
            user_id=self.test_user_id,
            title_type='enterprise',
            title_name='测试公司',
            tax_no='91310000MA1K12345X',
            bank_name='中国银行',
            bank_account='6217000800012345678',
            address='上海市浦东新区',
            phone='021-12345678',
            ec_id=self.test_ec_id,
            project_id=self.test_project_id
        )
        assert result is not None
        if result.get('success'):
            assert 'title_id' in result

    def test_create_enterprise_title_without_tax_no(self):
        """测试企业抬头缺少税号"""
        result = self.service.create_title(
            user_id=self.test_user_id,
            title_type='enterprise',
            title_name='测试公司'
        )
        assert result is not None
        assert result.get('success') == False
        assert '税号' in result.get('msg', '')

    def test_get_titles(self):
        """测试获取抬头列表"""
        result = self.service.get_titles(
            user_id=self.test_user_id,
            ec_id=self.test_ec_id
        )
        assert isinstance(result, list)

    def test_update_title(self):
        """测试更新抬头"""
        # 先创建
        create_result = self.service.create_title(
            user_id=self.test_user_id,
            title_type='personal',
            title_name='原名称',
            ec_id=self.test_ec_id
        )
        
        if create_result.get('success'):
            title_id = create_result['title_id']
            
            # 再更新
            update_result = self.service.update_title(
                title_id=title_id,
                user_id=self.test_user_id,
                title_name='新名称'
            )
            assert update_result is not None

    def test_delete_title(self):
        """测试删除抬头"""
        # 先创建
        create_result = self.service.create_title(
            user_id=self.test_user_id,
            title_type='personal',
            title_name='待删除抬头',
            ec_id=self.test_ec_id
        )
        
        if create_result.get('success'):
            title_id = create_result['title_id']
            
            # 再删除
            delete_result = self.service.delete_title(
                title_id=title_id,
                user_id=self.test_user_id
            )
            assert delete_result is not None
            assert delete_result.get('success') == True


class TestInvoiceApply:
    """发票申请测试"""

    def setup_method(self):
        """测试前准备"""
        self.service = InvoiceService()

    def test_apply_invoice_order_not_found(self):
        """测试订单不存在"""
        result = self.service.apply_invoice(
            user_id='nonexistent_user',
            order_id=999999,
            title_id=1
        )
        assert result is not None
        assert result.get('success') == False
        assert '不存在' in result.get('msg', '')

    def test_apply_invoice_title_not_found(self):
        """测试抬头不存在"""
        result = self.service.apply_invoice(
            user_id='test_user',
            order_id=1,
            title_id=999999
        )
        assert result is not None
        assert result.get('success') == False

    def test_get_invoices_pagination(self):
        """测试发票列表分页"""
        result = self.service.get_invoices(
            page=1,
            page_size=10
        )
        assert 'items' in result
        assert 'total' in result
        assert 'page' in result
        assert 'page_size' in result

    def test_get_invoices_with_filters(self):
        """测试带筛选条件的发票列表"""
        result = self.service.get_invoices(
            user_id='test_user',
            status='pending',
            page=1,
            page_size=10
        )
        assert 'items' in result


class TestInvoiceManagement:
    """发票管理测试"""

    def setup_method(self):
        """测试前准备"""
        self.service = InvoiceService()

    def test_approve_invoice_not_found(self):
        """测试审核不存在的发票"""
        result = self.service.approve_invoice(
            invoice_id=999999,
            admin_name='admin'
        )
        assert result is not None
        assert result.get('success') == False

    def test_reject_invoice_not_found(self):
        """测试驳回不存在的发票"""
        result = self.service.reject_invoice(
            invoice_id=999999,
            reason='测试驳回',
            admin_name='admin'
        )
        assert result is not None
        assert result.get('success') == False

    def test_issue_invoice_not_found(self):
        """测试开具不存在的发票"""
        result = self.service.issue_invoice(
            invoice_id=999999,
            admin_name='admin'
        )
        assert result is not None
        assert result.get('success') == False

    def test_cancel_invoice_not_found(self):
        """测试作废不存在的发票"""
        result = self.service.cancel_invoice(
            invoice_id=999999,
            reason='测试作废',
            admin_name='admin'
        )
        assert result is not None
        assert result.get('success') == False


class TestInvoiceStatistics:
    """发票统计测试"""

    def setup_method(self):
        """测试前准备"""
        self.service = InvoiceService()

    def test_get_statistics(self):
        """测试发票统计"""
        result = self.service.get_statistics()
        assert result is not None
        assert 'total_count' in result
        assert 'total_amount' in result
        assert 'by_status' in result

    def test_get_statistics_with_filters(self):
        """测试带筛选的发票统计"""
        result = self.service.get_statistics(
            ec_id=1,
            project_id=1,
            date_from='2026-01-01',
            date_to='2026-12-31'
        )
        assert result is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
