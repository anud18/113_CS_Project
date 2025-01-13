from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

import os
import pymysql

def get_cursor():
    db = pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        db=os.getenv('DB_NAME'),
        charset='utf8'
    )
    return db
