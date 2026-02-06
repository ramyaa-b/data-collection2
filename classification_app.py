import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

# ========================= CONFIG =========================
SUPABASE_DB_URL = "postgresql://postgres.pejsmevqeopxyvwddsdy:sakpal123412@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
CSV_FILE_PATH = "Indo-HateSpeech_NoNormal (1).csv"

Base = declarative_base()

# ========================= MODELS =========================
class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    platform = Column(String, nullable=False, default="Reddit")
    status = Column(String, default="pending")
    timestamp = Column(DateTime, default=datetime.utcnow)

class ClassificationProgress(Base):
    __tablename__ = "classification_progress"
    id = Column(Integer, primary_key=True, index=True)
    current_row = Column(BigInteger, nullable=False, default=0)
    total_processed = Column(BigInteger, default=0)
    total_skipped = Column(BigInteger, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)

# ========================= DATABASE SETUP =========================
@st.cache_resource
def get_db_engine():
    return create_engine(SUPABASE_DB_URL)

def init_tables():
    """Create tables if they don't exist"""
    engine = get_db_engine()
    Base.metadata.create_all(bind=engine)

def get_session():
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    return Session()

# ========================= DATA FUNCTIONS =========================
@st.cache_data
def load_csv():
    """Load CSV file"""
    df = pd.read_csv(CSV_FILE_PATH)
    return df

def get_progress():
    """Get current progress from database"""
    session = get_session()
    try:
        progress = session.query(ClassificationProgress).first()
        if not progress:
            # Create initial progress record
            progress = ClassificationProgress(current_row=0, total_processed=0, total_skipped=0)
            session.add(progress)
            session.commit()
            session.refresh(progress)
        return progress
    finally:
        session.close()

def update_progress(current_row, increment_processed=False, increment_skipped=False):
    """Update progress in database"""
    session = get_session()
    try:
        progress = session.query(ClassificationProgress).first()
        if progress:
            progress.current_row = current_row
            if increment_processed:
                progress.total_processed += 1
            if increment_skipped:
                progress.total_skipped += 1
            progress.last_updated = datetime.utcnow()
            session.commit()
    finally:
        session.close()

def save_classification(text, category):
    """Save classification to database"""
    session = get_session()
    try:
        submission = Submission(
            text=text,
            category=category,
            platform="Reddit",
            status="pending",
            timestamp=datetime.utcnow()
        )
        session.add(submission)
        session.commit()
        return True
    except Exception as e:
        st.error(f"Error saving to database: {e}")
        return False
    finally:
        session.close()

def get_statistics():
    """Get classification statistics"""
    session = get_session()
    try:
        from sqlalchemy import func
        
        # Count by category
        category_counts = session.query(
            Submission.category,
            func.count(Submission.id)
        ).group_by(Submission.category).all()
        
        stats = {cat: count for cat, count in category_counts}
        
        # Get progress
        progress = session.query(ClassificationProgress).first()
        
        return stats, progress
    finally:
        session.close()

# ========================= STREAMLIT APP =========================
def main():
    st.set_page_config(page_title="Text Classification Tool", layout="wide")
    
    st.title("🔍 Manual Text Classification Platform")
    st.markdown("---")
    
    # Initialize tables
    init_tables()
    
    # Load data
    df = load_csv()
    total_rows = len(df)
    
    # Get current progress
    progress = get_progress()
    current_row = progress.current_row
    
    # Check if all rows are processed
    if current_row >= total_rows:
        st.success("🎉 All rows have been processed!")
        st.balloons()
        
        # Show final statistics
        stats, prog = get_statistics()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", total_rows)
        with col2:
            st.metric("Completed", prog.total_processed)
        with col3:
            st.metric("Skipped", prog.total_skipped)
        
        st.subheader("Category Distribution")
        for category, count in stats.items():
            st.write(f"**{category.title()}**: {count}")
        
        if st.button("🔄 Reset Progress (Start Over)"):
            update_progress(0, increment_processed=False, increment_skipped=False)
            # Reset counters
            session = get_session()
            try:
                prog = session.query(ClassificationProgress).first()
                prog.total_processed = 0
                prog.total_skipped = 0
                session.commit()
            finally:
                session.close()
            st.rerun()
        
        return
    
    # Get current row data
    row_data = df.iloc[current_row]
    text = str(row_data.get('text', ''))
    original_label = str(row_data.get('label', 'N/A'))
    
    # Display statistics in sidebar
    with st.sidebar:
        st.header("📊 Statistics")
        
        stats, prog = get_statistics()
        
        st.metric("Total Rows", total_rows)
        st.metric("Current Row", current_row + 1)
        st.metric("Remaining", total_rows - current_row)
        st.metric("Completed", prog.total_processed)
        st.metric("Skipped", prog.total_skipped)
        
        # Progress bar
        progress_pct = (current_row / total_rows) * 100
        st.progress(progress_pct / 100)
        st.write(f"**{progress_pct:.1f}%** Complete")
        
        st.markdown("---")
        st.subheader("Category Counts")
        for category in ['religion', 'gender', 'language_caste', 'normal']:
            count = stats.get(category, 0)
            st.write(f"**{category.replace('_', '/').title()}**: {count}")
    
    # Main content area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"Row {current_row + 1} of {total_rows}")
        
        # Show original label as hint
        st.info(f"**Original Label (from CSV)**: `{original_label}`")
        
        # Display text in a large text area
        st.text_area(
            "Text to Classify:",
            value=text,
            height=200,
            disabled=True,
            key="text_display"
        )
    
    with col2:
        st.subheader("Actions")
        st.write("Select category:")
    
    # Classification buttons
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("🕌 Religion", use_container_width=True, type="primary"):
            if save_classification(text, "religion"):
                update_progress(current_row + 1, increment_processed=True)
                st.success("Saved as Religion!")
                st.rerun()
    
    with col2:
        if st.button("👤 Gender", use_container_width=True, type="primary"):
            if save_classification(text, "gender"):
                update_progress(current_row + 1, increment_processed=True)
                st.success("Saved as Gender!")
                st.rerun()
    
    with col3:
        if st.button("🗣️ Language/Caste", use_container_width=True, type="primary"):
            if save_classification(text, "language_caste"):
                update_progress(current_row + 1, increment_processed=True)
                st.success("Saved as Language/Caste!")
                st.rerun()
    
    with col4:
        if st.button("✅ Normal", use_container_width=True, type="primary"):
            if save_classification(text, "normal"):
                update_progress(current_row + 1, increment_processed=True)
                st.success("Saved as Normal!")
                st.rerun()
    
    with col5:
        if st.button("🗑️ Delete/Skip", use_container_width=True, type="secondary"):
            update_progress(current_row + 1, increment_skipped=True)
            st.warning("Row skipped!")
            st.rerun()
    
    # Keyboard shortcuts hint
    st.markdown("---")
    st.caption("💡 Tip: Use buttons to classify text. Progress is automatically saved after each action.")

if __name__ == "__main__":
    main()
