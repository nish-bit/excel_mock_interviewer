import os
import sqlite3

# ✅ Path for DB file (matches backend main app)
backend_dir = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(backend_dir, "interviews.db")   # unified name

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Create tables
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        started_at INTEGER,
        finished_at INTEGER
    );

    CREATE TABLE IF NOT EXISTS interviews (
        id TEXT PRIMARY KEY,
        candidate_id INTEGER,
        status TEXT,
        current_question_idx INTEGER,
        created_at INTEGER,
        FOREIGN KEY(candidate_id) REFERENCES candidates(id)
    );

    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT,
        qtype TEXT,
        difficulty INTEGER,
        expected_answer TEXT,
        rubric TEXT
    );

    CREATE TABLE IF NOT EXISTS responses (
        id TEXT PRIMARY KEY,
        interview_id TEXT,
        question_id INTEGER,
        response_text TEXT,
        score REAL,
        evaluator_details TEXT,
        created_at INTEGER,
        FOREIGN KEY(interview_id) REFERENCES interviews(id),
        FOREIGN KEY(question_id) REFERENCES questions(id)
    );

    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        interview_id TEXT,
        summary_text TEXT,
        strengths TEXT,
        weaknesses TEXT,
        overall_score REAL
    );
    """)

    conn.commit()

    # Seed questions if empty
    cur.execute("SELECT COUNT(1) FROM questions")
    if cur.fetchone()[0] == 0:
        qs = [
            # Existing 20
            {"text":"Explain the difference between relative and absolute cell references in Excel.","qtype":"explain","difficulty":1,"expected_answer":"Relative changes on copy; absolute uses $ to fix row/column."},
            {"text":"Write a formula to sum values in column B for rows where column A equals 'India'.","qtype":"formula","difficulty":1,"expected_answer":"=SUMIFS(B:B, A:A, \"India\")"},
            {"text":"When would you use VLOOKUP and when INDEX-MATCH?","qtype":"explain","difficulty":2,"expected_answer":"INDEX-MATCH is more flexible, can lookup leftwards, more stable to column insertions."},
            {"text":"How do you remove duplicate rows in Excel?","qtype":"explain","difficulty":1,"expected_answer":"Use Remove Duplicates in Data tab or use UNIQUE function in Excel 365."},
            {"text":"Write a formula to count distinct values in range A2:A100 (Excel 365).","qtype":"formula","difficulty":2,"expected_answer":"=COUNTA(UNIQUE(A2:A100))"},
            {"text":"Explain what a pivot table is and a scenario where you'd use it.","qtype":"explain","difficulty":1,"expected_answer":"Pivot tables aggregate and summarize data e.g., sales by region/month."},
            {"text":"Write a formula using INDEX-MATCH to find the price in column C where product ID in column A equals 123.","qtype":"formula","difficulty":2,"expected_answer":"=INDEX(C:C, MATCH(123, A:A, 0))"},
            {"text":"Describe how you would handle missing data in a sales dataset.","qtype":"explain","difficulty":2,"expected_answer":"Identify NA, impute or exclude depending on context, use filters or IFERROR."},
            {"text":"How to use SUMPRODUCT to compute weighted average? Provide formula.","qtype":"formula","difficulty":3,"expected_answer":"=SUMPRODUCT(values, weights)/SUM(weights)"},
            {"text":"Explain conditional formatting and a use-case.","qtype":"explain","difficulty":1,"expected_answer":"Formatting rules applied to cells based on criteria, e.g., highlight overdue tasks."},
            {"text":"Given a table, how would you pivot it to show monthly totals? (Describe steps)","qtype":"task","difficulty":2,"expected_answer":"Insert > PivotTable, drag date to rows (group by month), values to sum."},
            {"text":"How would you protect sensitive cells while allowing others to edit?","qtype":"explain","difficulty":2,"expected_answer":"Use cell lock + protect sheet with password, unlock editable ranges."},
            {"text":"Write an array formula to multiply two ranges and sum the result (pre-365).","qtype":"formula","difficulty":3,"expected_answer":"=SUM(A2:A10*B2:B10) entered as CSE (legacy)"},
            {"text":"Explain XLOOKUP and its advantages over VLOOKUP.","qtype":"explain","difficulty":2,"expected_answer":"XLOOKUP is more flexible, supports default values, returns arrays, not limited to left lookup."},
            {"text":"How do you create a dynamic named range using OFFSET? Provide example.","qtype":"explain","difficulty":3,"expected_answer":"=OFFSET($A$1,0,0,COUNTA($A:$A),1)"},
            {"text":"Describe how to audit formulas and find precedents/dependents.","qtype":"explain","difficulty":2,"expected_answer":"Use Formula Auditing toolbar: Trace Precedents/Dependents, Evaluate Formula."},
            {"text":"Write a formula to extract year from a date in cell A2.","qtype":"formula","difficulty":1,"expected_answer":"=YEAR(A2)"},
            {"text":"Explain how to use TEXTJOIN to combine values with a delimiter.","qtype":"explain","difficulty":2,"expected_answer":"TEXTJOIN(delimiter, ignore_empty, range)"},
            {"text":"Given a CSV upload, how would you validate that required columns 'Date','Amount','Category' exist?","qtype":"task","difficulty":2,"expected_answer":"Use pandas to check set inclusion and report missing columns."},
            {"text":"Explain how to optimize large workbooks for performance.","qtype":"explain","difficulty":3,"expected_answer":"Avoid volatile formulas, minimize volatile functions, use efficient ranges, use Power Query/Power Pivot."},

            # 🔹 Extra 10 Advanced Questions
            {"text":"What is the difference between COUNT, COUNTA, COUNTBLANK, and COUNTIF?","qtype":"explain","difficulty":2,"expected_answer":"COUNT numbers, COUNTA counts non-empty, COUNTBLANK counts blanks, COUNTIF applies condition."},
            {"text":"Write a formula to return the nth largest value in range A1:A50.","qtype":"formula","difficulty":2,"expected_answer":"=LARGE(A1:A50, n)"},
            {"text":"Explain the purpose of the INDIRECT function with an example.","qtype":"explain","difficulty":3,"expected_answer":"INDIRECT builds a cell reference from text, e.g., =SUM(INDIRECT(\"A\"&1:10))."},
            {"text":"How would you highlight the top 10% of scores in a dataset?","qtype":"task","difficulty":2,"expected_answer":"Use Conditional Formatting > Top/Bottom Rules > Top 10%."},
            {"text":"Write a formula that extracts the first name from 'John Smith' in A2.","qtype":"formula","difficulty":2,"expected_answer":"=LEFT(A2,SEARCH(\" \",A2)-1)"},
            {"text":"What is Power Query used for in Excel?","qtype":"explain","difficulty":3,"expected_answer":"Power Query is used to clean, transform, and load data from multiple sources."},
            {"text":"How do you create a data validation drop-down list in Excel?","qtype":"task","difficulty":1,"expected_answer":"Use Data > Data Validation > List and select the range."},
            {"text":"Explain difference between workbook protection and worksheet protection.","qtype":"explain","difficulty":2,"expected_answer":"Workbook protects structure, worksheet protects cell contents and formatting."},
            {"text":"Write a formula to calculate compound annual growth rate (CAGR).","qtype":"formula","difficulty":3,"expected_answer":"=(End/Start)^(1/Periods)-1"},
            {"text":"Explain how to use dynamic array functions like FILTER in Excel 365.","qtype":"explain","difficulty":3,"expected_answer":"FILTER(range, condition) returns matching rows dynamically without helper columns."},
        ]

        for q in qs:
            cur.execute(
                "INSERT INTO questions (text,qtype,difficulty,expected_answer,rubric) VALUES (?,?,?,?,?)",
                (q['text'], q['qtype'], q['difficulty'], q['expected_answer'], q.get('rubric',''))
            )
        conn.commit()

    conn.close()

if __name__ == '__main__':
    init_db()
    print('✅ DB initialized at', DB)
