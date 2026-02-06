import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import traceback

# ========================= CONFIG =========================
SUPABASE_DB_URL = "postgresql://postgres.pejsmevqeopxyvwddsdy:sakpal123412@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"

# IMPORTANT: Update this path to match your local file location
# For local testing, use absolute path like: "C:/Users/YourName/Downloads/Indo-HateSpeech_NoNormal.csv"
CSV_FILE_PATH = "Indo-HateSpeech_NoNormal (1).csv"  # Update this!

Base = declarative_base()

# ========================= MODELS =========================
class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    text = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    platform = Column(String, nullable=False, default="Reddit")
    status = Column(String, default="pending")
    timestamp = Column(DateTime, default=datetime.utcnow)

class ClassificationProgress(Base):
    __tablename__ = "classification_progress"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    current_row = Column(BigInteger, nullable=False, default=0)
    total_processed = Column(BigInteger, default=0)
    total_skipped = Column(BigInteger, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)

# ========================= DATABASE SETUP =========================
@st.cache_resource
def get_db_engine():
    """Create database engine with connection pooling"""
    return create_engine(
        SUPABASE_DB_URL,
        pool_pre_ping=True,  # Check connection before using
        pool_recycle=3600,   # Recycle connections after 1 hour
        echo=False           # Set to True for SQL debugging
    )

def init_tables():
    """Create tables if they don't exist"""
    try:
        engine = get_db_engine()
        Base.metadata.create_all(bind=engine)
        st.success("✅ Database tables initialized")
    except Exception as e:
        st.error(f"❌ Error initializing tables: {e}")
        st.stop()

def get_session():
    """Get a new database session"""
    engine = get_db_engine()
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    return Session()

# ========================= DATA FUNCTIONS =========================
@st.cache_data
def load_csv():
    """Load CSV file with error handling"""
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        st.success(f"✅ Loaded CSV: {len(df)} rows")
        return df
    except FileNotFoundError:
        st.error(f"❌ CSV file not found at: {CSV_FILE_PATH}")
        st.info("📝 Please update CSV_FILE_PATH in the code to match your file location")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error loading CSV: {e}")
        st.stop()

def get_progress():
    """Get current progress from database with proper error handling"""
    session = get_session()
    try:
        progress = session.query(ClassificationProgress).first()
        if not progress:
            # Create initial progress record
            progress = ClassificationProgress(
                current_row=0,
                total_processed=0,
                total_skipped=0,
                last_updated=datetime.utcnow()
            )
            session.add(progress)
            session.commit()
            session.refresh(progress)
            st.info("📊 Created new progress tracker")
        return progress
    except SQLAlchemyError as e:
        st.error(f"❌ Database error getting progress: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def update_progress(current_row, increment_processed=False, increment_skipped=False):
    """Update progress in database with proper transaction handling"""
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
           
            # Explicitly commit the transaction
            session.commit()
           
            # Debug logging
            st.sidebar.info(f"✅ Progress updated: Row {current_row}")
            return True
        else:
            st.error("❌ No progress record found")
            return False
    except SQLAlchemyError as e:
        st.error(f"❌ Database error updating progress: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def save_classification(text, category):
    """Save classification to database with proper error handling"""
    session = get_session()
    try:
        # Check if already exists (optional - remove if you want duplicates)
        # existing = session.query(Submission).filter_by(text=text).first()
        # if existing:
        #     st.warning("⚠️ This text was already classified")
       
        submission = Submission(
            text=text,
            category=category,
            platform="Reddit",
            status="pending",
            timestamp=datetime.utcnow()
        )
        session.add(submission)
        session.commit()
        session.refresh(submission)
       
        # Debug logging
        st.sidebar.success(f"✅ Saved to DB: ID {submission.id}")
        return True
       
    except SQLAlchemyError as e:
        st.error(f"❌ Database error saving classification: {e}")
        st.error(f"Full error: {traceback.format_exc()}")
        session.rollback()
        return False
    finally:
        session.close()

def get_statistics():
    """Get classification statistics with error handling"""
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
    except SQLAlchemyError as e:
        st.error(f"❌ Error getting statistics: {e}")
        return {}, None
    finally:
        session.close()

# ========================= STREAMLIT APP =========================
def main():
    st.set_page_config(
        page_title="Text Classification Tool",
        layout="wide",
        initial_sidebar_state="expanded"
    )
   
    st.title("🔍 Manual Text Classification Platform")
    st.markdown("---")
   
    # Initialize tables
    with st.spinner("Initializing database..."):
        init_tables()
   
    # Load data
    with st.spinner("Loading CSV file..."):
        df = load_csv()
   
    total_rows = len(df)
   
    # Get current progress
    progress = get_progress()
    current_row = progress.current_row
   
    # Debug info in expander
    with st.expander("🔧 Debug Info"):
        st.write(f"Current Row Index: {current_row}")
        st.write(f"Total Rows: {total_rows}")
        st.write(f"CSV File: {CSV_FILE_PATH}")
        st.write(f"Database: Connected")
   
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
            st.metric("Completed", prog.total_processed if prog else 0)
        with col3:
            st.metric("Skipped", prog.total_skipped if prog else 0)
       
        st.subheader("Category Distribution")
        for category, count in stats.items():
            st.write(f"**{category.replace('_', '/').title()}**: {count}")
       
        if st.button("🔄 Reset Progress (Start Over)"):
            session = get_session()
            try:
                prog = session.query(ClassificationProgress).first()
                if prog:
                    prog.current_row = 0
                    prog.total_processed = 0
                    prog.total_skipped = 0
                    prog.last_updated = datetime.utcnow()
                    session.commit()
                    st.success("✅ Progress reset!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error resetting: {e}")
                session.rollback()
            finally:
                session.close()
       
        return
   
    # Get current row data
    try:
        row_data = df.iloc[current_row]
        text = str(row_data.get('text', ''))
        original_label = str(row_data.get('label', 'N/A'))
    except Exception as e:
        st.error(f"❌ Error reading row {current_row}: {e}")
        st.stop()
   
    # Display statistics in sidebar
    with st.sidebar:
        st.header("📊 Statistics")
       
        stats, prog = get_statistics()
       
        st.metric("Total Rows", total_rows)
        st.metric("Current Row", current_row + 1)
        st.metric("Remaining", total_rows - current_row)
        st.metric("Completed", prog.total_processed if prog else 0)
        st.metric("Skipped", prog.total_skipped if prog else 0)
       
        # Progress bar
        progress_pct = (current_row / total_rows) * 100
        st.progress(progress_pct / 100)
        st.write(f"**{progress_pct:.1f}%** Complete")
       
        st.markdown("---")
        st.subheader("Category Counts")
        for category in ['religion', 'gender', 'language_caste', 'normal']:
            count = stats.get(category, 0)
            st.write(f"**{category.replace('_', '/').title()}**: {count}")
       
        # Manual navigation (for debugging)
        st.markdown("---")
        st.subheader("🔧 Manual Controls")
        jump_to = st.number_input("Jump to row:", min_value=0, max_value=total_rows-1, value=current_row)
        if st.button("Go"):
            update_progress(jump_to)
            st.rerun()
   
    # Main content area
    col1, col2 = st.columns([3, 1])
   
    with col1:
        st.subheader(f"Row {current_row + 1} of {total_rows}")
       
        # Show original label as hint
        label_color = "blue" if original_label != "N/A" else "red"
        st.info(f"**Original Label (from CSV)**: `{original_label}`")
       
        # Display text in a large text area
        st.text_area(
            "Text to Classify:",
            value=text,
            height=250,
            disabled=True,
            key=f"text_display_{current_row}"  # Unique key per row
        )
   
    with col2:
        st.subheader("Actions")
        st.write("Select category:")
   
    # Classification buttons
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
   
    with col1:
        if st.button("🕌 Religion", use_container_width=True, type="primary", key="btn_religion"):
            with st.spinner("Saving..."):
                if save_classification(text, "religion"):
                    if update_progress(current_row + 1, increment_processed=True):
                        st.success("✅ Saved as Religion!")
                        # Force cache clear
                        st.cache_data.clear()
                        # Small delay before rerun
                        import time
                        time.sleep(0.5)
                        st.rerun()
   
    with col2:
        if st.button("👤 Gender", use_container_width=True, type="primary", key="btn_gender"):
            with st.spinner("Saving..."):
                if save_classification(text, "gender"):
                    if update_progress(current_row + 1, increment_processed=True):
                        st.success("✅ Saved as Gender!")
                        st.cache_data.clear()
                        import time
                        time.sleep(0.5)
                        st.rerun()
   
    with col3:
        if st.button("🗣️ Language/Caste", use_container_width=True, type="primary", key="btn_lang"):
            with st.spinner("Saving..."):
                if save_classification(text, "language_caste"):
                    if update_progress(current_row + 1, increment_processed=True):
                        st.success("✅ Saved as Language/Caste!")
                        st.cache_data.clear()
                        import time
                        time.sleep(0.5)
                        st.rerun()
   
    with col4:
        if st.button("✅ Normal", use_container_width=True, type="primary", key="btn_normal"):
            with st.spinner("Saving..."):
                if save_classification(text, "normal"):
                    if update_progress(current_row + 1, increment_processed=True):
                        st.success("✅ Saved as Normal!")
                        st.cache_data.clear()
                        import time
                        time.sleep(0.5)
                        st.rerun()
   
    with col5:
        if st.button("🗑️ Delete/Skip", use_container_width=True, type="secondary", key="btn_skip"):
            with st.spinner("Skipping..."):
                if update_progress(current_row + 1, increment_skipped=True):
                    st.warning("⚠️ Row skipped!")
                    st.cache_data.clear()
                    import time
                    time.sleep(0.5)
                    st.rerun()
   
    # Keyboard shortcuts hint
    st.markdown("---")
    st.caption("💡 Tip: Click a button to classify. Progress saves automatically to Supabase.")
    st.caption("🔄 If stuck, use 'Manual Controls' in sidebar to jump to specific row.")

if __name__ == "__main__":
    main()
