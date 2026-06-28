import sys
import os

sys.path.insert(0, '/app')

from app.core.database import get_db_connection
from app.core.embeddings import get_embedding

test_data = {
    1: "رسید بانکی شماره ۴۵۲۱۸ به تاریخ ۲۰ فروردین ۱۴۰۳ بابت تسویه فاکتور شرکت تامین قطعات الکترونیک به مبلغ ۱۲۰ میلیون تومان در وجه بانک ملت ثبت گردید.",
    2: "سند شماره ۱۰۰۱ مربوط به پرداخت حقوق و دستمزد اسفند ماه ۱۴۰۲ کارکنان بخش توسعه نرم‌افزار به مبلغ ۵۰۰ میلیون تومان صادر گردید. این سند توسط مدیر مالی تایید شده است.",
    3: "در قراردادهای اختیار معامله کالا، تسویه فیزیکی تنها در صورتی مجاز است که خریدار سه روز قبل از سررسید، فرم درخواست تسویه فیزیکی را به کارگزاری ارائه دهد و وجه تضمین کافی در حساب خود داشته باشد.",
    4: "جهت تغییر کارگزار ناظر به کارگزاری ایساتیس پویا، مشتری باید تصویر کارت ملی، شناسنامه و آخرین برگه سهم خود را در پنل آپلود کرده و درخواست خود را ثبت نهایی کند. فرآیند تایید معمولا ۴۸ ساعت کاری زمان می‌برد.",
    5: "مهلت استفاده از حق تقدم خرید سهام ناشی از افزایش سرمایه از محل آورده نقدی معمولا ۶۰ روز پس از انتشار آگهی است و در صورت عدم واریز وجه، حق تقدم‌ها توسط شرکت به فروش رفته و مبلغ آن پس از کسر هزینه‌ها به حساب سهامدار واریز می‌شود."
}

def populate():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            for cat_id, text in test_data.items():
                print(f"Generating embedding for file_id {cat_id}...")
                # Fetch embedding using backend utility
                embedding = get_embedding(text)
                
                # Check if file_id already has a document, delete it first
                cur.execute("DELETE FROM pg_supervisor WHERE file_id = %s", (cat_id,))
                
                # Insert into pg_supervisor
                cur.execute("""
                    INSERT INTO pg_supervisor (content, embedding, label, file_id, sequence_id)
                    VALUES (%s, %s::vector, %s, %s, %s)
                """, (text, embedding, f"Mock Categorical Document {cat_id}", cat_id, 1))
                
                print(f"Inserted document for category ID {cat_id} successfully.")
                
            conn.commit()
    except Exception as e:
        print("Error:", str(e))
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    populate()
