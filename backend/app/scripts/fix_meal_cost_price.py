"""
修复餐费成本价历史数据
将餐费记录的 cost_price 更新为 amount（餐费金额）
并重新计算受影响房间会话的总成本和利润
"""
from sqlalchemy.orm import Session
from decimal import Decimal
from app.db.database import SessionLocal
from app.models.meal_record import MealRecord
from app.models.product_consumption import ProductConsumption
from app.models.room_session import RoomSession


def fix_meal_cost_price():
    """修复餐费成本价"""
    db: Session = SessionLocal()
    
    try:
        # 1. 查找所有 cost_price != amount 的餐费记录
        incorrect_meals = db.query(MealRecord).filter(
            MealRecord.amount != MealRecord.cost_price
        ).all()
        
        if not incorrect_meals:
            print("没有需要修复的餐费记录")
            return
        
        print(f"找到 {len(incorrect_meals)} 条需要修复的餐费记录")
        
        # 2. 获取受影响的房间会话ID
        affected_session_ids = set(meal.session_id for meal in incorrect_meals)
        print(f"受影响的房间会话数量: {len(affected_session_ids)}")
        
        # 3. 修复餐费记录的 cost_price
        for meal in incorrect_meals:
            old_cost = meal.cost_price
            new_cost = meal.amount
            print(f"修复餐费记录 ID={meal.id}: cost_price {old_cost} -> {new_cost}")
            meal.cost_price = new_cost
        
        db.flush()
        
        # 4. 重新计算受影响房间会话的总成本和利润
        for session_id in affected_session_ids:
            session = db.query(RoomSession).filter(RoomSession.id == session_id).first()
            if not session:
                continue
            
            # 计算商品总成本
            product_cost = Decimal("0")
            consumptions = db.query(ProductConsumption).filter(
                ProductConsumption.session_id == session_id
            ).all()
            for consumption in consumptions:
                product_cost += consumption.total_cost or Decimal("0")
            
            # 计算餐费总成本
            meal_cost = Decimal("0")
            meals = db.query(MealRecord).filter(
                MealRecord.session_id == session_id
            ).all()
            for meal in meals:
                meal_cost += meal.cost_price or Decimal("0")
            
            # 更新总成本
            old_total_cost = session.total_cost
            new_total_cost = product_cost + meal_cost
            session.total_cost = new_total_cost
            
            # 重新计算利润
            if session.table_fee:
                session.total_profit = session.table_fee - new_total_cost
            else:
                session.total_profit = Decimal("0")
            
            print(f"房间会话 ID={session_id}: total_cost {old_total_cost} -> {new_total_cost}, profit={session.total_profit}")
        
        # 5. 提交更改
        db.commit()
        print("修复完成！")
        
    except Exception as e:
        db.rollback()
        print(f"修复失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix_meal_cost_price()





