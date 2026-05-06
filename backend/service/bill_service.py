# service/bill_service.py - 费用管理业务
from typing import Dict
from decimal import Decimal
from sqlalchemy.orm import Session
from service.base_service import BaseService
from db.models import Bill, Payment
from utils.md5_fid_util import generate_fid
from utils.log_util import logger
from utils.time_util import now_str


class BillService(BaseService):
    """费用管理服务"""

    def list_bills(self, fec_id: str, fproject_id: str,
                   btype: str = "", status: str = "",
                   enterprise_id: str = "", keyword: str = "",
                   page: int = 1, page_size: int = 20) -> Dict:
        try:
            q = Bill.active_query(self.db).filter(
                Bill.fec_id == fec_id, Bill.fproject_id == fproject_id
            )
            if btype:
                q = q.filter(Bill.type == btype)
            if status:
                q = q.filter(Bill.status == status)
            if enterprise_id:
                q = q.filter(Bill.enterprise_id == enterprise_id)
            if keyword:
                q = q.filter(
                    Bill.bill_no.like(f"%{keyword}%") |
                    Bill.resident_name.like(f"%{keyword}%") |
                    Bill.room_number.like(f"%{keyword}%")
                )
            total = q.count()
            items = q.order_by(Bill.create_time.desc()) \
                .offset((page - 1) * page_size).limit(page_size).all()
            return self.success({
                "total": total, "page": page, "page_size": page_size,
                "items": [self._to_dict(b) for b in items]
            })
        except Exception as e:
            logger.error(f"查询账单列表失败：{str(e)}", exc_info=True)
            return self.error(f"查询账单列表失败：{str(e)}")

    def create_bill(self, fec_id: str, fproject_id: str, **kwargs) -> Dict:
        try:
            self.begin()
            fid = generate_fid()
            bill_no = f"B{now_str().replace('-','').replace(':','').replace(' ','')[:12]}"
            bill = Bill(fid=fid, fec_id=fec_id, fproject_id=fproject_id,
                        bill_no=bill_no, **kwargs)
            self.db.add(bill)
            self.commit()
            self.db.refresh(bill)
            return self.success(self._to_dict(bill), "创建账单成功")
        except Exception as e:
            self.rollback()
            return self.error(f"创建账单失败：{str(e)}")

    def record_payment(self, fec_id: str, fproject_id: str,
                       bill_id: str, amount: Decimal, method: str = "微信支付",
                       payer_name: str = "", transaction_no: str = "",
                       remark: str = "") -> Dict:
        """记录缴费"""
        try:
            self.begin()
            bill = Bill.active_query(self.db).filter(
                Bill.fid == bill_id, Bill.fec_id == fec_id,
                Bill.fproject_id == fproject_id
            ).first()
            if not bill:
                return self.error("账单不存在", 404)

            # 创建缴费记录
            fid = generate_fid()
            payment = Payment(
                fid=fid, fec_id=fec_id, fproject_id=fproject_id,
                bill_id=bill_id, bill_no=bill.bill_no,
                enterprise_id=bill.enterprise_id,
                room_number=bill.room_number,
                payer_name=payer_name or bill.resident_name,
                amount=amount, method=method,
                transaction_no=transaction_no,
                paid_at=now_str(), remark=remark
            )
            self.db.add(payment)

            # 更新账单状态
            new_paid = (bill.paid_amount or Decimal("0")) + amount
            bill.paid_amount = new_paid
            if new_paid >= bill.amount:
                bill.status = "已缴"
                bill.paid_at = now_str()
            else:
                bill.status = "部分缴"
            self.commit()
            return self.success({"bill_id": bill_id, "paid": float(new_paid), "bill_status": bill.status}, "缴费成功")
        except Exception as e:
            self.rollback()
            return self.error(f"缴费失败：{str(e)}")

    @staticmethod
    def _to_dict(b: Bill) -> dict:
        return {
            "fid": b.fid, "bill_no": b.bill_no,
            "enterprise_id": b.enterprise_id, "building_id": b.building_id,
            "room_number": b.room_number, "resident_name": b.resident_name,
            "type": b.type, "period": b.period,
            "amount": float(b.amount) if b.amount else 0,
            "paid_amount": float(b.paid_amount) if b.paid_amount else 0,
            "status": b.status, "due_date": b.due_date,
            "paid_at": b.paid_at,
            "create_time": b.create_time.strftime("%Y-%m-%d %H:%M:%S") if b.create_time else "",
        }
