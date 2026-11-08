# -*- coding: utf-8 -*-
"""
大專院校校務資訊系統 (University Information System - UIS)
=========================================================
功能亮點：
1. RBAC 三重角色控管 (教務管理員 Admin, 授課教師 Teacher, 在校學生 Student)
2. 完整選課機制：衝堂自動偵測、名額上限卡控、防重複加選、退選維護
3. 學生課表矩陣視覺化、歷年成績單累計 GPA 試算、線上請假與申請
4. 教師成績評分與等第自動換算、學生名冊、課堂線上點名
5. 行政端帳號建立、開課與教室排程、公告發布、申請審核
"""

import sqlite3
import hashlib
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict, Tuple

DB_FILE = "university_system.db"

# ==========================================
# 1. 資料庫初始化與結構 (Schema & Migration)
# ==========================================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 建立使用者表 (RBAC: admin, teacher, student)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'teacher', 'student')),
        full_name TEXT NOT NULL,
        department TEXT NOT NULL,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 建立課程表 (Courses)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_code TEXT UNIQUE NOT NULL,
        course_name TEXT NOT NULL,
        teacher_id INTEGER NOT NULL,
        credits INTEGER NOT NULL DEFAULT 3,
        capacity INTEGER NOT NULL DEFAULT 50,
        day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 1 AND 7), -- 1:週一 ~ 7:週日
        start_period INTEGER NOT NULL CHECK(start_period BETWEEN 1 AND 10),
        end_period INTEGER NOT NULL CHECK(end_period BETWEEN 1 AND 10),
        classroom TEXT NOT NULL,
        syllabus TEXT,
        semester TEXT NOT NULL DEFAULT '113-1',
        FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 建立選課紀錄表 (Enrollments)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        semester TEXT NOT NULL DEFAULT '113-1',
        status TEXT NOT NULL DEFAULT 'enrolled' CHECK(status IN ('enrolled', 'dropped')),
        enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, course_id, semester),
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
    );
    """)

    # 建立成績表 (Grades)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enrollment_id INTEGER UNIQUE NOT NULL,
        midterm_score REAL,
        final_score REAL,
        regular_score REAL,
        total_score REAL,
        letter_grade TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE
    );
    """)

    # 建立公告表 (Announcements)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        target_role TEXT NOT NULL DEFAULT 'all', -- 'all', 'student', 'teacher'
        publisher_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (publisher_id) REFERENCES users(id)
    );
    """)

    # 建立學生請假/各項申請表 (Applications)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        app_type TEXT NOT NULL,
        reason TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users(id)
    );
    """)

    # 建立點名紀錄表 (Attendance)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('present', 'absent', 'leave', 'late')),
        FOREIGN KEY (course_id) REFERENCES courses(id),
        FOREIGN KEY (student_id) REFERENCES users(id)
    );
    """)

    conn.commit()
    conn.close()

# ==========================================
# 2. 預設資料填充 (Seeding Sample Data)
# ==========================================

def seed_sample_data():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as cnt FROM users;")
    if cursor.fetchone()["cnt"] > 0:
        conn.close()
        return

    default_pwd = hash_password("123456")
    users = [
        ("admin", default_pwd, "admin", "系統管理員-張組長", "教務處註冊組", "admin@univ.edu.tw"),
        ("prof_lin", default_pwd, "teacher", "林資工 教授", "資訊工程學系", "lin@cs.univ.edu.tw"),
        ("prof_wang", default_pwd, "teacher", "王商管 副教授", "企業管理學系", "wang@ba.univ.edu.tw"),
        ("std101", default_pwd, "student", "陳小明", "資訊工程學系", "s101@univ.edu.tw"),
        ("std102", default_pwd, "student", "李美麗", "資訊工程學系", "s102@univ.edu.tw"),
        ("std103", default_pwd, "student", "張大同", "企業管理學系", "s103@univ.edu.tw"),
    ]
    cursor.executemany("""
    INSERT INTO users (username, password_hash, role, full_name, department, email)
    VALUES (?, ?, ?, ?, ?, ?);
    """, users)

    cursor.execute("SELECT id FROM users WHERE username = 'prof_lin';")
    prof_lin_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM users WHERE username = 'prof_wang';")
    prof_wang_id = cursor.fetchone()["id"]

    # 課程設計：包含時段衝突(CS101 vs CS103 均在週一3-4節)與額滿測試(BA202 上限2人)
    courses = [
        ("CS101", "資料結構與演算法", prof_lin_id, 3, 40, 1, 3, 4, "資工館 E201", "核心專業必修，涵蓋鏈結串列、樹、圖與複雜度分析。", "113-1"),
        ("CS102", "資料庫系統設計", prof_lin_id, 3, 35, 3, 5, 6, "資工館 E205", "正規化、SQL實作與交易隔離機制。", "113-1"),
        ("CS103", "作業系統導論", prof_lin_id, 3, 45, 1, 3, 4, "資工館 E101", "行程排程、虛擬記憶體與檔案系統 (與CS101衝堂)。", "113-1"),
        ("BA201", "行銷管理與社群策略", prof_wang_id, 2, 50, 4, 1, 2, "管院 M302", "數位行銷、受眾洞察與商業策略分析。", "113-1"),
        ("BA202", "統計學與巨量分析", prof_wang_id, 3, 1, 2, 7, 8, "管院 M105", "推論統計與資料探勘實務 (限額1人供測試額滿擋修)。", "113-1"),
    ]
    cursor.executemany("""
    INSERT INTO courses (course_code, course_name, teacher_id, credits, capacity, day_of_week, start_period, end_period, classroom, syllabus, semester)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, courses)

    cursor.execute("SELECT id FROM users WHERE username = 'std101';")
    std101_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM users WHERE username = 'std102';")
    std102_id = cursor.fetchone()["id"]

    cursor.execute("SELECT id FROM courses WHERE course_code = 'CS101';")
    cs101_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM courses WHERE course_code = 'BA201';")
    ba201_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM courses WHERE course_code = 'BA202';")
    ba202_id = cursor.fetchone()["id"]

    # 預先為 std101 選課與填入成績
    cursor.execute("INSERT INTO enrollments (student_id, course_id, semester) VALUES (?, ?, '113-1');", (std101_id, cs101_id))
    enr1_id = cursor.lastrowid
    cursor.execute("INSERT INTO enrollments (student_id, course_id, semester) VALUES (?, ?, '113-1');", (std101_id, ba201_id))
    enr2_id = cursor.lastrowid

    cursor.execute("""
    INSERT INTO grades (enrollment_id, midterm_score, final_score, regular_score, total_score, letter_grade)
    VALUES (?, 85.0, 92.0, 90.0, 89.1, 'A');
    """, (enr1_id,))
    cursor.execute("""
    INSERT INTO grades (enrollment_id, midterm_score, final_score, regular_score, total_score, letter_grade)
    VALUES (?, 78.0, 82.0, 80.0, 80.0, 'B+');
    """, (enr2_id,))

    # 為 std102 選滿 BA202
    cursor.execute("INSERT INTO enrollments (student_id, course_id, semester) VALUES (?, ?, '113-1');", (std102_id, ba202_id))

    # 建立系統公告
    cursor.execute("""
    INSERT INTO announcements (title, content, target_role, publisher_id)
    VALUES 
    ('113學年度第一學期選課注意事項', '請同學依序於加退選截止日前完成選修，若有衝堂系統將自動擋修。', 'all', 1),
    ('教師期中考成績登錄時程公告', '授課教師請於第9週結束前於教師專區完成學生成績上傳與等第核算。', 'teacher', 1);
    """)

    conn.commit()
    conn.close()

# ==========================================
# 3. 業務核心邏輯 (Business Logic Services)
# ==========================================

class AuthService:
    @staticmethod
    def login(username, password) -> Optional[Dict]:
        conn = get_db()
        cursor = conn.cursor()
        pwd_hash = hash_password(password)
        cursor.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?;", (username, pwd_hash))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

class StudentService:
    @staticmethod
    def get_enrolled_courses(student_id: int, semester="113-1"):
        conn = get_db()
        cursor = conn.cursor()
        query = """
        SELECT c.*, u.full_name as teacher_name, e.id as enrollment_id, e.status
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        JOIN users u ON c.teacher_id = u.id
        WHERE e.student_id = ? AND e.semester = ? AND e.status = 'enrolled'
        ORDER BY c.day_of_week, c.start_period;
        """
        cursor.execute(query, (student_id, semester))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def enroll_course(student_id: int, course_id: int, semester="113-1") -> Tuple[bool, str]:
        """
        核心選課邏輯：
        1. 檢查是否已修習
        2. 檢查名額限制 (Capacity)
        3. 檢查衝堂機制 (Time Clash Detection)
        4. 交易隔離防護
        """
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM courses WHERE id = ?;", (course_id,))
            target_course = cursor.fetchone()
            if not target_course:
                return False, "❌ 查無此課程代碼。"

            # 1. 重複選課檢核
            cursor.execute("""
            SELECT status FROM enrollments 
            WHERE student_id = ? AND course_id = ? AND semester = ?;
            """, (student_id, course_id, semester))
            existing = cursor.fetchone()
            if existing and existing["status"] == "enrolled":
                return False, "⚠️ 您已選修此課程，不可重複加選。"

            # 2. 名額檢核
            cursor.execute("""
            SELECT COUNT(*) as current_count FROM enrollments 
            WHERE course_id = ? AND status = 'enrolled' AND semester = ?;
            """, (course_id, semester))
            current_enrolled = cursor.fetchone()["current_count"]
            if current_enrolled >= target_course["capacity"]:
                return False, f"❌ 選課失敗：該課程名額已額滿 ({current_enrolled}/{target_course['capacity']})。"

            # 3. 衝堂檢核 (Time Clash)
            cursor.execute("""
            SELECT c.course_name, c.day_of_week, c.start_period, c.end_period
            FROM enrollments e
            JOIN courses c ON e.course_id = c.id
            WHERE e.student_id = ? AND e.semester = ? AND e.status = 'enrolled';
            """, (student_id, semester))
            enrolled_courses = cursor.fetchall()

            for ec in enrolled_courses:
                if ec["day_of_week"] == target_course["day_of_week"]:
                    # 重疊判定: max(start1, start2) <= min(end1, end2)
                    if max(ec["start_period"], target_course["start_period"]) <= min(ec["end_period"], target_course["end_period"]):
                        return False, f"🚫 衝堂攔截：與已選【{ec['course_name']}】(週{ec['day_of_week']} 第{ec['start_period']}~{ec['end_period']}節) 時間重疊！"

            # 4. 寫入或更新記錄
            if existing and existing["status"] == "dropped":
                cursor.execute("""
                UPDATE enrollments SET status = 'enrolled', enrolled_at = CURRENT_TIMESTAMP
                WHERE student_id = ? AND course_id = ? AND semester = ?;
                """, (student_id, course_id, semester))
            else:
                cursor.execute("""
                INSERT INTO enrollments (student_id, course_id, semester, status)
                VALUES (?, ?, ?, 'enrolled');
                """, (student_id, course_id, semester))

            conn.commit()
            return True, f"🎉 加選成功：【{target_course['course_name']}】({target_course['credits']} 學分)"
        except Exception as e:
            conn.rollback()
            return False, f"系統錯誤：{str(e)}"
        finally:
            conn.close()

    @staticmethod
    def drop_course(student_id: int, course_id: int, semester="113-1") -> Tuple[bool, str]:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            UPDATE enrollments SET status = 'dropped' 
            WHERE student_id = ? AND course_id = ? AND semester = ? AND status = 'enrolled';
            """, (student_id, course_id, semester))
            if cursor.rowcount > 0:
                conn.commit()
                return True, "✅ 退選成功。"
            else:
                return False, "⚠️ 您並未選修該課程或已經退選。"
        except Exception as e:
            conn.rollback()
            return False, f"退選失敗：{str(e)}"
        finally:
            conn.close()

    @staticmethod
    def get_grades(student_id: int):
        conn = get_db()
        cursor = conn.cursor()
        query = """
        SELECT c.course_code, c.course_name, c.credits, e.semester,
               g.regular_score, g.midterm_score, g.final_score, g.total_score, g.letter_grade
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        LEFT JOIN grades g ON g.enrollment_id = e.id
        WHERE e.student_id = ? AND e.status = 'enrolled'
        ORDER BY e.semester DESC, c.course_code ASC;
        """
        cursor.execute(query, (student_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def submit_application(student_id: int, app_type: str, reason: str):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO applications (student_id, app_type, reason)
        VALUES (?, ?, ?);
        """, (student_id, app_type, reason))
        conn.commit()
        conn.close()

    @staticmethod
    def get_applications(student_id: int):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM applications WHERE student_id = ? ORDER BY created_at DESC;", (student_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

class TeacherService:
    @staticmethod
    def get_teaching_courses(teacher_id: int):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT c.*, 
               (SELECT COUNT(*) FROM enrollments e WHERE e.course_id = c.id AND e.status = 'enrolled') as enrolled_count
        FROM courses c 
        WHERE c.teacher_id = ?
        ORDER BY c.day_of_week, c.start_period;
        """, (teacher_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_course_students(course_id: int):
        conn = get_db()
        cursor = conn.cursor()
        query = """
        SELECT e.id as enrollment_id, u.id as student_id, u.username, u.full_name, u.department,
               g.midterm_score, g.final_score, g.regular_score, g.total_score, g.letter_grade
        FROM enrollments e
        JOIN users u ON e.student_id = u.id
        LEFT JOIN grades g ON g.enrollment_id = e.id
        WHERE e.course_id = ? AND e.status = 'enrolled'
        ORDER BY u.username;
        """
        cursor.execute(query, (course_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def update_grade(enrollment_id: int, reg_s: float, mid_s: float, fin_s: float):
        total = round(reg_s * 0.3 + mid_s * 0.3 + fin_s * 0.4, 1)
        if total >= 90: letter = "A+"
        elif total >= 85: letter = "A"
        elif total >= 80: letter = "B+"
        elif total >= 75: letter = "B"
        elif total >= 70: letter = "C+"
        elif total >= 60: letter = "C"
        else: letter = "F"

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO grades (enrollment_id, regular_score, midterm_score, final_score, total_score, letter_grade, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(enrollment_id) DO UPDATE SET
            regular_score = excluded.regular_score,
            midterm_score = excluded.midterm_score,
            final_score = excluded.final_score,
            total_score = excluded.total_score,
            letter_grade = excluded.letter_grade,
            updated_at = CURRENT_TIMESTAMP;
        """, (enrollment_id, reg_s, mid_s, fin_s, total, letter))
        conn.commit()
        conn.close()

    @staticmethod
    def record_attendance(course_id: int, student_id: int, date_str: str, status: str):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO attendance (course_id, student_id, date, status)
        VALUES (?, ?, ?, ?);
        """, (course_id, student_id, date_str, status))
        conn.commit()
        conn.close()

    @staticmethod
    def update_syllabus(course_id: int, syllabus: str):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE courses SET syllabus = ? WHERE id = ?;", (syllabus, course_id))
        conn.commit()
        conn.close()

class AdminService:
    @staticmethod
    def list_users():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role, full_name, department, email, created_at FROM users ORDER BY role, id;")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def create_user(username, password, role, full_name, department, email):
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO users (username, password_hash, role, full_name, department, email)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (username, hash_password(password), role, full_name, department, email))
            conn.commit()
            return True, "✅ 使用者建立成功！"
        except sqlite3.IntegrityError:
            return False, "❌ 帳號重複，該使用者帳號已存在。"
        finally:
            conn.close()

    @staticmethod
    def add_course(code, name, teacher_id, credits, capacity, day, start, end, classroom, syllabus, semester):
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO courses (course_code, course_name, teacher_id, credits, capacity, day_of_week, start_period, end_period, classroom, syllabus, semester)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (code, name, teacher_id, credits, capacity, day, start, end, classroom, syllabus, semester))
            conn.commit()
            return True, "✅ 課程建立成功！"
        except sqlite3.IntegrityError as e:
            return False, f"❌ 建立失敗 (課程代碼重複或教師ID無效): {str(e)}"
        finally:
            conn.close()

    @staticmethod
    def list_all_courses():
        conn = get_db()
        cursor = conn.cursor()
        query = """
        SELECT c.*, u.full_name as teacher_name,
               (SELECT COUNT(*) FROM enrollments e WHERE e.course_id = c.id AND e.status = 'enrolled') as enrolled_count
        FROM courses c
        JOIN users u ON c.teacher_id = u.id
        ORDER BY c.semester, c.course_code;
        """
        cursor.execute(query)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def post_announcement(title, content, target_role, publisher_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO announcements (title, content, target_role, publisher_id)
        VALUES (?, ?, ?, ?);
        """, (title, content, target_role, publisher_id))
        conn.commit()
        conn.close()

    @staticmethod
    def list_applications():
        conn = get_db()
        cursor = conn.cursor()
        query = """
        SELECT a.*, u.full_name, u.username, u.department
        FROM applications a
        JOIN users u ON a.student_id = u.id
        ORDER BY a.created_at DESC;
        """
        cursor.execute(query)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def review_application(app_id: int, status: str):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE applications SET status = ? WHERE id = ?;", (status, app_id))
        conn.commit()
        conn.close()

# ==========================================
# 4. 終端機使用者介面 (Terminal UI Views)
# ==========================================

DAYS_MAP = {1: "週一", 2: "週二", 3: "週三", 4: "週四", 5: "週五", 6: "週六", 7: "週日"}

def print_header(title: str):
    print("\n" + "=" * 65)
    print("🎓  " + title)
    print("=" * 65)

def print_announcements(role: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT a.*, u.full_name as publisher 
    FROM announcements a 
    JOIN users u ON a.publisher_id = u.id
    WHERE a.target_role = 'all' OR a.target_role = ?
    ORDER BY a.created_at DESC LIMIT 5;
    """, (role,))
    announcements = cursor.fetchall()
    conn.close()

    if announcements:
        print("\n📢 【最新教務公告】")
        for ann in announcements:
            print(" • [" + ann['created_at'][:10] + "] " + ann['title'] + " (發布者: " + ann['publisher'] + ")")
            print("   內文: " + ann['content'])
        print("-" * 65)

# --- 學生介面 ---
def student_menu(user: Dict):
    while True:
        print_header("學生專區 (Student Portal) - " + user['full_name'] + " [" + user['department'] + "]")
        print_announcements("student")
        print("1. 查詢個人學籍與修業門檻")
        print("2. 學生選課系統 (加選 / 查詢課程清單 / 衝堂檢核)")
        print("3. 已選課程與退選")
        print("4. 個人週課表 (視覺化矩陣)")
        print("5. 歷年成績單與 GPA 試算")
        print("6. 線上請假與行政各項申請")
        print("0. 登出系統")
        choice = input("\n請輸入選項 [0-6]: ").strip()

        if choice == "1":
            print_header("個人學籍與畢業門檻查詢")
            enrolled = StudentService.get_enrolled_courses(user["id"])
            total_credits = sum(c["credits"] for c in enrolled)
            print("姓名：" + user['full_name'])
            print("學號：" + user['username'])
            print("系所：" + user['department'])
            print("電子郵件：" + (user['email'] or '無'))
            print("本學期已選學分：" + str(total_credits) + " 學分")
            print("畢業最低門檻：128 學分 (目前已修習採計中)")
            input("\n按 Enter 鍵返回主選單...")

        elif choice == "2":
            print_header("全校開課清單與加選")
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
            SELECT c.*, u.full_name as teacher_name,
                   (SELECT COUNT(*) FROM enrollments e WHERE e.course_id = c.id AND e.status = 'enrolled') as current_count
            FROM courses c
            JOIN users u ON c.teacher_id = u.id
            ORDER BY c.day_of_week, c.start_period;
            """)
            all_courses = cursor.fetchall()
            conn.close()

            print(f"{'ID':<4} {'代碼':<8} {'課程名稱':<18} {'授課教師':<10} {'學分':<5} {'名額狀態':<10} {'上課時間與教室'}")
            print("-" * 75)
            for c in all_courses:
                time_str = f"{DAYS_MAP.get(c['day_of_week'])} 第{c['start_period']}~{c['end_period']}節 ({c['classroom']})"
                cap_str = f"{c['current_count']}/{c['capacity']}"
                print(f"{c['id']:<4} {c['course_code']:<8} {c['course_name']:<18} {c['teacher_name']:<10} {c['credits']:<5} {cap_str:<10} {time_str}")

            print("\n輸入課程 ID 即可加選，或輸入 Q 放棄返回：")
            target = input("請選擇課程 ID: ").strip()
            if target.upper() != "Q" and target.isdigit():
                success, msg = StudentService.enroll_course(user["id"], int(target))
                print(msg)
            input("\n按 Enter 鍵繼續...")

        elif choice == "3":
            print_header("目前已選修課程清單")
            enrolled = StudentService.get_enrolled_courses(user["id"])
            if not enrolled:
                print("尚無任何選課紀錄。")
            else:
                print(f"{'課程ID':<6} {'代碼':<8} {'課程名稱':<18} {'授課教師':<10} {'學分':<5} {'上課時間'}")
                print("-" * 65)
                for c in enrolled:
                    time_str = f"{DAYS_MAP.get(c['day_of_week'])} 第{c['start_period']}~{c['end_period']}節"
                    print(f"{c['id']:<6} {c['course_code']:<8} {c['course_name']:<18} {c['teacher_name']:<10} {c['credits']:<5} {time_str}")
                print("\n輸入欲退選的【課程ID】，或輸入 Q 放棄：")
                drop_id = input("退選課程 ID: ").strip()
                if drop_id.upper() != "Q" and drop_id.isdigit():
                    confirm = input("⚠️ 確認要退選嗎？(y/N): ").strip().lower()
                    if confirm == 'y':
                        ok, msg = StudentService.drop_course(user["id"], int(drop_id))
                        print(msg)
            input("\n按 Enter 鍵繼續...")

        elif choice == "4":
            print_header("本學期個人週課表矩陣")
            enrolled = StudentService.get_enrolled_courses(user["id"])
            schedule_grid = {p: {d: "" for d in range(1, 6)} for p in range(1, 11)}
            for c in enrolled:
                d = c["day_of_week"]
                if 1 <= d <= 5:
                    for p in range(c["start_period"], c["end_period"] + 1):
                        schedule_grid[p][d] = c["course_name"][:6]

            print(f"{'節次':<6} | {'週一':<10} | {'週二':<10} | {'週三':<10} | {'週四':<10} | {'週五':<10}")
            print("-" * 65)
            for p in range(1, 11):
                row = [f"第{p}節".ljust(5)]
                for d in range(1, 6):
                    cname = schedule_grid[p][d]
                    row.append(cname.ljust(9) if cname else " " * 9)
                print(" | ".join(row))
            input("\n按 Enter 鍵返回...")

        elif choice == "5":
            print_header("歷年成績單與總成績")
            grades = StudentService.get_grades(user["id"])
            if not grades:
                print("目前尚無學期成績紀錄。")
            else:
                print(f"{'學期':<8} {'代碼':<8} {'課程名稱':<18} {'學分':<5} {'平時':<6} {'期中':<6} {'期末':<6} {'總分':<6} {'等第'}")
                print("-" * 75)
                total_earned_credits = 0
                weighted_sum = 0
                for g in grades:
                    ts = f"{g['total_score']:.1f}" if g['total_score'] is not None else "--"
                    lg = g['letter_grade'] or "--"
                    ps = f"{g['regular_score']:.1f}" if g['regular_score'] is not None else "--"
                    ms = f"{g['midterm_score']:.1f}" if g['midterm_score'] is not None else "--"
                    fs = f"{g['final_score']:.1f}" if g['final_score'] is not None else "--"
                    print(f"{g['semester']:<8} {g['course_code']:<8} {g['course_name']:<18} {g['credits']:<5} {ps:<6} {ms:<6} {fs:<6} {ts:<6} {lg}")
                    if g['total_score'] is not None:
                        total_earned_credits += g['credits']
                        weighted_sum += g['total_score'] * g['credits']
                if total_earned_credits > 0:
                    avg_score = weighted_sum / total_earned_credits
                    print("-" * 75)
                    print(f"📊 加權平均總分：{avg_score:.2f} 分 | 累計核算學分：{total_earned_credits} 學分")
            input("\n按 Enter 鍵返回...")

        elif choice == "6":
            print_header("線上申請與請假系統")
            print("1. 提交請假申請")
            print("2. 提交歷年成績單列印申請")
            print("3. 提交校內優秀獎學金申請")
            print("4. 查詢我的申請歷史進度")
            sub_c = input("\n請選擇 [1-4, 其餘返回]: ").strip()
            if sub_c == "1":
                reason = input("請輸入請假日期、假別與事由: ").strip()
                if reason:
                    StudentService.submit_application(user["id"], "請假申請", reason)
                    print("✅ 請假申請已送出，等待教務組審核。")
            elif sub_c == "2":
                reason = input("請註明需要份數與用途: ").strip()
                if reason:
                    StudentService.submit_application(user["id"], "成績單列印申請", reason)
                    print("✅ 成績單列印申請已送出。")
            elif sub_c == "3":
                reason = input("請填寫申請學年期與檢附事由: ").strip()
                if reason:
                    StudentService.submit_application(user["id"], "獎學金申請", reason)
                    print("✅ 獎學金申請已送出。")
            elif sub_c == "4":
                apps = StudentService.get_applications(user["id"])
                print(f"{'申請項目':<15} {'事由內容':<25} {'審核狀態':<10} {'申請時間'}")
                print("-" * 65)
                for a in apps:
                    status_badge = {"pending": "⏳ 待審核", "approved": "🟢 已核准", "rejected": "🔴 已駁回"}.get(a["status"], a["status"])
                    print(f"{a['app_type']:<15} {a['reason'][:20]:<25} {status_badge:<10} {a['created_at'][:16]}")
            input("\n按 Enter 鍵繼續...")

        elif choice == "0":
            break

# --- 教師介面 ---
def teacher_menu(user: Dict):
    while True:
        print_header("教師專區 (Faculty Portal) - " + user['full_name'] + " [" + user['department'] + "]")
        print_announcements("teacher")
        print("1. 我的授課課程清單與學生名冊")
        print("2. 成績登錄與等第結算")
        print("3. 課堂出缺席點名")
        print("4. 更新課程教學大綱 (Syllabus)")
        print("0. 登出系統")
        choice = input("\n請輸入選項 [0-4]: ").strip()

        if choice == "1":
            print_header("授課課程與名冊管理")
            courses = TeacherService.get_teaching_courses(user["id"])
            if not courses:
                print("您本學期目前沒有開授任何課程。")
            else:
                for c in courses:
                    print(f"\n📚 [{c['course_code']}] {c['course_name']} | 選課人數: {c['enrolled_count']}/{c['capacity']}")
                    students = TeacherService.get_course_students(c["id"])
                    if not students:
                        print("   (目前尚無修課學生)")
                    else:
                        print(f"   {'學號':<10} {'姓名':<10} {'系所':<18} {'期中':<6} {'期末':<6} {'總成績'}")
                        print("   " + "-" * 55)
                        for s in students:
                            mid = f"{s['midterm_score']:.1f}" if s['midterm_score'] is not None else "--"
                            fin = f"{s['final_score']:.1f}" if s['final_score'] is not None else "--"
                            tot = f"{s['total_score']:.1f}" if s['total_score'] is not None else "--"
                            print(f"   {s['username']:<10} {s['full_name']:<10} {s['department']:<18} {mid:<6} {fin:<6} {tot}")
            input("\n按 Enter 鍵繼續...")

        elif choice == "2":
            print_header("成績輸入與登錄系統")
            courses = TeacherService.get_teaching_courses(user["id"])
            for idx, c in enumerate(courses, 1):
                print(f"{idx}. [{c['course_code']}] {c['course_name']}")
            c_sel = input("\n請選擇欲登錄成績的課程編號: ").strip()
            if c_sel.isdigit() and 1 <= int(c_sel) <= len(courses):
                target_course = courses[int(c_sel) - 1]
                students = TeacherService.get_course_students(target_course["id"])
                if not students:
                    print("⚠️ 該課程目前沒有學生修習。")
                else:
                    for s in students:
                        print(f"\n登錄學生：{s['full_name']} ({s['username']})")
                        try:
                            reg = float(input(f" 平時成績 (目前: {s['regular_score']}): ") or s['regular_score'] or 0)
                            mid = float(input(f" 期中考成績 (目前: {s['midterm_score']}): ") or s['midterm_score'] or 0)
                            fin = float(input(f" 期末考成績 (目前: {s['final_score']}): ") or s['final_score'] or 0)
                            TeacherService.update_grade(s["enrollment_id"], reg, mid, fin)
                            print("  ✅ 成績已儲存並自動計算加權總分與等第！")
                        except ValueError:
                            print("  ❌ 輸入格式錯誤，略過此學生。")
            input("\n按 Enter 鍵繼續...")

        elif choice == "3":
            print_header("線上課堂點名紀錄")
            courses = TeacherService.get_teaching_courses(user["id"])
            for idx, c in enumerate(courses, 1):
                print(f"{idx}. [{c['course_code']}] {c['course_name']}")
            c_sel = input("\n請選擇課程編號: ").strip()
            if c_sel.isdigit() and 1 <= int(c_sel) <= len(courses):
                target_course = courses[int(c_sel) - 1]
                students = TeacherService.get_course_students(target_course["id"])
                today = datetime.now().strftime("%Y-%m-%d")
                print(f"\n開始點名【{target_course['course_name']}】(日期: {today})")
                print("代碼說明：1.出席(present) 2.缺席(absent) 3.請假(leave) 4.遲到(late)")
                for s in students:
                    st_choice = input(f"{s['full_name']} ({s['username']}) [預設 1]: ").strip() or "1"
                    status_map = {"1": "present", "2": "absent", "3": "leave", "4": "late"}
                    TeacherService.record_attendance(target_course["id"], s["student_id"], today, status_map.get(st_choice, "present"))
                print("✅ 點名紀錄完成！")
            input("\n按 Enter 鍵繼續...")

        elif choice == "4":
            print_header("課程教學大綱維護")
            courses = TeacherService.get_teaching_courses(user["id"])
            for idx, c in enumerate(courses, 1):
                print(f"{idx}. [{c['course_code']}] {c['course_name']}")
            c_sel = input("\n請選擇欲編輯大綱的課程: ").strip()
            if c_sel.isdigit() and 1 <= int(c_sel) <= len(courses):
                tc = courses[int(c_sel) - 1]
                print(f"目前大綱：\n{tc['syllabus']}")
                new_s = input("\n請輸入新課程大綱 (直接按 Enter 放棄): ").strip()
                if new_s:
                    TeacherService.update_syllabus(tc["id"], new_s)
                    print("✅ 教學大綱已更新！")
            input("\n按 Enter 鍵繼續...")

        elif choice == "0":
            break

# --- 教務行政介面 ---
def admin_menu(user: Dict):
    while True:
        print_header("教務行政管理端 (Admin Portal) - " + user['full_name'])
        print("1. 帳號與權限管理 (檢視 / 新增師生帳號)")
        print("2. 開課管理 (新增課程、排程與教室設定)")
        print("3. 全校開課與選課人次統計")
        print("4. 發布教務公告")
        print("5. 學生各項申請審核 (請假 / 獎學金 / 成績單)")
        print("0. 登出系統")
        choice = input("\n請輸入選項 [0-5]: ").strip()

        if choice == "1":
            print_header("帳號管理清單")
            users = AdminService.list_users()
            print(f"{'ID':<4} {'角色':<10} {'帳號':<12} {'姓名':<14} {'所屬系所/單位':<18} {'電子郵件'}")
            print("-" * 75)
            for u in users:
                print(f"{u['id']:<4} {u['role']:<10} {u['username']:<12} {u['full_name']:<14} {u['department']:<18} {u['email']}")

            print("\n是否新增帳號？(y/N): ")
            if input().strip().lower() == "y":
                un = input("帳號: ").strip()
                pw = input("預設密碼: ").strip()
                ro = input("角色 (admin / teacher / student): ").strip().lower()
                fn = input("真實姓名: ").strip()
                dp = input("系所/單位: ").strip()
                em = input("電子郵件: ").strip()
                if un and pw and ro in ["admin", "teacher", "student"]:
                    ok, msg = AdminService.create_user(un, pw, ro, fn, dp, em)
                    print(msg)
                else:
                    print("❌ 輸入資料不完整或角色無效。")
            input("\n按 Enter 鍵繼續...")

        elif choice == "2":
            print_header("系所開課與教室排程設定")
            code = input("課程代碼 (如 CS201): ").strip()
            name = input("課程名稱: ").strip()
            tid = input("授課教師 User ID: ").strip()
            cre = input("學分數 (如 3): ").strip()
            cap = input("開課名額上限 (如 45): ").strip()
            day = input("星期幾 (1-7): ").strip()
            st = input("開始節次 (1-10): ").strip()
            et = input("結束節次 (1-10): ").strip()
            room = input("上課教室 (如 工館 301): ").strip()
            syl = input("簡要課程大綱: ").strip()
            sem = input("學期 (預設 113-1): ").strip() or "113-1"

            if all([code, name, tid.isdigit(), cre.isdigit(), cap.isdigit(), day.isdigit(), st.isdigit(), et.isdigit(), room]):
                ok, msg = AdminService.add_course(code, name, int(tid), int(cre), int(cap), int(day), int(st), int(et), room, syl, sem)
                print(msg)
            else:
                print("❌ 輸入欄位有誤，請檢核數值格式。")
            input("\n按 Enter 鍵繼續...")

        elif choice == "3":
            print_header("全校課程與修課人次統計")
            courses = AdminService.list_all_courses()
            print(f"{'代碼':<8} {'課程名稱':<18} {'授課教師':<10} {'修課/名額':<12} {'時間地點'}")
            print("-" * 65)
            for c in courses:
                time_str = f"{DAYS_MAP.get(c['day_of_week'])} 第{c['start_period']}~{c['end_period']}節 ({c['classroom']})"
                cap_stat = f"{c['enrolled_count']}/{c['capacity']}"
                print(f"{c['course_code']:<8} {c['course_name']:<18} {c['teacher_name']:<10} {cap_stat:<12} {time_str}")
            input("\n按 Enter 鍵繼續...")

        elif choice == "4":
            print_header("發布全校/特定對象公告")
            title = input("公告標題: ").strip()
            content = input("公告內文: ").strip()
            print("發布對象: 1. 全體師生(all)  2. 僅學生(student)  3. 僅教師(teacher)")
            target_map = {"1": "all", "2": "student", "3": "teacher"}
            t_sel = input("請選擇對象 [1-3]: ").strip()
            target = target_map.get(t_sel, "all")
            if title and content:
                AdminService.post_announcement(title, content, target, user["id"])
                print("✅ 公告已成功發布！")
            else:
                print("❌ 標題與內文不可為空。")
            input("\n按 Enter 鍵繼續...")

        elif choice == "5":
            print_header("學生各項申請審核")
            apps = AdminService.list_applications()
            if not apps:
                print("目前沒有任何待審核的申請。")
            else:
                print(f"{'ID':<4} {'學號':<10} {'姓名':<10} {'申請類型':<14} {'狀態':<10} {'內容說明'}")
                print("-" * 65)
                for a in apps:
                    print(f"{a['id']:<4} {a['username']:<10} {a['full_name']:<10} {a['app_type']:<14} {a['status']:<10} {a['reason'][:20]}")
                print("\n輸入申請 ID 進行審核 (核准或駁回)，或輸入 Q 返回：")
                app_id = input("請輸入申請 ID: ").strip()
                if app_id.isdigit():
                    print("選擇處理結果: 1. 核准 (approved)  2. 駁回 (rejected)")
                    rev_c = input("審核決策 [1/2]: ").strip()
                    if rev_c == "1":
                        AdminService.review_application(int(app_id), "approved")
                        print("✅ 已核准該筆申請！")
                    elif rev_c == "2":
                        AdminService.review_application(int(app_id), "rejected")
                        print("🚫 已駁回該筆申請。")
            input("\n按 Enter 鍵繼續...")

        elif choice == "0":
            break

# ==========================================
# 5. 主程式入口與登入畫面
# ==========================================

def main():
    init_db()
    seed_sample_data()

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=" * 65)
        print("🏛️   大專院校校務行政資訊整合系統 (Campus Academic Portal)")
        print("=" * 65)
        print(" 系統包含 RBAC 權限角色控管機制：")
        print(" 📌 預設測試帳號 (密碼皆為 123456)：")
        print("   • 管理員(Admin)  : admin")
        print("   • 教師端(Faculty): prof_lin (資工系) / prof_wang (企管系)")
        print("   • 學生端(Student): std101 (陳小明) / std102 (李美麗)")
        print("-" * 65)
        print("1. 系統登入 (Login)")
        print("0. 結束離開系統")
        choice = input("\n請選擇 [0/1]: ").strip()

        if choice == "1":
            print("\n--- 請輸入身分驗證憑證 ---")
            username = input("帳號 (Username): ").strip()
            password = input("密碼 (Password): ").strip()
            user = AuthService.login(username, password)

            if not user:
                print("❌ 登入失敗：帳號或密碼錯誤！")
                input("按 Enter 鍵重試...")
                continue

            print("\n🎉 驗證成功！歡迎【" + user['full_name'] + "】進入系統。")

            # 依據 RBAC 角色分流進入對應 Portal
            if user["role"] == "student":
                student_menu(user)
            elif user["role"] == "teacher":
                teacher_menu(user)
            elif user["role"] == "admin":
                admin_menu(user)
            else:
                print("⚠️ 未知的角色權限，請聯絡系統管理員。")
                input()

        elif choice == "0":
            print("\n感謝使用大專院校校務資訊系統，系統安全登出。再見！\n")
            sys.exit(0)

if __name__ == "__main__":
    main()
