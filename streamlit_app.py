import streamlit as st
import requests
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Excel Mock Interviewer PoC", layout="centered")

# ✅ Use Render backend instead of localhost
API = "https://excel-mock-interviewer-4.onrender.com"

st.title("📝 Excel Mock Interviewer — PoC")


# ✅ Function to generate PDF using ReportLab
def generate_pdf(report_data, interview_id):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Excel Mock Interview Report")

    c.setFont("Helvetica", 11)
    c.drawString(50, height - 80, f"Interview ID: {interview_id}")
    c.drawString(50, height - 100, f"Overall Score: {report_data.get('overall', 'N/A')}")

    y = height - 130
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Summary: {report_data.get('summary_text', 'N/A')}")
    y -= 20
    c.drawString(50, y, f"Strengths: {report_data.get('strengths', 'N/A')}")
    y -= 20
    c.drawString(50, y, f"Weaknesses: {report_data.get('weaknesses', 'N/A')}")
    y -= 40

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Detailed Question-wise Report:")
    y -= 20

    qa_data = report_data.get("questions", [])
    c.setFont("Helvetica", 9)
    for idx, qa in enumerate(qa_data, 1):
        text_lines = [
            f"Q{idx}. {qa.get('question', 'N/A')}",
            f"Your Answer: {qa.get('your_answer', 'N/A')}",
            f"Correct Answer: {qa.get('correct_answer', 'N/A')}",
            f"Score: {qa.get('score', 'N/A')}"
        ]
        for line in text_lines:
            c.drawString(60, y, line)
            y -= 14
            if y < 80:  # New page if space is low
                c.showPage()
                c.setFont("Helvetica", 9)
                y = height - 80
        y -= 10

    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# --- Start Interview ---
if 'interview_id' not in st.session_state:
    name = st.text_input('Your Name')
    email = st.text_input('Email')
    college = st.text_input('College Name')
    course = st.text_input('Course')

    if st.button('Start Interview'):
        if not name or not email or not college or not course:
            st.error("⚠️ Please fill in all fields before starting the interview.")
        else:
            try:
                payload = {
                    'candidate_name': name,
                    'candidate_email': email,
                    'college_name': college,
                    'course': course
                }
                r = requests.post(API + '/interviews', json=payload, timeout=10)
                if r.ok:
                    st.session_state['interview_id'] = r.json().get('interview_id')
                    st.session_state['q_idx'] = 0
                    st.session_state['current_answer'] = ""
                    st.rerun()
                else:
                    st.error('❌ Could not start interview: ' + r.text)
            except Exception as e:
                st.error(f"Connection failed: {e}")


# --- Interview Questions ---
if 'interview_id' in st.session_state:
    st.markdown('**Interview ID:** ' + st.session_state['interview_id'])
    idx = st.session_state.get('q_idx', 0)

    try:
        r = requests.get(API + f'/questions/{idx}', timeout=10)
        r.raise_for_status()
        q = r.json()
    except Exception as e:
        st.error(f"Could not fetch question: {e}")
        st.stop()

    st.subheader(f"Q{idx+1}. {q['text']}")

    # Keep answer text in session state
    if "current_answer" not in st.session_state:
        st.session_state.current_answer = ""

    ans = st.text_area(
        'Your answer',
        value=st.session_state.current_answer,
        height=120,
        key=f"answer_{idx}"
    )

    # --- Submit Answer ---
    if st.button('Submit Answer'):
        if not ans.strip():
            st.warning("⚠️ Please provide an answer.")
        else:
            try:
                payload = {
                    'interview_id': st.session_state['interview_id'],
                    'question_id': q['id'],
                    'response_text': ans
                }
                r = requests.post(API + '/responses', data=payload, timeout=10)
                if r.ok:
                    res = r.json()
                    st.success(f"✅ Score: {res.get('score')}")
                    st.json(res.get('evaluator'))
                    st.session_state['q_idx'] = idx + 1
                    # ✅ Clear previous answer
                    st.session_state.current_answer = ""
                    st.rerun()
                else:
                    st.error('❌ Error: ' + r.text)
            except Exception as e:
                st.error(f"Submission failed: {e}")

    # --- Download Q&A PDF anytime ---
    if st.button("📥 Download Q&A Report"):
        try:
            report_resp = requests.get(
                API + f'/final_report/{st.session_state["interview_id"]}', timeout=30
            )
            if report_resp.ok:
                report_data = report_resp.json()
                pdf_bytes = generate_pdf(report_data, st.session_state["interview_id"])
                file_name = f'qa_report_{st.session_state["interview_id"]}.pdf'
                st.download_button(
                    label="⬇️ Download Questions & Answers PDF",
                    data=pdf_bytes,
                    file_name=file_name,
                    mime="application/pdf"
                )
            else:
                st.error("❌ Could not fetch report for PDF.")
        except Exception as e:
            st.error(f"Download failed: {e}")

    # --- Finish Interview (show feedback + generate/download PDF) ---
    if st.button("Finish Interview"):
        try:
            report_resp = requests.get(
                API + f'/final_report/{st.session_state["interview_id"]}', timeout=30
            )
            if report_resp.ok:
                report_data = report_resp.json()
                pdf_bytes = generate_pdf(report_data, st.session_state["interview_id"])
                file_name = f'final_report_{st.session_state["interview_id"]}.pdf'
                st.download_button(
                    label="⬇️ Download Final Report (PDF)",
                    data=pdf_bytes,
                    file_name=file_name,
                    mime="application/pdf"
                )
                st.subheader("📊 Feedback Summary")
                st.write("**Summary:**", report_data.get("summary_text", "N/A"))
                st.write("**Strengths:**", report_data.get("strengths", "N/A"))
                st.write("**Weaknesses:**", report_data.get("weaknesses", "N/A"))
                st.metric("Overall Score", report_data.get("overall", "N/A"))
                st.success("✅ Interview finished. Report generated successfully.")
                st.balloons()
            else:
                st.warning("⚠️ Could not fetch final report.")
        except Exception as e:
            st.error(f"Report fetch error: {e}")

        # ✅ Reset session after finishing
        for key in ["interview_id", "q_idx", "current_answer"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


